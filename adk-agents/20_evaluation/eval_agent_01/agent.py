"""ADK Learning - 20: Evaluation (agents-cli eval).

USE CASE:
An expense policy assistant that MUST call a tool before answering.

WHAT YOU LEARN:
- How to write an evalset with expected tool calls.
- How to score tool usage and final responses.

HOW TO RUN (interactive):
adk run 20_evaluation/eval_agent_01

HOW TO RUN EVAL:
uv tool install google-agents-cli
agents-cli eval run \
  --evalset adk-agents/20_evaluation/eval_agent_01/eval/evalset.json \
  --config adk-agents/20_evaluation/eval_agent_01/eval/eval_config.json
"""

from typing import Annotated

from google.adk.agents import LlmAgent


POLICY_LIMITS = {
    "meals": 75.0,
    "taxi": 40.0,
    "hotel": 200.0,
}


def check_policy(
    category: Annotated[str, "Expense category: meals, taxi, or hotel"],
    amount: Annotated[float, "Expense amount in USD"],
) -> dict:
    """Return a policy decision for the given category and amount."""
    normalized_category = category.strip().lower()
    amount_value = round(float(amount), 2)
    limit_value = POLICY_LIMITS.get(normalized_category)

    if limit_value is None:
        return {
            "category": normalized_category,
            "amount": f"{amount_value:.2f}",
            "limit": "UNKNOWN",
            "decision": "DENIED",
            "reason": "unknown_category",
        }

    approved = amount_value <= limit_value
    reason = "within_limit" if approved else f"over_limit_by_{amount_value - limit_value:.2f}"

    return {
        "category": normalized_category,
        "amount": f"{amount_value:.2f}",
        "limit": f"{limit_value:.2f}",
        "decision": "APPROVED" if approved else "DENIED",
        "reason": reason,
    }


root_agent = LlmAgent(
    name="EvalAgent",
    model="gemini-2.5-flash",
    instruction=(
        "You are an expense policy assistant. Always call check_policy before you answer. "
        "Map user wording to categories: meal/meal(s) -> meals, cab/taxi -> taxi, hotel -> hotel. "
        "Use ONLY the values returned by the tool and respond in exactly this format:\n"
        "DECISION: <decision>\n"
        "CATEGORY: <category>\n"
        "AMOUNT: <amount>\n"
        "LIMIT: <limit>\n"
        "REASON: <reason>\n"
        "Do not add extra text."
    ),
    tools=[check_policy],
)
