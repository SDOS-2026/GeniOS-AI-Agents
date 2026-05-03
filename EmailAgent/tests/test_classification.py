"""
Unit Tests: Email Classification Pipeline
Tests sender classification, intent detection, and priority scoring.

Run with: pytest test_classification.py -v
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

# --- Fixtures (test setup) ---

@pytest.fixture
def sample_metadata():
    """Provides a standard email metadata object for tests."""
    from EmailAgent.app.classification.models import EmailMetadata
    return EmailMetadata(
        sender="alice@example.com",
        subject="Urgent: Action Required on Invoice",
        body="Please review the attached invoice and approve it by EOD today.",
        date=datetime.now(timezone.utc),
        recipients=["me@mycompany.com"],
        has_attachments=True,
    )

@pytest.fixture
def vip_metadata():
    """Provides metadata simulating a VIP sender (e.g., Google)."""
    from EmailAgent.app.classification.models import EmailMetadata
    return EmailMetadata(
        sender="admin@google.com",
        subject="Partnership Opportunity",
        body="We'd like to discuss a potential partnership.",
        date=datetime.now(timezone.utc),
    )

@pytest.fixture
def spam_metadata():
    """Provides metadata simulating a spam/no-reply sender."""
    from EmailAgent.app.classification.models import EmailMetadata
    return EmailMetadata(
        sender="noreply@newsletter.com",
        subject="Weekly Newsletter",
        body="Unsubscribe from our mailing list.",
        date=datetime.now(timezone.utc) - timedelta(days=5),
    )

@pytest.fixture
def sender_classifier():
    from EmailAgent.app.classification.sender import SenderClassifier
    return SenderClassifier()

@pytest.fixture
def intent_scanner():
    from EmailAgent.app.classification.intent import IntentScanner
    return IntentScanner()

@pytest.fixture
def priority_scorer():
    from EmailAgent.app.classification.priority import PriorityScorer
    return PriorityScorer()


# ==============================================================
# S1: SENDER CLASSIFICATION TESTS
# ==============================================================

class TestSenderClassifier:

    def test_vip_domain_is_classified_as_vip(self, sender_classifier, vip_metadata):
        """A sender from a known VIP domain (google.com) must be flagged as VIP."""
        result = sender_classifier.classify(vip_metadata)
        assert result.is_vip is True, "Sender from google.com should be flagged VIP"

    def test_noreply_sender_is_classified_as_spam(self, sender_classifier, spam_metadata):
        """A 'noreply@' address must be classified as SPAM."""
        from EmailAgent.app.classification.models import SenderType
        result = sender_classifier.classify(spam_metadata)
        assert result.sender_type == SenderType.SPAM

    def test_regular_professional_sender_classified_as_customer(self, sender_classifier, sample_metadata):
        """A sender from a professional (non-free) external domain is a CUSTOMER."""
        from EmailAgent.app.classification.models import SenderType
        sample_metadata.sender = "boss@acme-corp.com"
        result = sender_classifier.classify(sample_metadata)
        assert result.sender_type == SenderType.CUSTOMER

    def test_domain_extraction_is_correct(self, sender_classifier):
        """Domain extraction utility should handle standard email formats."""
        domain = sender_classifier._extract_domain("user@subdomain.company.org")
        assert domain == "subdomain.company.org"

    def test_empty_sender_does_not_crash(self, sender_classifier):
        """Empty/None sender input must not raise an exception."""
        from EmailAgent.app.classification.models import EmailMetadata
        meta = EmailMetadata(sender="", subject="test", body="test", date=datetime.now(timezone.utc))
        result = sender_classifier.classify(meta)
        assert result is not None

    def test_classification_result_has_all_fields(self, sender_classifier, sample_metadata):
        """Classification result must include all required fields."""
        result = sender_classifier.classify(sample_metadata)
        assert hasattr(result, "sender_type")
        assert hasattr(result, "is_vip")
        assert hasattr(result, "confidence")
        assert 0.0 <= result.confidence <= 1.0

    def test_vip_email_list_override(self, sender_classifier):
        """An email explicitly in the VIP list must be flagged VIP regardless of domain."""
        from EmailAgent.app.classification.models import EmailMetadata
        sender_classifier.vip_emails = ["ceo@randomcompany.com"]
        meta = EmailMetadata(sender="ceo@randomcompany.com", subject="Hi", body="check this", date=datetime.now(timezone.utc))
        result = sender_classifier.classify(meta)
        assert result.is_vip is True


# ==============================================================
# S2: INTENT DETECTION TESTS
# ==============================================================

class TestIntentScanner:

    def test_urgent_subject_triggers_high_score(self, intent_scanner):
        """Subject containing 'urgent' must produce a high urgency score (>= 30)."""
        result = intent_scanner.scan("URGENT: System Down", "Production is failing.")
        assert result.urgency_score >= 30, "Urgent subject should yield high score"

    def test_action_required_subject_override(self, intent_scanner):
        """'Action Required' in subject should trigger override with action_required=True."""
        result = intent_scanner.scan("Action Required: Please approve", "")
        assert result.action_required is True

    def test_question_mark_sets_question_detected(self, intent_scanner):
        """Body with a question mark must set question_detected=True."""
        result = intent_scanner.scan("Meeting Update", "Can you confirm your attendance?")
        assert result.question_detected is True

    def test_newsletter_subject_reduces_score(self, intent_scanner):
        """Newsletter subjects must reduce urgency score."""
        result_newsletter = intent_scanner.scan("Weekly Newsletter", "Here is your update.")
        result_urgent = intent_scanner.scan("URGENT action needed", "Please act now.")
        assert result_newsletter.urgency_score < result_urgent.urgency_score

    def test_follow_up_is_detected(self, intent_scanner):
        """'Follow up' in body must be detected."""
        result = intent_scanner.scan("Re: Project", "Just wanted to follow up on this.")
        assert result.is_follow_up is True

    def test_finance_keywords_detected(self, intent_scanner):
        """Finance keywords in body should result in 'finance' intent."""
        result = intent_scanner.scan("Invoice Due", "Please process the payment for invoice #1234.")
        assert "finance" in result.intents

    def test_legal_keywords_detected(self, intent_scanner):
        """Legal keywords should be detected in intents."""
        result = intent_scanner.scan("Contract Review", "Please review the attached legal agreement.")
        assert "legal" in result.intents

    def test_empty_inputs_do_not_crash(self, intent_scanner):
        """Empty subject and body must not raise an exception."""
        result = intent_scanner.scan("", "")
        assert result is not None
        assert result.urgency_score >= 0

    def test_urgency_score_is_clamped(self, intent_scanner):
        """Urgency score must always be within 0-40 range."""
        result = intent_scanner.scan(
            "URGENT CRITICAL EMERGENCY IMMEDIATELY",
            "EMERGENCY EMERGENCY EMERGENCY security breach data loss outage blocked"
        )
        assert 0 <= result.urgency_score <= 40


# ==============================================================
# S3 + S4: PRIORITY SCORING TESTS
# ==============================================================

class TestPriorityScorer:

    def test_vip_sender_produces_high_priority(self, priority_scorer, vip_metadata):
        """An email from a VIP sender with urgency keywords must be HIGH priority."""
        from EmailAgent.app.classification.sender import SenderClassifier
        from EmailAgent.app.classification.intent import IntentScanner
        from EmailAgent.app.classification.models import PriorityLevel

        classifier = SenderClassifier()
        scanner = IntentScanner()

        # Add urgency to force high/medium priority
        vip_metadata.subject = "URGENT: " + vip_metadata.subject
        vip_metadata.body = vip_metadata.body + " This is an emergency, please respond ASAP."

        sender_result = classifier.classify(vip_metadata)
        intent_result = scanner.scan(vip_metadata.subject, vip_metadata.body)
        priority = priority_scorer.calculate_score(vip_metadata, sender_result, intent_result)

        assert priority.priority_level in [PriorityLevel.HIGH, PriorityLevel.MEDIUM]

    def test_spam_produces_low_or_not_required(self, priority_scorer, spam_metadata):
        """A spam email with no urgency must be LOW or NOT_REQUIRED priority."""
        from EmailAgent.app.classification.sender import SenderClassifier
        from EmailAgent.app.classification.intent import IntentScanner
        from EmailAgent.app.classification.models import PriorityLevel

        classifier = SenderClassifier()
        scanner = IntentScanner()

        sender_result = classifier.classify(spam_metadata)
        intent_result = scanner.scan(spam_metadata.subject, spam_metadata.body)
        priority = priority_scorer.calculate_score(spam_metadata, sender_result, intent_result)

        assert priority.priority_level in [PriorityLevel.LOW, PriorityLevel.NOT_REQUIRED]

    def test_score_is_within_valid_range(self, priority_scorer, sample_metadata):
        """Priority score must always be between 0 and 150."""
        from EmailAgent.app.classification.sender import SenderClassifier
        from EmailAgent.app.classification.intent import IntentScanner

        classifier = SenderClassifier()
        scanner = IntentScanner()

        sender_result = classifier.classify(sample_metadata)
        intent_result = scanner.scan(sample_metadata.subject, sample_metadata.body)
        priority = priority_scorer.calculate_score(sample_metadata, sender_result, intent_result)

        assert 0 <= priority.score <= 150

    def test_reasoning_is_non_empty_string(self, priority_scorer, sample_metadata):
        """Priority result must always include a non-empty reasoning string."""
        from EmailAgent.app.classification.sender import SenderClassifier
        from EmailAgent.app.classification.intent import IntentScanner

        classifier = SenderClassifier()
        scanner = IntentScanner()

        sender_result = classifier.classify(sample_metadata)
        intent_result = scanner.scan(sample_metadata.subject, sample_metadata.body)
        priority = priority_scorer.calculate_score(sample_metadata, sender_result, intent_result)

        assert isinstance(priority.reasoning, str)
        assert len(priority.reasoning) > 0

    def test_recent_email_scores_higher_than_old(self, priority_scorer):
        """A recent email should score higher on age factor than an old email."""
        from EmailAgent.app.classification.models import EmailMetadata
        from EmailAgent.app.classification.sender import SenderClassifier
        from EmailAgent.app.classification.intent import IntentScanner

        classifier = SenderClassifier()
        scanner = IntentScanner()

        recent = EmailMetadata(sender="x@example.com", subject="Hi", body="Hello",
                               date=datetime.now(timezone.utc) - timedelta(minutes=30))
        old = EmailMetadata(sender="x@example.com", subject="Hi", body="Hello",
                            date=datetime.now(timezone.utc) - timedelta(days=10))

        def get_score(meta):
            s = classifier.classify(meta)
            i = scanner.scan(meta.subject, meta.body)
            return priority_scorer.calculate_score(meta, s, i).score

        assert get_score(recent) > get_score(old)

    @pytest.mark.parametrize("subject,expected_not_level", [
        ("URGENT: Fix production", "NOT_REQUIRED"),
        ("FYI: Weekly report is ready", "HIGH"),
    ])
    def test_priority_levels_via_parametrize(self, priority_scorer, subject, expected_not_level):
        """Parameterized: urgent subjects should not be NOT_REQUIRED; FYI should not be HIGH."""
        from EmailAgent.app.classification.models import EmailMetadata
        from EmailAgent.app.classification.sender import SenderClassifier
        from EmailAgent.app.classification.intent import IntentScanner

        classifier = SenderClassifier()
        scanner = IntentScanner()

        meta = EmailMetadata(sender="user@external.com", subject=subject,
                             body="Please take action.", date=datetime.now(timezone.utc))
        s = classifier.classify(meta)
        i = scanner.scan(meta.subject, meta.body)
        result = priority_scorer.calculate_score(meta, s, i)

        assert result.priority_level.value != expected_not_level.lower()