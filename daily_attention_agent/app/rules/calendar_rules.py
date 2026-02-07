# app/rules/calendar_rules.py

from typing import List, Tuple
from datetime import datetime

from app.models.unified_signal import UnifiedSignal


def apply_calendar_rules(signal: UnifiedSignal) -> Tuple[float, List[str]]:
    """
    Deterministic calendar scoring rules.
    Returns (score_delta, reasons)
    """
    score = 0.0
    reasons: List[str] = []

    meta = signal.raw_metadata

    # 1. Meeting starting soon
    hours_until = (signal.timestamp - datetime.utcnow()).total_seconds() / 3600
    if 0 <= hours_until <= 2:
        score += 30
        reasons.append("Meeting starting within 2 hours")

    # 2. Missing meeting link
    if not meta.get("has_meet_link", True):
        score += 20
        reasons.append("Meeting missing video / location link")

    # 3. No description / agenda
    if not signal.snippet or signal.snippet == "No description provided":
        score += 15
        reasons.append("Meeting has no agenda or notes")

    # 4. Multiple attendees (higher coordination risk)
    attendee_count = meta.get("attendee_count", 0)
    if attendee_count >= 3:
        score += 10
        reasons.append("Meeting involves multiple attendees")

    return score, reasons
