from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Any
from datetime import datetime

class SenderType(Enum):
    VIP = "vip"
    TEAM = "team"
    VENDOR = "vendor"
    CUSTOMER = "customer"
    SPAM = "spam"
    UNKNOWN = "unknown"

class PriorityLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NOT_REQUIRED = "not_required"

@dataclass
class EmailMetadata:
    sender: str
    subject: str
    body: str
    date: datetime
    recipients: List[str] = field(default_factory=list)
    has_attachments: bool = False

@dataclass
class ClassificationResult:
    sender_type: SenderType
    sender_email: str
    sender_domain: str
    is_vip: bool
    is_internal: bool
    confidence: float
    notes: str

@dataclass
class IntentDetection:
    intents: List[str]
    urgency_keywords: List[str]
    urgency_score: int
    action_required: bool
    question_detected: bool
    is_follow_up: bool

@dataclass
class PriorityScore:
    score: int
    priority_level: PriorityLevel
    factors: dict
    reasoning: str

@dataclass
class SecurityFlag:
    flag_type: str
    severity: str
    description: str
    details: dict
    blocks_sending: bool

@dataclass
class DraftReply:
    subject: str
    body: str

@dataclass
class ProcessedEmail:
    metadata: Any # Should be EmailMetadata but for flexibility Any
    draft_reply: Optional[DraftReply] = None
    security_flags: List[SecurityFlag] = field(default_factory=list)
    has_pii: bool = False
    