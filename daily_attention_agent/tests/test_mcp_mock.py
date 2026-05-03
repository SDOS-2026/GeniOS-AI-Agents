import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock
from daily_attention_agent.app.connectors.gmail.fetch import fetch_gmail_signals
from daily_attention_agent.app.connectors.calendar.fetch import fetch_calendar_signals
from daily_attention_agent.app.core.state import DAAState

class MockContent:
    def __init__(self, text):
        self.type = "text"
        self.text = text

class MockResult:
    def __init__(self, content):
        self.content = content

class MockMCPSession:
    def __init__(self, mock_response_data):
        self.mock_response_data = mock_response_data

    async def call_tool(self, name, args):
        text_content = json.dumps(self.mock_response_data)
        return MockResult([MockContent(text_content)])
@pytest.mark.asyncio
async def test_fetch_gmail_signals_with_mock_mcp():
    mock_threads = [
        {"id": "msg1", "messages": [{"payload": {"headers": [{"name": "Subject", "value": "Test Subject"}]}}]},
    ]
    
    mcp_session = MockMCPSession(mock_threads)
    state = DAAState(
        user_id="test",
        workspace_id="test",
        time_window={"start": "2026-04-18T00:00:00Z", "end": "2026-04-20T00:00:00Z"},
        mcp_session=mcp_session,
    )
    
    result = await fetch_gmail_signals(state)
    print("Fetch email results: ",result)
    assert len(result) == 1
    assert result[0]["id"] == "msg1"

@pytest.mark.asyncio
async def test_fetch_calendar_signals_with_mock_mcp():
    mock_events = [
        {"id": "evt1", "summary": "Test Meeting", "start": {"dateTime": "2026-04-19T10:00:00Z"}},
    ]
    
    mcp_session = MockMCPSession(mock_events)
    state = DAAState(
        user_id="test",
        workspace_id="test",
        time_window={"start": "2026-04-18T00:00:00Z", "end": "2026-04-20T00:00:00Z"},
        mcp_session=mcp_session,
    )
    
    result = await fetch_calendar_signals(state)
    print("Fetch calendar results:", result)
    assert len(result) == 1
    assert result[0]["id"] == "evt1"

