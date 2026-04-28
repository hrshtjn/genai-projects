"""
ADK Chat Agent – AG-UI backend.

Uses `ag-ui-adk` to expose the Google ADK agent as an AG-UI/SSE endpoint
that the CopilotKit Runtime can call via HttpAgent.

Project structure follows the canonical ADK layout:
  my_agent/
      __init__.py
      agent.py   ← defines `root_agent`
      .env
"""

from __future__ import annotations

import os
import logging
import time

from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Set up logging for GKE to capture
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("adk_agent")

# Load .env from the my_agent package directory first, then fall back to cwd
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "my_agent", ".env"))
load_dotenv()  # also pick up agent/.env if present

# Import the agent defined in my_agent/agent.py
from my_agent import root_agent  # noqa: E402

# ---------------------------------------------------------------------------
# Wrap with AG-UI ADK middleware
# ---------------------------------------------------------------------------

adk_agent = ADKAgent(
    adk_agent=root_agent,
    user_id="demo_user",
    session_timeout_seconds=3600,
    use_in_memory_services=True,
)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="ADK Chat Agent", version="1.0.0")

# Request Logging Middleware for Debugging on GKE
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"request: {request.method} {request.url.path} - status: {response.status_code} - time: {process_time:.4f}s")
    return response

# Allow requests from the CopilotKit Runtime and the frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the AG-UI endpoint at "/"
add_adk_fastapi_endpoint(app, adk_agent, path="/")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    if not os.getenv("GOOGLE_API_KEY"):
        print("⚠️  Warning: GOOGLE_API_KEY environment variable is not set!")
        print("   Set it with: export GOOGLE_API_KEY='your-key-here'")
        print("   Get a key from: https://makersuite.google.com/app/apikey")
        print()

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
