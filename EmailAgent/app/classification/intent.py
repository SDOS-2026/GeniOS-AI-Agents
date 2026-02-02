from typing import List
import re
from .models import IntentDetection
from .config import Config


class IntentScanner:
    """Scans email content for intents and urgency markers (org-realistic)"""

    def scan(self, subject: str, body: str) -> IntentDetection:
        subject = subject or ""
        body = body or ""

        subject_lower = subject.lower()
        text = (subject + " " + body).lower()

        detected_urgency = []
        urgency_score = 0
        intents = []

        # =========================
        # 1. SUBJECT HARD OVERRIDES
        # =========================
        for kw in Config.SUBJECT_HIGH_PRIORITY:
            if kw in subject_lower:
                return IntentDetection(
                    intents=["subject_override"],
                    urgency_keywords=["subject_high"],
                    urgency_score=35,
                    action_required=True,
                    question_detected=False,
                    is_follow_up=False,
                )

        for kw in Config.SUBJECT_LOW_PRIORITY:
            if kw in subject_lower:
                urgency_score -= 8
                detected_urgency.append("subject_low")

        # Forwarded mails often matter in orgs
        if subject_lower.startswith(("fwd:", "fw:")):
            urgency_score += 4
            detected_urgency.append("forwarded")

        # =========================
        # 2. URGENCY KEYWORDS
        # =========================
        for keyword, weight in Config.URGENCY_KEYWORDS.items():
            if keyword in subject_lower:
                urgency_score += int(weight * 1.7)
                detected_urgency.append(f"subject:{keyword}")
            elif keyword in text:
                urgency_score += weight
                detected_urgency.append(keyword)

        # =========================
        # 3. DOMAIN INTENTS
        # =========================
        if any(w in text for w in Config.FINANCE_KEYWORDS):
            intents.append("finance")
            urgency_score += 6

        if any(w in text for w in Config.ACADEMIC_KEYWORDS):
            intents.append("academic")
            urgency_score += 6

        if any(w in text for w in Config.LEGAL_KEYWORDS):
            intents.append("legal")
            urgency_score += 5

        if any(w in text for w in Config.IT_KEYWORDS):
            intents.append("it")

        if any(w in text for w in Config.HR_KEYWORDS):
            intents.append("hr")

        # =========================
        # 4. DEADLINE DETECTION
        # =========================
        if self._has_near_deadline(text):
            urgency_score += 8
            detected_urgency.append("near_deadline")

        # Finance + deadline = auto HIGH
        if "finance" in intents and "near_deadline" in detected_urgency:
            urgency_score = max(urgency_score, 32)
            detected_urgency.append("finance_deadline_override")

        # =========================
        # 5. ACTION / QUESTIONS
        # =========================
        action_required = any(
            p in text
            for p in ["action required", "please", "need you to", "approval", "required"]
        )

        question_detected = "?" in text

        # =========================
        # 6. LOW PRIORITY REDUCERS
        # =========================
        low_hits = sum(1 for w in Config.LOW_PRIORITY_INDICATORS if w in text)
        urgency_score -= low_hits * 5

        # =========================
        # 7. FINAL CLAMP
        # =========================
        urgency_score = max(0, min(urgency_score, 40))

        return IntentDetection(
            intents=intents,
            urgency_keywords=detected_urgency,
            urgency_score=urgency_score,
            action_required=action_required,
            question_detected=question_detected,
            is_follow_up="follow up" in text,
        )

    def _has_near_deadline(self, text: str) -> bool:
        patterns = [
            r"due (today|tomorrow|this week)",
            r"deadline.*(today|tomorrow)",
            r"by (today|tomorrow|eod)",
            r"within.*(24|48) hours?",
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)
