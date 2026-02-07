# app/state.py

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class DAAState(BaseModel):
    """
    LangGraph state for Daily Attention Agent (V1).

    RULES:
    - Every node MUST read/write only via this object
    - If something is not here, it does not exist
    """

    # ========== INPUT (from Mr. Elite / entry point) ==========
    user_id: str
    workspace_id: str

    connected_tools: List[str] = Field(
        default_factory=list,
        description="e.g. ['gmail', 'calendar']"
    )

    time_window: Dict[str, datetime] = Field(
        description="{'start': datetime, 'end': datetime}"
    )

    vip_senders: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)

    depth_mode: str = Field(
        default="quick",
        description="quick | deep"
    )

    output_mode: str = Field(
        default="brief_only",
        description="brief_only | brief_with_drafts"
    )

    # ========== INTERNAL STATE (mutated by graph nodes) ==========
    raw_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Runtime-only metadata (e.g. credentials, injected context)"
    )

    raw_signals: List[Dict[str, Any]] = Field(default_factory=list)
    unified_signals: List[Dict[str, Any]] = Field(default_factory=list)

    scored_items: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Signals + scores + reasons"
    )

    drafts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Draft payloads (DRAFT ONLY)"
    )

    # ========== OUTPUT ==========
    attention_items: List[Dict[str, Any]] = Field(default_factory=list)
    risks: List[Dict[str, Any]] = Field(default_factory=list)
    opportunities: List[Dict[str, Any]] = Field(default_factory=list)

    warnings: List[str] = Field(default_factory=list)

    # ========== METADATA ==========
    run_started_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc)
    )
    run_completed_at: Optional[datetime] = None
