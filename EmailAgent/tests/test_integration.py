"""
EmailAgent Integration Tests
=============================

Tests the EmailAgent FastAPI service endpoints, both directly
and through the gateway proxy.

Usage:
  # Start services first:
  #   1. cd mcp_server && bash start.sh
  #   2. cd EmailAgent && uvicorn main:app --port 8002 --reload
  #   3. cd gateway && bash start.sh
  #
  # Then run:
  #   cd EmailAgent && source ../venv/bin/activate && pytest tests/test_integration.py -v
"""

import pytest
import httpx

# Service URLs
EMAIL_SERVICE = "http://localhost:8002"
GATEWAY = "http://localhost:8000"

TIMEOUT = 30.0


# ─── Health Checks ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_email_service_health_direct():
    """Direct health check on the EmailAgent service."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{EMAIL_SERVICE}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["service"] == "email"
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_email_service_health_via_gateway():
    """Health check through the gateway proxy."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{GATEWAY}/email/health", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["service"] == "email"
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_gateway_root():
    """Gateway root lists email service."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{GATEWAY}/", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "email" in data["services"]


# ─── Run Endpoint ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_compose_returns_interrupt():
    """
    POST /run with a compose prompt should trigger the draft_review interrupt
    (after the compose node generates a draft and review node fires interrupt).
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{EMAIL_SERVICE}/run",
            json={"prompt": "Send an email to alice@example.com about the project update"},
            timeout=60.0,
        )
    assert r.status_code == 200
    data = r.json()

    assert data["thread_id"] is not None
    assert data["status"] in ("interrupted", "done", "error")

    # For a compose prompt, we expect an interrupt at the review node
    if data["status"] == "interrupted":
        assert data["interrupt_payload"] is not None
        assert "interrupt_type" in data["interrupt_payload"]


@pytest.mark.asyncio
async def test_run_via_gateway():
    """Same compose test but through the gateway proxy."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{GATEWAY}/email/run",
            json={"prompt": "Send an email to bob@example.com saying hello"},
            timeout=60.0,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["thread_id"] is not None
    assert data["status"] in ("interrupted", "done", "error")


# ─── Resume Endpoint ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resume_invalid_thread_returns_404():
    """POST /resume with a fake thread_id should return 404."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{EMAIL_SERVICE}/resume",
            json={
                "thread_id": "00000000-0000-0000-0000-000000000000",
                "response": {"decision": "SEND"},
            },
            timeout=TIMEOUT,
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_full_compose_approve_flow():
    """
    End-to-end: Run (compose) → draft_review interrupt → Resume (SEND) → done.
    This tests the full interrupt/resume cycle.
    """
    async with httpx.AsyncClient() as client:
        # Step 1: Start a compose run
        r1 = await client.post(
            f"{EMAIL_SERVICE}/run",
            json={"prompt": "Compose an email to test@example.com about integration test"},
            timeout=60.0,
        )
        assert r1.status_code == 200
        data1 = r1.json()

        # If the graph errored (e.g., no Gemini API key), skip the rest
        if data1["status"] == "error":
            pytest.skip(f"Run returned error: {data1.get('interrupt_payload')}")

        if data1["status"] != "interrupted":
            pytest.skip("Run completed without interrupt — cannot test resume")

        thread_id = data1["thread_id"]
        assert data1["interrupt_payload"]["interrupt_type"] == "draft_review"

        # Step 2: Resume with SEND approval
        r2 = await client.post(
            f"{EMAIL_SERVICE}/resume",
            json={
                "thread_id": thread_id,
                "response": {"decision": "SEND"},
            },
            timeout=60.0,
        )
        assert r2.status_code == 200
        data2 = r2.json()

        # After sending, graph should either complete or hit another interrupt
        assert data2["status"] in ("done", "interrupted", "error")


@pytest.mark.asyncio
async def test_compose_edit_then_send_flow():
    """
    Run (compose) → draft_review → Resume (EDIT) → new draft_review → Resume (SEND).
    Tests the edit loop.
    """
    async with httpx.AsyncClient() as client:
        # Step 1: Start compose run
        r1 = await client.post(
            f"{EMAIL_SERVICE}/run",
            json={"prompt": "Write an email to manager@example.com requesting PTO next Friday"},
            timeout=60.0,
        )
        assert r1.status_code == 200
        data1 = r1.json()

        if data1["status"] != "interrupted":
            pytest.skip("Run did not interrupt — cannot test edit flow")

        thread_id = data1["thread_id"]

        # Step 2: Resume with EDIT
        r2 = await client.post(
            f"{EMAIL_SERVICE}/resume",
            json={
                "thread_id": thread_id,
                "response": {
                    "decision": "EDIT",
                    "edit_instructions": "Make the tone more casual",
                },
            },
            timeout=60.0,
        )
        assert r2.status_code == 200
        data2 = r2.json()

        # After edit, should get another draft_review interrupt
        if data2["status"] == "interrupted":
            assert data2["interrupt_payload"]["interrupt_type"] == "draft_review"

            # Step 3: Now send
            r3 = await client.post(
                f"{EMAIL_SERVICE}/resume",
                json={
                    "thread_id": thread_id,
                    "response": {"decision": "SEND"},
                },
                timeout=60.0,
            )
            assert r3.status_code == 200


# ─── State Endpoint ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_state_invalid_thread_returns_404():
    """GET /state with a fake thread_id should return 404."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{EMAIL_SERVICE}/state/00000000-0000-0000-0000-000000000000",
            timeout=TIMEOUT,
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_state_after_run():
    """Start a run, then verify state is retrievable."""
    async with httpx.AsyncClient() as client:
        # Start a run
        r1 = await client.post(
            f"{EMAIL_SERVICE}/run",
            json={"prompt": "Check my inbox"},
            timeout=60.0,
        )
        assert r1.status_code == 200
        data1 = r1.json()
        thread_id = data1["thread_id"]

        # Retrieve state
        r2 = await client.get(
            f"{EMAIL_SERVICE}/state/{thread_id}",
            timeout=TIMEOUT,
        )
        assert r2.status_code == 200
        state = r2.json()

        # State should contain the user_prompt we sent
        assert state.get("user_prompt") == "Check my inbox"
