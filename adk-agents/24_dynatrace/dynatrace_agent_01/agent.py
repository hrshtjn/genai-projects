from google.adk.agents import Agent
from google.adk.agents import LlmAgent

# Ensure Dynatrace/Traceloop init runs even when ADK loads this file directly.
try:
    import dynatrace_agent_01  # noqa: F401
except Exception as exc:
    print(f"Dynatrace telemetry init import failed: {exc}")

# Define the root agent as required by ADK conventions
root_agent = LlmAgent(
    name="PersistentMemoryAgent",
    model="gemini-2.5-flash",
    instruction=(
        "You are a helpful assistant. "
    ),
    
)

