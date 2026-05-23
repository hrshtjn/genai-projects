"""ADK Learning - 22: Safety and Security.

USE CASE:
A personal assistant that stores user notes but applies guardrails:
- Refuses to handle secrets or credentials.
- Redacts accidental tokens before saving.
- Requires explicit confirmation for destructive actions.

HOW TO RUN:
adk web 22_safety_security/safety_agent_01
# or
adk run 22_safety_security/safety_agent_01

TRY:
1. "Remember: my favorite color is blue."
2. "Remember: my api key is sk-1234567890"
3. "List my notes."
4. "Delete all notes." (agent should ask for confirmation)
5. "Confirm delete: DELETE"
"""

from __future__ import annotations

import re
from typing import Iterable

from google.adk.agents import LlmAgent
from google.adk.tools.tool_context import ToolContext
from google.genai import types

# Simple patterns to detect common secrets. This is a teaching example, not a full
# secret scanner.
_SECRET_PATTERNS: Iterable[str] = (
    r"AIza[0-9A-Za-z\-_]{35}",
    r"sk-[0-9A-Za-z]{16,}",
    r"ghp_[0-9A-Za-z]{36}",
    r"xox[baprs]-[0-9A-Za-z-]{10,}",
    r"ya29\.[0-9A-Za-z\-_]+",
    r"-----BEGIN (?:RSA|EC|OPENSSH|PRIVATE) KEY-----",
)

_SENSITIVE_PHRASES = (
    "api key",
    "password",
    "secret",
    "private key",
    "token",
)


def _looks_like_secret(text: str) -> bool:
    for pattern in _SECRET_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def _redact_secrets(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = re.sub(pattern, "[REDACTED]", redacted)
    return redacted


def before_agent(callback_context):
    """Blocks obvious attempts to share or request secrets."""
    user_text = ""
    session = callback_context._invocation_context.session
    if session.events:
        last_event = session.events[-1]
        if last_event.content and last_event.content.parts:
            user_text = last_event.content.parts[0].text or ""

    lower = user_text.lower()
    if any(phrase in lower for phrase in _SENSITIVE_PHRASES):
        return types.Content(
            parts=[
                types.Part(
                    text=(
                        "I cannot help with secrets or credentials. "
                        "Please remove sensitive data and try again."
                    )
                )
            ],
            role="model",
        )
    return None


def before_tool(tool, args, tool_context):
    """Applies tool-level guardrails before execution."""
    if tool.name == "store_note":
        note = args.get("note", "")
        if _looks_like_secret(note):
            return {
                "error": "Refused to store potential secrets. Remove sensitive data and retry."
            }

    if tool.name == "delete_all_notes":
        confirm = (args.get("confirm") or "").strip().upper()
        if confirm != "DELETE":
            return {
                "error": "Confirmation required. Reply with 'Confirm delete: DELETE'."
            }

    return None


def store_note(note: str, tool_context: ToolContext) -> dict:
    """Store a user note after redacting accidental secrets."""
    clean_note = _redact_secrets(note)
    notes = tool_context.state.get("notes", [])
    notes.append(clean_note)
    tool_context.state["notes"] = notes
    return {
        "status": "saved",
        "redacted": clean_note != note,
        "note": clean_note,
        "notes_count": len(notes),
    }


def list_notes(tool_context: ToolContext) -> dict:
    """Return all stored notes."""
    notes = tool_context.state.get("notes", [])
    return {"notes": notes, "count": len(notes)}


def delete_all_notes(confirm: str, tool_context: ToolContext) -> dict:
    """Delete all notes after explicit confirmation."""
    if confirm.strip().upper() != "DELETE":
        return {"error": "Confirmation required. Use confirm='DELETE'."}
    tool_context.state["notes"] = []
    return {"status": "deleted", "count": 0}


root_agent = LlmAgent(
    name="SafetySecurityAgent",
    model="gemini-2.5-flash",
    instruction=(
        "You are a safety-first personal assistant. "
        "You can store and recall user notes. "
        "Never handle secrets or credentials. "
        "If the user asks to delete notes, request explicit confirmation. "
        "Only call delete_all_notes after the user provides 'Confirm delete: DELETE'. "
        "If you recall information from notes, say so."
    ),
    tools=[store_note, list_notes, delete_all_notes],
    before_agent_callback=before_agent,
    before_tool_callback=before_tool,
)
