# app/connectors/calendar/normalize.py

from typing import List
from datetime import datetime, timezone
from datetime import timedelta
from app.models.unified_signal import UnifiedSignal


def _parse_event_timestamp(event: dict) -> datetime:
    if not event:
        return None

    if "dateTime" in event:
        return datetime.fromisoformat(event["dateTime"].replace("Z", "+00:00")).astimezone(timezone.utc)

    if "date" in event:
        return datetime.fromisoformat(event["date"]).replace(tzinfo=timezone.utc)

    return None


def normalize_calendar_events(raw_events: List[dict]) -> List[UnifiedSignal]:
    signals: List[UnifiedSignal] = []

    for event in raw_events:
        event_id = event.get("id")
        summary = event.get("summary", "(no title)")

        try:
            start_time = _parse_event_timestamp(event.get("start"))
            end_time = _parse_event_timestamp(event.get("end"))

            if not start_time:
                continue

            is_all_day = "date" in event.get("start", {})

            if start_time and not end_time and not is_all_day:
                end_time = start_time + timedelta(hours=1)
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
            timestamp=start_time,  # ✅ ALWAYS timezone-aware UTC
            end_time=end_time,
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
