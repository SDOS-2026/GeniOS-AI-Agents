# app/models/attention_item.py

from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime
from uuid import uuid4


PriorityLevel = Literal["low", "medium", "high", "critical"]


class Evidence(BaseModel):
    """
    Mandatory evidence backing every attention item.
    """
    tool: Literal["gmail", "calendar"]
    record_id: str
    timestamp: datetime
    snippet: str


class AttentionItem(BaseModel):
    """
    Final, ranked attention item presented to the user.
    """

    # ---------- Identity ----------
    id: str = Field(default_factory=lambda: str(uuid4()))

    type: Literal["email", "meeting"]

    priority_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Numeric score used for ranking"
    )

    priority_level: PriorityLevel

    title: str

    # ---------- Why this exists ----------
    why_flagged: List[str] = Field(
        description="Human-readable reasons (deterministic)"
    )

    recommended_action: str = Field(
        description="What the user should probably do next"
    )

    # ---------- Evidence (NON-NEGOTIABLE) ----------
    evidence: Evidence

    # ---------- Optional Draft ----------
    draft_id: Optional[str] = Field(
        default=None,
        description="Reference to draft payload if generated"
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="How confident the system is this needs attention"
    )

    class Config:
        frozen = True
