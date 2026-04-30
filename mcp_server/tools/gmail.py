"""
Gmail tool handler for the MCP server.

Implements gmail_search using the Google Gmail API.
Returns data in the exact format the DAA normalizer expects:
  - Thread dicts with: id, messages[].payload.headers[], messages[].snippet
"""
import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def handle_gmail_search(args: Dict[str, Any]):
    """
    Search Gmail threads and return full thread data.

    Args (from DAA connector):
      - query: str        Gmail search query (e.g. "in:inbox after:2026/04/01")
      - maxResults: int   Max threads to return (default 50)

    Returns ToolResponse with content containing a JSON list of thread objects.
    Each thread has the structure the DAA normalizer expects:
      {
        "id": "thread_id",
        "messages": [{
          "payload": {"headers": [{"name": "Subject", "value": "..."}, ...]},
          "snippet": "..."
        }]
      }
    """
    from mcp_server.services import get_gmail_service
    from mcp_server.main import ToolResponse, ContentItem

    service = get_gmail_service()
    query = args.get("query", "in:inbox")
    max_results = args.get("maxResults", 50)

    try:
        # Step 1: List threads matching the query
        list_result = (
            service.users()
            .threads()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

        thread_ids = [t["id"] for t in list_result.get("threads", [])]
        logger.info(f"[Gmail] Found {len(thread_ids)} threads for query: {query}")

        if not thread_ids:
            return ToolResponse(content=[ContentItem(text="[]")])

        # Step 2: Fetch full thread data for each thread
        threads = []
        for tid in thread_ids:
            try:
                thread = (
                    service.users()
                    .threads()
                    .get(userId="me", id=tid, format="metadata",
                         metadataHeaders=["Subject", "From", "Date", "To"])
                    .execute()
                )
                threads.append(thread)
            except Exception as e:
                logger.warning(f"[Gmail] Failed to fetch thread {tid}: {e}")
                continue

        logger.info(f"[Gmail] Returning {len(threads)} full thread objects.")

        # Return as a single JSON list in one content item
        return ToolResponse(
            content=[ContentItem(text=json.dumps(threads))]
        )

    except Exception as e:
        logger.exception("[Gmail] gmail_search failed")
        return ToolResponse(
            content=[ContentItem(text=f"Gmail API error: {e}")],
            is_error=True,
        )
