"""
FastMCP server exposing a web_search tool backed by Tavily.
Deployed as its own Render web service using the streamable-http transport.
"""
import os
from fastmcp import FastMCP
from tavily import TavilyClient

mcp = FastMCP("Web Search Server")

_tavily_client = None


def get_client() -> TavilyClient:
    global _tavily_client
    if _tavily_client is None:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY environment variable is not set.")
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> str:
    """Search the live web for up-to-date information on a topic.

    Args:
        query: The search query.
        max_results: Maximum number of results to return (default 5).
    """
    client = get_client()
    response = client.search(query=query, max_results=max_results)
    results = response.get("results", [])
    if not results:
        return "No results found."

    formatted = []
    for r in results:
        formatted.append(
            f"Title: {r.get('title')}\n"
            f"URL: {r.get('url')}\n"
            f"Content: {r.get('content')}"
        )
    return "\n\n---\n\n".join(formatted)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
