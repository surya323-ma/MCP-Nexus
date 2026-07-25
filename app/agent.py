"""
Builds a LangGraph ReAct agent whose tools are dynamically discovered from
two FastMCP servers (file operations + web search) via langchain-mcp-adapters.
This is the piece that shows MCP's real value: the agent never hardcodes
what tools exist, it asks each MCP server at startup.
"""
import os
import asyncio
import time

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

FILE_SERVER_URL = os.environ.get("FILE_SERVER_URL", "http://localhost:8000/mcp")
SEARCH_SERVER_URL = os.environ.get("SEARCH_SERVER_URL", "http://localhost:8001/mcp")

_agent = None
_tool_names_cache = None


async def _build_agent():
    global _agent, _tool_names_cache

    client = MultiServerMCPClient(
        {
            "file_ops": {
                "url": FILE_SERVER_URL,
                "transport": "streamable_http",
            },
            "web_search": {
                "url": SEARCH_SERVER_URL,
                "transport": "streamable_http",
            },
        }
    )

    tools = await client.get_tools()
    _tool_names_cache = [t.name for t in tools]

    llm = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.environ["OPENAI_API_KEY"],
        temperature=0,
    )

    _agent = create_react_agent(llm, tools)
    return _agent


async def _get_agent():
    if _agent is None:
        await _build_agent()
    return _agent


def _to_lc_messages(history: list) -> list:
    """Convert simple {role, content} dicts into LangChain message objects."""
    lc_messages = []
    for m in history:
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))
    return lc_messages


async def _run(message: str, history: list) -> dict:
    agent = await _get_agent()
    messages = _to_lc_messages(history) + [HumanMessage(content=message)]

    start = time.time()
    result = await agent.ainvoke({"messages": messages})
    elapsed = time.time() - start

    tool_calls = []
    for msg in result["messages"]:
        if isinstance(msg, ToolMessage):
            tool_calls.append({"tool": msg.name, "output": str(msg.content)[:400]})

    final_message = result["messages"][-1]
    return {
        "response": final_message.content,
        "tool_calls": tool_calls,
        "elapsed_seconds": round(elapsed, 2),
        "available_tools": _tool_names_cache or [],
    }


def run_agent_sync(message: str, history: list) -> dict:
    """Synchronous entrypoint for use inside Streamlit's sync execution model."""
    return asyncio.run(_run(message, history))
