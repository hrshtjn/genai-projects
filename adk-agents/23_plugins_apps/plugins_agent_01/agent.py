"""ADK Learning - 23: Plugins and Apps.

USE CASE:
One app loads multiple plugins (toolsets) to extend a single agent.
A plugin here is a Toolset: a reusable bundle of tools plus optional
instructions that can be shared across agents.

THIS DEMO INCLUDES TWO PLUGINS:
1) NotesPluginToolset  - store and list notes
2) TasksPluginToolset  - track a simple task list

Each toolset uses a tool name prefix so tools from different plugins
can coexist without name collisions.

HOW TO RUN:
adk web 23_plugins_apps/plugins_agent_01
# or
adk run 23_plugins_apps/plugins_agent_01

TRY:
1. "Add note: Remember to study toolsets."
2. "List notes."
3. "Add task: Read the plugins docs."
4. "List tasks."
5. "Clear tasks."
"""

from __future__ import annotations

from typing import List

from google.adk.agents import LlmAgent
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

# ---------------------------------------------------------------------------
# PLUGIN 1: Notes
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


class NotesPluginToolset(BaseToolset):
    """Reusable notes plugin (toolset)."""

    def __init__(self) -> None:
        super().__init__(tool_name_prefix="notes")
        self._tools = [
            FunctionTool(add_note),
            FunctionTool(list_notes),
        ]

    async def get_tools(self, readonly_context=None):
        return self._tools

    async def process_llm_request(self, *, tool_context, llm_request) -> None:
        llm_request.append_instructions(
            [
                "Notes plugin: use notes_add_note to save a note and "
                "notes_list_notes to show all notes."
            ]
        )


# ---------------------------------------------------------------------------
# PLUGIN 2: Tasks
# ---------------------------------------------------------------------------

def add_task(task: str, tool_context: ToolContext) -> dict:
    """Add a task to session state."""
    tasks: List[str] = tool_context.state.get("tasks", [])
    cleaned = task.strip()
    if cleaned:
        tasks.append(cleaned)
    tool_context.state["tasks"] = tasks
    return {"status": "saved", "tasks_count": len(tasks), "task": cleaned}


def list_tasks(tool_context: ToolContext) -> dict:
    """List all tasks."""
    tasks: List[str] = tool_context.state.get("tasks", [])
    return {"tasks": tasks, "count": len(tasks)}


def clear_tasks(tool_context: ToolContext) -> dict:
    """Clear all tasks."""
    tool_context.state["tasks"] = []
    return {"status": "cleared", "count": 0}


class TasksPluginToolset(BaseToolset):
    """Reusable tasks plugin (toolset)."""

    def __init__(self) -> None:
        super().__init__(tool_name_prefix="tasks")
        self._tools = [
            FunctionTool(add_task),
            FunctionTool(list_tasks),
            FunctionTool(clear_tasks),
        ]

    async def get_tools(self, readonly_context=None):
        return self._tools

    async def process_llm_request(self, *, tool_context, llm_request) -> None:
        llm_request.append_instructions(
            [
                "Tasks plugin: use tasks_add_task to add, "
                "tasks_list_tasks to list, and tasks_clear_tasks to clear."
            ]
        )


notes_plugin = NotesPluginToolset()
tasks_plugin = TasksPluginToolset()


root_agent = LlmAgent(
    name="PluginsAppsAgent",
    model="gemini-2.5-flash",
    description="An app-like agent that loads multiple plugins (toolsets).",
    instruction=(
        "You are a personal productivity assistant. "
        "You have two plugins: Notes and Tasks. "
        "Use the Notes plugin for notes and the Tasks plugin for tasks. "
        "If the user asks for something unrelated, answer normally."
    ),
    tools=[notes_plugin, tasks_plugin],
)
