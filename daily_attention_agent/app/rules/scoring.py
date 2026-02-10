# app/rules/scoring.py

from typing import List, Dict, Any

from app.models.unified_signal import UnifiedSignal
from app.rules.email_rules import apply_email_rules
from app.rules.calendar_rules import apply_calendar_rules


def priority_level_from_score(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def score_signals(
    unified_signals: List[UnifiedSignal],
    vip_senders: List[str],
    keywords: List[str],
) -> List[Dict[str, Any]]:
    """
    Applies deterministic rules to all unified signals.
    Returns scored items with reasons.
    """
    # print(f"[DEBUG] Scoring {len(unified_signals)} signals")
    # for s in unified_signals:
    #     print(
    #         "  -",
    #         s.signal_type,
    #         "|",
    #         s.title,
    #     )
    scored_items: List[Dict[str, Any]] = []

    for signal in unified_signals:
        score = 0.0
        reasons: List[str] = []

        if signal.signal_type == "EMAIL_THREAD":
            delta, why = apply_email_rules(
                signal,
                vip_senders=vip_senders,
                keywords=keywords,
            )
            score += delta
            reasons.extend(why)

        elif signal.signal_type == "CALENDAR_EVENT":
            delta, why = apply_calendar_rules(signal)
            score += delta
            reasons.extend(why)

        if score == 0:
            continue  # ignore noise in V1

        scored_items.append({
            "signal": signal,
            "priority_score": min(score, 100.0),
            "priority_level": priority_level_from_score(score),
            "reasons": reasons,
        })

    # Sort highest priority first
    scored_items.sort(key=lambda x: x["priority_score"], reverse=True)
    # print(f"[DEBUG] Scored items: {len(scored_items)}")
    # for item in scored_items:
    #     print(
    #         "  -",
    #         item["signal"].signal_type,
    #         "|",
    #         item["signal"].title,
    #         "| score:",
    #         item["priority_score"],
    #     )
    
    return scored_items
