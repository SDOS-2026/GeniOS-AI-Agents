# app/models/unified_signal.py

from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any
from datetime import datetime
from uuid import uuid4


SignalType = Literal[
    "EMAIL_THREAD",
    "CALENDAR_EVENT",
]


class UnifiedSignal(BaseModel):
    """
    Tool-agnostic, normalized signal.

    Represents ONE unit of attention potential
    (e.g., one email thread, one calendar event).
    """

    # ---------- Identity ----------
    id: str = Field(default_factory=lambda: str(uuid4()))
    signal_type: SignalType

    source_tool: Literal["gmail", "calendar"]
    record_id: str = Field(
        description="Tool-specific ID (gmail thread ID, calendar event ID)"
    )

    # ---------- Ownership / Timing ----------
    owner: Optional[str] = Field(
        default=None,
        description="User email or calendar owner if applicable"
    )

    timestamp: datetime = Field(
        description="Last activity time (email received, meeting start)"
    )

    end_time: Optional[datetime] = Field(
        default=None,
        description="Meeting end time if applicable"
    )

    is_all_day: bool = Field(
        default=False,
        description="True if this is an all-day event"
    )

    # ---------- Content (minimal, privacy-safe) ----------
    title: str = Field(
        description="Subject line or meeting title"
    )

    snippet: str = Field(
        description="Short snippet only (never full body)"
    )

    url: Optional[str] = Field(
        default=None,
        description="Link to email thread or calendar event"
    )

    # ---------- Attention Hints (facts, not opinions) ----------
    requires_action: bool = Field(
        description="True if this likely needs user action"
    )

    raw_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool-specific facts (unread, attendees, etc.)"
    )

    class Config:
        frozen = True  # Signals are immutable once created
