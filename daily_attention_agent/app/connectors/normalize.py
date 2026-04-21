# app/connectors/normalize.py

from typing import List
from app.core.state import DAAState
from app.models.unified_signal import UnifiedSignal

from app.connectors.gmail.normalize import normalize_gmail_threads
from app.connectors.calendar.normalize import normalize_calendar_events


def normalize_signals(state: DAAState) -> DAAState:
    """
    Normalize raw Gmail + Calendar data into UnifiedSignal objects.
    """

    unified: List[UnifiedSignal] = []

    for raw in state.raw_signals:
        # Gmail thread detection
        if isinstance(raw, dict) and "messages" in raw:
            unified.extend(normalize_gmail_threads([raw]))

        # Calendar event detection
        elif isinstance(raw, dict) and "start" in raw:
            unified.extend(normalize_calendar_events([raw]))

    if not unified:
        state.warnings.append("No signals normalized from fetched data")
    # print(f"[DEBUG] Unified signals count: {len(unified)}")
    # for u in unified:
    #     print(
    #         "  -",
    #         u.signal_type,
    #         "|",
    #         u.source_tool,
    #         "|",
    #         u.title,
    #     )

    state.unified_signals = unified
    return state
