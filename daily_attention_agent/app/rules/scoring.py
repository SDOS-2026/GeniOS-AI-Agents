# app/rules/scoring.py

from typing import List, Dict, Any

from daily_attention_agent.app.models.unified_signal import UnifiedSignal
from daily_attention_agent.app.rules.email_rules import apply_email_rules, apply_email_batch
from daily_attention_agent.app.rules.calendar_rules import apply_calendar_batch


def priority_level_from_score(score: float) -> str:
    if score >= 90:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def score_signals(
    unified_signals: List[UnifiedSignal],
    vip_senders: List[str],
    keywords: List[str],
    calendar_cache: dict,
    email_cache: dict,
) -> List[Dict[str, Any]]:
    """
    Applies scoring to unified signals.

    Calendar → Gemini batch scoring
    Email → Gemini batch scoring (limit 5)
    """

    scored_items: List[Dict[str, Any]] = []

    # --------- STEP 1: Collect signals ----------
    calendar_signals = [
        s for s in unified_signals
        if s.signal_type == "CALENDAR_EVENT"
    ]

    email_signals = [
        s for s in unified_signals
        if s.signal_type == "EMAIL_THREAD"
    ]
    # Sort by timestamp descending and take top 5
    email_signals.sort(key=lambda x: x.timestamp, reverse=True)
    emails_to_score = email_signals[:5]

    # --------- STEP 2: Run batch Gemini scoring ----------
    if calendar_signals:
        apply_calendar_batch(calendar_signals, calendar_cache)

    if emails_to_score:
        apply_email_batch(emails_to_score, email_cache, vip_senders, keywords)

    # --------- STEP 3: Score signals ----------
    for signal in unified_signals:

        score = 0.0
        reasons: List[str] = []

        # --------- Email ----------
        if signal.signal_type == "EMAIL_THREAD":
            # Only score if it was in the top 5 (and thus has llm_score set)
            # or fallback if needed.
            meta = signal.raw_metadata
            if "llm_score" in meta:
                score = meta.get("llm_score", 0)
                reasons = meta.get("llm_reasons", [])
            else:
                # If not in top 5, we could either give it 0 or a very low score.
                # The user said "limit number of mails being checked to 5".
                # This implies we don't care about the others for now.
                continue

        # --------- Calendar ----------
        elif signal.signal_type == "CALENDAR_EVENT":
            meta = signal.raw_metadata
            score = meta.get("llm_score", 0)
            reasons = meta.get("llm_reasons", [])

        # --------- Ignore noise ----------
        # We skip if score is 0, UNLESS it's an email that was specifically checked
        # (indicated by the presence of llm_score in metadata).
        if score == 0 and "llm_score" not in signal.raw_metadata:
            continue

        scored_items.append({
            "signal": signal,
            "priority_score": min(score, 100.0),
            "priority_level": priority_level_from_score(score),
            "reasons": reasons,
        })

    # --------- STEP 4: Sort by priority ----------
    scored_items.sort(
        key=lambda x: x["priority_score"],
        reverse=True
    )

    return scored_items
