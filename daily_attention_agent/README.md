# Daily Attention Agent (V2) 🧠📬

An intelligent, asynchronous, read-only Executive Assistant Agent built with **FastAPI**, **LangGraph**, and **Gemini 2.5 Flash**. The agent utilizes the **Model Context Protocol (MCP)** to securely retrieve and analyze Gmail and Google Calendar data, surfacing critical updates and schedule risks.

---

## 🏗️ Architecture Overview

The project has transitioned from a synchronous CLI application to a state-of-the-art asynchronous web service.

### 1. **FastAPI Layer** (`app/api/`)
-   **Main Entry** ([main.py](file:///home/satvik/Documents/GeniOS-AI-Agents/daily_attention_agent/app/api/main.py)): Initializes the application and manages the **lifespan** of the MCP connection via SSE.
-   **Agent Router** ([agent.py](file:///home/satvik/Documents/GeniOS-AI-Agents/daily_attention_agent/app/api/routers/agent.py)): Exposes endpoints for executing the agent (`POST /agent/run`), checking status (`GET /agent/status/{id}`), and viewing run history.
-   **Run Store** ([run_store.py](file:///home/satvik/Documents/GeniOS-AI-Agents/daily_attention_agent/app/services/run_store.py)): An in-memory persistent layer tracks background tasks and store results indexed by UUID.

### 2. **MCP Core** (`app/services/`)
-   **MCP Client** ([mcp_client.py](file:///home/satvik/Documents/GeniOS-AI-Agents/daily_attention_agent/app/services/mcp_client.py)): Uses the Anthropic MCP SDK to establish a persistent **Server-Sent Events (SSE)** connection to a remote MCP provider (e.g., Zapier). The session is injected into the application state for use during agent execution.

### 3. **LangGraph Pipeline** (`app/core/`)
-   **Async Graph** ([graph.py](file:///home/satvik/Documents/GeniOS-AI-Agents/daily_attention_agent/app/core/graph.py)): Defines the logical flow of the agent as an asynchronous direct cyclic graph.
-   **State Management** ([state.py](file:///home/satvik/Documents/GeniOS-AI-Agents/daily_attention_agent/app/core/state.py)): The `DAAState` object carries raw signals, scored items, and metadata (including the active MCP session) through the pipeline.
-   **Runner** ([runner.py](file:///home/satvik/Documents/GeniOS-AI-Agents/daily_attention_agent/app/core/runner.py)): The orchestrator that initializes the state and executes `ainvoke` on the graph.

---

## 🛠️ Data Flow: From Request to Briefing

1.  **Request Intake**: A client calls `POST /agent/run`.
2.  **Background Task**: FastAPI spawns an `execute_and_store` task.
3.  **Signal Fetching**: The `fetch_signals` node triggers:
    -   `fetch_gmail_signals` ([fetch.py](file:///home/satvik/Documents/GeniOS-AI-Agents/daily_attention_agent/app/connectors/gmail/fetch.py))
    -   `fetch_calendar_signals` ([fetch.py](file:///home/satvik/Documents/GeniOS-AI-Agents/daily_attention_agent/app/connectors/calendar/fetch.py))
    Both use `await mcp_session.call_tool(...)` to retrieve raw data from the MCP server.
4.  **Normalization**: Raw payloads are mapped to a standard `UnifiedSignal` schema in `normalize.py`.
5.  **Scoring & LLM**: Pydantic-validated data is sent to Gemini (with Groq fallback) to assess priority, category, and attention reasons.
6.  **Guardrails**: Final validation ensures the output schema is correct and no side effects occurred.

---

## ⚙️ Setup & Configuration

### 1. Prerequisites
- Python 3.10+
- A Gemini API Key (and optionally Groq API Key).
- A running MCP Server URL (e.g., Zapier MCP Bridge).

### 2. Environment Variables (`.env`)
```env
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-flash

ZAPIER_MCP_SERVER_URL=https://mcp.zapier.com/api/v1/connect?token=...
```

### 3. Running the Server
```bash
source ./venv/bin/activate
uvicorn app.api.main:app --reload
```

### 4. Testing
The project includes a robust test suite in the `tests/` directory:
- **API Tests**: `test_api.py` verifies FastApi routing logic.
- **Mock Tests**: `test_mcp_mock.py` validates the internal agent logic using a mocked MCP tool provider.
- **Integration Tests**: `test_integration.py` attempts a real SSE handshake and tool discovery with the configured provider.

Run all tests with:
```bash
PYTHONPATH=. pytest tests/ -v
```

---

## 📁 Updated Project Structure

```text
daily_attention_agent/
├── app/
│   ├── api/            # Web Layer (FastAPI Routers, Lifespan)
│   ├── core/           # Agent Logic (LangGraph, State, Runner)
│   ├── connectors/     # MCP Tool Wrappers & Normalizers
│   ├── services/       # Persistent MCP Connections & Run Stores
│   ├── llm/            # Gemini & Groq Clients
│   └── models/         # Pydantic V2 Schemas
├── tests/              # Multi-level test suite
├── .env                # Secret keys and URLs
└── README.md           # This documentation
```

---

## 🚀 Getting Started for Developers
To start working on the agent:
1.  Verify the **MCP connection** in `app/services/mcp_client.py`.
2.  Inspect **Connector Mapping** in `app/connectors/*/fetch.py` to ensure tool names match your provider.
3.  Add new reasoning logic in `app/core/graph.py` nodes.
4.  Run `test_mcp_mock.py` to verify your changes without using LLM/MCP credits.