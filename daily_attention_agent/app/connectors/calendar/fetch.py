# app/connectors/calendar/fetch.py

from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone

from app.core.state import DAAState
from app.core.state import DAAState
import asyncio
import json

MAX_EVENTS = 50

async def fetch_calendar_signals(state: DAAState) -> List[Dict[str, Any]]:
    mcp_session = state.mcp_session
    if not mcp_session:
        print("[WARNING] No MCP session found in state, skipping Calendar fetch.")
        return []

    start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = start + timedelta(days=7)

    # Call tool asynchronously
    try:
        result = await mcp_session.call_tool("calendar_get_events", {
            "timeMin": start.isoformat(),
            "timeMax": end.isoformat(),
            "maxResults": MAX_EVENTS
        })
    except Exception as e:
        print(f"[ERROR] Calendar MCP tool call failed: {e}")
        return []

    try:
        events = [json.loads(c.text) for c in result.content if getattr(c, "type", "") == "text"]
        if events and isinstance(events[0], list):
             return events[0]
        return events
    except Exception as e:
        print(f"[ERROR] Failed to parse Calendar MCP output: {e}")
        return []


