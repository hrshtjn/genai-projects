"""ADK Learning — 05: Memory with VertexAiMemoryBankService.

USE CASE:
Same personal assistant as basic_agent_01, but with PERSISTENT memory
backed by Vertex AI Memory Bank (managed by Agent Engine).

With InMemoryMemoryService (basic_agent_01):
- Memory lives only while the server is running
- Stop the server → memory is gone

With VertexAiMemoryBankService (this agent):
- Memory is stored in Vertex AI Memory Bank (cloud storage)
- Stop the server, restart it → memory is still there
- Extracts meaningful information from conversations (LLM-powered)
- Advanced semantic search (not just keyword matching)
- Production-ready for real applications

SETUP (one-time):
Before running this agent, you need to create an Agent Engine instance.
Run the setup script:

python 05_memory/basic_agent_03/create_agent_engine.py

This will print an Agent Engine ID like:
1234567890

Copy that value and paste it into the AGENT_ENGINE_ID variable below.

HOW TO RUN:
adk web 05_memory/basic_agent_03 --memory_service_uri="agentengine://YOUR_AGENT_ENGINE_ID"

The memory service is passed via the CLI flag — no code changes needed.

HOW TO TEST:
1. Open http://127.0.0.1:8000
2. Send: "My name is Harshit and I am a data engineer."
3. Send: "I love hiking and Python."
4. STOP the server (Ctrl+C)
5. RESTART: adk web 05_memory/basic_agent_03
6. Create a new session, then ask: "What is my name?"
→ Agent recalls "Harshit" from Memory Bank — memory survived!

COMPARISON:
| Feature | basic_agent_01 (InMemory) | basic_agent_03 (MemoryBank) |
|-----------------------|---------------------------|------------------------------|
| Survives restart? | ❌ No | ✅ Yes |
| Cloud storage? | ❌ In-process only | ✅ Vertex AI Memory Bank |
| Memory extraction | Stores full conversation | Extracts meaningful memories |
| Search | Basic keyword matching | Advanced semantic search |
| Setup needed? | None | Create Agent Engine instance |
| Cost? | Free | Vertex AI pricing |
| Production-ready? | ❌ Dev/testing only | ✅ Yes |
"""

from google.adk.agents import LlmAgent
from google.adk.tools import load_memory

# NOTE: VertexAiMemoryBankService is NOT instantiated here.
# It is provided by adk web via the --memory_service_uri CLI flag:
#
# adk web 05_memory/basic_agent_03 --memory_service_uri="agentengine://YOUR_AGENT_ENGINE_ID"
#
# The agent.py only defines the agent — the Runner (managed by adk web)
# wires in the memory service automatically.


async def auto_save_to_memory(callback_context):
    """After each agent turn, save the session to Memory Bank.

    This is the same callback as basic_agent_01, but now the
    memory_service writes to Vertex AI Memory Bank instead of in-memory.

    Memory Bank uses an LLM to EXTRACT meaningful information from the
    conversation — it doesn't just store raw text. This means it builds
    consolidated, evolving memories from your conversations.
    """
    mem_svc = callback_context._invocation_context.memory_service
    if mem_svc is not None:
        session = callback_context._invocation_context.session
        await mem_svc.add_session_to_memory(session)


root_agent = LlmAgent(
    name="PersistentMemoryAgent",
    model="gemini-2.5-flash",
    instruction=(
        "You are a personal assistant with persistent long-term memory. "
        "You remember things the user has told you in past conversations, "
        "even if the server was restarted in between. "
        "When the user asks about something from a previous conversation, "
        "use the load_memory tool to search your memory. "
        "When the user shares new information, acknowledge it — it will be "
        "automatically saved to your persistent memory. "
        "Always mention when you recall something from a past conversation."
    ),
    tools=[load_memory],
    after_agent_callback=auto_save_to_memory,
)
