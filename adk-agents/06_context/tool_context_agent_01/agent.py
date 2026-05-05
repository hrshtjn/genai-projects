"""ADK Learning — Tool Context.
The ToolContext in ADK provides crucial context specifically targeted at tools during execution. Instead of managing the entire invocation complexity (InvocationContext), it gives tools specific capabilities and read/write state access.

Here's an overview of how ToolContext is primarily used:

Managing State: Tools can share data between them using tool_context.state. This modifies session state dynamically across tool calls (e.g. tool_context.state['user:pref'] = 'dark_mode').
Handling Artifacts: Tools can load or save large blob references (like documents or data logs) using tool_context.load_artifact() or tool_context.save_artifact().
Authentication: If a tool needs API credentials, it can pause execution and request credentials via tool_context.request_credential(auth_config).
Memory Service: Tools can query the memory service via tool_context.search_memory("query").

This agent demonstrates how to use `ToolContext` in ADK to maintain state and share data between tools.

HOW TO RUN:
adk web 06_context/tool_context_agent_01

WHAT THIS AGENT DOES:
It provides two tools:
1. `set_user_preference`: A tool that saves a user preference (e.g. name, theme) into the tool_context state.
2. `get_user_preference`: A tool that retrieves a saved preference from the tool_context state.

SUGGESTED TEST MESSAGES:
1. "Set my theme to dark_mode"
2. "What is my current theme?"
"""

from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext

# ═══════════════════════════════════════════════════════════════
# TOOLS
# ═══════════════════════════════════════════════════════════════

def set_user_preference(tool_context: ToolContext, key: str, value: str) -> dict:
    """Save a user preference to the session state."""
    # Prefix state keys to organize them
    state_key = f"user:{key}"
    tool_context.state[state_key] = value
    print(f"[set_user_preference] Set preference '{key}' to '{value}'")
    return {"status": "Preference completely updated"}


def get_user_preference(tool_context: ToolContext, key: str) -> dict:
    """Retrieve a user preference from the session state."""
    state_key = f"user:{key}"
    value = tool_context.state.get(state_key)
    
    if value is None:
        print(f"[get_user_preference] Preference '{key}' not found.")
        return {"error": f"Preference '{key}' not found"}
        
    print(f"[get_user_preference] Retrieved preference '{key}': '{value}'")
    return {"preference": key, "value": value}


# ═══════════════════════════════════════════════════════════════
# AGENT DEFINITION
# ═══════════════════════════════════════════════════════════════
root_agent = LlmAgent(
    name="ToolContextDemo",
    model="gemini-2.5-flash",
    instruction=(
        "You are a helpful assistant that can remember user preferences. "
        "Use the set_user_preference tool to remember things the user tells you about themselves or their preferences. "
        "Use the get_user_preference tool to recall things they have previously asked you to remember. "
        "If a preference is not found, politely tell the user."
    ),
    tools=[set_user_preference, get_user_preference],
)
