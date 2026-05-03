"""
GeniOS MCP Server — self-hosted replacement for Zapier MCP.

Exposes tool endpoints that match Zapier's tool names exactly:
  - gmail_search
  - calendar_get_events

This ensures zero changes to DAA connector code.

On startup, checks for Google OAuth credentials and exits with
a clear message if they are missing.
"""
import os
import sys
import json
import logging
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, List
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Credential check ----------

CREDENTIALS_PATH = os.getenv(
    "GOOGLE_CREDENTIALS_PATH",
    os.path.join(os.path.dirname(__file__), "credentials.json"),
)


def check_credentials():
    """
    Verify that Google OAuth credentials exist on disk.
    If not, print clear instructions and exit.
    """
    cred_file = Path(CREDENTIALS_PATH)
    if not cred_file.exists():
        logger.error(
            "\n"
            "========================================================\n"
            "  MISSING: Google OAuth credentials file\n"
            f"  Expected at: {cred_file.resolve()}\n"
            "\n"
            "  To fix:\n"
            "  1. Go to https://console.cloud.google.com/apis/credentials\n"
            "  2. Create an OAuth 2.0 Client ID (Desktop app)\n"
            "  3. Download the JSON and save it as:\n"
            f"     {cred_file.resolve()}\n"
            "  4. Set GOOGLE_CREDENTIALS_PATH env var if using a custom path\n"
            "========================================================\n"
        )
        sys.exit(1)

    logger.info(f"[OK] Credentials file found: {cred_file.resolve()}")


# ---------- Lifespan ----------

@asynccontextmanager
async def lifespan(app):
    check_credentials()

    # Eagerly initialize Google API services (triggers OAuth flow if needed)
    from mcp_server.services import get_gmail_service, get_calendar_service
    try:
        get_gmail_service()
        get_calendar_service()
        logger.info("[MCP Server] Google API services initialized.")
    except Exception as e:
        logger.error(f"[MCP Server] Failed to initialize Google services: {e}")
        logger.error("Run the server interactively to complete the OAuth flow.")
        sys.exit(1)

    logger.info("[MCP Server] Startup complete — ready to serve tool calls.")
    yield
    logger.info("[MCP Server] Shutting down.")


# ---------- App ----------

app = FastAPI(
    title="GeniOS MCP Server",
    description="Self-hosted MCP tool server for Gmail and Calendar.",
    lifespan=lifespan,
)


class ContentItem(BaseModel):
    type: str = "text"
    text: str


class ToolRequest(BaseModel):
    tool_name: str  # e.g. "gmail_search", "calendar_get_events"
    arguments: Dict[str, Any]


class ToolResponse(BaseModel):
    content: List[ContentItem]
    is_error: bool = False


# ---------- Import tool handlers ----------

from mcp_server.tools.gmail import handle_gmail_search
from mcp_server.tools.calendar import handle_calendar_get_events
from mcp_server.tools.email import handle_gmail_fetch_messages, handle_gmail_send

TOOL_REGISTRY = {
    "gmail_search": handle_gmail_search,
    "calendar_get_events": handle_calendar_get_events,
    "gmail_fetch_messages": handle_gmail_fetch_messages,
    "gmail_send": handle_gmail_send,
}


@app.get("/")
def read_root():
    return {
        "message": "GeniOS MCP Server is running.",
        "available_tools": list(TOOL_REGISTRY.keys()),
    }


@app.post("/call_tool")
async def call_tool(request: ToolRequest) -> ToolResponse:
    """
    Route tool calls to the appropriate handler.
    Tool names match Zapier's exactly so connectors need no changes.
    """
    handler = TOOL_REGISTRY.get(request.tool_name)
    if not handler:
        return ToolResponse(
            content=[ContentItem(text=f"Unknown tool: {request.tool_name}")],
            is_error=True,
        )
    try:
        return await handler(request.arguments)
    except Exception as e:
        logger.exception(f"Tool '{request.tool_name}' failed")
        return ToolResponse(
            content=[ContentItem(text=f"Tool error: {e}")],
            is_error=True,
        )
