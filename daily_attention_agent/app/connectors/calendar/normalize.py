# app/connectors/calendar/normalize.py

from typing import List
from datetime import datetime, timezone

from app.models.unified_signal import UnifiedSignal


def _parse_event_timestamp(event: dict) -> datetime:
    """
    Return a timezone-aware UTC datetime for both timed and all-day events.
    """
    start = event.get("start", {})

    # Timed event (RFC3339)
    if "dateTime" in start:
        ts = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
        return ts.astimezone(timezone.utc)

    # All-day event → treat as start of day UTC
    if "date" in start:
        return datetime.fromisoformat(start["date"]).replace(
            tzinfo=timezone.utc
        )

    # Fallback (should never happen)
    return datetime.now(timezone.utc)


def normalize_calendar_events(raw_events: List[dict]) -> List[UnifiedSignal]:
    signals: List[UnifiedSignal] = []

    for event in raw_events:
        event_id = event.get("id")
        summary = event.get("summary", "(no title)")

        try:
            timestamp = _parse_event_timestamp(event)
        except Exception:
            continue

        attendees = event.get("attendees", [])
        has_meet_link = bool(
            event.get("hangoutLink")
            or event.get("conferenceData")
        )

        description = event.get("description", "") or ""
        snippet = description[:200] if description else "No description provided"

        requires_action = (
            not has_meet_link
            or (len(attendees) > 1 and not description)
        )

        signal = UnifiedSignal(
            signal_type="CALENDAR_EVENT",
            source_tool="calendar",
            record_id=event_id,
            owner=event.get("organizer", {}).get("email"),
            timestamp=timestamp,  # ✅ ALWAYS timezone-aware UTC
            title=summary,
            snippet=snippet,
            url=event.get("htmlLink"),
            requires_action=requires_action,
            raw_metadata={
                "attendee_count": len(attendees),
                "has_meet_link": has_meet_link,
                "is_all_day": "date" in event.get("start", {}),
            },
        )

        signals.append(signal)

    return signals
