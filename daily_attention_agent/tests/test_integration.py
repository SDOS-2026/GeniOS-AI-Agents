import os
import pytest
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client
from app.connectors.gmail.fetch import fetch_gmail_signals
from app.connectors.calendar.fetch import fetch_calendar_signals
from app.core.state import DAAState
from dotenv import load_dotenv

load_dotenv()

@pytest.mark.asyncio
async def test_mcp_real_server_integration():
    url = os.getenv("ZAPIER_MCP_SERVER_URL")
    if not url:
        pytest.skip("ZAPIER_MCP_SERVER_URL not set")

    print(f"[DEBUG] Connecting to MCP at {url}...")
    async with sse_client(url=url) as (read, write):
        print("[DEBUG] SSE Client context entered.")
        async with ClientSession(read, write) as session:
            print("[DEBUG] Client Session wrapper started. Initializing...")
            await session.initialize()
            print("[DEBUG] Session initialized successfully.")
            
            state = DAAState(
                user_id="integration-test-user",
                workspace_id="test-workspace",
                time_window={
                    "start": "2026-04-18T00:00:00Z",
                    "end": "2026-04-20T00:00:00Z"
                },
                raw_metadata={"mcp_session": session}
            )

            # Test Gmail fetch (real request)
            gmail_results = await fetch_gmail_signals(state)
            print(f"Gmail results: {len(gmail_results)}")
            assert isinstance(gmail_results, list)

            # Test Calendar fetch (real request)
            calendar_results = await fetch_calendar_signals(state)
            print(f"Calendar results: {len(calendar_results)}")
            assert isinstance(calendar_results, list)