from pydantic import BaseModel
from typing import Any, Dict, Literal, Optional


class RunRequest(BaseModel):
    """Start a new email agent run."""
    prompt: str


class RunResponse(BaseModel):
    """Response from starting a new run."""
    thread_id: str
    status: Literal["interrupted", "done", "error"]
    interrupt_payload: Optional[Dict[str, Any]] = None


class ResumeRequest(BaseModel):
    """Resume an interrupted run."""
    thread_id: str
    response: Dict[str, Any]
    # Possible payloads per interrupt type:
    # inbox_review:   {"email_index": 2, "action": "REPLY"}
    # summarize_ack:  {"acknowledged": true}
    # draft_review:   {"decision": "SEND" | "EDIT" | "CANCEL", "edit_instructions": "..."}


class ResumeResponse(BaseModel):
    """Response from resuming a run."""
    thread_id: str
    status: Literal["interrupted", "done", "error"]
    interrupt_payload: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None  # populated when status == "done"
