"""
A2A Remote Agent - weather_agent
=================================

This agent is EXPOSED over the A2A protocol so that other agents can
call it across the network, as if it were a local sub-agent.

What this demonstrates:
-----------------------------------------------------------------------
| PATTERN: ADK agent -> 'A2A Server (exposing)
|
| Step 1: Build a normal LlmAgent with tools
| Step 2: Wrap it with to_a2a() -> creates a Starlette app
| Step 3: Serve it with uvicorn on port 8001
|
| to_a2a() auto-generates:
| • Agent card -> GET /.well-known/agent-card.json
| • A2A routes -> POST /
-----------------------------------------------------------------------

Tools:
• get_weather(city) - current conditions
• get_forecast(city, days) - N-day forecast

Run this server (from 18_a2a/ folder):
uvicorn weather_agent.agent:a2a_app --host localhost --port 8001

Verify the agent card:
curl http://localhost:8001/.well-known/agent-card.json
"""

from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a


# ------------------------------------------------------------------------------------------------------------------------------------
# Domain tools (plain Python functions - ADK wraps them automatically)
# ------------------------------------------------------------------------------------------------------------------------------------

def get_weather(city: str) -> dict:
    """Returns the current weather conditions for a given city.

    Args:
        city: Name of the city (case-insensitive).

    Returns:
        A dict with city, temperature_celsius, condition, and humidity_pct.
        Returns an error key if the city is not in the dataset.
    """
    data = {
        "london":         {"temperature_celsius": 12, "condition": "cloudy",         "humidity_pct": 78},
        "new_york":       {"temperature_celsius": 18, "condition": "sunny",          "humidity_pct": 55},
        "tokyo":          {"temperature_celsius": 22, "condition": "partly cloudy",  "humidity_pct": 65},
        "sydney":         {"temperature_celsius": 25, "condition": "sunny",          "humidity_pct": 50},
        "paris":          {"temperature_celsius": 14, "condition": "rainy",          "humidity_pct": 82},
        "dubai":          {"temperature_celsius": 38, "condition": "clear",          "humidity_pct": 35},
        "san_francisco":  {"temperature_celsius": 17, "condition": "foggy",          "humidity_pct": 87},
        "mumbai":         {"temperature_celsius": 32, "condition": "humid",          "humidity_pct": 88},
    }
    result = data.get(city.strip().lower())
    if result:
        return {"city": city, **result}
    return {"city": city, "error": f"No weather data available for '{city}'"}

def get_forecast(city: str, days: int = 3) -> dict:
    """Returns a simplified weather forecast for the next N days.

    Args:
        city: Name of the city.
        days: Number of forecast days (1-5). Defaults to 3.

    Returns:
        A dict with city and a list of daily forecast entries.
    """
    days = max(1, min(days, 5))  # clamp to 1-5

    # Fake forecast offsets - temperature fluctuates by ±2°C each day
    base = get_weather(city)

    if "error" in base:
        return base

    base_temp = base["temperature_celsius"]
    offsets = [0, +2, -1, +1, -2]
    conditions = ["sunny", "partly cloudy", "cloudy", "rainy", "sunny"]

    forecast = [
        {
            "day": i + 1,
            "temperature_celsius": base_temp + offsets[i],
            "condition": conditions[i],
        }
        for i in range(days)
    ]
    return {"city": city, "forecast_days": days, "forecast": forecast}

# --------------------------------------------------------------------------------------------------------------------------------------------
# The ADK agent
# --------------------------------------------------------------------------------------------------------------------------------------------

root_agent = LlmAgent(
    name="weather_agent",
    model="gemini-2.5-flash",
    description=(
        "A specialist weather agent that provides current conditions and "
        "multi-day forecasts for cities around the world."
    ),
    instruction=(
        "You are a professional meteorologist assistant. "
        "Use get_weather to answer questions about current conditions, "
        "and get_forecast to answer questions about upcoming weather. "
        "Always include the city name and key metrics (temperature, condition) "
        "in your response. Be concise."
    ),
    tools=[get_weather, get_forecast],
)

# --------------------------------------------------------------------------------------------------------------------------------------------
# Expose the agent over the A2A protocol
# --------------------------------------------------------------------------------------------------------------------------------------------
# to_a2a() wraps root_agent in a Starlette application that:
#   1. Auto-builds an agent card from the agent's metadata
#   2. Serves GET /.well-known/agent-card.json
#   3. Serves POST / for A2A JSON-RPC message exchange

# Serve it with:
#   uvicorn weather_agent.agent:a2a_app --host localhost --port 8001
# --------------------------------------------------------------------------------------------------------------------------------------------
a2a_app = to_a2a(root_agent, port=8001)