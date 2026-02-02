class Config:
    # =========================
    # ORGANIZATION CONTEXT
    # =========================

    VIP_DOMAINS = [
        "google.com", "deepmind.com", "ycombinator.com",
        "microsoft.com", "apple.com", "amazon.com",
        "meta.com", "facebook.com", "openai.com",
        "anthropic.com", "nvidia.com", "tesla.com"
    ]

    VIP_EMAILS = ["boss@example.com", "ceo@example.com"]

    # =========================
    # PRIORITY BANDS (REALISTIC)
    # =========================
    HIGH_PRIORITY_SCORE = 30
    MEDIUM_PRIORITY_SCORE = 18
    PRIORITY_THRESHOLD = HIGH_PRIORITY_SCORE
    # =========================
    # SUBJECT HARD OVERRIDES
    # =========================
    SUBJECT_HIGH_PRIORITY = [
        "high priority",
        "urgent",
        "action required",
        "payment due",
        "fee demand",
        "deadline",
        "overdue",
        "approval required",
        "security alert",
        "incident",
        "outage",
    ]

    SUBJECT_MEDIUM_PRIORITY = [
        "follow up",
        "reminder",
        "please review",
        "response needed",
        "request",
        "update required",
    ]

    SUBJECT_LOW_PRIORITY = [
        "fyi",
        "newsletter",
        "notification",
        "no action required",
        "for your information",
    ]

    # =========================
    # URGENCY KEYWORDS (BODY)
    # =========================
    URGENCY_KEYWORDS = {
        "emergency": 11,
        "immediately": 10,
        "critical": 10,
        "production down": 11,
        "system down": 11,
        "outage": 10,
        "data loss": 10,
        "security breach": 11,

        "urgent": 8,
        "asap": 8,
        "blocked": 8,
        "blocker": 8,
        "stuck": 7,
        "time sensitive": 8,
        "today": 7,
        "before eod": 7,

        "deadline": 6,
        "action required": 6,
        "please review": 5,
        "waiting on": 6,

        "reminder": 4,
        "follow up": 4,
        "update": 3,
        "no rush": 1,
    }

    # =========================
    # DOMAIN KEYWORDS
    # =========================
    LEGAL_KEYWORDS = ["contract", "agreement", "legal", "lawyer", "compliance"]
    FINANCE_KEYWORDS = ["invoice", "payment", "bank", "fee", "salary", "tax"]
    IT_KEYWORDS = ["access", "password", "login", "server", "database", "api"]
    HR_KEYWORDS = ["offer", "hiring", "leave", "vacation"]
    MEETING_KEYWORDS = ["schedule", "calendar", "meet", "zoom"]
    INVITATION_KEYWORDS = ["invited", "invitation", "join"]

    # Academic / org admin (VERY important in real orgs)
    ACADEMIC_KEYWORDS = [
        "semester", "academic year", "registration",
        "exam", "fee", "tuition", "ay "
    ]

    COMPLAINT_KEYWORDS = [
        "complaint", "unacceptable", "frustrated",
        "not working", "issue", "problem", "escalate"
    ]

    # =========================
    # LOW PRIORITY REDUCERS
    # =========================
    LOW_PRIORITY_INDICATORS = [
        "fyi", "no action required", "optional",
        "newsletter", "automated", "unsubscribe"
    ]

    # =========================
    # TIME SENSITIVITY
    # =========================
    RESPONSE_TIME_URGENT = [
        "need by", "due by", "respond by",
        "expires", "deadline is", "before"
    ]
