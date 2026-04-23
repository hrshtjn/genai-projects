"""main.py — FastAPI entry point for GKE deployment.

When ADK runs on GKE (or Cloud Run), it is served as a regular FastAPI app.
`get_fast_api_app` wires up all the ADK REST endpoints automatically:

GET /list-apps → lists registered agents
POST /apps/{app}/users/{u}/sessions → create/get session
POST /run → run the agent (streaming)
GET /dev-ui/ → web UI (when web=True)

The agent directory is resolved from this file's location, so ADK
auto-discovers any subdirectories that contain an agent.py with root_agent.
"""

import os

import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

# Directory that contains the agent package folder(s).
# Because main.py lives in 15_deployment/, ADK will discover gke_agent_01/
# automatically by scanning for root_agent in subdirectories.
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# SQLite session store.
# - Use 'sqlite+aiosqlite' (async driver) — plain 'sqlite' will raise errors.
# - Fine for a single-replica GKE pod; for multi-replica use Cloud SQL/Spanner.
SESSION_SERVICE_URI = "sqlite+aiosqlite:///./sessions.db"

# CORS origins — allow all for a learning deployment.
# Tighten this in production to your actual frontend domain.
ALLOWED_ORIGINS = ["*"]

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri=SESSION_SERVICE_URI,
    allow_origins=ALLOWED_ORIGINS,
    web=True,  # serve the ADK dev UI at /dev-ui/
)

if __name__ == "__main__":
    # PORT env var is set by GKE/Cloud Run; default to 8080 locally.
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
