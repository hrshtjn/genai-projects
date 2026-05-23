"""ADK Learning - 23: Plugins and Apps (Logging Plugin).

USE CASE:
Run a small app with the built-in LoggingPlugin enabled. The plugin logs
activity across the entire workflow (user message, agent, model, tools).

HOW TO RUN (plugin is Runner-level):
adk web 23_plugins_apps/logging_plugin_agent_01 \
    --extra_plugins google.adk.plugins.logging_plugin.LoggingPlugin

NOTE:
Plugins are registered on the Runner. The agent code stays clean and the
plugin is injected by the CLI.
"""

from __future__ import annotations

from typing import List

from google.adk.agents import LlmAgent
from google.adk.tools.tool_context import ToolContext


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def add_note(note: str, tool_context: ToolContext) -> dict:
    """Add a note to session state."""
    notes: List[str] = tool_context.state.get("notes", [])
    cleaned = note.strip()
    if cleaned:
        notes.append(cleaned)
    tool_context.state["notes"] = notes
    return {"status": "saved", "notes_count": len(notes), "note": cleaned}


def list_notes(tool_context: ToolContext) -> dict:
    """List all notes."""
    notes: List[str] = tool_context.state.get("notes", [])
    return {"notes": notes, "count": len(notes)}


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

root_agent = LlmAgent(
    name="LoggingPluginDemo",
    model="gemini-2.5-flash",
    description="A simple notes assistant to demonstrate the LoggingPlugin.",
    instruction=(
        "You are a notes assistant. Use add_note to store notes and "
        "list_notes to show them. Keep responses concise."
    ),
    tools=[add_note, list_notes],
)
