# app/connectors/gmail/fetch.py

from typing import List, Dict, Any
from datetime import datetime, timedelta

from app.core.state import DAAState
from app.core.state import DAAState
import asyncio
import json

MAX_THREADS = 50

async def fetch_gmail_signals(state: DAAState) -> List[Dict[str, Any]]:
    """
    Fetch raw Gmail thread metadata using MCP.
    Returns raw dicts (normalization happens later).
    """
    mcp_session = state.mcp_session
    if not mcp_session:
        print("[WARNING] No MCP session found in state, skipping Gmail fetch.")
        return []

    query = "in:inbox"
    if state.depth_mode == "quick":
        days = 3
    else:
        days = 7

    after_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y/%m/%d")
    query += f" after:{after_date}"

    # Call tool asynchronously
    try:
        result = await mcp_session.call_tool("gmail_search", {
            "query": query,
            "maxResults": MAX_THREADS
        })
    except Exception as e:
        print(f"[ERROR] Gmail MCP tool call failed: {e}")
        return []

    try:
        raw_threads = [json.loads(c.text) for c in result.content if getattr(c, "type", "") == "text"]
        if raw_threads and isinstance(raw_threads[0], list):
             return raw_threads[0]
        return raw_threads
    except Exception as e:
        print(f"[ERROR] Failed to parse Gmail MCP output: {e}")
        return []



