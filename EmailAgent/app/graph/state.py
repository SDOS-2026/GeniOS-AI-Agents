from typing import TypedDict, Optional, List, Dict, Literal

class Recipients(TypedDict):
    to: List[str]
    cc: List[str]
    bcc: List[str]


class EmailAgentState(TypedDict):
    # ===== Session / Control =====
    thread_id: str
    reply_message_id: Optional[str]
    mode: Optional[Literal["CATEGORIZE", "COMPOSE"]]
    user_prompt: Optional[str]

    # ===== Inbox Data =====
    emails: Optional[List[Dict]]          # filtered email list
    current_email_index: int              # pointer to active email
    selected_email: Optional[Dict]        # convenience cache
    raw_thread: Optional[Dict]            # The raw thread object for single-item processing

    filter_criteria: Optional[Dict]       # priority keywords, recency, sender rules
    priority: Optional[Literal["HIGH", "MEDIUM", "LOW"]]

    # ===== User Intent at Inbox =====
    user_action: Optional[
        Literal["SUMMARIZE", "REPLY", "DONE"]
    ]

    # ===== Summarization =====
    summary: Optional[str]

    # ===== Drafting =====
    draft: Optional[str]
    subject: Optional[str]
    body: Optional[str]
    recipient: Optional[Recipients]
    attachments: Optional[List[str]]

    edit_instructions: Optional[str]

    # ===== Approval =====
    approval_decision: Optional[
        Literal["YES", "NO"]
    ]

    # ===== Sending =====
    sent: Optional[bool]

    # ===== Reasoning =====
    show_reasoning: Optional[bool]
    reasoning: Optional[List[str]]

    # ===== Metadata =====
    tone: Optional[str]
    brevity: Optional[str]
