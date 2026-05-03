import json
import logging
from app.mcp_client import get_mcp_client

logger = logging.getLogger(__name__)

async def fetch_node(state):
    """
    Fetches emails from Gmail via the MCP Server based on filters in state.
    Returns a partial state update.
    """
    filters = state.get("filter_criteria", {})
    limit = filters.get("limit")
    if limit is None:
        limit = 5
    
    # If filtering by priority, fetch more to increase chance of finding matches
    target_priority = filters.get("priority", "ANY")
    fetch_limit = limit
    if target_priority != "ANY":
        fetch_limit = max(limit * 3, 20) # Fetch at least 20 or 3x request
        
    logger.info(f"[FetchNode] Fetching {fetch_limit} emails via MCP (Limit: {limit})...")
    
    try:
        mcp = get_mcp_client()
        result = await mcp.call_tool("gmail_fetch_messages", {
            "query": "in:inbox",
            "maxResults": fetch_limit
        })

        if result.is_error:
            error_text = result.content[0].text if result.content else "Unknown error"
            logger.error(f"[FetchNode] MCP error fetching emails: {error_text}")
            emails = []
        else:
            json_text = result.content[0].text if result.content else "[]"
            emails = json.loads(json_text)
            
        logger.info(f"[FetchNode] Successfully fetched {len(emails)} emails.")
            
    except Exception as e:
        logger.exception(f"[FetchNode] Exception fetching emails: {e}")
        emails = []
        
    return {"emails": emails}
