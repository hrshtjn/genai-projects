# AG-UI Overview

AG-UI is the communication protocol between the frontend and the agent backend.

## 1. Python agent → ag-ui-adk (`main.py`)

```python
adk_agent = ADKAgent(adk_agent=root_agent, ...)
add_adk_fastapi_endpoint(app, adk_agent, path="/")
```

`ag-ui-adk` wraps the Google ADK agent and **translates ADK events into AG-UI events** — things like `RUN_STARTED`, `TEXT_MESSAGE_CONTENT` (each token), `TOOL_CALL_START`, `STATE_SNAPSHOT`, and `RUN_FINISHED` — streamed as SSE.

## 2. Runtime → @ag-ui/client (`server.ts`)

```ts
my_agent: new HttpAgent({ url: "http://localhost:8000/" })
```

`HttpAgent` from `@ag-ui/client` **speaks the AG-UI protocol** to the Python server — it sends run requests and reads back the SSE event stream.

## 3. Frontend → CopilotKit (`App.tsx`)

```tsx
<CopilotKit runtimeUrl="/copilotkit" agent="my_agent">
  <CopilotChat />
</CopilotKit>
```

CopilotKit is built on top of AG-UI on the frontend. `CopilotChat` subscribes to the AG-UI event stream and reacts to each event type — rendering tokens as they stream, showing tool call progress, syncing shared state, and more.

## End-to-End Flow

```text
User types → CopilotChat → Runtime → HttpAgent → Python agent
                                                       ↓
                      AG-UI SSE events:

                      RUN_STARTED

                      TEXT_MESSAGE_CONTENT (×N tokens)

                      RUN_FINISHED

                                                       ↓
CopilotChat renders ← Runtime forwards ← HttpAgent reads SSE
```

```text
POST / (from HttpAgent in runtime)
        ↓
  ADKAgent.run()
        ↓
  Google ADK executes root_agent (calls Gemini)
        ↓
  ADK fires internal ADK events:
    - LlmRequest started
    - Each token from Gemini
    - Tool call invoked
    - Tool result returned
    - Invocation complete
        ↓
  ag-ui-adk translates each ADK event into an AG-UI event and streams it as SSE:
```

## The AG-UI Events Your Agent Emits

| ADK internal event | AG-UI event emitted |
|---|---|
| Run begins | `RUN_STARTED` |
| First token from Gemini | `TEXT_MESSAGE_START` |
| Each subsequent token | `TEXT_MESSAGE_CONTENT` |
| Gemini finishes responding | `TEXT_MESSAGE_END` |
| Agent calls a tool | `TOOL_CALL_START` + `TOOL_CALL_ARGS` |
| Tool returns result | `TOOL_CALL_END` |
| Agent state changes | `STATE_SNAPSHOT` |
| Run completes | `RUN_FINISHED` |
| Error occurs | `RUN_ERROR` |

`add_adk_fastapi_endpoint` registers a single `POST /` route. When called, `ADKAgent` runs the ADK agent, intercepts every ADK internal event via callbacks, converts it to the AG-UI event schema, and writes it to the SSE response stream — one `data: {...}\n\n` chunk per event.

The `HttpAgent` in the runtime reads this stream and forwards the events to the frontend, where `CopilotChat` renders them in real time.

## Relative Runtime URL

In `App.tsx`, `<CopilotKit runtimeUrl="/copilotkit">` is a relative URL. The browser resolves it against the current page origin (`http://localhost:5173`), so requests go to `http://localhost:5173/copilotkit`.

## Why the Vite Proxy Is Needed

Vite's dev server has a built-in HTTP proxy. When you configure it, any request matching a path prefix gets forwarded to a different host — transparently, from the browser's perspective.

**Why it's needed here:**
Browsers block cross-origin requests (CORS). If the frontend (`localhost:5173`) called the runtime (`localhost:3001`) directly, it would be a cross-origin request. With the proxy, the browser only ever talks to `localhost:5173` — Vite silently forwards it server-side, where CORS doesn't apply.

```text
Browser thinks it's talking to:   localhost:5173/copilotkit
Vite actually forwards it to:     localhost:3001/copilotkit
```

**It only exists in development.** In production, Vite is not involved — you'd configure the same forwarding in nginx, a load balancer, or your cloud gateway. That's also why `runtimeUrl` is set to a relative path (`"/copilotkit"`) rather than hardcoding `localhost:3001` — the relative URL works unchanged in both dev (via Vite proxy) and production (via a real reverse proxy).

## Vite Proxy Config

```ts
"/copilotkit": {
  target: "http://localhost:3001",
}
```
