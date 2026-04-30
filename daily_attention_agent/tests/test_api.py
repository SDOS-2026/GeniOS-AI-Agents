import pytest
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

def test_read_root():
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

def test_agent_status_not_found():
    # Test status endpoint for invalid run_id
    response = client.get("/status/invalid-uuid")
    assert response.status_code == 404

def test_agent_history_endpoint():
    # We should have an empty history or history containing the basic run above
    response = client.get("/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
