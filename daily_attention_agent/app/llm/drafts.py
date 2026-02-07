# app/llm/drafts.py

from typing import List, Dict, Any
from app.state import DAAState


def generate_drafts_if_enabled(state: DAAState) -> List[Dict[str, Any]]:
    """
    V1 stub for draft generation.

    Guardrails:
    - Always returns draft-only payloads
    - No execution
    - Safe to skip entirely
    """

    # V1: drafts are optional and disabled by default
    # Returning empty list keeps graph deterministic
    return []
