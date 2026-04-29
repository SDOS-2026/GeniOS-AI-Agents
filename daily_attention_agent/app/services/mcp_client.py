import os
from mcp import ClientSession
from mcp.client.sse import sse_client
from contextlib import asynccontextmanager
from typing import Optional

class MCPConnectionManager:
    _session: Optional[ClientSession] = None
    
    @classmethod
    def get_session(cls) -> Optional[ClientSession]:
        return cls._session
        
    @classmethod
    def set_session(cls, session: ClientSession):
        cls._session = session

@asynccontextmanager
async def lifespan(app):
    url = os.getenv("ZAPIER_MCP_SERVER_URL")
    if url:
        print("[DEBUG] Connecting to Zapier MCP at:", url)
        try:
            async with sse_client(url=url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    print("[DEBUG] Zapier MCP Connected Successfully.")
                    MCPConnectionManager.set_session(session)
                    app.state.mcp_session = session
                    yield
        except Exception as e:
            print(f"[ERROR] MCP Connection failed: {e}")
            yield
    else:
        print("[WARNING] ZAPIER_MCP_SERVER_URL not found, skipping MCP connection.")
        yield
