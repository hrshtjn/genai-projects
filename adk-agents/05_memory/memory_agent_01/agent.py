"""ADK Learning — 05: Memory (Long-Term Knowledge).

USE CASE:
A personal assistant that remembers things across DIFFERENT sessions.

- Session state lives only during ONE conversation.
- Memory persists across ALL conversations for the same user.

Example: You tell the agent your name in Session 1. You close it.
You open Session 2 and ask "what is my name?" — the agent recalls
it from memory (not session state, which is blank in a new session).

HOW TO RUN:

Option A — adk web (recommended, use InMemoryMemoryService):
adk web 05_memory --memory_service_uri=inmemory://

Option B — adk run (no memory support, agent will work but won't recall):
adk run 05_memory

HOW TO TEST MEMORY (with adk web):
1. Open http://127.0.0.1:8000 in browser
2. Send: "My name is Harshit and I work as a data engineer."
3. Send: "I love Python and I am learning ADK."
4. Create a NEW SESSION (click + button in the web UI)
5. Send: "What is my name?"
→ The agent uses load_memory to recall from the previous session.
6. Send: "What am I learning?"
→ Agent recalls "ADK" from the first session's memory.

TWO BUILT-IN MEMORY TOOLS:
load_memory → agent DECIDES when to search past conversations
PreloadMemoryTool → ALWAYS loads relevant memory at start of every turn

This agent uses BOTH:
- PreloadMemoryTool preloads context automatically
- load_memory is available if the agent wants to search explicitly

It also uses an after_agent_callback to AUTOMATICALLY save every
conversation turn to memory — so you don't need to call
add_session_to_memory manually.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import load_memory
from google.adk.tools.preload_memory_tool import PreloadMemoryTool


async def auto_save_to_memory(callback_context):
    """After each agent turn, automatically save the session to memory.

    This means everything said in this session becomes searchable
    in future sessions — no manual add_session_to_memory() needed.
    """
    memory_service = callback_context._invocation_context.memory_service
    if memory_service is not None:
        session = callback_context._invocation_context.session
        await memory_service.add_session_to_memory(session)


root_agent = LlmAgent(
    name="MemoryAgent",
    model="gemini-2.5-flash",
    instruction=(
        "You are a personal assistant with long-term memory. "
        "You remember things the user has told you in past conversations. "
        "When the user asks about something from a previous conversation, "
        "check your memory using load_memory tool or the preloaded memory context. "
        "When the user shares new information, acknowledge it — it will be "
        "automatically saved to memory for future conversations. "
        "Always mention when you recall something from a past conversation."
    ),
    tools=[
        PreloadMemoryTool(),  # auto-loads relevant memory every turn
        # load_memory,  # agent can explicitly search memory
    ],
    after_agent_callback=auto_save_to_memory,
)
