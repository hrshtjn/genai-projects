"""
A2A Consuming Agent - root_agent_01
==================================

This agent CONSUMES the remote weather_agent over the A2A protocol.
From this agent's perspective, the remote agent looks just like a local agent.

What this demonstrates:
+-----------------------------------------------------------------------+
| PATTERN: RemoteA2aAgent (consuming)                                   |
|                                                                       |
| Step 1: Start the weather_agent A2A server on port 8001               |
| Step 2: Declare a RemoteA2aAgent pointing at its agent card           |
| Step 3: Add it as a sub_agent in root_agent                           |
|                                                                       |
| ADK handles all network communication (HTTP/JSON-RPC) and             |
| routes calls transparently - no manual HTTP code needed.              |
+-----------------------------------------------------------------------+

Architecture:
   User
    |  (adk web)
    ▼
   root_agent (local, this file)
    |  sub_agents=[weather_agent] (RemoteA2aAgent)
    |  A2A protocol over HTTP
    ▼
   weather_agent (remote, port 8001)
    ├── get_weather()
    └── get_forecast()

Prerequisites:
   1. Install the A2A extra if not already done:
      pip install google-adk[a2a]

   2. Start the remote agent server (in a separate terminal):
      cd /Users/harshitjain3/Documents/Learning/AI/adk2/18_a2a
      uvicorn weather_agent.agent:a2a_app --host localhost --port 8001

   3. Verify the server is up (agent card should return JSON):
      curl http://localhost:8001/.well-known/agent-card.json

   4. Run this consuming agent:
      cd /Users/harshitjain3/Documents/Learning/AI/adk2/18_a2a
      adk web root_agent_01

Try asking:
   "What's the weather like in Tokyo?"
   "Give me a 5-day forecast for Paris"
   "Is it raining in London?"
"""

# Correcting the apparent typo in the image from `agents.import` to `from ... import`
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

# --------------------------------------------------------------------------------------------------------------------
# RemoteA2aAgent: client-side proxy for the remote weather_agent
# --------------------------------------------------------------------------------------------------------------------
# agent_card: URL of the auto-generated agent card (served by to_a2a())
#   The card describes the remote agent's name, description, and skills.
#   ADK fetches this card at startup to understand what the remote agent does.
# --------------------------------------------------------------------------------------------------------------------
weather_agent = RemoteA2aAgent(
    name="weather_agent",
    description=(
        "A remote specialist agent for weather. "
        "Handles questions about current conditions and multi-day forecasts "
        "for cities around the world."
    ),
    agent_card="http://localhost:8001/.well-known/agent-card.json",
)

# --------------------------------------------------------------------------------------------------------------------------------------------
# Root agent: local orchestrator that delegates to the remote weather agent
# --------------------------------------------------------------------------------------------------------------------------------------------
root_agent = LlmAgent(
    name="root_agent",
    model="gemini-2.5-flash",
    description="Orchestrating agent that delegates weather tasks to a remote A2A weather specialist.",
    instruction=(
        "You are a helpful assistant. "
        "For any weather-related questions (current conditions, forecasts, temperature, rain, etc.), "
        "delegate to the weather_agent sub-agent – it is a remote specialist running as a separate service. "
        "For all other questions, answer them yourself directly."
    ),
    sub_agents=[weather_agent],
)