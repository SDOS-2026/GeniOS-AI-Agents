# app/connectors/calendar/normalize.py

from typing import List
from datetime import datetime

from app.models.unified_signal import UnifiedSignal


def normalize_calendar_events(raw_events: List[dict]) -> List[UnifiedSignal]:
    signals: List[UnifiedSignal] = []

    for event in raw_events:
        event_id = event.get("id")
        summary = event.get("summary", "(no title)")

        start = event.get("start", {})
        start_time = start.get("dateTime") or start.get("date")

        if not start_time:
            continue

        try:
            timestamp = datetime.fromisoformat(start_time.replace("Z", ""))
        except Exception:
            continue

        attendees = event.get("attendees", [])
        has_meet_link = bool(
            event.get("hangoutLink")
            or event.get("conferenceData")
        )

        description = event.get("description", "") or ""
        snippet = description[:200]

        requires_action = (
            not has_meet_link
            or len(attendees) > 1 and not description
        )

        signal = UnifiedSignal(
            signal_type="CALENDAR_EVENT",
            source_tool="calendar",
            record_id=event_id,
            owner=event.get("organizer", {}).get("email"),
            timestamp=timestamp,
            title=summary,
            snippet=snippet or "No description provided",
            url=event.get("htmlLink"),
            requires_action=requires_action,
            raw_metadata={
                "attendee_count": len(attendees),
                "has_meet_link": has_meet_link,
                "is_all_day": "date" in start,
            },
        )

        signals.append(signal)

    return signals
