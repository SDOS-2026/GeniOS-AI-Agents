# app/rules/scoring.py

from typing import List, Dict, Any

from app.models.unified_signal import UnifiedSignal
from app.rules.email_rules import apply_email_rules
from app.rules.calendar_rules import apply_calendar_batch


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
) -> List[Dict[str, Any]]:
    """
    Applies scoring to unified signals.

    Calendar → Gemini batch scoring
    Email → rule-based scoring
    """

    scored_items: List[Dict[str, Any]] = []

    # --------- STEP 1: Collect calendar signals ----------
    calendar_signals = [
        s for s in unified_signals
        if s.signal_type == "CALENDAR_EVENT"
    ]

    # --------- STEP 2: Run batch Gemini scoring ----------
    if calendar_signals:
        apply_calendar_batch(calendar_signals)

    # --------- STEP 3: Score signals ----------
    for signal in unified_signals:

        score = 0.0
        reasons: List[str] = []

        # --------- Email ----------
        if signal.signal_type == "EMAIL_THREAD":

            delta, why = apply_email_rules(
                signal,
                vip_senders=vip_senders,
                keywords=keywords,
            )

            score += delta
            reasons.extend(why)

        # --------- Calendar ----------
        elif signal.signal_type == "CALENDAR_EVENT":
            # print(signal.raw_metadata)
            meta = signal.raw_metadata
            print("DEBUG CAL:", signal.title, meta.get("llm_score"))
            # print(
            #     "DEBUG CAL:",
            #     signal.title,
            #     signal.raw_metadata.get("calendar_name"),
            #     signal.raw_metadata.get("llm_score")
            # )
            score = meta.get("llm_score", 0)
            reasons = meta.get("llm_reasons", [])

        # --------- Ignore noise ----------
        if score == 0:
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