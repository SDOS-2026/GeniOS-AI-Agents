import os
import pytest

# By default skip integration-style API tests that require running services
# locally. Set `RUN_DAA_INTEGRATION=1` in your environment to execute them.
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DAA_INTEGRATION") != "1",
    reason="Integration tests require local services; set RUN_DAA_INTEGRATION=1 to enable"
)

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # Import app lazily to avoid import-time side effects during collection.
    from daily_attention_agent.app.api.main import app
    return TestClient(app)


def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Daily Attention Agent service is running" in response.json()["message"]

def test_agent_run_endpoint_basic():
    # Test that the POST endpoint returns a run_id immediately
    payload = {
        "user_id": "test_user",
        "workspace_id": "test_workspace",
        "vip_senders": ["ceo@example.com"],
        "keywords": ["urgent"]
    }
    response = client.post("/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert data["status"] == "running"

def test_agent_status_not_found(client):
    # Test status endpoint for invalid run_id
    response = client.get("/status/invalid-uuid")
    assert response.status_code == 404

def test_agent_history_endpoint(client):
    # We should have an empty history or history containing the basic run above
    response = client.get("/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
