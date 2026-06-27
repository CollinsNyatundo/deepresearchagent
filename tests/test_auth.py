import pytest
from fastapi.testclient import TestClient
from research_engine.api import app
from research_engine.auth import get_supabase_jwt_secret

client = TestClient(app)

def test_get_supabase_jwt_secret_raises_runtime_error(monkeypatch):
    """Verify that get_supabase_jwt_secret raises RuntimeError when environment variable is missing."""
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        get_supabase_jwt_secret()
    assert "SUPABASE_JWT_SECRET is not set in the environment variables" in str(exc_info.value)

def test_get_runs_unauthorized():
    """Verify that GET /runs returns 401 without token."""
    response = client.get("/runs?workspace_id=test-workspace-id")
    assert response.status_code == 401

def test_get_workspaces_unauthorized():
    """Verify that GET /workspaces returns 401 without token."""
    response = client.get("/workspaces")
    assert response.status_code == 401

def test_post_research_unauthorized():
    """Verify that POST /research returns 401 without token."""
    response = client.post("/research", json={
        "query": "test query",
        "workspace_id": "test-workspace-id"
    })
    assert response.status_code == 401

def test_post_research_plan_unauthorized():
    """Verify that POST /research/plan returns 401 without token."""
    response = client.post("/research/plan", json={
        "query": "test query",
        "workspace_id": "test-workspace-id"
    })
    assert response.status_code == 401

def test_get_report_unauthorized():
    """Verify that GET /runs/{run_id}/report returns 401 without token."""
    response = client.get("/runs/some-run-id/report")
    assert response.status_code == 401

def test_get_mindmap_unauthorized():
    """Verify that GET /runs/{run_id}/mindmap returns 401 without token."""
    response = client.get("/runs/some-run-id/mindmap")
    assert response.status_code == 401

def test_post_open_file_unauthorized():
    """Verify that POST /open-file returns 401 without token."""
    response = client.post("/open-file", json={"path": "README.md"})
    assert response.status_code == 401

def test_post_validate_model_unauthorized():
    """Verify that POST /validate-model returns 401 without token."""
    response = client.post("/validate-model", json={"model": "openai/gpt-4"})
    assert response.status_code == 401

def test_get_scraper_status_unauthorized():
    """Verify that GET /scraper/status returns 401 without token."""
    response = client.get("/scraper/status")
    assert response.status_code == 401

def test_post_scraper_refresh_cache_unauthorized():
    """Verify that POST /scraper/refresh-cache returns 401 without token."""
    response = client.post("/scraper/refresh-cache")
    assert response.status_code == 401

def test_post_gitnexus_serve_start_unauthorized():
    """Verify that POST /gitnexus/serve/start returns 401 without token."""
    response = client.post("/gitnexus/serve/start")
    assert response.status_code == 401

def test_post_gitnexus_serve_stop_unauthorized():
    """Verify that POST /gitnexus/serve/stop returns 401 without token."""
    response = client.post("/gitnexus/serve/stop")
    assert response.status_code == 401

def test_get_gitnexus_serve_status_unauthorized():
    """Verify that GET /gitnexus/serve/status returns 401 without token."""
    response = client.get("/gitnexus/serve/status")
    assert response.status_code == 401

def test_get_telemetry_unauthorized():
    """Verify that GET /api/telemetry returns 401 without token."""
    response = client.get("/api/telemetry")
    assert response.status_code == 401


def test_dev_bypass_workspaces(monkeypatch):
    """Verify that under dev bypass mode, GET /workspaces returns the synthetic UUID workspace."""
    from research_engine import auth
    monkeypatch.setattr(auth, "_is_dev_bypass", lambda: True)
    
    response = client.get("/workspaces", headers={"Authorization": "Bearer bypass"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "11111111-1111-1111-1111-111111111111"
    assert data[0]["name"] == "Dev Workspace"


def test_dev_bypass_create_workspace(monkeypatch):
    """Verify that under dev bypass mode, POST /workspaces generates a valid UUID workspace."""
    from research_engine import auth
    monkeypatch.setattr(auth, "_is_dev_bypass", lambda: True)
    
    from unittest.mock import MagicMock
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
    
    monkeypatch.setattr("research_engine.api.get_supabase_client", lambda: mock_client)
    
    response = client.post(
        "/workspaces",
        json={"name": "New Dev Workspace"},
        headers={"Authorization": "Bearer bypass"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    
    import uuid
    val = uuid.UUID(data["id"])
    assert val is not None
    assert data["name"] == "New Dev Workspace"
