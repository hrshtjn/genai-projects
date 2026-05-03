"""
ADK Learning — 06: Context Caching
===================================
PROBLEM:
  Every time you send a message to an agent, ADK sends the FULL context
  (system instructions + conversation history + tool definitions) to the LLM.

  If your agent has long instructions or large static data, this means:
  - The same large text is sent with EVERY request
  - Each request is slower (more tokens to process)
  - Each request costs more (you pay per token)

SOLUTION — Context Caching:
  Cache the static parts (instructions, tool definitions) with the LLM
  so they don't need to be re-sent every time. The LLM reuses the cached
  content, making subsequent requests faster and cheaper.

HOW IT WORKS:
  1. First request: ADK sends everything to the LLM AND creates a cache
  2. Next requests: ADK sends only the new message + a cache reference
  3. The LLM reads the cached instructions/tools from its own cache

  Think of it like:
    Without caching:  📄📄📄📄📄 + 💬  → sent every time
    With caching:     🔗(cached) + 💬  → only new message sent

IMPORTANT:
  - Context caching is configured on the `App` object, NOT the agent
  - `adk run` does NOT support `App` — you must use `adk web`
  - Only works with models that support caching (Gemini 2.0+)
  - Cache has a TTL (time-to-live) — expires after a set time

CONFIGURATION:
  - min_tokens:      Minimum token count to trigger caching (skip tiny requests)
  - ttl_seconds:     How long the cache lives (default: 1800 = 30 minutes)
  - cache_intervals: Max reuses before cache is refreshed (default: 10)

HOW TO RUN:
  This example uses `App` so it must be run programmatically:

    python 06_context/context_caching/agent.py

  It sends multiple messages and shows how caching affects performance.

  you can also run with `adk web` to test in the browser
"""

import asyncio
import time
from google.adk.agents import LlmAgent
from google.adk.apps.app import App
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai.types import Content, Part


# ─── Callback: log cache usage after every LLM call ──────────────
# usage_metadata.cached_content_token_count > 0 means the cache was hit.
# On the FIRST call it will be 0 (cache is being created).
# On SUBSEQUENT calls it should be > 0 (cache is being reused).
def log_cache_usage(callback_context, llm_response):
    usage = getattr(llm_response, "usage_metadata", None)
    if usage:
        total    = getattr(usage, "total_token_count", "?")
        cached   = getattr(usage, "cached_content_token_count", 0)
        prompt   = getattr(usage, "prompt_token_count", "?")
        response = getattr(usage, "candidates_token_count", "?")
        hit = "✅ CACHE HIT" if cached and cached > 0 else "❌ no cache (first call or miss)"
        print(f"[Cache] {hit} | "
              f"total={total} | prompt={prompt} | cached={cached} | response={response}")
    return None  # None means: don't modify the response, pass it through


# ─── A long instruction to make caching worthwhile ───────────────
# Context caching only kicks in when there are enough tokens.
# Short instructions won't benefit from caching.
LONG_INSTRUCTION = """
You are an expert travel advisor with deep knowledge of world geography,
cultures, cuisines, travel logistics, visa requirements, and local customs.

REGIONS OF EXPERTISE:
- Europe: All 44 countries. Focus on hidden gems beyond typical tourist spots.
  Popular: France, Italy, Spain, Germany, Netherlands, Greece, Portugal.
  Hidden gems: Albania, North Macedonia, Moldova, Faroe Islands, Kosovo.
- Asia: Southeast Asia (Thailand, Vietnam, Cambodia, Indonesia, Philippines),
  East Asia (Japan, South Korea, Taiwan, China), South Asia (India, Sri Lanka, Nepal).
  Budget travel tips for backpackers and luxury experiences for high-end travelers.
- Americas: North America (USA, Canada, Mexico), Central America (Costa Rica, Guatemala,
  Belize, Panama), South America (Colombia, Peru, Argentina, Brazil, Chile, Bolivia).
  Adventure travel, ecotourism, and cultural immersion focus.
- Africa: East Africa safaris (Kenya, Tanzania, Uganda), North Africa (Morocco, Egypt),
  Southern Africa (South Africa, Botswana, Namibia, Zimbabwe), West Africa (Ghana, Senegal).
- Oceania: Australia (Sydney, Melbourne, Great Barrier Reef, Outback),
  New Zealand (North Island, South Island, adventure sports),
  Pacific Islands (Fiji, Bora Bora, Palau, Vanuatu).

TRAVEL PLANNING RULES:
1. Always consider the traveler's budget category: budget ($30-80/day),
   mid-range ($80-200/day), or luxury ($200+/day). Tailor recommendations accordingly.
2. Suggest seasonal timing — when is the best time to visit? Avoid monsoon seasons,
   extreme heat, or peak tourist crowds unless the traveler prefers that.
3. Include visa and entry requirements for common nationalities (US, UK, EU, Indian,
   Australian). Mention e-visa, visa on arrival, or embassy visit requirements.
4. Recommend local food and restaurants, not just tourist traps. Street food is
   often the best way to experience authentic cuisine.
5. Suggest off-beaten-path experiences alongside popular attractions. Balance
   iconic landmarks with local neighborhood exploration.
6. Consider travel safety and health precautions. Mention vaccinations, travel
   insurance, and any current safety advisories.
7. Provide estimated daily budgets in USD for accommodation, food, transport,
   and activities separately.
8. Include transportation options: flights, trains, buses, ferries, tuk-tuks,
   rental cars. Compare cost vs. convenience.
9. Suggest accommodation types appropriate to budget: hostels, guesthouses,
   boutique hotels, luxury resorts, or home stays.
10. Mention cultural etiquette: dress codes for temples, tipping customs,
    greeting norms, photography rules, and bargaining culture.
11. For multi-city trips, suggest logical itinerary routing to minimize
    backtracking and transportation time.
12. Highlight sustainable travel options: eco-lodges, local guides,
    responsible wildlife tourism, supporting local artisans.
13. When comparing destinations, use a structured format showing pros, cons,
    cost difference, and best fit for different traveler types.
14. For first-time visitors to a region, always recommend starting with the
    most accessible/safe entry point before venturing off the beaten path.
15. Include estimated flight costs from major hubs (London, New York, Dubai)
    when relevant to the question.

DESTINATION QUICK FACTS (use these when relevant):
Japan: Best Mar-May (cherry blossom) or Oct-Nov. JR Pass for trains. Cash society.
  Bow as greeting. No tipping. Shoes off indoors. Very safe. Vending machines everywhere.
Thailand: Best Nov-Feb (dry season). Avoid June-Oct (heavy monsoon in south).
  Wai greeting. Cover shoulders/knees at temples. Haggle at markets. Excellent street food.
Vietnam: Best Oct-Apr overall. North/south have different seasons. Motorbike taxis (Grab).
  Pho for breakfast. Coffee culture. Bargain at Ben Thanh market. Visa required for most.
Italy: Best Apr-Jun or Sep-Oct (avoid Aug heat/crowds). Validate train tickets.
  No cappuccino after 11am (locals). Coperto charge at restaurants is normal.
  Dress code enforced at Vatican and major churches.
Peru: Best May-Sep (dry season). Altitude sickness above 3500m — acclimatize first.
  Book Machu Picchu tickets 3-6 months ahead. Ceviche is the national dish.
Morocco: Best Mar-May or Sep-Nov. Medinas are confusing — hire a guide first time.
  Bargain at souks (start at 30% of asking price). Ramadan changes everything.
  Women should cover shoulders. Mint tea is offered everywhere — accepting is polite.

RESPONSE FORMAT:
- Be conversational but informative.
- Use bullet points for lists of recommendations.
- Include estimated costs where relevant.
- Organize by category (accommodation, food, transport, activities) for planning questions.
- If asked about a place you're uncertain about, say so honestly.
- Keep responses focused — don't overwhelm with too much information at once.
"""

# ─── Agent definition ────────────────────────────────────────────
root_agent = LlmAgent(
    name="TravelAdvisor",
    model="gemini-2.5-flash",
    instruction=LONG_INSTRUCTION,
    after_model_callback=log_cache_usage,  # logs cache hit/miss on every LLM call
)

# ─── App with context caching enabled ────────────────────────────
# This is the KEY difference from a regular agent setup.
# The App wraps the agent and adds caching behavior.
app = App(
    name="context_caching",
    root_agent=root_agent,
    context_cache_config=ContextCacheConfig(
        min_tokens=1024,    # Vertex AI hard minimum is 1024 tokens (instruction is ~1100 tokens)
        ttl_seconds=600,    # Cache lives for 10 minutes
        cache_intervals=5,  # Refresh cache after 5 uses
    ),
)


# ─── Demo: show caching in action ────────────────────────────────
async def main():
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="context_caching",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="context_caching",
        user_id="learner",
        session_id="caching_demo",
    )

    questions = [
        "What's the best time to visit Japan?",
        "How about budget tips for Tokyo?",
        "Compare Kyoto vs Osaka for a 3-day stay.",
    ]

    print("=" * 60)
    print("CONTEXT CACHING DEMO")
    print("=" * 60)
    print()
    print("Without caching, the full instruction (~500 tokens) is sent")
    print("with EVERY request. With caching, it's sent once and reused.")
    print()

    for i, question in enumerate(questions, 1):
        msg = Content(parts=[Part(text=question)], role="user")
        start = time.time()

        final_text = "(No response)"
        async for event in runner.run_async(
            user_id="learner",
            session_id="caching_demo",
            new_message=msg,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text

        elapsed = time.time() - start
        print(f"--- Turn {i} ({elapsed:.2f}s) ---")
        print(f"Q: {question}")
        print(f"A: {final_text[:200]}...")
        print()

    print("=" * 60)
    print("KEY TAKEAWAY:")
    print("  Context caching is configured on App, not Agent.")
    print("  It's transparent — the agent code doesn't change.")
    print("  You save tokens and get faster responses on repeated calls.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
