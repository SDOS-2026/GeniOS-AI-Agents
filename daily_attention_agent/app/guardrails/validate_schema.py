# app/guardrails/validate_schema.py

from app.core.state import DAAState


def validate_schema(state: DAAState) -> None:
    """
    Ensures required output fields exist and are well-formed.
    Raises AssertionError if invalid.
    """

    assert isinstance(state.attention_items, list), "attention_items must be a list"
    assert isinstance(state.risks, list), "risks must be a list"
    assert isinstance(state.opportunities, list), "opportunities must be a list"

    for item in state.attention_items:
        assert "title" in item, "AttentionItem missing title"
        assert "priority_score" in item, "AttentionItem missing priority_score"
        assert "priority_level" in item, "AttentionItem missing priority_level"
        assert "recommended_action" in item, "AttentionItem missing recommended_action"
        assert "evidence" in item, "AttentionItem missing evidence"
        assert "confidence" in item, "AttentionItem missing confidence"
