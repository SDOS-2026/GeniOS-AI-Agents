# app/connectors/calendar/fetch.py

from typing import List, Dict, Any
from datetime import datetime, timedelta

from app.state import DAAState
from app.connectors.calendar.client import get_calendar_service


MAX_EVENTS = 50


def fetch_calendar_signals(state: DAAState) -> List[Dict[str, Any]]:
    """
    Fetch raw Google Calendar events.
    Returns raw event dicts (normalization happens later).
    """
    creds = state.raw_metadata.get("calendar_credentials")  # injected upstream
    service = get_calendar_service(creds)

    now = datetime.utcnow()
    time_min = now.isoformat() + "Z"

    if state.depth_mode == "quick":
        time_max = (now + timedelta(days=2)).isoformat() + "Z"
    else:
        time_max = (now + timedelta(days=7)).isoformat() + "Z"

    response = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        maxResults=MAX_EVENTS,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return response.get("items", [])
