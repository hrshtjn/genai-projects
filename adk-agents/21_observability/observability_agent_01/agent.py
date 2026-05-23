"""ADK Learning — 21: Observability and Logging.

USE CASE:
Tracking and understanding agent behavior, performance, and decisions.

When building production agents, you need visibility into:
1. What the LLM sees (prompts) and returns (responses)
2. Which tools are being called and with what arguments
3. How long different steps take (latency and bottlenecks)
4. Issues or errors during execution

This example uses ADK's Lifecycle Callbacks to implement custom
logging that intercepts and records intermediate agent execution steps
which are usually hidden from the user.

HOW TO RUN:
adk run 21_observability/observability_agent_01

HOW TO TEST:
1. Run the agent in the terminal.
2. Ask: "What is the weather in Tokyo?"
3. Watch the terminal output! You will see structured log messages
   printed BEFORE the tool is called, AFTER the tool returns,
   and AFTER the model generates a response.
   
This transparency is key for Observability in production.
"""

import logging
import time
from typing import Annotated
from opentelemetry import trace
from google.adk.agents import LlmAgent

# 1. Setup standard Python logging
# We configure this so our callback logs stand out in the terminal
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("adk_observability")


# A simple tool for the agent to call so we can track its execution
def get_weather(location: Annotated[str, "The city to check weather for"]) -> str:
    """Get the current weather for a specific location."""
    # Simulate a slow API call for our latency tracker
    time.sleep(1.2)
    return f"The weather in {location} is 72°F and sunny."


# 2. Define Custom Observability Callbacks

async def before_tool_logging(tool, args, tool_context):
    """Logs right before a tool is executed."""
    # We use the tool_context's state dictionary to store the start time.
    # This state persists throughout the current evaluation loop.
    tool_context.state["tool_start_time"] = time.time()
    
    msg = f"⏳ OBSERVABILITY: Tool '{tool.name}' execution started with args: {args}"
    logger.info(msg)
    
    # Attach this as an event to the current OpenTelemetry trace span!
    current_span = trace.get_current_span()
    current_span.add_event(msg)

async def after_tool_logging(tool, args, tool_context, tool_response):
    """Logs right after a tool completes, measuring latency."""
    # Retrieve the start time from before the tool ran
    start_time = tool_context.state.get("tool_start_time", time.time())
    duration = time.time() - start_time
    
    msg = f"✅ OBSERVABILITY: Tool '{tool.name}' execution finished in {duration:.3f} seconds."
    logger.info(msg)
    
    current_span = trace.get_current_span()
    current_span.add_event(msg)

async def after_model_logging(callback_context, llm_response):
    """Logs after the LLM generates a response."""
    # This helps track when the LLM finishes reasoning/generating
    # we can print the content, usage_metadata, or finish_reason from llm_response
    msg = f"🧠 OBSERVABILITY: Model finished generating a response. Content: {llm_response.content}"
    logger.info(msg)
    
    current_span = trace.get_current_span()
    current_span.add_event(msg)


# 3. Wire up the Agent with Callbacks and Tools
root_agent = LlmAgent(
    name="ObservabilityAgent",
    model="gemini-2.5-flash",
    instruction=(
        "You are a helpful assistant. Use the get_weather tool "
        "whenever the user asks about the weather."
    ),
    tools=[get_weather],
    # Hook our observability functions into the agent's lifecycle callbacks
    before_tool_callback=before_tool_logging,
    after_tool_callback=after_tool_logging,
    after_model_callback=after_model_logging
)
