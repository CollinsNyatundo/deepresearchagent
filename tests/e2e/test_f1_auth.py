# ==========================================
# MANDATORY INTEGRITY WARNING
# DO NOT CHEAT. All implementations must be genuine.
# - DO NOT hardcode test results, expected outputs, or verification strings.
# - DO NOT create dummy or facade implementations.
# - Every implementation must maintain real state and produce real behavior.
# ==========================================

import time
import pytest
from fastapi.testclient import TestClient
from tests.e2e.conftest import DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID, DEFAULT_EMAIL

def test_auth_success(e2e_test_client: TestClient):
    """Happy Path: Valid Bearer JWT returns workspaces list with status 200."""
    response = e2e_test_client.get("/workspaces")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["id"] == DEFAULT_WORKSPACE_ID

def test_workspace_create(e2e_test_client: TestClient):
    """Happy Path: Create a new workspace with valid name."""
    ws_name = "New Dynamic Test Workspace"
    response = e2e_test_client.post("/workspaces", json={"name": ws_name})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["name"] == ws_name
    
    # Check that it appears in workspaces list
    list_response = e2e_test_client.get("/workspaces")
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert any(ws["name"] == ws_name for ws in list_data)

def test_workspace_select(e2e_test_client: TestClient):
    """Happy Path: Select workspace and retrieve runs filtered by workspace_id."""
    response = e2e_test_client.get(f"/runs?workspace_id={DEFAULT_WORKSPACE_ID}")
    assert response.status_code == 200
    runs = response.json()
    assert isinstance(runs, list)

def test_workspace_members_list(e2e_test_client: TestClient):
    """Happy Path: Retrieve member list for workspace."""
    response = e2e_test_client.get(f"/workspaces/{DEFAULT_WORKSPACE_ID}/members")
    assert response.status_code == 200
    members = response.json()
    assert isinstance(members, list)
    assert len(members) > 0
    assert members[0]["user_id"] == DEFAULT_USER_ID

def test_jwt_signature_check(e2e_test_client: TestClient, generate_mock_jwt):
    """Happy Path: Successful access using dynamically generated valid JWT."""
    valid_jwt = generate_mock_jwt(user_id="dynamic-user-id", email="dynamic@example.com")
    headers = {"Authorization": f"Bearer {valid_jwt}"}
    
    # User needs a workspace first to list workspaces
    # Let's create a workspace using this user
    create_resp = e2e_test_client.post("/workspaces", json={"name": "Dynamic User Workspace"}, headers=headers)
    assert create_resp.status_code == 200
    
    response = e2e_test_client.get("/workspaces", headers=headers)
    assert response.status_code == 200
    workspaces = response.json()
    assert len(workspaces) > 0
    assert workspaces[0]["name"] == "Dynamic User Workspace"

def test_auth_expired_jwt(e2e_test_client: TestClient, generate_mock_jwt):
    """Boundary/Corner: Token past exp claim returns HTTP 401."""
    expired_jwt = generate_mock_jwt(expires_in=-10)  # Expired 10 seconds ago
    headers = {"Authorization": f"Bearer {expired_jwt}"}
    response = e2e_test_client.get("/workspaces", headers=headers)
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()

def test_auth_invalid_signature(e2e_test_client: TestClient):
    """Boundary/Corner: Token signed with different key returns HTTP 401."""
    import jwt
    bad_secret = "totally-wrong-jwt-secret-key-signature-fail"
    payload = {
        "sub": DEFAULT_USER_ID,
        "email": DEFAULT_EMAIL,
        "role": "authenticated",
        "aud": "authenticated",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600
    }
    invalid_jwt = jwt.encode(payload, bad_secret, algorithm="HS256")
    headers = {"Authorization": f"Bearer {invalid_jwt}"}
    response = e2e_test_client.get("/workspaces", headers=headers)
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()

def test_auth_missing_header(e2e_test_client: TestClient):
    """Boundary/Corner: Request without Authorization header returns HTTP 401."""
    # Temporarily remove headers by popping from client headers
    auth_header = e2e_test_client.headers.pop("Authorization", None)
    try:
        response = e2e_test_client.get("/workspaces")
    finally:
        if auth_header:
            e2e_test_client.headers["Authorization"] = auth_header
    # FastAPI HTTPBearer returns 403 or 401 on missing auth credentials.
    # verify_supabase_jwt / security scheme returns 403 on missing or invalid Authorization header
    assert response.status_code in (401, 403)

def test_workspace_create_empty_name(e2e_test_client: TestClient):
    """Boundary/Corner: Creating workspace with empty name returns HTTP 400."""
    response = e2e_test_client.post("/workspaces", json={"name": ""})
    # Since pydantic or route validation checks workspace name size or non-empty string,
    # it should return 422 (validation error) or 400 based on validation rules.
    # Accept either 400 or 422 as validation failure.
    assert response.status_code in (400, 422)

def test_workspace_access_denied(e2e_test_client: TestClient, generate_mock_jwt):
    """Boundary/Corner: Accessing workspace that user does not belong to returns HTTP 403."""
    unauthorized_jwt = generate_mock_jwt(user_id="other-stranger-user-id", email="stranger@example.com")
    headers = {"Authorization": f"Bearer {unauthorized_jwt}"}
    
    # Try to access default workspace using stranger's JWT
    response = e2e_test_client.get(f"/workspaces/{DEFAULT_WORKSPACE_ID}/members", headers=headers)
    assert response.status_code == 403
