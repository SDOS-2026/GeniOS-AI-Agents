# app/brief/generator.py

from typing import List, Dict, Any
from datetime import datetime

from app.rules.calendar_rules import detect_conflicts, detect_overload, detect_duplicates, detect_missing_links, detect_missing_agenda
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
        llm_brief = item.get("llm_brief")
        title = signal.title
        llm_reasoning = item.get("llm_reasoning")

        calendar_name = signal.raw_metadata.get("calendar_name", "Calendar")

        summary = None
        # ---------- Map signal → attention type ----------
        if signal.signal_type == "EMAIL_THREAD":
            item_type = "email"
            recommended_action = "Review and respond if needed"
            # Always keep original subject
            title = signal.title
            # LLM summary (if exists)
            summary = item.get("llm_brief")
            llm_reasoning = item.get("llm_reasoning")
            if isinstance(llm_reasoning, str):
                reasons = [llm_reasoning]
            elif isinstance(llm_reasoning, list):
                reasons = llm_reasoning
        elif signal.signal_type == "CALENDAR_EVENT":

            item_type = "meeting"

            if score >= 80:
                recommended_action = "Prepare in advance"
            elif score >= 40:
                recommended_action = "Check details before attending"
            else:
                recommended_action = "Attend if relevant"

        else:
            item_type = "event"
            recommended_action = "Check details"

        # ---------- Evidence ----------
        evidence = Evidence(
            tool=signal.source_tool,
            record_id=signal.record_id,
            timestamp=signal.timestamp,
            end_time=signal.end_time,
            is_all_day=signal.is_all_day,
            snippet=signal.snippet,
            calendar_name=calendar_name,
        )

        attention_item = AttentionItem(
            type=item_type,
            priority_score=score,
            priority_level=level,
            title=title,
            summary=summary,
            why_flagged=reasons,
            recommended_action=recommended_action,
            evidence=evidence,
            confidence=_confidence_from_score(score),
        )

        attention_items.append(attention_item)

        # ---------- Risks (priority-based) ----------
        if level in ("high", "critical"):
            risks.append({
                "title": signal.title,
                "reason": reasons,
                "tool": signal.source_tool,
            })

        # ---------- Opportunities ----------
        if signal.signal_type == "EMAIL_THREAD" and 25 <= score < 50:
            opportunities.append({
                "title": signal.title,
                "suggestion": "Quick response could unblock progress",
            })

    # ---------- Calendar structural risk analysis ----------
    calendar_signals = [
        item["signal"]
        for item in state.scored_items
        if item["signal"].signal_type == "CALENDAR_EVENT"
    ]

    for detector in (detect_conflicts,
                     detect_overload,
                     detect_duplicates,
                     detect_missing_links,
                     detect_missing_agenda):
        risks.extend(detector(calendar_signals))

    # ---------- Sort attention items ----------
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
    if score >= 80:
        return 0.95
    if score >= 50:
        return 0.85
    if score >= 25:
        return 0.7
    return 0.5