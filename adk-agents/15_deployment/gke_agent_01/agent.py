"""Deployment (Topic 15) — GKE Agent.

A simple ADK agent intentionally kept minimal so you can focus on the
deployment mechanics rather than agent complexity.

This agent answers questions about capital cities. It is the same example
used in the official ADK GKE deployment docs, so you can cross-reference
the two without confusion.

When deployed on GKE this agent:
- Runs as a FastAPI app (main.py wraps it via get_fast_api_app)
- Is containerised by the Dockerfile
- Exposes an HTTP API + optional web UI on port 8080
- Uses SQLite for sessions (fine for a single-replica learning deployment;
  swap to Cloud SQL / Firestore for production multi-replica setups)
"""

from google.adk.agents import LlmAgent


def get_capital_city(country: str) -> str:
    """Retrieves the capital city for a given country.

    Args:
        country: The name of the country (case-insensitive).

    Returns:
        The capital city, or a not-found message.
    """
    capitals = {
        "france": "Paris",
        "japan": "Tokyo",
        "canada": "Ottawa",
        "germany": "Berlin",
        "india": "New Delhi",
        "brazil": "Brasília",
        "australia": "Canberra",
        "usa": "Washington D.C.",
        "united states": "Washington D.C.",
        "uk": "London",
        "united kingdom": "London",
        "china": "Beijing",
        "russia": "Moscow",
    }
    result = capitals.get(country.lower())
    if result:
        return result
    return f"Sorry, I don't know the capital of {country}."


root_agent = LlmAgent(
    name="capital_agent",
    model="gemini-2.0-flash",
    description="Answers questions about the capital city of any country.",
    instruction=(
        "You are a helpful geography assistant. "
        "When a user asks about the capital of a country, "
        "use the get_capital_city tool to look it up. "
        "Be brief and friendly in your response."
    ),
    tools=[get_capital_city],
)
