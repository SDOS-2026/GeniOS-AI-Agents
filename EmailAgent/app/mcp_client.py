"""
MCP Client Adapter for the EmailAgent.
Connects the EmailAgent to the self-hosted MCP Server over HTTP.

This enables the EmailAgent to fetch and send emails via the centralized
MCP server, rather than managing its own Google credentials directly.
"""
import os
import httpx
import logging
from typing import Optional, Any, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ToolContent:
    """Mimics MCP's content item structure."""
    type: str
    text: str


@dataclass
class ToolResult:
    """Mimics MCP's call_tool response structure."""
    content: list  # List[ToolContent]
    is_error: bool = False


class MCPHttpAdapter:
    """
    HTTP client that proxies requests to the self-hosted MCP server.
    Matches the interface of mcp.ClientSession for easy migration.
    """
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        logger.debug(f"[MCP Client] Calling tool '{tool_name}'")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/call_tool",
                    json={"tool_name": tool_name, "arguments": arguments},
                    timeout=30.0,
                )
                resp.raise_for_status()
                data = resp.json()
                
                content = [
                    ToolContent(type=c.get("type", "text"), text=c.get("text", ""))
                    for c in data.get("content", [])
                ]
                is_error = data.get("isError", False)
                
                return ToolResult(content=content, is_error=is_error)
            
            except httpx.HTTPStatusError as e:
                logger.error(f"[MCP Client] HTTP error calling '{tool_name}': {e.response.text}")
                return ToolResult(
                    content=[ToolContent(type="text", text=f"HTTP Error: {e.response.status_code}")],
                    is_error=True
                )
            except Exception as e:
                logger.error(f"[MCP Client] Request error calling '{tool_name}': {e}")
                return ToolResult(
                    content=[ToolContent(type="text", text=f"Request Error: {e}")],
                    is_error=True
                )

    async def initialize(self):
        """No-op for HTTP adapter."""
        pass


class MCPConnectionManager:
    _session: Optional[MCPHttpAdapter] = None

    @classmethod
    def get_session(cls) -> MCPHttpAdapter:
        if cls._session is None:
            raise RuntimeError("MCP client not initialized. Call initialize_mcp_client() first.")
        return cls._session

    @classmethod
    def set_session(cls, session: MCPHttpAdapter):
        cls._session = session


def get_mcp_client() -> MCPHttpAdapter:
    """Helper to get the global MCP client instance."""
    return MCPConnectionManager.get_session()


def initialize_mcp_client():
    """Initializes the MCP client with the URL from the environment."""
    url = os.getenv("MCP_SERVER_URL", "http://localhost:9000")
    logger.info(f"[EmailAgent] Initializing MCP Client targeting: {url}")
    adapter = MCPHttpAdapter(base_url=url)
    MCPConnectionManager.set_session(adapter)
