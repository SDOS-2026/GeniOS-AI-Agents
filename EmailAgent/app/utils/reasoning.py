# app/utils/reasoning.py
from typing import Any

def add_reasoning(state: dict, message: str) -> None:
    """
    Append a short, user-facing reasoning message to state['reasoning']
    only if state['show_reasoning'] is truthy.
    Keep messages short and explain *why* a decision was made, not internals.
    """
    if not state.get("show_reasoning"):
        return
    state.setdefault("reasoning", [])
    state["reasoning"].append(message)
