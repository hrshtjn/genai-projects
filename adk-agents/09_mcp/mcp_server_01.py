"""MCP Server — mcp_server_01.

This is an MCP SERVER built with ADK tools, following Section 2 of the docs:
https://adk.dev/tools-custom/mcp-tools/#2-building-an-mcp-server-with-adk-tools

What this demonstrates:
┌──────────────────────────────────────────────────────────────────────┐
│ PATTERN: ADK → MCP (opposite of mcp_agent_01!)                      │
│                                                                      │
│ mcp_agent_01: ADK agent CONSUMES external MCP servers               │
│ mcp_server_01: ADK tools EXPOSED AS an MCP server                   │
│                                                                      │
│ Any MCP client (Claude Desktop, another ADK agent, VS Code, etc.)   │
│ can connect to this server and use the ADK tools inside it.         │
└──────────────────────────────────────────────────────────────────────┘

Tools exposed by this MCP server:
1. load_web_page (built-in ADK tool) — fetches content from a URL
2. get_weather (custom FunctionTool) — returns fake weather data

Architecture:
MCP Client (any)
│ stdin/stdout (MCP stdio transport)
▼
This MCP server (mcp_server_01.py)
├── @app.list_tools() → advertises ADK tools in MCP schema format
└── @app.call_tool() → runs the ADK tool and formats the response

Key ADK utilities used:
- FunctionTool wraps a plain Python function as an ADK tool
- adk_to_mcp_tool_type converts an ADK tool's schema → MCP Tool schema
- tool.run_async() executes the ADK tool directly (no Runner needed)

Run this server standalone (stdio — waits for MCP client to connect):
python mcp_server_01.py

Or, have the companion agent (mcp_client_agent_02) start it automatically
via StdioConnectionParams — see mcp_client_agent_02/agent.py.
"""

import asyncio
import json

import mcp.server.stdio
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.load_web_page import load_web_page
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type
from mcp import types as mcp_types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# ---------------------------------------------------------------------------
# Tool 1: Built-in ADK tool — load_web_page
# ---------------------------------------------------------------------------
# load_web_page is a standard ADK tool that fetches the text content of a URL.
# We wrap it in FunctionTool so ADK can introspect its schema.
web_tool = FunctionTool(load_web_page)


# ---------------------------------------------------------------------------
# Tool 2: Custom FunctionTool — get_weather
# ---------------------------------------------------------------------------
# A plain Python function promoted to an ADK FunctionTool.
# In a real implementation this would call a weather API.
def get_weather(city: str) -> dict:
	"""Returns the current weather for a given city.

	Args:
		city: The name of the city to get weather for.

	Returns:
		A dict with temperature_celsius, condition, and humidity_pct.
	"""
	fake_data = {
		"london": {
			"temperature_celsius": 12,
			"condition": "cloudy",
			"humidity_pct": 78,
		},
		"new york": {
			"temperature_celsius": 18,
			"condition": "sunny",
			"humidity_pct": 55,
		},
		"tokyo": {
			"temperature_celsius": 22,
			"condition": "partly cloudy",
			"humidity_pct": 65,
		},
		"sydney": {
			"temperature_celsius": 25,
			"condition": "sunny",
			"humidity_pct": 50,
		},
		"mumbai": {
			"temperature_celsius": 32,
			"condition": "humid",
			"humidity_pct": 88,
		},
	}
	data = fake_data.get(city.lower())
	if data:
		return {"city": city, **data}
	return {"city": city, "error": f"No weather data available for '{city}'"}


weather_tool = FunctionTool(get_weather)

# ---------------------------------------------------------------------------
# Registry: all ADK tools this server exposes
# ---------------------------------------------------------------------------
ADK_TOOLS = {
	web_tool.name: web_tool,
	weather_tool.name: weather_tool,
}

# ---------------------------------------------------------------------------
# MCP Server instance
# ---------------------------------------------------------------------------
print("Initializing MCP server: adk-tool-mcp-server")
app = Server("adk-tool-mcp-server")


@app.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
	"""MCP handler: tell clients which tools this server advertises.

	adk_to_mcp_tool_type() converts an ADK tool's schema (built from
	Python type hints and docstrings) into the MCP Tool schema format.
	"""
	print("MCP Server: list_tools requested")
	schemas = [adk_to_mcp_tool_type(tool) for tool in ADK_TOOLS.values()]
	for schema in schemas:
		print(f" → advertising: {schema.name}")
	return schemas


@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.Content]:
	"""MCP handler: execute a tool call requested by an MCP client.

	Steps:
	1. Look up the ADK tool by name from the registry.
	2. Call tool.run_async(args, tool_context=None).
	   tool_context=None is valid here — we are outside a full ADK Runner,
	   so session state / artifact features are not available. Only tools
	   that don't need ToolContext work correctly this way.
	3. Serialize the result dict → JSON string → mcp_types.TextContent.
	"""
	print(f"MCP Server: call_tool '{name}' args={arguments}")

	adk_tool = ADK_TOOLS.get(name)
	if adk_tool is None:
		error = {"error": f"Tool '{name}' is not implemented by this server."}
		return [mcp_types.TextContent(type="text", text=json.dumps(error))]

	try:
		result = await adk_tool.run_async(args=arguments, tool_context=None)
		print(f"MCP Server: '{name}' succeeded")
		return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]
	except Exception as exc:
		print(f"MCP Server: '{name}' raised: {exc}")
		error = {"error": f"Tool '{name}' failed: {str(exc)}"}
		return [mcp_types.TextContent(type="text", text=json.dumps(error))]


# ---------------------------------------------------------------------------
# Stdio server runner
# ---------------------------------------------------------------------------
async def run_stdio_server() -> None:
	"""Starts the MCP server listening on stdin/stdout (stdio transport).

	The MCP client communicates by writing JSON-RPC to our stdin and
	reading responses from our stdout. When used with StdioConnectionParams
	in an ADK agent, the agent framework starts this script as a subprocess
	automatically and wires up the pipes.
	"""
	async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
		print(f"MCP Server: running, exposing tools: {list(ADK_TOOLS.keys())}")
		await app.run(
			read_stream,
			write_stream,
			InitializationOptions(
				server_name=app.name,
				server_version="0.1.0",
				capabilities=app.get_capabilities(
					notification_options=NotificationOptions(),
					experimental_capabilities={},
				),
			),
		)


if __name__ == "__main__":
	print("Launching ADK-backed MCP server (stdio)...")
	try:
		asyncio.run(run_stdio_server())
	except KeyboardInterrupt:
		print("\nMCP server stopped.")