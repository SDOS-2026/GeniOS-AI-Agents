# conftest.py — Shared pytest configuration and fixtures
# Place this file in your project root alongside EmailAgent/ and daily_attention_agent/

import pytest
import sys
import os
import importlib

# --- Test environment defaults --------------------------------------------
# Ensure tests can run without real LLM keys or external services.
os.environ.setdefault("GEMINI_API_KEY", "test_dummy_key")
os.environ.setdefault("GEMINI_ENABLED", "false")
os.environ.setdefault("GEMINI_MODEL", "test-model")

# --- Pydantic / FastAPI compatibility shim --------------------------------
# Some environments may have mismatched FastAPI / Pydantic versions which
# lead to import-time errors during test collection (e.g. FastAPI trying
# to import `Undefined` from `pydantic.fields`). Patch `pydantic.fields`
# at test startup if the symbol is missing so imports succeed.
try:
    # Attempt to access the symbol; if present, nothing to do.
    from pydantic.fields import Undefined  # type: ignore
except Exception:
    try:
        pf = importlib.import_module("pydantic.fields")
        if not hasattr(pf, "Undefined"):
            setattr(pf, "Undefined", object())
    except Exception:
        # If we can't import pydantic.fields at all, continue — the
        # real import error will surface later in tests that need it.
        pass

# ---------------------------------------------------------------------------
# Path setup: ensures both EmailAgent and daily_attention_agent packages
# are importable when running pytest from the project root.
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ---------------------------------------------------------------------------
# asyncio mode: enables pytest-asyncio for async test functions.
# ---------------------------------------------------------------------------
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio: mark test as async (requires pytest-asyncio)"
    )


# ---------------------------------------------------------------------------
# Shared fixtures available to ALL test files
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def utc_now():
    """Returns a timezone-aware UTC datetime — shared across all tests."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


@pytest.fixture
def sample_email_state():
    """
    Returns a fully populated EmailAgentState dict for use in node tests.
    Pre-filled with realistic defaults — override as needed per test.
    """
    return {
        "user_prompt": "check my inbox",
        "mode": "CHECK_INBOX",
        "emails": [],
        "filter_criteria": {"priority": "ANY", "limit": 5},
        "thread_id": "thread_test_001",
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


@pytest.fixture
def sample_daa_state():
    """
    Returns a fully populated DAAState object for use in DAA tests.
    Uses no MCP session — set mcp_session separately if needed.
    """
    from datetime import datetime, timedelta, timezone
    from daily_attention_agent.app.core.state import DAAState

    now = datetime.now(timezone.utc)
    return DAAState(
        user_id="test_user@example.com",
        workspace_id="test_workspace",
        connected_tools=["gmail", "calendar"],
        time_window={"start": now - timedelta(days=3), "end": now + timedelta(days=7)},
        vip_senders=["ceo@company.com"],
        keywords=["urgent", "deadline"],
        depth_mode="quick",
        output_mode="brief_only",
        mcp_session=None,
    )


@pytest.fixture
def mock_llm_response(monkeypatch):
    """
    Monkeypatches call_llm to return a controlled string.
    Usage: mock_llm_response("Your custom LLM response here")
    """
    def _factory(response_text: str):
        monkeypatch.setattr(
            "EmailAgent.app.llm.router.call_llm",
            lambda prompt, task: response_text
        )
    return _factory


@pytest.fixture
def mock_gmail_service():
    """
    Returns a fully mocked Gmail service object.
    Pre-configured to return empty message list by default.
    """
    from unittest.mock import MagicMock
    service = MagicMock()
    service.users().messages().list().execute.return_value = {"messages": []}
    service.users().getProfile().execute.return_value = {"emailAddress": "test@example.com"}
    return service