"""
Calendar tool handler for the MCP server.

Implements calendar_get_events using the Google Calendar API.
Returns data in the exact format the DAA normalizer expects:
  - Event dicts with: id, summary, start, end, description,
    attendees, hangoutLink, conferenceData, organizer, htmlLink
"""
import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def handle_calendar_get_events(args: Dict[str, Any]):
    """
    Get calendar events for a time range.

    Args (from DAA connector):
      - timeMin: str      ISO 8601 datetime for range start
      - timeMax: str      ISO 8601 datetime for range end
      - maxResults: int   Max events to return (default 50)

    Returns ToolResponse with content containing a JSON list of event objects.
    Each event has the structure the DAA normalizer expects:
      {
        "id": "event_id",
        "summary": "Meeting Title",
        "start": {"dateTime": "..."},
        "end": {"dateTime": "..."},
        "description": "...",
        "attendees": [...],
        "organizer": {"email": "..."},
        "htmlLink": "...",
        "hangoutLink": "...",
        "conferenceData": {...}
      }
    """
    from mcp_server.services import get_calendar_service
    from mcp_server.main import ToolResponse, ContentItem

    service = get_calendar_service()
    time_min = args.get("timeMin")
    time_max = args.get("timeMax")
    max_results = args.get("maxResults", 50)

    try:
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])
        logger.info(
            f"[Calendar] Found {len(events)} events "
            f"between {time_min} and {time_max}"
        )

        # Return as a single JSON list in one content item
        return ToolResponse(
            content=[ContentItem(text=json.dumps(events))]
        )

    except Exception as e:
        logger.exception("[Calendar] calendar_get_events failed")
        return ToolResponse(
            content=[ContentItem(text=f"Calendar API error: {e}")],
            is_error=True,
        )
