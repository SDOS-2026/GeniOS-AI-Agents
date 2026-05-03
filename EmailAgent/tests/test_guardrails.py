"""
Unit Tests: Email Guardrails (G1, G2, G3)
Tests PII detection, domain restriction, and tone enforcement.

Run with: pytest test_guardrails.py -v
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone


# ==============================================================
# SHARED FIXTURES
# ==============================================================

def _make_processed_email(subject="Test", body="Test body", draft_subject="Re: Test", draft_body="Thank you."):
    """Helper that builds a minimal ProcessedEmail-like object."""
    from EmailAgent.app.classification.models import ProcessedEmail, EmailMetadata, DraftReply
    from pydantic import ValidationError

    meta = EmailMetadata(
        sender="sender@example.com",
        subject=subject,
        body=body,
        date=datetime.now(timezone.utc),
    )
    draft = DraftReply(subject=draft_subject, body=draft_body)

    email = ProcessedEmail(metadata=meta, draft_reply=draft)
    return email


# ==============================================================
# G1: PII DETECTION TESTS
# ==============================================================

class TestPIIDetector:

    @pytest.fixture
    def detector(self):
        from EmailAgent.app.guardrails.pii_detector import PIIDetector
        return PIIDetector()

    def test_ssn_detected_in_body(self, detector):
        """SSN pattern (XXX-XX-XXXX) must be detected in email body."""
        email = _make_processed_email(body="My SSN is 123-45-6789 please process it.")
        has_pii, types = detector.detect_pii_and_confidential(email)
        assert has_pii is True
        assert "ssn" in types

    def test_credit_card_detected(self, detector):
        """16-digit credit card pattern must be detected."""
        email = _make_processed_email(body="Card: 4111 1111 1111 1111")
        has_pii, types = detector.detect_pii_and_confidential(email)
        assert has_pii is True
        assert "credit_card" in types

    def test_clean_email_passes_pii_check(self, detector):
        """Normal professional email must pass PII scan with no hits."""
        email = _make_processed_email(
            body="Hi, please find the meeting notes attached. Let me know your thoughts."
        )
        has_pii, types = detector.detect_pii_and_confidential(email)
        assert has_pii is False
        assert types == []

    def test_confidential_keyword_detected(self, detector):
        """Body containing the word 'confidential' must trigger confidential_marker."""
        email = _make_processed_email(body="This document is confidential. Do not share.")
        has_pii, types = detector.detect_pii_and_confidential(email)
        assert has_pii is True
        assert "confidential_marker" in types

    def test_pii_in_draft_body_detected(self, detector):
        """SSN included accidentally in a draft reply body must be caught."""
        email = _make_processed_email(
            body="Normal original email.",
            draft_body="Your SSN 987-65-4321 has been processed."
        )
        has_pii, types = detector.detect_pii_and_confidential(email)
        assert has_pii is True

    def test_anonymize_ssn(self, detector):
        """anonymize_text must replace SSN with [SSN]."""
        text = "SSN: 123-45-6789"
        result = detector.anonymize_text(text)
        assert "123-45-6789" not in result
        assert "[SSN]" in result

    def test_anonymize_credit_card(self, detector):
        """anonymize_text must replace credit card with [CREDIT_CARD]."""
        text = "card number is 4111 1111 1111 1111"
        result = detector.anonymize_text(text)
        assert "4111 1111 1111 1111" not in result

    def test_security_flag_added_when_pii_found(self, detector):
        """A SecurityFlag must be appended to email.security_flags when PII is detected."""
        email = _make_processed_email(body="SSN: 000-00-0000")
        detector.detect_pii_and_confidential(email)
        assert len(email.security_flags) > 0
        assert any(f.flag_type == "pii_detected" for f in email.security_flags)

    def test_no_draft_skips_draft_scan(self, detector):
        """Email with no draft_reply should still complete PII scan without errors."""
        from EmailAgent.app.classification.models import ProcessedEmail, EmailMetadata
        meta = EmailMetadata(sender="a@b.com", subject="test", body="hello world", date=datetime.now(timezone.utc))
        email = ProcessedEmail(metadata=meta)
        has_pii, types = detector.detect_pii_and_confidential(email)
        assert has_pii is False


# ==============================================================
# G3: TONE ENFORCEMENT TESTS
# ==============================================================

class TestToneEnforcer:

    @pytest.fixture
    def enforcer(self):
        from EmailAgent.app.guardrails.tone_enforcer import ToneEnforcer
        return ToneEnforcer()

    def test_professional_draft_passes_tone_check(self, enforcer):
        """A polite, professional draft must pass tone enforcement."""
        email = _make_processed_email(
            draft_body="Thank you for your message. I will review this and respond within 24 hours."
        )
        tone_approved, issues = enforcer.enforce_safe_tone(email)
        assert tone_approved is True
        assert issues == []

    def test_aggressive_word_flagged(self, enforcer):
        """A draft containing 'demand' must be flagged."""
        email = _make_processed_email(draft_body="I demand an immediate resolution to this issue.")
        tone_approved, issues = enforcer.enforce_safe_tone(email)
        assert tone_approved is False
        assert any("demand" in i.lower() for i in issues)

    def test_liability_phrase_flagged(self, enforcer):
        """A draft with 'we guarantee' must be flagged as legal liability."""
        email = _make_processed_email(draft_body="We guarantee this will be resolved by Monday.")
        tone_approved, issues = enforcer.enforce_safe_tone(email)
        assert tone_approved is False
        assert any("liability" in i.lower() or "guarantee" in i.lower() for i in issues)

    def test_unprofessional_slang_flagged(self, enforcer):
        """Use of 'asap' in a draft should be flagged as unprofessional."""
        email = _make_processed_email(draft_body="Please fix this asap or we will escalate.")
        tone_approved, issues = enforcer.enforce_safe_tone(email)
        assert tone_approved is False
        assert any("asap" in i.lower() for i in issues)

    def test_no_draft_returns_true(self, enforcer):
        """Email with no draft should pass tone check by default (nothing to check)."""
        from EmailAgent.app.classification.models import ProcessedEmail, EmailMetadata
        meta = EmailMetadata(sender="a@b.com", subject="test", body="hello", date=datetime.now(timezone.utc))
        email = ProcessedEmail(metadata=meta)
        tone_approved, issues = enforcer.enforce_safe_tone(email)
        assert tone_approved is True

    def test_suggest_alternatives_replaces_demand(self, enforcer):
        """suggest_alternatives must replace 'demand' with 'request'."""
        result = enforcer.suggest_alternatives("I demand an answer")
        assert "request" in result

    @pytest.mark.parametrize("word,should_fail", [
        ("I demand results", True),
        ("We guarantee success", True),
        ("Please review at your earliest convenience", False),
        ("Looking forward to your response", False),
    ])
    def test_tone_parametrized(self, enforcer, word, should_fail):
        """Parameterized: verify specific phrases pass or fail tone check."""
        email = _make_processed_email(draft_body=word)
        tone_approved, _ = enforcer.enforce_safe_tone(email)
        if should_fail:
            assert tone_approved is False
        else:
            assert tone_approved is True