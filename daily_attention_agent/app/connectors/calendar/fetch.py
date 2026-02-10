# app/connectors/calendar/fetch.py

from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone

from app.state import DAAState
from app.connectors.calendar.client import get_calendar_service

MAX_EVENTS = 50


def fetch_calendar_signals(state: DAAState) -> List[Dict[str, Any]]:
    creds = state.raw_metadata.get("calendar_credentials")
    service = get_calendar_service(creds)

    start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = start + timedelta(days=7)

    events: List[Dict[str, Any]] = []

    # 🔑 STEP 1: list all calendars
    calendar_list = service.calendarList().list().execute()

    # print("[DEBUG] Calendars found:")
    for cal in calendar_list.get("items", []):
        # print(
        #     " -",
        #     cal["summary"],
        #     "| id:",
        #     cal["id"],
        #     "| primary:",
        #     cal.get("primary", False),
        # )

        # 🔑 STEP 2: fetch events from EACH calendar
        resp = service.events().list(
            calendarId=cal["id"],
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            maxResults=MAX_EVENTS,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        items = resp.get("items", [])
        # print(f"   → {len(items)} events")

        for ev in items:
            ev["_calendar_name"] = cal["summary"]
            ev["_calendar_id"] = cal["id"]
            events.append(ev)

    # print(f"[DEBUG] Total calendar events fetched: {len(events)}")
    return events
