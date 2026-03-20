# app/connectors/calendar/normalize.py

from typing import List
from datetime import datetime, timezone

from app.models.unified_signal import UnifiedSignal


def _parse_event_time(event: dict) -> tuple[datetime, datetime, bool]:
    """
    Return (start, end, is_all_day) as timezone-aware UTC datetimes.
    """
    start_data = event.get("start", {})
    end_data = event.get("end", {})

    is_all_day = "date" in start_data

    if "dateTime" in start_data:
        # Timed event (RFC3339)
        start_ts = datetime.fromisoformat(start_data["dateTime"].replace("Z", "+00:00")).astimezone(timezone.utc)
        end_ts = None
        if "dateTime" in end_data:
            end_ts = datetime.fromisoformat(end_data["dateTime"].replace("Z", "+00:00")).astimezone(timezone.utc)
        
        # If no end time, default to start + 30m or same as start
        return start_ts, end_ts or start_ts, False

    if "date" in start_data:
        # All-day event
        start_ts = datetime.fromisoformat(start_data["date"]).replace(tzinfo=timezone.utc)
        end_ts = start_ts
        if "date" in end_data:
            end_ts = datetime.fromisoformat(end_data["date"]).replace(tzinfo=timezone.utc)
        
        return start_ts, end_ts, True

    # Fallback
    now = datetime.now(timezone.utc)
    return now, now, False


def normalize_calendar_events(raw_events: List[dict]) -> List[UnifiedSignal]:
    signals: List[UnifiedSignal] = []

    for event in raw_events:
        event_id = event.get("id")
        summary = event.get("summary", "(no title)")

        try:
            start_ts, end_ts, is_all_day = _parse_event_time(event)
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
            timestamp=start_ts,  # ✅ ALWAYS timezone-aware UTC
            end_time=end_ts,
            is_all_day=is_all_day,
            title=summary,
            snippet=snippet,
            url=event.get("htmlLink"),
            requires_action=requires_action,
            raw_metadata={
                "attendee_count": len(attendees),
                "has_meet_link": has_meet_link,
                "is_all_day": is_all_day,
                "calendar_name": event.get("_calendar_name"),
                "calendar_id": event.get("_calendar_id"),
                "llm_cached": False,
            }
        )

        signals.append(signal)

    return signals
