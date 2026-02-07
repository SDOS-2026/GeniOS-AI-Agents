# app/brief/generator.py

from typing import List, Dict, Any
from datetime import datetime

from app.state import DAAState
from app.models.attention_item import AttentionItem, Evidence


def generate_brief(state: DAAState) -> DAAState:
    """
    Build the Daily Attention Brief from scored items.
    Deterministic. Evidence-first. V1-safe.
    """

    attention_items: List[AttentionItem] = []
    risks: List[Dict[str, Any]] = []
    opportunities: List[Dict[str, Any]] = []

    for item in state.scored_items:
        signal = item["signal"]
        score = item["priority_score"]
        level = item["priority_level"]
        reasons = item["reasons"]

        # ---------- Map signal → attention type ----------
        if signal.signal_type == "EMAIL_THREAD":
            item_type = "email"
            recommended_action = "Review and respond to this email"
        else:
            item_type = "meeting"
            recommended_action = "Prepare for this meeting"

        # ---------- Evidence (mandatory) ----------
        evidence = Evidence(
            tool=signal.source_tool,
            record_id=signal.record_id,
            timestamp=signal.timestamp,
            snippet=signal.snippet,
        )

        attention_item = AttentionItem(
            type=item_type,
            priority_score=score,
            priority_level=level,
            title=signal.title,
            why_flagged=reasons,
            recommended_action=recommended_action,
            evidence=evidence,
            confidence=_confidence_from_score(score),
        )

        attention_items.append(attention_item)

        # ---------- Risks (V1: simple heuristic) ----------
        if level in ("high", "critical"):
            risks.append({
                "title": signal.title,
                "reason": reasons,
                "tool": signal.source_tool,
            })

        # ---------- Opportunities (V1: soft signal) ----------
        if signal.signal_type == "EMAIL_THREAD" and score >= 25 and score < 50:
            opportunities.append({
                "title": signal.title,
                "suggestion": "Quick response could unblock progress",
            })

    # Sort again defensively
    attention_items.sort(
        key=lambda x: x.priority_score,
        reverse=True
    )

    # ---------- Attach to state ----------
    state.attention_items = [item.dict() for item in attention_items]
    state.risks = risks
    state.opportunities = opportunities

    return state


def _confidence_from_score(score: float) -> float:
    """
    Simple, explainable confidence mapping.
    """
    if score >= 80:
        return 0.95
    if score >= 50:
        return 0.85
    if score >= 25:
        return 0.7
    return 0.5
