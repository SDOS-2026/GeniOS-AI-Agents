"""
MCP Client Adapter — connects DAA to the self-hosted MCP server over HTTP.

Provides MCPHttpAdapter which is a drop-in replacement for mcp.ClientSession.call_tool().
The adapter returns objects with .content[].type and .content[].text attributes,
matching the MCP SDK interface so that connectors (gmail/fetch.py, calendar/fetch.py)
need zero changes.
"""
import os
import httpx
from contextlib import asynccontextmanager
from typing import Optional, Any, Dict
from dataclasses import dataclass, field


@dataclass
class ToolContent:
    """Mimics MCP's content item structure."""
    type: str
    text: str


@dataclass
class ToolResult:
    """Mimics MCP's call_tool response structure."""
    content: list  # List[ToolContent]


class MCPHttpAdapter:
    """
    Drop-in replacement for mcp.ClientSession.call_tool().
    Routes requests to our self-hosted MCP server over HTTP.
    """
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/call_tool",
                json={"tool_name": tool_name, "arguments": arguments},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            content = [
                ToolContent(type=c["type"], text=c["text"])
                for c in data["content"]
            ]
            return ToolResult(content=content)

    async def initialize(self):
        """No-op for HTTP adapter (compatibility with MCP ClientSession)."""
        pass


class MCPConnectionManager:
    _session: Optional[Any] = None

    @classmethod
    def get_session(cls) -> Optional[Any]:
        return cls._session

    @classmethod
    def set_session(cls, session: Any):
        cls._session = session


@asynccontextmanager
async def lifespan(app):
    url = os.getenv("MCP_SERVER_URL")
    if url:
        print(f"[DEBUG] Connecting to MCP Server at: {url}")
        adapter = MCPHttpAdapter(base_url=url)
        MCPConnectionManager.set_session(adapter)
        print("[DEBUG] MCP HTTP Adapter ready.")
        yield
    else:
        print("[WARNING] MCP_SERVER_URL not set, skipping MCP connection.")
        yield
