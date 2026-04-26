"""Cloud SQL Agent via Remote MCP Server — cloudsql_agent_01.

An ADK agent that connects directly to the Cloud SQL remote MCP server
at https://sqladmin.googleapis.com/mcp using the Streamable HTTP transport.

What this demonstrates:
┌─────────────────────────────────────────────────────────────────┐
│ PATTERN: McpToolset + StreamableHTTPConnectionParams           │
│                                                                 │
│ Cloud SQL MCP is a Google-managed REMOTE MCP server.           │
│ It has a fixed public HTTPS endpoint — no local subprocess,    │
│ no API Registry lookup needed.                                 │
│                                                                 │
│ vs mcp_agent_01 (Topic 9):                                     │
│ mcp_agent_01 → local subprocess (stdio)                        │
│ this agent → Google-hosted HTTPS endpoint (SSE/HTTP)           │
└─────────────────────────────────────────────────────────────────┘

Architecture:
adk web
│
▼
root_agent (LlmAgent)
│ tools=[cloudsql_tools] (McpToolset)
│ StreamableHTTPConnectionParams
│ Bearer token via Application Default Credentials
▼
https://sqladmin.googleapis.com/mcp (Google-managed MCP server)
│
▼
Cloud SQL Admin API

Available tools (from the MCP server):
list_instances, get_instance, create_instance, update_instance,
clone_instance, list_users, create_user, update_user,
execute_sql, execute_sql_readonly, create_backup, restore_backup,
import_data, get_operation

Prerequisites (one-time setup):
1. Enable the Cloud SQL Admin API (enables the MCP server automatically):
gcloud services enable sqladmin.googleapis.com \
--project=us-con-gcp-sbx-0000467-031725

2. Grant the MCP Tool User role to your account:
gcloud projects add-iam-policy-binding us-con-gcp-sbx-0000467-031725 \
--member=user:YOUR_EMAIL \
--role="roles/mcp.toolUser"

3. Grant Cloud SQL Viewer (to list/read instances):
gcloud projects add-iam-policy-binding us-con-gcp-sbx-0000467-031725 \
--member=user:YOUR_EMAIL \
--role="roles/cloudsql.viewer"

4. Ensure Application Default Credentials are set:
gcloud auth application-default login

Run:
cd /Users/harshitjain3/Documents/Learning/AI/adk2/25_api_registry
adk web cloudsql_agent_01

Try asking:
"List all Cloud SQL instances in my project"
"Show me the details of instance <name>"
"What databases are on instance <name>?"
"What is the state and database version of all my instances?"
"""

import os

import google.auth
import google.auth.transport.requests
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import (
	McpToolset,
	StreamableHTTPConnectionParams,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")

# Fixed endpoint for the Google-managed Cloud SQL remote MCP server.
# This is enabled automatically when the Cloud SQL Admin API is enabled.
# No API Registry registration or gcloud beta commands needed.
CLOUDSQL_MCP_URL = "https://sqladmin.googleapis.com/mcp"

# ---------------------------------------------------------------------------
# Google OAuth token via Application Default Credentials
# ---------------------------------------------------------------------------
# The Cloud SQL MCP server requires:
# Authorization: Bearer <access_token>
# x-goog-user-project: <project_id> (routes billing/quota to your project)
#
# google.auth.default() reads ADC in this order:
# 1. GOOGLE_APPLICATION_CREDENTIALS env var (service account key file)
# 2. gcloud auth application-default login credentials
# 3. GCE/GKE metadata service (when running on Google Cloud)
# ---------------------------------------------------------------------------
_credentials, _ = google.auth.default(
	scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

# Refresh to ensure a valid access token is available at startup
_credentials.refresh(google.auth.transport.requests.Request())

# ---------------------------------------------------------------------------
# McpToolset with HTTP/SSE transport
# ---------------------------------------------------------------------------
cloudsql_tools = McpToolset(
	connection_params=StreamableHTTPConnectionParams(
		url=CLOUDSQL_MCP_URL,
		headers={
			"Authorization": f"Bearer {_credentials.token}",
			"x-goog-user-project": PROJECT_ID,
		},
		timeout=30.0,
		sse_read_timeout=120.0,
	),
	# Uncomment to restrict which tools are exposed to the LLM:
	# tool_filter=["list_instances", "get_instance", "execute_sql_readonly"],
)

# ---------------------------------------------------------------------------
# The ADK agent
# ---------------------------------------------------------------------------
root_agent = LlmAgent(
	name="cloudsql_agent",
	model="gemini-2.5-flash",
	description="An agent that manages and queries Cloud SQL instances via the remote MCP server.",
	instruction=f"""
You are a Google Cloud SQL assistant for project '{PROJECT_ID}'.

You have access to Cloud SQL management tools via the remote MCP server at sqladmin.googleapis.com.
Use them to help the user inspect, manage, and query their Cloud SQL instances.

When answering:
- Always include the instance name, region, database version, and current state in summaries.
- Format lists as tables where possible for readability.
- If a tool call fails with a permissions error, explain what IAM roles may be missing.
- Do not attempt to modify, delete, or create instances unless explicitly asked.
- For SQL execution, prefer execute_sql_readonly for read-only queries.
""",
	tools=[cloudsql_tools],
)


