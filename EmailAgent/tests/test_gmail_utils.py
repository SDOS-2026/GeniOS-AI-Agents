"""
Unit Tests: Gmail Client Utilities (send.py, fetch.py, utils.py)
Tests email construction, send blocking, and safe fetching.

Run with: pytest test_gmail_utils.py -v
"""

import pytest
import base64
from unittest.mock import MagicMock, patch, call
from email.mime.text import MIMEText


# ==============================================================
# SEND EMAIL TESTS
# ==============================================================

class TestSendEmail:

    @pytest.fixture
    def mock_service(self):
        """Minimal mock for the Gmail service object."""
        service = MagicMock()
        service.users.return_value.messages.return_value.send.return_value.execute.return_value = {"id": "msg123"}
        return service

    def test_send_blocked_without_approval(self, mock_service):
        """send_email must raise PermissionError if approval_status != APPROVED."""
        from EmailAgent.app.gmail.send import send_email
        with pytest.raises(PermissionError, match="approval required"):
            send_email(
                service=mock_service,
                to="user@example.com",
                subject="Test",
                body="Hello",
                approval_status="PENDING",
            )

    def test_send_succeeds_with_approval(self, mock_service):
        """send_email must call the Gmail API when approval_status == APPROVED."""
        from EmailAgent.app.gmail.send import send_email
        send_email(
            service=mock_service,
            to="user@example.com",
            subject="Test Subject",
            body="Hello World",
            approval_status="APPROVED",
        )
        mock_service.users().messages().send.assert_called_once()

    def test_send_includes_thread_id_for_replies(self, mock_service):
        """When thread_id and in_reply_to are provided, the threadId must appear in payload."""
        from EmailAgent.app.gmail.send import send_email

        captured_body = {}

        def fake_send(userId, body):
            captured_body.update(body)
            return MagicMock(execute=MagicMock(return_value={}))

        mock_service.users().messages().send = fake_send

        send_email(
            service=mock_service,
            to="user@example.com",
            subject="Re: Original",
            body="Reply here",
            approval_status="APPROVED",
            thread_id="thread123",
            in_reply_to="<original_msg_id>",
            references="<original_msg_id>",
        )

        assert captured_body.get("threadId") == "thread123"

    def test_send_raises_error_for_missing_attachment(self, mock_service):
        """send_email must raise FileNotFoundError if attachment path does not exist."""
        from EmailAgent.app.gmail.send import send_email
        with pytest.raises(FileNotFoundError):
            send_email(
                service=mock_service,
                to="user@example.com",
                subject="Attachment Test",
                body="See attached.",
                approval_status="APPROVED",
                attachments=["/nonexistent/path/file.pdf"],
            )

    def test_send_with_cc_and_bcc(self, mock_service):
        """send_email must not raise exceptions when CC and BCC are provided as lists."""
        from EmailAgent.app.gmail.send import send_email
        send_email(
            service=mock_service,
            to="to@example.com",
            subject="CC BCC Test",
            body="Hello",
            approval_status="APPROVED",
            cc=["cc@example.com"],
            bcc=["bcc@example.com"],
        )
        mock_service.users().messages().send.assert_called_once()


# ==============================================================
# FETCH EMAIL TESTS
# ==============================================================

class TestFetchRecentEmails:

    def _build_mock_service(self, messages):
        """Build a mock Gmail service that returns given messages."""
        service = MagicMock()

        msg_list = [{"id": m["id"]} for m in messages]
        service.users().messages().list().execute.return_value = {"messages": msg_list}

        def get_message(userId, id, format, metadataHeaders):
            matching = next((m for m in messages if m["id"] == id), None)
            return MagicMock(execute=MagicMock(return_value=matching or {}))

        service.users().messages().get = get_message
        return service

    def _make_raw_message(self, msg_id, subject="Test", sender="a@b.com", body_text="Hello"):
        """Build a minimal Gmail API message payload."""
        encoded_body = base64.urlsafe_b64encode(body_text.encode()).decode()
        return {
            "id": msg_id,
            "threadId": f"thread_{msg_id}",
            "payload": {
                "headers": [
                    {"name": "From", "value": sender},
                    {"name": "Subject", "value": subject},
                    {"name": "Message-Id", "value": f"<{msg_id}@mail.example.com>"},
                ],
                "body": {"data": encoded_body},
                "parts": [],
            },
        }

    def test_fetch_returns_correct_number_of_emails(self):
        """fetch_recent_emails must return exactly max_results emails."""
        from EmailAgent.app.gmail.fetch import fetch_recent_emails

        messages = [self._make_raw_message(f"msg{i}") for i in range(3)]
        service = self._build_mock_service(messages)
        result = fetch_recent_emails(service, max_results=3)
        assert len(result) == 3

    def test_fetch_extracts_subject_and_sender(self):
        """Fetched email dict must contain 'subject' and 'from' fields."""
        from EmailAgent.app.gmail.fetch import fetch_recent_emails

        messages = [self._make_raw_message("abc", subject="Important Notice", sender="boss@company.com")]
        service = self._build_mock_service(messages)

        result = fetch_recent_emails(service, max_results=1)
        assert result[0]["subject"] == "Important Notice"
        assert result[0]["from"] == "boss@company.com"

    def test_fetch_decodes_body_correctly(self):
        """Email body must be base64-decoded correctly by the fetch function."""
        from EmailAgent.app.gmail.fetch import fetch_recent_emails

        body_text = "This is a special message: héllo!"
        messages = [self._make_raw_message("xyz", body_text=body_text)]
        service = self._build_mock_service(messages)

        result = fetch_recent_emails(service, max_results=1)
        assert body_text in result[0]["body"]

    def test_fetch_with_empty_inbox(self):
        """fetch_recent_emails must return an empty list when inbox is empty."""
        from EmailAgent.app.gmail.fetch import fetch_recent_emails

        service = MagicMock()
        service.users().messages().list().execute.return_value = {"messages": []}

        result = fetch_recent_emails(service, max_results=5)
        assert result == []

    def test_fetch_includes_thread_id(self):
        """Each fetched email must include a 'thread_id' field."""
        from EmailAgent.app.gmail.fetch import fetch_recent_emails

        messages = [self._make_raw_message("m1")]
        service = self._build_mock_service(messages)
        result = fetch_recent_emails(service, max_results=1)
        assert "thread_id" in result[0]
        assert result[0]["thread_id"] == "thread_m1"


# ==============================================================
# UTILS TESTS
# ==============================================================

class TestGmailUtils:

    def test_get_user_profile_returns_email(self):
        """get_user_profile must return the email address string."""
        from EmailAgent.app.gmail.utils import get_user_profile

        service = MagicMock()
        service.users().getProfile().execute.return_value = {"emailAddress": "me@example.com"}

        result = get_user_profile(service)
        assert result == "me@example.com"

    def test_get_user_profile_returns_none_on_error(self):
        """get_user_profile must return None (not raise) if API call fails."""
        from EmailAgent.app.gmail.utils import get_user_profile

        service = MagicMock()
        service.users().getProfile().execute.side_effect = Exception("API error")

        result = get_user_profile(service)
        assert result is None
