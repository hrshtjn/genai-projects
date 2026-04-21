"""MCP Client Agent 02 — mcp_client_agent_02.

Companion to mcp_server_01.py.

This ADK agent connects to the ADK-backed MCP server (mcp_server_01.py)
via the stdio transport. ADK automatically starts the server as a child
process and wires up stdin/stdout communication.

What this illustrates (the full loop):
┌──────────────────────────────────────────────────────────────────┐
│ ADK agent (this file)                                           │
│                                                                  │
│   McpToolset + StdioConnectionParams                            │
│   (starts mcp_server_01.py as subprocess)                       │
│   ▼                                                              │
│ mcp_server_01.py ← Python MCP server built on ADK tools         │
│   ├── load_web_page (ADK built-in)                              │
│   └── get_weather (custom FunctionTool)                         │
└──────────────────────────────────────────────────────────────────┘

Run with:
cd /Users/harshitjain3/Documents/Learning/AI/adk2/09_mcp
adk web mcp_client_agent_02

Try asking the agent:
"What is the weather in Tokyo?"
"Fetch the content of https://example.com"
"""

import os
import shutil
import sys

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters

# Absolute path to the MCP server script
SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "mcp_server_01.py")
SERVER_SCRIPT = os.path.abspath(SERVER_SCRIPT)

# Use the Python interpreter from the current virtual environment so that
# ADK and MCP packages are available when the server subprocess is launched.
PYTHON_PATH = shutil.which("python3") or sys.executable

# Pass PATH so the subprocess can find any CLI tools it might need
SUBPROCESS_ENV = {"PATH": os.environ.get("PATH", "")}

# ---------------------------------------------------------------------------
# McpToolset: connects this agent to our local MCP server
# ---------------------------------------------------------------------------
# StdioServerParameters tells ADK to:
# 1. Spawn: python3 /path/to/mcp_server_01.py
# 2. Talk to it over stdin/stdout using the MCP JSON-RPC protocol
# 3. Discover tools via the list_tools() response
# 4. Route agent tool calls to call_tool() on the server
# ---------------------------------------------------------------------------
mcp_toolset = McpToolset(
	connection_params=StdioConnectionParams(
		server_params=StdioServerParameters(
			command=PYTHON_PATH,
			args=[SERVER_SCRIPT],
			env=SUBPROCESS_ENV,
		),
		timeout=60.0,  # seconds to wait for server startup
	),
	# Leave tool_filter unset → expose ALL tools from the server
)

root_agent = LlmAgent(
	name="mcp_client_agent_02",
	model="gemini-2.0-flash",
	description=(
		"An ADK agent that accesses tools served by a local Python MCP server "
		"(mcp_server_01.py). The server exposes ADK tools: load_web_page and "
		"get_weather."
	),
	instruction=(
		"You are a helpful assistant with access to two tools provided by a "
		"local MCP server:\n"
		" • get_weather — returns current weather for a city\n"
		" • load_web_page — fetches the text content of a URL\n\n"
		"Use these tools to answer the user's questions. When using load_web_page "
		"summarize the content rather than dumping the raw text."
	),
	tools=[mcp_toolset],
)
SERVER_SCRIPT = os.path.abspath(SERVER_SCRIPT) 



 
