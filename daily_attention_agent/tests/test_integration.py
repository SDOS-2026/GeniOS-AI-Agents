import os
import pytest
import asyncio

# Skip long-running external integration tests by default. To run them set:
# RUN_DAA_INTEGRATION=1 and provide MCP_SERVER_URL or other service endpoints.
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DAA_INTEGRATION") != "1",
    reason="External integration tests disabled by default"
)
from daily_attention_agent.app.connectors.gmail.fetch import fetch_gmail_signals
from daily_attention_agent.app.connectors.calendar.fetch import fetch_calendar_signals
from daily_attention_agent.app.core.state import DAAState
from daily_attention_agent.app.services.mcp_client import MCPHttpAdapter
from dotenv import load_dotenv

load_dotenv()

@pytest.mark.asyncio
async def test_mcp_server_integration():
    """
    Integration test against the self-hosted MCP server.
    Requires the MCP server to be running on MCP_SERVER_URL.
    """
    url = os.getenv("MCP_SERVER_URL")
    if not url:
        pytest.skip("MCP_SERVER_URL not set")

    print(f"[DEBUG] Connecting to MCP Server at {url}...")
    adapter = MCPHttpAdapter(base_url=url)

    state = DAAState(
        user_id="integration-test-user",
        workspace_id="test-workspace",
        time_window={
            "start": "2026-04-18T00:00:00Z",
            "end": "2026-04-20T00:00:00Z"
        },
        mcp_session=adapter,
    )

    # Test Gmail fetch (real request)
    gmail_results = await fetch_gmail_signals(state)
    print(f"Gmail results: {len(gmail_results)}")
    assert isinstance(gmail_results, list)

    # Test Calendar fetch (real request)
    calendar_results = await fetch_calendar_signals(state)
    print(f"Calendar results: {len(calendar_results)}")
    assert isinstance(calendar_results, list)



