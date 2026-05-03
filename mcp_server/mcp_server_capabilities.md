# MCP Server Capabilities & Logic

The GeniOS MCP Server is a self-hosted replacement for the Zapier MCP. It provides a standardized interface for agents to interact with Google Services (Gmail and Calendar) without relying on third-party integration platforms.

## 1. Core Architecture

The server is built with **FastAPI** and interacts directly with Google APIs using official Python client libraries. It handles authentication locally via OAuth 2.0.

- **Port**: 9000
- **Auth**: Google OAuth 2.0 (Desktop Flow)
- **Interface**: REST API with a unified `/call_tool` endpoint.

---

## 2. Tool Capabilities

The server exposes specific tools that match Zapier's naming conventions to ensure compatibility with existing agent connectors.

### A. `gmail_search`
- **Purpose**: Search and retrieve Gmail threads.
- **Logic**:
    1. Receives a search `query` (e.g., `is:unread`) and `maxResults`.
    2. Calls `service.users().threads().list()` to find matching thread IDs.
    3. For each ID, calls `service.users().threads().get()` to fetch metadata and snippets.
    4. **Output**: A JSON list of thread objects structured exactly as the DAA normalizer expects (headers, snippets, IDs).
- **Technical Detail**: Uses `format="metadata"` for efficiency, fetching only necessary headers (Subject, From, Date, To).

### B. `calendar_get_events`
- **Purpose**: Fetch calendar events for a specific time window.
- **Logic**:
    1. Receives `timeMin` and `timeMax` (ISO 8601 strings).
    2. Calls `service.events().list()` on the `primary` calendar.
    3. Filters for single events and orders them by start time.
    4. **Output**: A JSON list of event objects (summary, start, end, description, attendees, conference data).

---

## 3. Low-Level Logic & Lifecycle

### Startup & Authentication
1. **Credential Check**: On startup, the server checks for `credentials.json`. if missing, it exits with setup instructions.
2. **Service Initialization**: It eagerly initializes Gmail and Calendar services. If `token.json` is missing or expired, it triggers a local browser-based OAuth flow to obtain a new token.
3. **Lifespan Management**: Services are initialized once at startup and reused for all tool calls to minimize latency.

### Tool Routing (`/call_tool`)
- All tool requests are sent to the `POST /call_tool` endpoint with a `tool_name` and `arguments`.
- A internal `TOOL_REGISTRY` maps the name to the appropriate handler function in the `tools/` directory.
- This abstraction allows for easy addition of new tools (e.g., Drive, Sheets) without changing the API structure.

---

## 4. Integration for Other Services

Other services (like the Daily Attention Agent) can use this server by:
1. Sending a POST request to `http://localhost:9000/call_tool`.
2. Providing a payload like:
   ```json
   {
     "tool_name": "gmail_search",
     "arguments": { "query": "label:urgent", "maxResults": 5 }
   }
   ```
3. Receiving the raw Google API response wrapped in an MCP-compliant `ToolResponse`.
