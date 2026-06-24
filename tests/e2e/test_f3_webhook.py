# ==========================================
# MANDATORY INTEGRITY WARNING
# DO NOT CHEAT. All implementations must be genuine.
# - DO NOT hardcode test results, expected outputs, or verification strings.
# - DO NOT create dummy or facade implementations.
# - Every implementation must maintain real state and produce real behavior.
# ==========================================

import time
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from tests.e2e.conftest import DEFAULT_WORKSPACE_ID

@pytest.fixture
def valid_webhook_payload() -> dict:
    return {
        "query": "quantum entanglement bounds",
        "run_id": str(uuid.uuid4()),
        "workspace_id": DEFAULT_WORKSPACE_ID,
        "depth": 1,
        "timestamp": int(time.time())
    }

def test_webhook_trigger_authorized(worker_test_client: TestClient, generate_webhook_signature, valid_webhook_payload):
    """Happy Path: POST /webhook/trigger with valid HMAC signature starts scraping job."""
    payload_bytes = json.dumps(valid_webhook_payload).encode("utf-8")
    sig = generate_webhook_signature(payload_bytes)
    
    response = worker_test_client.post(
        "/webhook/trigger",
        content=payload_bytes,
        headers={"X-Webhook-Signature": sig}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "triggered"
    assert "task_id" in data

def test_webhook_response_format(worker_test_client: TestClient, generate_webhook_signature, valid_webhook_payload):
    """Happy Path: Trigger returns task ID and confirmation structure."""
    payload_bytes = json.dumps(valid_webhook_payload).encode("utf-8")
    sig = generate_webhook_signature(payload_bytes)
    
    response = worker_test_client.post(
        "/webhook/trigger",
        content=payload_bytes,
        headers={"X-Webhook-Signature": sig}
    )
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert "status" in data
    assert "message" in data

def test_webhook_trigger_uses_camoufox(e2e_test_client: TestClient):
    """Happy Path: Check that scraper status endpoint lists stealthy_camoufox as available/active."""
    response = e2e_test_client.get("/scraper/status")
    assert response.status_code == 200
    data = response.json()
    assert "availability" in data
    # Ensure our scraper environment reports fetcher details
    assert "stealthy_camoufox" in data["availability"]

def test_webhook_trigger_uses_playwright(e2e_test_client: TestClient):
    """Happy Path: Check that scraper status endpoint lists dynamic_fetcher (Playwright) as available/active."""
    response = e2e_test_client.get("/scraper/status")
    assert response.status_code == 200
    data = response.json()
    assert "availability" in data
    assert "dynamic" in data["availability"]

def test_webhook_custom_secret(worker_test_client: TestClient, generate_webhook_signature, valid_webhook_payload, monkeypatch):
    """Happy Path: Custom HMAC secret overrides default and authenticates correctly."""
    custom_secret = "my-custom-super-secret-webhook-key"
    monkeypatch.setenv("WEBHOOK_HMAC_SECRET", custom_secret)
    
    payload_bytes = json.dumps(valid_webhook_payload).encode("utf-8")
    # Generate signature using the custom secret
    sig = generate_webhook_signature(payload_bytes, secret=custom_secret)
    
    response = worker_test_client.post(
        "/webhook/trigger",
        content=payload_bytes,
        headers={"X-Webhook-Signature": sig}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "triggered"

def test_webhook_trigger_unauthorized(worker_test_client: TestClient, valid_webhook_payload):
    """Boundary/Corner: Trigger with incorrect HMAC signature returns HTTP 403."""
    payload_bytes = json.dumps(valid_webhook_payload).encode("utf-8")
    bad_sig = "a"*64 # Wrong signature
    
    response = worker_test_client.post(
        "/webhook/trigger",
        content=payload_bytes,
        headers={"X-Webhook-Signature": bad_sig}
    )
    assert response.status_code == 403
    assert "signature" in response.json()["detail"].lower()

def test_webhook_trigger_missing_signature(worker_test_client: TestClient, valid_webhook_payload):
    """Boundary/Corner: Trigger without X-Webhook-Signature header returns HTTP 400."""
    payload_bytes = json.dumps(valid_webhook_payload).encode("utf-8")
    response = worker_test_client.post(
        "/webhook/trigger",
        content=payload_bytes
    )
    assert response.status_code == 400
    assert "signature" in response.json()["detail"].lower()

def test_webhook_trigger_empty_body(worker_test_client: TestClient, generate_webhook_signature):
    """Boundary/Corner: Empty POST request body returns HTTP 400."""
    empty_body = b""
    sig = generate_webhook_signature(empty_body)
    
    response = worker_test_client.post(
        "/webhook/trigger",
        content=empty_body,
        headers={"X-Webhook-Signature": sig}
    )
    assert response.status_code == 400

def test_webhook_trigger_expired_timestamp(worker_test_client: TestClient, generate_webhook_signature, valid_webhook_payload):
    """Boundary/Corner: Reject signatures older than 5 minutes limit."""
    # Set payload timestamp to 10 minutes ago
    valid_webhook_payload["timestamp"] = int(time.time()) - 600
    payload_bytes = json.dumps(valid_webhook_payload).encode("utf-8")
    sig = generate_webhook_signature(payload_bytes)
    
    response = worker_test_client.post(
        "/webhook/trigger",
        content=payload_bytes,
        headers={"X-Webhook-Signature": sig}
    )
    assert response.status_code == 403
    assert "expired" in response.json()["detail"].lower()

def test_webhook_trigger_invalid_json(worker_test_client: TestClient, generate_webhook_signature):
    """Boundary/Corner: Malformed JSON webhook payload returns HTTP 400."""
    bad_json = b"{'query': 'unclosed brace"
    sig = generate_webhook_signature(bad_json)
    
    response = worker_test_client.post(
        "/webhook/trigger",
        content=bad_json,
        headers={"X-Webhook-Signature": sig}
    )
    assert response.status_code == 400
    assert "malformed" in response.json()["detail"].lower()
