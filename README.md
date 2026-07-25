# MCP AI Assistant — FastMCP + LangGraph + Streamlit

An AI assistant that discovers and uses tools through **Anthropic's Model
Context Protocol (MCP)** instead of hardcoded API integrations. Two
standalone **FastMCP** servers expose tools (file operations, Tavily web
search) over HTTP; a **LangGraph** ReAct agent connects to both at runtime,
pulls in whatever tools they advertise, and reasons over them; a
**Streamlit** app provides the chat UI plus a small live dashboard.

## Architecture

```
┌─────────────────────┐      MCP / streamable-http      ┌──────────────────────┐
│  file_server/        │◄────────────────────────────────►│                      │
│  FastMCP server       │                                  │  app/                 │
│  (list/read/write/    │                                  │  LangGraph ReAct agent│
│   delete file)        │                                  │  + Streamlit chat UI  │
└─────────────────────┘      MCP / streamable-http      │  + activity dashboard  │
┌─────────────────────┐◄────────────────────────────────►│                      │
│  search_server/       │                                  └──────────┬───────────┘
│  FastMCP server       │                                             │
│  (Tavily web_search)  │                                             ▼
└─────────────────────┘                                       OpenAI (gpt-4o-mini)
```

Each MCP server is a separate deployable process. The agent never imports
their code directly — it calls `MultiServerMCPClient.get_tools()`, which
asks each server over the network what tools it exposes and wraps them as
LangChain tools. Add a third MCP server later and the agent picks it up
with zero code changes, which is the whole point of the protocol.

## Project layout

```
mcp_assistant_project/
├── file_server/        FastMCP server: list_files, read_file, write_file, delete_file
├── search_server/       FastMCP server: web_search (Tavily)
├── app/                 LangGraph agent (agent.py) + Streamlit UI (streamlit_app.py)
├── render.yaml           Render blueprint deploying all 3 services
└── .env.example          Environment variable template
```

## Prerequisites

- Python 3.11+
- An OpenAI API key
- A Tavily API key (free tier at tavily.com)

## Run locally

Open three terminals from the project root.

**1. File server**
```bash
cd file_server
pip install -r requirements.txt
python server.py            # listens on http://localhost:8000/mcp
```

**2. Search server**
```bash
cd search_server
pip install -r requirements.txt
export TAVILY_API_KEY=tvly-...
python server.py            # listens on http://localhost:8001/mcp
```

**3. Streamlit app**
```bash
cd app
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
export FILE_SERVER_URL=http://localhost:8000/mcp
export SEARCH_SERVER_URL=http://localhost:8001/mcp
streamlit run streamlit_app.py
```

Open the URL Streamlit prints (usually http://localhost:8501). Try:
- "Search the web for the latest news on MCP and summarize it"
- "Write a file called notes.txt with a haiku about protocols, then read it back"

The right-hand dashboard shows which tools were called, how long each turn
took, and the full list of tools currently discovered from both MCP servers.

## Deploy on Render

The included `render.yaml` is a Render **Blueprint** that provisions all
three services in one shot.

1. Push this project to a GitHub repo.
2. In the Render dashboard: **New → Blueprint**, point it at the repo.
   Render reads `render.yaml` and creates three web services:
   `mcp-file-server`, `mcp-search-server`, `mcp-ai-assistant`.
3. Render will prompt for the `sync: false` secrets during setup — set:
   - `mcp-search-server` → `TAVILY_API_KEY`
   - `mcp-ai-assistant` → `OPENAI_API_KEY`
4. After the first deploy, copy the two backend URLs from the Render
   dashboard (each service card shows something like
   `https://mcp-file-server.onrender.com`) and set on `mcp-ai-assistant`:
   - `FILE_SERVER_URL = https://mcp-file-server.onrender.com/mcp`
   - `SEARCH_SERVER_URL = https://mcp-search-server.onrender.com/mcp`
5. Redeploy `mcp-ai-assistant`. Open its URL — that's your live dashboard.

Notes for the free Render plan:
- Free web services spin down after inactivity, so the first message after
  idle time may take ~30–60s while both MCP servers wake up.
- `file_server`'s workspace (`/tmp/mcp_files`) is ephemeral on free plan
  restarts — fine for a demo, but attach a persistent disk if you need
  files to survive restarts.

## Extending it

To add another tool server (e.g. a calendar or database MCP server):
1. Write a new FastMCP server exposing `@mcp.tool()` functions.
2. Deploy it (Render web service or any host).
3. Add one entry to the `connections` dict in `app/agent.py`.

No other code changes needed — that's the protocol doing its job.
