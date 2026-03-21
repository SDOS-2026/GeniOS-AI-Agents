# app/graph.py

from langgraph.graph import StateGraph, END
from app.state import DAAState

# ---- Import node functions (to be implemented next) ----
from app.connectors.gmail.fetch import fetch_gmail_signals
from app.connectors.calendar.fetch import fetch_calendar_signals

from app.rules.scoring import score_signals
from app.brief.generator import generate_brief

from app.guardrails.validate_schema import validate_schema
from app.guardrails.validate_evidence import validate_evidence
from app.guardrails.no_side_effects import validate_no_side_effects

from app.llm.drafts import generate_drafts_if_enabled
from app.llm.email_brief import generate_email_briefs
from app.connectors.normalize import normalize_signals



# ---------- GRAPH NODES ----------

def fetch_signals(state: DAAState) -> DAAState:
    """
    Fetch raw signals from Gmail and Calendar.
    NO LLM. NO SCORING.
    """
    if "gmail" in state.connected_tools:
        print("[DEBUG] gmail fetch start")
        state.raw_signals.extend(
            fetch_gmail_signals(state)
        )
        print("[DEBUG] gmail fetch end")

    if "calendar" in state.connected_tools:
        print("[DEBUG] cal fetch start")
        state.raw_signals.extend(
            fetch_calendar_signals(state)
        )
        print("[DEBUG] cal fetch end")

    if not state.raw_signals:
        state.warnings.append("No signals fetched from connected tools")

    return state


def rule_scoring(state: DAAState) -> DAAState:
    """
    Deterministic scoring (rules first, always).
    """
    state.scored_items = score_signals(
        unified_signals=state.unified_signals,
        vip_senders=state.vip_senders,
        keywords=state.keywords,
        calendar_cache=state.raw_metadata.setdefault("calendar_llm_cache", {}),
        email_cache=state.raw_metadata.setdefault("email_llm_cache", {})
    )
    return state


def llm_optional(state: DAAState) -> DAAState:

    emails_for_llm = []

    for item in state.scored_items:

        signal = item["signal"]

        if signal.signal_type != "EMAIL_THREAD":
            continue

        if item["priority_level"] not in ["medium", "high", "critical"]:
            continue

        emails_for_llm.append(item)

    if emails_for_llm:

        results = generate_email_briefs(emails_for_llm)

        for item in state.scored_items:

            signal = item["signal"]

            if signal.record_id in results:
                item["llm_brief"] = results[signal.record_id]["brief"]
                item["llm_reasoning"] = results[signal.record_id]["reasoning"]

    return state


def guardrails(state: DAAState) -> DAAState:
    """
    Hard stop if any rule is violated.
    """
    validate_schema(state)
    validate_evidence(state)
    validate_no_side_effects(state)

    state.run_completed_at = state.run_completed_at or state.run_started_at
    return state


# ---------- GRAPH DEFINITION ----------

def build_graph():
    graph = StateGraph(DAAState)

    # Nodes
    graph.add_node("fetch_signals", fetch_signals)
    graph.add_node("normalize", normalize_signals)
    graph.add_node("score", rule_scoring)
    graph.add_node("llm_optional", llm_optional)
    graph.add_node("generate_brief", generate_brief)
    graph.add_node("guardrails", guardrails)

    # Entry
    graph.set_entry_point("fetch_signals")

    # Edges
    graph.add_edge("fetch_signals", "normalize")
    graph.add_edge("normalize","score")
    graph.add_edge("score", "llm_optional")
    graph.add_edge("llm_optional", "generate_brief")
    graph.add_edge("generate_brief", "guardrails")
    graph.add_edge("guardrails", END)

    return graph.compile()
