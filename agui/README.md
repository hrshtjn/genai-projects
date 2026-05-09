# AG-UI Chat POC

A full-stack chat application demonstrating the **AG-UI protocol** connecting a React frontend to a **Google ADK** agent backend via the **CopilotKit Runtime**.

```
┌─────────────────┐     AG-UI / SSE      ┌──────────────────┐     AG-UI / SSE     ┌──────────────────┐
│  React Frontend │ ──────────────────► │ CopilotKit       │ ──────────────────► │ Python ADK Agent │
│  (Vite + CK UI) │ ◄────────────────── │ Runtime (Express)│ ◄────────────────── │  (FastAPI)       │
└─────────────────┘                      └──────────────────┘                      └──────────────────┘
  localhost:5173                           localhost:3001                             localhost:8000
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + CopilotKit UI |
| Runtime proxy | Node.js + Express + `@copilotkit/runtime` |
| Agent | Python + Google ADK + `ag-ui-adk` + FastAPI |
| Protocol | [AG-UI](https://ag-ui.com/) (Server-Sent Events) |

## Prerequisites

- Node.js 20+
- Python 3.12+
- A [Google Gemini API key](https://makersuite.google.com/app/apikey)

## Quick Start

### 1. Install dependencies

```bash
# Node packages (runtime + frontend)
npm install          # installs concurrently in root
npm run install:all  # installs runtime and frontend node_modules

# Python packages (uses uv or pip)
cd agent
pip install -e .
# OR with uv:
# uv pip install -e .
cd ..
```

### 2. Configure environment variables

```bash
# Agent
cp agent/.env.example agent/.env
# Edit agent/.env and set GOOGLE_API_KEY=<your key>

# Runtime (optional – defaults are fine for local dev)
cp runtime/.env.example runtime/.env
```

### 3. Run everything

```bash
npm run dev
```

This starts all three servers concurrently:

| Server | URL | Description |
|--------|-----|-------------|
| Python agent | http://localhost:8000 | Google ADK + AG-UI endpoint |
| CopilotKit Runtime | http://localhost:3001 | Node.js proxy / runtime |
| React frontend | http://localhost:5173 | Chat UI |

Open **http://localhost:5173** and start chatting!

## Running Servers Individually

```bash
# Agent only
npm run dev:agent

# Runtime only
npm run dev:runtime

# Frontend only
npm run dev:frontend
```

## Project Structure

```
agui-poc/
├── agent/                  # Python ADK agent (FastAPI)
│   ├── main.py             # Agent definition + FastAPI app
│   ├── pyproject.toml      # Python dependencies
│   └── .env.example
├── runtime/                # CopilotKit Runtime (Express)
│   ├── src/
│   │   └── server.ts       # Runtime server + HttpAgent config
│   ├── package.json
│   └── .env.example
├── frontend/               # React + CopilotKit UI (Vite)
│   ├── src/
│   │   ├── App.tsx         # CopilotKit provider + CopilotChat
│   │   ├── main.tsx
│   │   └── index.css
│   ├── index.html
│   ├── vite.config.ts      # Dev proxy /copilotkit → runtime
│   └── package.json
├── package.json            # Root – concurrently dev script
└── README.md
```

## How It Works

1. The **React frontend** wraps the app in `<CopilotKit runtimeUrl="/copilotkit" agent="my_agent">` and renders `<CopilotChat>`.
2. Vite proxies `/copilotkit` requests to the **CopilotKit Runtime** on port 3001.
3. The **Runtime** registers an `HttpAgent` pointing at the Python agent on port 8000, then forwards AG-UI events over SSE.
4. The **Python agent** uses `ag-ui-adk` to wrap a Google ADK `LlmAgent` and expose it at `POST /` as an AG-UI SSE endpoint.

## Extending the Agent

Edit `agent/main.py` to:

- Change the Gemini model (e.g. `gemini-2.5-flash`)
- Add tools via ADK's `tools=[...]` parameter
- Add human-in-the-loop with `before_model_callback`
- Implement shared state with `ToolContext`

See [Google ADK docs](https://google.github.io/adk-docs/) and [CopilotKit ADK docs](https://docs.copilotkit.ai/adk) for details.
