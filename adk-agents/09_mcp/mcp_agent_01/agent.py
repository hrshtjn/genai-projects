"""MCP Tools (Topic 9) — mcp_agent_01.

Demonstrates ADK's McpToolset — how to connect an ADK agent to external
MCP (Model Context Protocol) servers and expose their tools to the LLM.

This agent connects to TWO MCP servers simultaneously:

1. mcp-server-time (launched via `uvx`)
   → provides: get_current_time, convert_time
   → demonstrates: StdioConnectionParams + tool_filter

2. @modelcontextprotocol/server-filesystem (launched via `npx`)
   → provides: read_file, write_file, list_directory, etc.
   → demonstrates: npx-launched Node.js MCP server

Key concepts shown:
┌─────────────────────────────────────────────────────────────────────┐
│ McpToolset ADK wrapper around a single MCP server                  │
│ StdioConnectionParams Launch the MCP server as a child process     │
│ StdioServerParameters command + args for the child process         │
│ tool_filter Only expose selected tools from that server            │
│ tools=[...] Pass multiple toolsets to one LlmAgent                 │
└─────────────────────────────────────────────────────────────────────┘

How MCP differs from regular FunctionTool:
- Regular FunctionTool: your Python function, runs in-process
- MCP server: an external process (Node.js, Python, etc.) that
  speaks the MCP protocol. ADK auto-discovers its tools, calls them
  over stdin/stdout (Stdio transport) or HTTP (SSE/Streamable HTTP).

Prerequisites:
- uvx (install: curl -LsSf https://astral.sh/uv/install.sh | sh)
- npx (comes with Node.js — https://nodejs.org)

Run:
cd /Users/harshitjain3/Documents/Learning/AI/adk2/09_mcp
adk web mcp_agent_01

Try asking:
"What time is it right now in New York?"
"What time is it in Tokyo?"
"Convert 3:00 PM New York time to London time"
"List the files in my sandbox"
"Write a file called notes.txt with the text: Hello from ADK MCP!"
"Read the contents of notes.txt"
"Create a file called todo.txt: Buy groceries, Call dentist, Learn MCP"
"""

import os
import shutil

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters

# ---------------------------------------------------------------------------
# Sandbox directory — the filesystem MCP server is locked to this path only.
# It cannot read or write outside this directory (security boundary).
# ---------------------------------------------------------------------------
SANDBOX_DIR = os.path.expanduser("~/mcp_sandbox")
os.makedirs(SANDBOX_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Pass the current shell PATH to subprocesses.
# When `adk web` launches MCP server child processes, they inherit a minimal
# environment that may not include paths like ~/.local/bin (where uvx lives).
# Explicitly forwarding the PATH ensures uvx and npx are found.
# ---------------------------------------------------------------------------
SUBPROCESS_ENV = {"PATH": os.environ.get("PATH", "")}

# Resolve absolute paths to be extra safe
UVX_PATH = shutil.which("uvx") or "uvx"
NPX_PATH = shutil.which("npx") or "npx"

# ---------------------------------------------------------------------------
# MCP Toolset 1: Time server
# ---------------------------------------------------------------------------
# `uvx mcp-server-time` downloads and runs the mcp-server-time package
# in an isolated environment (no global install needed).
#
# tool_filter restricts which tools from this server are exposed to the LLM.
# The server has more tools, but we only want these two.
# ---------------------------------------------------------------------------
time_toolset = McpToolset(
	connection_params=StdioConnectionParams(
		server_params=StdioServerParameters(
			command=UVX_PATH,
			args=["mcp-server-time"],
			env=SUBPROCESS_ENV,
		),
		timeout=30.0,  # seconds to wait for server startup
	),
	tool_filter=["get_current_time", "convert_time"],
)

# ---------------------------------------------------------------------------
# MCP Toolset 2: Filesystem server (Node.js via npx)
# ---------------------------------------------------------------------------
# `npx -y @modelcontextprotocol/server-filesystem <dir>` runs the official
# MCP filesystem server. It can only access files under SANDBOX_DIR.
#
# No tool_filter here — we expose ALL filesystem tools:
# read_file, write_file, list_directory, create_directory,
# move_file, search_files, get_file_info, read_multiple_files
# ---------------------------------------------------------------------------
filesystem_toolset = McpToolset(
	connection_params=StdioConnectionParams(
		server_params=StdioServerParameters(
			command=NPX_PATH,
			args=[
				"-y",  # auto-install without prompt
				"@modelcontextprotocol/server-filesystem",
				SANDBOX_DIR,  # the ONLY allowed directory
			],
			env=SUBPROCESS_ENV,
		),
		timeout=60.0,  # npx may need time to download on first run
	),
)

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
# Both toolsets are passed in tools=[]. ADK manages the MCP server lifecycle —
# starting the process when needed and shutting it down cleanly.
#
# The LLM sees all MCP tools transparently, exactly like FunctionTools.
# ---------------------------------------------------------------------------
root_agent = LlmAgent(
	name="mcp_agent",
	model="gemini-2.5-flash",
	instruction=(
		"You are a helpful personal assistant with two special capabilities:\n\n"
		"1. TIME TOOLS (from mcp-server-time via uvx):\n"
		" - get_current_time: get the current time in any timezone\n"
		" - convert_time: convert a time from one timezone to another\n"
		" Always use IANA timezone names like 'America/New_York', 'Asia/Tokyo', 'Europe/London'.\n\n"
		"2. FILE TOOLS (from @modelcontextprotocol/server-filesystem via npx):\n"
		f" - Sandbox directory: {SANDBOX_DIR}\n"
		" - You can read_file, write_file, list_directory, create_directory, move_file.\n"
		" - You can ONLY access files inside the sandbox. Never attempt paths outside it.\n\n"
		"When you use a tool, briefly mention which MCP server provided it.\n"
		"Be concise and helpful."
	),
	tools=[time_toolset, filesystem_toolset],
)


# environment that may not include paths like ~/.local/bin (where uvx lives). 


