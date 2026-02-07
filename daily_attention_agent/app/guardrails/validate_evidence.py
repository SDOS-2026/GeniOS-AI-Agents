# app/guardrails/validate_evidence.py

from app.state import DAAState


def validate_evidence(state: DAAState) -> None:
    """
    Every attention item MUST cite concrete evidence.
    """
    for item in state.attention_items:
        evidence = item.get("evidence")
        assert evidence is not None, "Evidence missing"

        assert evidence.get("tool"), "Evidence missing tool"
        assert evidence.get("record_id"), "Evidence missing record_id"
        assert evidence.get("timestamp"), "Evidence missing timestamp"
        assert evidence.get("snippet"), "Evidence missing snippet"
