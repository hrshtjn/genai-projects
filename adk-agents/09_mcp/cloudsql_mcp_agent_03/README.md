# Cloud SQL MCP Agent

This ADK agent connects directly to the Google Cloud SQL remote MCP server (`https://sqladmin.googleapis.com/mcp`) using the Streamable HTTP transport. It manages and queries Google Cloud SQL for MySQL databases.

## Prerequisites

Before running the agent, you must configure your Google Cloud project and authenticate.

1. **Enable the Cloud SQL Admin API** (this automatically enables the remote MCP endpoint):
   ```bash
   gcloud services enable sqladmin.googleapis.com --project=YOUR_PROJECT_ID
   ```

2. **Grant the MCP Tool User role** to your account (required to avoid `403 Forbidden` errors):
   ```bash
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="user:YOUR_EMAIL" \
     --role="roles/mcp.toolUser"
   ```

3. **Grant Cloud SQL Viewer** (to list/read instances):
   ```bash
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="user:YOUR_EMAIL" \
     --role="roles/cloudsql.viewer"
   ```

4. **Set up Application Default Credentials (ADC)**:
   ```bash
   gcloud auth application-default login
   ```

## Usage

Make sure your `GOOGLE_CLOUD_PROJECT` environment variable is set, or that your ADC has a default project configured.
```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
```

