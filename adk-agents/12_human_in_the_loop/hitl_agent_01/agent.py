"""ADK Learning - 12: Human-in-the-Loop (Tool Confirmation).

USE CASE:
A money transfer assistant that requires human confirmation for
high-risk actions (large transfers).

HOW IT WORKS:
- The transfer_funds tool requires confirmation when amount >= 100.
- ADK emits a confirmation request event instead of executing the tool.
- In adk web, you approve or reject in the UI, then the tool resumes.

HOW TO RUN (recommended for confirmations):
  adk web adk-agents

HOW TO TEST:
1. "Transfer 25 from checking to savings" -> no confirmation.
2. "Transfer 250 from checking to savings" -> UI asks for confirmation.
3. Reject and observe the tool call is canceled.
4. Confirm and observe the transfer is executed.

NOTE:
adk run does not provide a confirmation UI, so use adk web for this demo.
"""

from typing import Annotated

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool


def transfer_funds(
    from_account: Annotated[str, "Source account name"],
    to_account: Annotated[str, "Destination account name"],
    amount_usd: Annotated[float, "Transfer amount in USD"],
) -> dict:
    """Create a transfer between accounts.

    This is a demo-only action. No real funds are moved.
    """
    amount_value = round(float(amount_usd), 2)
    return {
        "status": "scheduled",
        "from_account": from_account.strip().lower(),
        "to_account": to_account.strip().lower(),
        "amount": f"{amount_value:.2f}",
        "currency": "USD",
    }


def requires_confirmation(
    from_account: str,
    to_account: str,
    amount_usd: float,
) -> bool:
    """Require confirmation for large transfers."""
    return float(amount_usd) >= 100.0


root_agent = LlmAgent(
    name="HitlAgent",
    model="gemini-2.5-flash",
    instruction=(
        "You are a transfer assistant. Always call transfer_funds to execute a transfer. "
        "If the system requests confirmation, wait for it and then continue. "
        "Summarize the result using ONLY the tool output fields."
    ),
    tools=[
        FunctionTool(transfer_funds, require_confirmation=requires_confirmation)
    ],
)
