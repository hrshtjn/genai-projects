"""
ADK Learning — 06: Context Compaction (Compression)
====================================================
PROBLEM:
  As a conversation gets longer, the context grows with EVERY turn:
    Turn 1:  instructions + Q1 + A1
    Turn 5:  instructions + Q1 + A1 + Q2 + A2 + Q3 + A3 + Q4 + A4 + Q5 + A5
    Turn 20: instructions + ALL 20 Q&As... HUGE context!

  This causes:
  - Slower responses (more tokens to process)
  - Higher costs (pay per token)
  - Eventually hitting the model's context window limit

SOLUTION — Context Compaction:
  Periodically summarize older conversation history so the context stays small.
  Instead of sending ALL past events, ADK:
  1. Keeps recent events as-is (they're still relevant)
  2. Summarizes older events into a compact summary
  3. Sends: summary + recent events + new message

  Think of it like:
    Without compaction:  Turn1 + Turn2 + Turn3 + Turn4 + Turn5 + Turn6 + new
    With compaction:     [Summary of T1-T3] + Turn4 + Turn5 + Turn6 + new

HOW IT WORKS (Sliding Window):
  Configure two settings:
  - compaction_interval: How many turns before triggering a summary
  - overlap_size: How many of the last summarized turns to include in the
                  next window (for continuity)

  Example with interval=3, overlap=1:
    After Turn 3:  Summarize turns 1-3
    After Turn 6:  Summarize turns 3-6 (overlap: turn 3 is included again)
    After Turn 9:  Summarize turns 6-9 (overlap: turn 6 is included again)

IMPORTANT:
  - Configured on the `App` object (like context caching)
  - The agent doesn't know compaction is happening — it's transparent
  - Uses an LLM to generate summaries (you can customize which model)
  - The overlap ensures no context is lost at summary boundaries

HOW TO RUN:
  python 06_context/context_compaction/agent.py

  This sends 9 messages and shows how compaction summarizes older turns.
"""

import asyncio
import time
from google.adk.agents import LlmAgent
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai.types import Content, Part


# ─── Agent definition (same as any agent — compaction is transparent) ──
root_agent = LlmAgent(
    name="StorytellerAgent",
    model="gemini-2.5-flash",
    instruction=(
        "You are a collaborative storyteller. The user gives you story elements "
        "(characters, settings, plot twists) and you weave them into an ongoing "
        "story. Keep track of ALL characters and plot points mentioned so far. "
        "Each response should continue the story, not restart it. "
        "Keep responses to 2-3 sentences to make the demo readable."
    ),
)

# ─── App with context compaction enabled ──────────────────────────
# This is where compaction is configured — NOT on the agent.
app = App(
    name="storyteller_app",
    root_agent=root_agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,  # Summarize every 3 turns
        overlap_size=1,         # Include 1 turn from previous window for continuity
    ),
)


# ─── Demo: show compaction in action ──────────────────────────────
async def main():
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="storyteller_app",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="storyteller_app",
        user_id="learner",
        session_id="compaction_demo",
    )

    # 9 story prompts — compaction triggers after turns 3, 6, and 9
    story_prompts = [
        # Window 1: Turns 1-3 → summarized after turn 3
        "Start a story about a detective named Luna who lives in a floating city.",
        "Introduce her robot sidekick named Bolt who is afraid of heights.",
        "Luna discovers a mysterious letter under her door with a riddle.",

        # Window 2: Turns 4-6 → summarized after turn 6 (includes turn 3 overlap)
        "The riddle leads them to an ancient library in the lower decks.",
        "In the library, they find a map to a hidden island below the clouds.",
        "A rival detective named Shadow appears and tries to steal the map.",

        # Window 3: Turns 7-9 → summarized after turn 9 (includes turn 6 overlap)
        "Luna and Bolt escape on a sky-glider, but Bolt is terrified.",
        "They crash-land on the hidden island and discover it's full of talking animals.",
        "The animals reveal that Shadow is actually Luna's long-lost sister.",
    ]

    print("=" * 60)
    print("CONTEXT COMPACTION DEMO")
    print("=" * 60)
    print()
    print("Compaction interval: 3 turns  |  Overlap: 1 turn")
    print("After turns 3, 6, 9 — older history is summarized.")
    print()

    for i, prompt in enumerate(story_prompts, 1):
        msg = Content(parts=[Part(text=prompt)], role="user")
        start = time.time()

        final_text = "(No response)"
        async for event in runner.run_async(
            user_id="learner",
            session_id="compaction_demo",
            new_message=msg,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text

        elapsed = time.time() - start

        # Show when compaction triggers
        compaction_note = ""
        if i % 3 == 0:
            compaction_note = "  ← COMPACTION TRIGGERED (older turns summarized)"

        print(f"--- Turn {i} ({elapsed:.2f}s){compaction_note} ---")
        print(f"You: {prompt}")
        print(f"Agent: {final_text[:300]}")
        print()

    # Check session events to see compaction in action
    updated_session = await session_service.get_session(
        app_name="storyteller_app",
        user_id="learner",
        session_id="compaction_demo",
    )
    print("=" * 60)
    print(f"Total events in session: {len(updated_session.events)}")
    print()
    print("WITHOUT compaction, you'd have 18+ events (9 user + 9 agent).")
    print("WITH compaction, older events are replaced by summaries,")
    print("keeping the context window small even after many turns.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
