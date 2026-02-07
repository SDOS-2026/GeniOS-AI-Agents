# app/guardrails/cost_caps.py

from app.state import DAAState


MAX_ATTENTION_ITEMS = 15
MAX_DRAFTS = 10


def validate_cost_caps(state: DAAState) -> None:
    """
    Enforces hard caps to avoid overload and runaway cost.
    """
    assert len(state.attention_items) <= MAX_ATTENTION_ITEMS, (
        f"Too many attention items ({len(state.attention_items)})"
    )

    assert len(state.drafts) <= MAX_DRAFTS, (
        f"Too many drafts ({len(state.drafts)})"
    )
