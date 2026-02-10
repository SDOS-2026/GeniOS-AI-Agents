# app/rules/email_rules.py

from typing import List, Tuple
from datetime import datetime, timedelta, timezone

from app.models.unified_signal import UnifiedSignal


def apply_email_rules(
    signal: UnifiedSignal,
    vip_senders: List[str],
    keywords: List[str],
) -> Tuple[float, List[str]]:
    """
    Deterministic email scoring rules.
    Returns (score_delta, reasons)
    """
    score = 0.0
    reasons: List[str] = []

    meta = signal.raw_metadata
    last_sender = meta.get("last_sender", "").lower()

    # 1. Requires action
    if signal.requires_action:
        score += 25
        reasons.append("Email likely requires a reply")

    # 2. VIP sender
    for vip in vip_senders:
        if vip.lower() in last_sender:
            score += 30
            reasons.append("Email from VIP sender")
            break

    # 3. Keyword intent
    content = f"{signal.title} {signal.snippet}".lower()
    for kw in keywords:
        if kw.lower() in content:
            score += 15
            reasons.append(f"Contains keyword: '{kw}'")
            break

    # 4. Staleness
    now_utc = datetime.now(timezone.utc)
    age_hours = (now_utc - signal.timestamp).total_seconds() / 3600
    if age_hours > 24:
        score += 10
        reasons.append("Email pending for over 24 hours")

    if age_hours > 72:
        score += 10
        reasons.append("Email pending for over 72 hours")

    return score, reasons
