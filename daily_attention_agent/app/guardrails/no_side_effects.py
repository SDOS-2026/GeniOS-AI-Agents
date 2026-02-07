# app/guardrails/no_side_effects.py

from app.state import DAAState


FORBIDDEN_ACTION_WORDS = [
    "sent",
    "sending",
    "rescheduled",
    "deleted",
    "archived",
    "posted",
    "updated",
    "created",
    "executed",
]


def validate_no_side_effects(state: DAAState) -> None:
    """
    Ensures the agent only suggests actions, never performs or claims them.
    """
    for item in state.attention_items:
        action_text = item.get("recommended_action", "").lower()

        for word in FORBIDDEN_ACTION_WORDS:
            assert word not in action_text, (
                f"Forbidden side-effect language detected: '{word}'"
            )

    for draft in state.drafts:
        assert draft.get("is_draft", True), "Draft missing is_draft=True flag"
