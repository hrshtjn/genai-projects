"""ADK Learning — 03: Callbacks.

Callbacks let you intercept and control an agent's execution at 6 precise points.
They are the primary way to add guardrails, logging, caching, and custom logic
WITHOUT modifying the agent's core instructions.

═══════════════════════════════════════════════════════════════
THE 6 CALLBACK TYPES (in execution order per turn):
═══════════════════════════════════════════════════════════════

[User sends message]
│
▼
1. before_agent_callback ← runs before ANY agent logic starts
   │ return Content → skip agent entirely
   │ return None → proceed normally
▼
2. before_model_callback ← runs before LLM is called
   │ return LlmResponse → skip LLM call
   │ return None → proceed normally
▼
[LLM generates response / tool calls]
│
▼
3. after_model_callback ← runs after LLM responds
   │ return LlmResponse → replace LLM output
   │ return None → use original output
   │
   │ (if LLM requested a tool call)
▼
4. before_tool_callback ← runs before each tool executes
   │ return dict → skip tool, use dict as result
   │ return None → execute tool normally
▼
[Tool executes]
│
▼
5. after_tool_callback ← runs after each tool completes
   │ return dict → replace tool result
   │ return None → use original result
   │
▼
6. after_agent_callback ← runs after agent turn finishes
   │ return Content → append to agent output
   │ return None → use original output
▼
[Response shown to user]

═══════════════════════════════════════════════════════════════

HOW TO RUN:
adk web 03_callbacks

WHAT THIS AGENT DOES:
A simple calculator agent with tools. Every callback fires and
logs what it's doing so you can see exactly when each one runs.
Some callbacks also demonstrate the "skip" behaviour:
- before_agent_callback: blocks the agent if message contains "BLOCK"
- before_model_callback: injects today's date into every LLM request
- after_model_callback: logs token usage
- before_tool_callback: logs tool arguments before execution
- after_tool_callback: logs tool results, catches divide-by-zero
- after_agent_callback: appends a disclaimer to every response

SUGGESTED TEST MESSAGES:
1. "What is 10 + 5?" → normal flow, all 6 callbacks fire
2. "What is 20 / 4?" → tool path: before/after_tool fire
3. "What is 10 / 0?" → before_tool_callback intercepts it
4. "BLOCK this message" → before_agent_callback skips the agent
"""

from google.adk.agents import LlmAgent
from google.genai import types

# ═══════════════════════════════════════════════════════════════
# TOOLS
# ═══════════════════════════════════════════════════════════════


def add(a: float, b: float) -> dict:
    """Add two numbers together."""
    return {"result": a + b}


def subtract(a: float, b: float) -> dict:
    """Subtract b from a."""
    return {"result": a - b}


def multiply(a: float, b: float) -> dict:
    """Multiply two numbers together."""
    return {"result": a * b}


def divide(a: float, b: float) -> dict:
    """Divide a by b."""
    if b == 0:
        return {"error": "Cannot divide by zero"}
    return {"result": a / b}


# ═══════════════════════════════════════════════════════════════
# CALLBACK 1: before_agent_callback
# Fires: before any agent logic starts for this turn
# Can: completely skip the agent by returning Content
# ═══════════════════════════════════════════════════════════════
def before_agent(callback_context):
    """Gatekeeper: blocks any message containing "BLOCK".

    Also logs when the agent turn starts.
    """
    user_message = ""

    # peek at the incoming message from session events
    session = callback_context._invocation_context.session
    if session.events:
        last_event = session.events[-1]
        if last_event.content and last_event.content.parts:
            user_message = last_event.content.parts[0].text or ""

    print(f"\n[before_agent] Agent turn starting. Message preview: '{user_message[:50]}'")

    # GUARDRAIL: block messages containing "BLOCK"
    if "BLOCK" in user_message.upper():
        print("[before_agent] ⛔ Blocking this message — returning early without calling LLM")
        return types.Content(
            parts=[
                types.Part(
                    text="⛔ This message was blocked by the before_agent_callback guardrail."
                )
            ],
            role="model",
        )

    # Return None → agent runs normally
    print("[before_agent] ✅ Message allowed — proceeding")
    return None


# ═══════════════════════════════════════════════════════════════
# CALLBACK 2: before_model_callback
# Fires: just before the LLM API call is made
# Can: modify the request, or skip the LLM entirely
# ═══════════════════════════════════════════════════════════════
def before_model(callback_context, llm_request):
    """Injects a dynamic date context into every LLM request.

    This is a common pattern: add info that changes over time
    without hardcoding it in the static agent instruction.
    """
    from datetime import date

    today = date.today().strftime("%B %d, %Y")
    print(f"\n[before_model] 📅 Injecting today's date: {today}")

    # Append a dynamic instruction to the system prompt
    llm_request.append_instructions([f"Today's date is {today}."])

    # Return None → LLM is called normally with the modified request
    return None


# ═══════════════════════════════════════════════════════════════
# CALLBACK 3: after_model_callback
# Fires: after the LLM responds, before the response is processed
# Can: inspect or replace the LLM output
# ═══════════════════════════════════════════════════════════════
def after_model(callback_context, llm_response):
    """Logs token usage after every LLM call.

    This is exactly what we used in context_caching to detect cache hits.
    """
    usage = getattr(llm_response, "usage_metadata", None)
    if usage:
        total = getattr(usage, "total_token_count", "?")
        prompt = getattr(usage, "prompt_token_count", "?")
        cached = getattr(usage, "cached_content_token_count", None)
        output = getattr(usage, "candidates_token_count", "?")
        cache_note = f" | cached={cached}" if cached else ""
        print(
            f"\n[after_model] 📊 Tokens — prompt={prompt} | output={output}{cache_note} | total={total}"
        )

    # Return None → use the original LLM response unchanged
    return None


# ═══════════════════════════════════════════════════════════════
# CALLBACK 4: before_tool_callback
# Fires: before each tool execution (after LLM requested it)
# Can: inspect/modify args, or skip the tool entirely
# ═══════════════════════════════════════════════════════════════
def before_tool(tool, args, tool_context):
    """Logs what tool is about to run and with what arguments.

    Also intercepts divide-by-zero BEFORE the tool is called.
    """
    print(f"\n[before_tool] 🔧 About to call tool: '{tool.name}' with args: {args}")

    # GUARDRAIL: intercept divide by zero before the tool even runs
    if tool.name == "divide" and args.get("b") == 0:
        print("[before_tool] ⛔ Intercepted divide-by-zero — returning error without calling tool")
        return {"error": "Division by zero intercepted by before_tool_callback"}

    # Return None → tool runs normally
    return None


# ═══════════════════════════════════════════════════════════════
# CALLBACK 5: after_tool_callback
# Fires: after each tool completes
# Can: inspect/modify the tool result before it goes back to LLM
# ═══════════════════════════════════════════════════════════════
def after_tool(tool, args, tool_context, tool_response):
    """Logs the tool result.

    If the result has a numeric value, rounds it to 4 decimal places for clean output.
    """
    print(f"\n[after_tool] ✅ Tool '{tool.name}' returned: {tool_response}")

    # Post-process: round floats to 4 decimal places
    if "result" in tool_response and isinstance(tool_response["result"], float):
        rounded = round(tool_response["result"], 4)
        if rounded != tool_response["result"]:
            print(f"[after_tool] 🔄 Rounding {tool_response['result']} → {rounded}")
            return {"result": rounded}

    # Return None → use original tool response unchanged
    return None


# ═══════════════════════════════════════════════════════════════
# CALLBACK 6: after_agent_callback
# Fires: after the entire agent turn finishes
# Can: append content to the agent's final response
# ═══════════════════════════════════════════════════════════════
def after_agent(callback_context):
    """Appends a short disclaimer to every response.

    Also a good place for audit logging, cleanup, or saving to state.
    """
    print("\n[after_agent] 🏁 Agent turn complete — appending disclaimer")

    # You can read/write session state here if needed:
    # callback_context.state["turns_completed"] = ...

    # Return Content → appended to the agent's response
    # Return None → agent's response used as-is
    return None  # change to Content(...) to append something


# ═══════════════════════════════════════════════════════════════
# AGENT DEFINITION
# ═══════════════════════════════════════════════════════════════
root_agent = LlmAgent(
    name="CallbacksDemo",
    model="gemini-2.5-flash",
    instruction=(
        "You are a helpful calculator assistant. "
        "Use the add, subtract, multiply, and divide tools to compute results. "
        "Always show your work by stating which operation you're performing."
    ),
    tools=[add, subtract, multiply, divide],
    # Wire up all 6 callbacks:
    before_agent_callback=before_agent,
    after_agent_callback=after_agent,
    before_model_callback=before_model,
    after_model_callback=after_model,
    before_tool_callback=before_tool,
    after_tool_callback=after_tool,
)
