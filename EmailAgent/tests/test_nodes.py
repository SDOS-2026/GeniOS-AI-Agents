"""
Unit Tests: EmailAgent Graph Nodes
Tests classify_node, draft_node, send_node, input_agent_node, and approval logic.

Run with: pytest test_nodes.py -v
"""

import pytest
from unittest.mock import MagicMock, patch


# ==============================================================
# SHARED STATE FACTORY
# ==============================================================

def _base_state(**overrides):
    """Returns a minimal valid EmailAgentState dict."""
    state = {
        "user_prompt": "",
        "mode": "UNKNOWN",
        "emails": [],
        "filter_criteria": {},
        "thread_id": "test_thread",
        "reply_message_id": None,
        "raw_thread": None,
        "classification": {},
        "summary": "",
        "draft": "",
        "subject": "",
        "recipient": {"to": [], "cc": [], "bcc": []},
        "attachments": [],
        "approval_status": "REQUIRED",
        "risk_flags": [],
        "show_reasoning": False,
        "reasoning": [],
        "sent": False,
        "edit_instructions": None,
        "body": None,
        "tone": None,
        "brevity": None,
    }
    state.update(overrides)
    return state


# ==============================================================
# CLASSIFY NODE TESTS
# ==============================================================

class TestClassifyNode:

    def test_classify_node_adds_classification_to_each_email(self):
        from EmailAgent.app.nodes.classify import classify_node

        state = _base_state(emails=[
            {"id": "e1", "from": "user@external.com", "subject": "Invoice Due", "snippet": "Please pay invoice"},
            {"id": "e2", "from": "noreply@news.com", "subject": "Newsletter", "snippet": "Latest updates"},
        ])

        result = classify_node(state)
        for email in result["emails"]:
            assert "classification" in email
            assert "priority" in email["classification"]

    def test_classify_node_handles_empty_email_list(self):
        from EmailAgent.app.nodes.classify import classify_node

        state = _base_state(emails=[])
        result = classify_node(state)
        assert result["emails"] == []

    def test_classify_node_sets_action_reply_for_urgent_email(self):
        from EmailAgent.app.nodes.classify import classify_node

        state = _base_state(emails=[
            {
                "id": "e1",
                "from": "boss@company.com",
                "subject": "Action Required: Approve Budget",
                "snippet": "Please approve by EOD",
            }
        ])
        result = classify_node(state)
        cls = result["emails"][0]["classification"]
        assert cls.get("intent") == "REPLY"

    def test_classify_node_handles_missing_fields_gracefully(self):
        from EmailAgent.app.nodes.classify import classify_node

        state = _base_state(emails=[{"id": "e1"}])
        result = classify_node(state)
        assert "classification" in result["emails"][0]


# ==============================================================
# DRAFT NODE TESTS
# ==============================================================

class TestDraftNode:

    @patch("EmailAgent.app.llm.router.call_llm", return_value="Thank you for your message. I will get back to you shortly.")
    def test_draft_node_populates_draft_field(self, _mock_llm):
        from EmailAgent.app.nodes.draft import draft_node

        state = _base_state(
            raw_thread={"from": "sender@example.com", "subject": "Meeting Request", "body": "Can we meet tomorrow?"},
            classification={"category": "MEETING", "intent": "REPLY"},
        )

        result = draft_node(state)
        assert result["draft"]
        assert len(result["draft"]) > 0

    @patch("EmailAgent.app.llm.router.call_llm", return_value="")
    def test_draft_node_uses_fallback_for_empty_llm_response(self, _mock_llm):
        from EmailAgent.app.nodes.draft import draft_node

        state = _base_state(
            raw_thread={"from": "a@b.com", "subject": "Test", "body": "Hello"},
            classification={},
        )

        result = draft_node(state)
        assert result["draft"]
        assert len(result["draft"]) > 10

    @patch("EmailAgent.app.llm.router.call_llm", return_value='{"priority": "HIGH", "intent": "REPLY"}')
    def test_draft_node_rejects_json_blob_as_draft(self, _mock_llm):
        from EmailAgent.app.nodes.draft import draft_node

        state = _base_state(
            raw_thread={"from": "a@b.com", "subject": "Test", "body": "Hello"},
            classification={},
        )

        result = draft_node(state)
        assert not result["draft"].startswith("{")

    @patch("EmailAgent.app.llm.router.call_llm", return_value="Here is my reply.")
    def test_draft_node_sets_subject_with_re_prefix(self, _mock_llm):
        from EmailAgent.app.nodes.draft import draft_node

        state = _base_state(
            raw_thread={"from": "a@b.com", "subject": "Original Subject", "body": "Hello"},
            classification={},
        )

        result = draft_node(state)
        assert result["subject"].startswith("Re:")

    @patch("EmailAgent.app.llm.router.call_llm", return_value="Already a reply.")
    def test_draft_node_does_not_double_re_prefix(self, _mock_llm):
        from EmailAgent.app.nodes.draft import draft_node

        state = _base_state(
            raw_thread={"from": "a@b.com", "subject": "Re: Existing Thread", "body": "Context here"},
            classification={},
        )

        result = draft_node(state)
        assert result["subject"] == "Re: Existing Thread"


# ==============================================================
# SEND NODE TESTS
# ==============================================================

class TestSendNode:

    @pytest.mark.asyncio
    @patch("EmailAgent.app.nodes.send.get_mcp_client")
    async def test_send_node_calls_mcp_client(self, mock_get_client):
        from EmailAgent.app.nodes.send import send_node

        mock_client = MagicMock()
        mock_client.call_tool = MagicMock(return_value=MagicMock(is_error=False, content=[]))
        mock_get_client.return_value = mock_client
        
        # mock_client.call_tool needs to be an AsyncMock, but since Python 3.8 AsyncMock is available.
        # To avoid importing AsyncMock explicitly, we can just set a side_effect that returns a future or use AsyncMock
        from unittest.mock import AsyncMock
        mock_client.call_tool = AsyncMock(return_value=MagicMock(is_error=False, content=[]))

        state = _base_state(
            recipient={"to": ["user@example.com"], "cc": [], "bcc": []},
            subject="Test",
            draft="Hello there",
        )

        result = await send_node(state)
        mock_client.call_tool.assert_called_once_with("gmail_send", {
            "to": "user@example.com",
            "subject": "Test",
            "body": "Hello there",
            "cc": None,
            "bcc": None,
            "thread_id": "test_thread",
            "in_reply_to": None,
            "references": None
        })
        assert result["sent"] is True

    @pytest.mark.asyncio
    @patch("EmailAgent.app.nodes.send.get_mcp_client")
    async def test_send_node_handles_mcp_error(self, mock_get_client):
        from EmailAgent.app.nodes.send import send_node
        from unittest.mock import AsyncMock

        mock_client = MagicMock()
        mock_client.call_tool = AsyncMock(return_value=MagicMock(is_error=True, content=[MagicMock(text="API error")]))
        mock_get_client.return_value = mock_client

        state = _base_state(
            recipient={"to": ["user@example.com"], "cc": [], "bcc": []},
            subject="Test",
            draft="Hello",
        )

        result = await send_node(state)
        assert result["sent"] is False
        assert "API error" in result["reasoning"][0]


# ==============================================================
# INPUT AGENT NODE TESTS
# ==============================================================

class TestInputAgentNode:

    @patch("EmailAgent.app.nodes.input_agent.interpret_intent")
    def test_compose_intent_sets_mode(self, mock_intent):
        from EmailAgent.app.nodes.input_agent import input_agent_node

        mock_intent.return_value = {
            "intent": "COMPOSE",
            "parameters": {
                "recipient": {"to": ["hr@company.com"], "cc": [], "bcc": []},
                "subject": "Leave Request",
                "body": None,
                "attachments": [],
            },
            "filters": {"priority": None, "time_range": None, "limit": None},
        }

        state = _base_state(user_prompt="Write an email to HR about my leave")
        result = input_agent_node(state)
        assert result["mode"] == "COMPOSE"

    @patch("EmailAgent.app.nodes.input_agent.interpret_intent")
    def test_check_inbox_intent_sets_mode(self, mock_intent):
        from EmailAgent.app.nodes.input_agent import input_agent_node

        mock_intent.return_value = {
            "intent": "CHECK_INBOX",
            "parameters": {
                "recipient": {"to": [], "cc": [], "bcc": []},
                "subject": None,
                "body": None,
                "attachments": [],
            },
            "filters": {"priority": "HIGH", "time_range": None, "limit": 5},
        }

        state = _base_state(user_prompt="Show me my high priority emails")
        result = input_agent_node(state)
        assert result["mode"] == "CHECK_INBOX"

    @patch("EmailAgent.app.nodes.input_agent.interpret_intent", side_effect=Exception("LLM error"))
    def test_fallback_intent_used_when_llm_fails(self, _mock_intent):
        from EmailAgent.app.nodes.input_agent import input_agent_node

        state = _base_state(user_prompt="compose an email to john")
        result = input_agent_node(state)
        assert result["mode"] in ["COMPOSE", "CHECK_INBOX", "REPLY", "UNKNOWN"]

    def test_fallback_intent_compose(self):
        from EmailAgent.app.nodes.input_agent import _fallback_intent

        result = _fallback_intent("write an email to the finance team")
        assert result["intent"] == "COMPOSE"

    def test_fallback_intent_inbox(self):
        from EmailAgent.app.nodes.input_agent import _fallback_intent

        result = _fallback_intent("show me my latest emails")
        assert result["intent"] == "CHECK_INBOX"

    def test_extract_limit_from_prompt(self):
        from EmailAgent.app.nodes.input_agent import _extract_limit

        assert _extract_limit("show me last 5 emails") == 5
        assert _extract_limit("latest email") == 1
        assert _extract_limit("check my inbox") is None


# ==============================================================
# APPROVAL NODE TESTS
# ==============================================================

class TestApprovalNode:

    def test_approval_required_when_risk_flags_present(self):
        from EmailAgent.app.nodes.approval import approval_node

        state = _base_state(risk_flags=["EXTERNAL_SENDER", "PII_DETECTED"])
        result = approval_node(state)
        assert result["approval_status"] == "REQUIRED"

    def test_approval_not_required_when_no_flags(self):
        from EmailAgent.app.nodes.approval import approval_node

        state = _base_state(risk_flags=[])
        result = approval_node(state)
        assert result["approval_status"] == "NOT_REQUIRED"
