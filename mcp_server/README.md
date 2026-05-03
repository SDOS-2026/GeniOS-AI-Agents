# GeniOS MCP Server 🛠️

The GeniOS MCP Server is a self-hosted replacement for the Zapier MCP. It provides a standardized interface for agents to interact with Google Services (Gmail and Calendar) without relying on third-party integration platforms.

## 🏗️ Core Architecture

The server is built with **FastAPI** and interacts directly with Google APIs using official Python client libraries. It handles authentication locally via OAuth 2.0.

- **Port**: 9000
- **Auth**: Google OAuth 2.0 (Desktop Flow)
- **Interface**: REST API with a unified `/call_tool` endpoint.

## 🧰 Tool Capabilities

The server exposes specific tools that match Zapier's naming conventions to ensure compatibility with existing agent connectors.

### 1. `gmail_search`
- **Purpose**: Search and retrieve Gmail threads.
- **Logic**: Calls `service.users().threads().list()` to find matching thread IDs, then fetches metadata and snippets.

### 2. `calendar_get_events`
- **Purpose**: Fetch calendar events for a specific time window.
- **Logic**: Calls `service.events().list()` on the primary calendar, filtering for single events and ordering by start time.

## 🚀 Setup & Execution

### 1. Authentication
- Obtain `credentials.json` (OAuth 2.0 Client credentials) from Google Cloud Console.
- Place `credentials.json` in this directory.

### 2. Running the Server
Start the server using the provided script:

```bash
bash start.sh
```

*(On the first run, a browser window will open to authenticate the Google account and generate `token.json`)*

## 🔗 Integration

Other services (like the Daily Attention Agent) can use this server by sending a POST request to `http://localhost:9000/call_tool` with a `tool_name` and `arguments`.
