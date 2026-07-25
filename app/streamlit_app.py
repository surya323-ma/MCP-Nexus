import streamlit as st
from agent import run_agent_sync

st.set_page_config(page_title="MCP AI Assistant", page_icon="🤖", layout="wide")

if "history" not in st.session_state:
    st.session_state.history = []          # [{role, content}, ...]
if "activity_log" not in st.session_state:
    st.session_state.activity_log = []     # [{tool_calls, elapsed_seconds}, ...]
if "available_tools" not in st.session_state:
    st.session_state.available_tools = []

chat_col, dash_col = st.columns([2, 1])

# ---------------------------------------------------------------- Chat panel
with chat_col:
    st.title("🤖 MCP AI Assistant")
    st.caption("FastMCP servers + LangGraph ReAct agent + OpenAI + Tavily")

    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input(
        "Ask me anything — I can search the web or manage files..."
    )

    if user_input:
        st.session_state.history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    result = run_agent_sync(
                        user_input, st.session_state.history[:-1]
                    )
                    response_text = result["response"]
                    st.session_state.activity_log.insert(0, result)
                    st.session_state.available_tools = result["available_tools"]
                except Exception as e:
                    response_text = f"⚠️ Error: {e}"
            st.markdown(response_text)

        st.session_state.history.append(
            {"role": "assistant", "content": response_text}
        )

# ------------------------------------------------------------- Dashboard tab
with dash_col:
    st.header("📊 Dashboard")

    st.subheader("Connected MCP Tools")
    if st.session_state.available_tools:
        for name in st.session_state.available_tools:
            st.markdown(f"- `{name}`")
    else:
        st.caption("Tools will appear here after the first message.")

    st.subheader("Session Stats")
    total_turns = len(
        [m for m in st.session_state.history if m["role"] == "user"]
    )
    total_tool_calls = sum(
        len(entry["tool_calls"]) for entry in st.session_state.activity_log
    )
    avg_latency = (
        round(
            sum(e["elapsed_seconds"] for e in st.session_state.activity_log)
            / len(st.session_state.activity_log),
            2,
        )
        if st.session_state.activity_log
        else 0
    )
    m1, m2, m3 = st.columns(3)
    m1.metric("Turns", total_turns)
    m2.metric("Tool calls", total_tool_calls)
    m3.metric("Avg latency (s)", avg_latency)

    st.subheader("Recent Tool Activity")
    if not st.session_state.activity_log:
        st.caption("No tool calls yet.")
    for entry in st.session_state.activity_log[:5]:
        with st.expander(
            f"{len(entry['tool_calls'])} tool call(s) · {entry['elapsed_seconds']}s"
        ):
            if not entry["tool_calls"]:
                st.caption("Model answered directly, no tool was needed.")
            for tc in entry["tool_calls"]:
                st.markdown(f"**{tc['tool']}**")
                st.code(tc["output"], language="text")

    st.divider()
    if st.button("🗑️ Clear conversation"):
        st.session_state.history = []
        st.session_state.activity_log = []
        st.rerun()
