"""
Integration Tests: DAA FastAPI Endpoints & MCP Mock
Tests the full HTTP API layer and agent execution with mocked MCP tools.

Run with: pytest test_daa_api_integration.py -v
"""

import os
import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

# Skip integration tests by default; set `RUN_DAA_INTEGRATION=1` to run.
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DAA_INTEGRATION") != "1",
    reason="Integration tests require local services; set RUN_DAA_INTEGRATION=1 to enable"
)


# ==============================================================
# FASTAPI ENDPOINT TESTS (using TestClient — no real server needed)
# ==============================================================

class TestDAAAPI:

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from daily_attention_agent.app.api.main import app
        return TestClient(app)

    def test_root_endpoint_returns_200(self, client):
        """GET / must return 200 with a running message."""
        response = client.get("/")
        assert response.status_code == 200
        assert "running" in response.json()["message"].lower()

    def test_run_endpoint_returns_run_id(self, client):
        """POST /run must return a run_id and status=running immediately."""
        payload = {
            "user_id": "test_user",
            "workspace_id": "test_workspace",
            "vip_senders": [],
            "keywords": [],
        }
        response = client.post("/run", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["status"] == "running"

    def test_status_endpoint_unknown_id_returns_404(self, client):
        """GET /status/<invalid_id> must return 404."""
        response = client.get("/status/nonexistent-run-id")
        assert response.status_code == 404

    def test_status_endpoint_returns_run_data(self, client):
        """After starting a run, /status/<run_id> must return the run entry."""
        from daily_attention_agent.app.services.run_store import run_store

        run_id = "test-status-check"
        run_store[run_id] = {"status": "success", "result": {"attention_items": []}}

        response = client.get(f"/status/{run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Cleanup
        del run_store[run_id]

    def test_history_endpoint_returns_list(self, client):
        """GET /history must return a list (possibly empty)."""
        response = client.get("/history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_run_endpoint_accepts_all_optional_fields(self, client):
        """POST /run with all optional fields must succeed."""
        payload = {
            "user_id": "power_user",
            "workspace_id": "corp_workspace",
            "vip_senders": ["ceo@example.com", "founder@startup.io"],
            "keywords": ["urgent", "deadline", "invoice"],
            "depth_mode": "deep",
            "output_mode": "brief_only",
        }
        response = client.post("/run", json=payload)
        assert response.status_code == 200

    def test_run_endpoint_missing_required_field_returns_422(self, client):
        """POST /run without 'user_id' must return 422 Unprocessable Entity."""
        payload = {"workspace_id": "ws"}  # missing user_id
        response = client.post("/run", json=payload)
        assert response.status_code == 422


# ==============================================================
# MCP MOCK INTEGRATION TESTS (Async)
# ==============================================================

class MockContent:
    def __init__(self, text):
        self.type = "text"
        self.text = text

class MockToolResult:
    def __init__(self, data):
        self.content = [MockContent(json.dumps(data))]

class MockMCPSession:
    """Simulates a real MCP session with controllable responses."""
    def __init__(self, gmail_data=None, calendar_data=None):
        self.gmail_data = gmail_data or []
        self.calendar_data = calendar_data or []

    async def call_tool(self, tool_name: str, arguments: dict):
        if tool_name == "gmail_search":
            return MockToolResult(self.gmail_data)
        if tool_name == "calendar_get_events":
            return MockToolResult(self.calendar_data)
        raise ValueError(f"Unknown tool: {tool_name}")


def _sample_gmail_thread():
    return {
        "id": "thread_001",
        "messages": [{
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Urgent: Review Required"},
                    {"name": "From", "value": "boss@company.com"},
                    {"name": "Date", "value": "Mon, 01 Jan 2026 10:00:00 +0000"},
                ]
            },
            "snippet": "Please review the attached report urgently.",
        }]
    }

def _sample_calendar_event():
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    return {
        "id": "evt_001",
        "summary": "All Hands Meeting",
        "start": {"dateTime": (now + timedelta(hours=2)).isoformat()},
        "end": {"dateTime": (now + timedelta(hours=3)).isoformat()},
        "description": "Q1 company update",
        "attendees": [{"email": f"p{i}@company.com"} for i in range(5)],
        "hangoutLink": "https://meet.google.com/abc",
        "organizer": {"email": "organizer@company.com"},
        "htmlLink": "https://cal.google.com/event",
    }


@pytest.mark.asyncio
async def test_gmail_fetch_with_mock_session():
    """fetch_gmail_signals must return structured data from mocked MCP session."""
    from daily_attention_agent.app.connectors.gmail.fetch import fetch_gmail_signals
    from daily_attention_agent.app.core.state import DAAState

    mcp = MockMCPSession(gmail_data=[_sample_gmail_thread()])
    state = DAAState(
        user_id="u1", workspace_id="w1",
        time_window={"start": datetime.now(timezone.utc), "end": datetime.now(timezone.utc)},
        mcp_session=mcp,
    )

    result = await fetch_gmail_signals(state)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["id"] == "thread_001"


@pytest.mark.asyncio
async def test_calendar_fetch_with_mock_session():
    """fetch_calendar_signals must return structured data from mocked MCP session."""
    from daily_attention_agent.app.connectors.calendar.fetch import fetch_calendar_signals
    from daily_attention_agent.app.core.state import DAAState

    mcp = MockMCPSession(calendar_data=[_sample_calendar_event()])
    state = DAAState(
        user_id="u1", workspace_id="w1",
        time_window={"start": datetime.now(timezone.utc), "end": datetime.now(timezone.utc)},
        mcp_session=mcp,
    )

    result = await fetch_calendar_signals(state)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["id"] == "evt_001"


@pytest.mark.asyncio
async def test_fetch_returns_empty_list_when_mcp_fails():
    """If MCP call raises an exception, fetch functions must return [] not raise."""
    from daily_attention_agent.app.connectors.gmail.fetch import fetch_gmail_signals
    from daily_attention_agent.app.core.state import DAAState

    class FailingMCPSession:
        async def call_tool(self, *args, **kwargs):
            raise ConnectionError("MCP server unavailable")

    state = DAAState(
        user_id="u1", workspace_id="w1",
        time_window={"start": datetime.now(timezone.utc), "end": datetime.now(timezone.utc)},
        mcp_session=FailingMCPSession(),
    )

    result = await fetch_gmail_signals(state)
    assert result == []


@pytest.mark.asyncio
async def test_no_mcp_session_returns_empty():
    """fetch functions must return [] gracefully if mcp_session is None."""
    from daily_attention_agent.app.connectors.gmail.fetch import fetch_gmail_signals
    from daily_attention_agent.app.core.state import DAAState

    state = DAAState(
        user_id="u1", workspace_id="w1",
        time_window={"start": datetime.now(timezone.utc), "end": datetime.now(timezone.utc)},
        mcp_session=None,
    )

    result = await fetch_gmail_signals(state)
    assert result == []


# ==============================================================
# GATEWAY PROXY TESTS
# ==============================================================

class TestGatewayProxy:

    @pytest.fixture
    def gateway_client(self):
        from fastapi.testclient import TestClient
        from gateway.main import app
        return TestClient(app)

    def test_gateway_root_is_healthy(self, gateway_client):
        """GET / on gateway must return a healthy status."""
        response = gateway_client.get("/")
        assert response.status_code == 200
        assert "gateway" in response.json()["message"].lower()

    def test_gateway_unknown_service_returns_404(self, gateway_client):
        """Routing to an unknown service key must return 404."""
        response = gateway_client.get("/unknownservice/health")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data or "Unknown service" in str(data)
