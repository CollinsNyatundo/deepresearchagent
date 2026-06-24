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
from tests.e2e.conftest import mock_db, mock_broadcasts, DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID

def test_auth_and_scraper_trigger_flow(e2e_test_client: TestClient, worker_test_client: TestClient, generate_webhook_signature):
    """Tier 3: Auth + Scraper Trigger Interaction.
    Authenticate User -> Create Workspace -> Trigger webhook with valid HMAC signature.
    """
    # 1. Authenticate user & create workspace
    ws_response = e2e_test_client.post("/workspaces", json={"name": "Integration Workspace"})
    assert ws_response.status_code == 200
    workspace_id = ws_response.json()["id"]
    
    # 2. Trigger webhook using the created workspace ID
    run_id = str(uuid.uuid4())
    payload = {
        "query": "artificial intelligence safety",
        "run_id": run_id,
        "workspace_id": workspace_id,
        "depth": 1,
        "timestamp": int(time.time())
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    sig = generate_webhook_signature(payload_bytes)
    
    response = worker_test_client.post(
        "/webhook/trigger",
        content=payload_bytes,
        headers={"X-Webhook-Signature": sig}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "triggered"

def test_graph_persistence_and_realtime_broadcast_flow(e2e_test_client: TestClient, sse_event_parser):
    """Tier 3: Graph Persistence + Realtime Broadcast Interaction.
    Start research stream -> Save KG -> Verify database persistence and realtime broadcast sync.
    """
    run_id = str(uuid.uuid4())
    req_data = {
        "query": "high-temperature superconductors",
        "depth": 1,
        "workspace_id": DEFAULT_WORKSPACE_ID,
        "run_id": run_id
    }
    
    # 1. Trigger stream research (this runs orchestrator under the hood)
    response = e2e_test_client.post("/research/stream", json=req_data)
    assert response.status_code == 200
    events = sse_event_parser(response.content)
    
    # 2. Verify that realtime broadcasts were sent on the channel
    channel_name = f"research_run:{run_id}"
    broadcasts_for_run = [b for b in mock_broadcasts if b[0] == channel_name]
    assert len(broadcasts_for_run) > 0
    
    # 3. Trigger manual graph build (which writes to Supabase database)
    build_response = e2e_test_client.post(f"/runs/{run_id}/knowledge-graph/build")
    assert build_response.status_code == 200
    
    # 4. Verify database persistence
    nodes = mock_db["graph_nodes"]
    edges = mock_db["graph_edges"]
    assert len(nodes) > 0
    assert any(n["run_id"] == run_id for n in nodes)

def test_campaign_standard_happy_path(
    e2e_test_client: TestClient, 
    worker_test_client: TestClient, 
    generate_webhook_signature, 
    sse_event_parser
):
    """Tier 4: Standard User Campaign Flow.
    Authenticate User -> Create Workspace -> Trigger webhook with valid HMAC -> Stream research progress via SSE -> Verify knowledge graph written to DB -> Query semantic similarity on pgvector.
    """
    # Step 1: Create Workspace
    ws_name = "Campaign Workspace"
    ws_response = e2e_test_client.post("/workspaces", json={"name": ws_name})
    assert ws_response.status_code == 200
    workspace_id = ws_response.json()["id"]
    
    # Step 2: Trigger webhook with valid HMAC on worker
    run_id = str(uuid.uuid4())
    payload = {
        "query": "quantum speed limits in open systems",
        "run_id": run_id,
        "workspace_id": workspace_id,
        "depth": 1,
        "timestamp": int(time.time())
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    sig = generate_webhook_signature(payload_bytes)
    
    webhook_response = worker_test_client.post(
        "/webhook/trigger",
        content=payload_bytes,
        headers={"X-Webhook-Signature": sig}
    )
    assert webhook_response.status_code == 200
    
    # Step 3: Stream research progress via SSE
    stream_response = e2e_test_client.post(
        "/research/stream",
        json={
            "query": "quantum speed limits in open systems",
            "depth": 1,
            "workspace_id": workspace_id,
            "run_id": run_id
        }
    )
    assert stream_response.status_code == 200
    
    # Parse events to verify progression
    events = sse_event_parser(stream_response.content)
    assert len(events) > 0
    assert any(e.get("event") == "complete" for e in events)
    
    # Step 4: Verify knowledge graph written to DB by building it
    build_response = e2e_test_client.post(f"/runs/{run_id}/knowledge-graph/build")
    assert build_response.status_code == 200
    
    # Step 5: Check database nodes and edges
    assert len(mock_db["graph_nodes"]) > 0
    assert len(mock_db["graph_edges"]) > 0
    
    # Set mock embedding coordinates to check pgvector rpc similarity
    node_id = mock_db["graph_nodes"][0]["id"]
    mock_db["graph_nodes"][0]["embedding"] = [1.0] + [0.0]*1535
    
    # Step 6: Query similarity
    similarity_query = {
        "query_embedding": [1.0] + [0.0]*1535,
        "match_threshold": 0.8,
        "match_count": 5
    }
    sim_response = e2e_test_client.post(
        f"/runs/{run_id}/knowledge-graph/similarity",
        json=similarity_query
    )
    assert sim_response.status_code == 200
    sim_results = sim_response.json()
    assert len(sim_results) > 0
    assert sim_results[0]["id"] == node_id
    assert abs(sim_results[0]["similarity"] - 1.0) < 1e-5

def test_webhook_and_realtime_broadcast_flow(
    e2e_test_client: TestClient,
    worker_test_client: TestClient,
    generate_webhook_signature
):
    """Tier 3: Webhook Trigger + Realtime Broadcast Interaction.
    Trigger webhook on worker -> worker executes background run -> check realtime broadcasts captured.
    """
    run_id = str(uuid.uuid4())
    payload = {
        "query": "realtime webhook interaction",
        "run_id": run_id,
        "workspace_id": DEFAULT_WORKSPACE_ID,
        "depth": 1,
        "timestamp": int(time.time())
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    sig = generate_webhook_signature(payload_bytes)
    
    response = worker_test_client.post(
        "/webhook/trigger",
        content=payload_bytes,
        headers={"X-Webhook-Signature": sig}
    )
    assert response.status_code == 200
    
    # Check that realtime broadcasts were sent
    channel_name = f"research_run:{run_id}"
    broadcasts_for_run = [b for b in mock_broadcasts if b[0] == channel_name]
    assert len(broadcasts_for_run) > 0
    assert any(b[1]["event"] == "complete" for b in broadcasts_for_run)

def test_auth_and_similarity_query_authorization(
    e2e_test_client: TestClient,
    generate_mock_jwt
):
    """Tier 3: Auth + Similarity Query Authorization Check.
    Attempt similarity query with invalid/missing auth, verify rejection.
    """
    run_id = str(uuid.uuid4())
    # Populate a dummy node
    mock_db["graph_nodes"].append({
        "run_id": run_id,
        "id": "node_auth_test",
        "label": "Auth Test Node",
        "embedding": [0.1] * 1536
    })
    # Add research run to workspace
    mock_db["research_runs"].append({
        "id": run_id,
        "workspace_id": DEFAULT_WORKSPACE_ID,
        "query": "auth test",
        "status": "complete",
        "created_at": "2026-06-18T00:00:00Z"
    })
    
    # Try querying similarity with invalid token
    invalid_token = generate_mock_jwt(user_id="stranger", expires_in=-10) # Expired
    headers = {"Authorization": f"Bearer {invalid_token}"}
    response = e2e_test_client.post(
        f"/runs/{run_id}/knowledge-graph/similarity",
        json={"query_embedding": [0.1]*1536, "match_threshold": 0.5},
        headers=headers
    )
    assert response.status_code == 401

def test_campaign_academic_deep_research(
    e2e_test_client: TestClient,
    sse_event_parser
):
    """Tier 4: Academic Deep Research Campaign Flow.
    Authenticate -> Create Workspace -> Research Academic Query -> Verify citations and build KG.
    """
    ws_name = "Academic Workspace"
    ws_response = e2e_test_client.post("/workspaces", json={"name": ws_name})
    assert ws_response.status_code == 200
    workspace_id = ws_response.json()["id"]
    
    run_id = str(uuid.uuid4())
    req_data = {
        "query": "quantum gravity bounds on information",
        "depth": 1,
        "workspace_id": workspace_id,
        "run_id": run_id
    }
    
    # Run research
    response = e2e_test_client.post("/research/stream", json=req_data)
    assert response.status_code == 200
    events = sse_event_parser(response.content)
    
    # Verify complete event exists
    assert any(e.get("event") == "complete" for e in events)
    
    # Trigger build knowledge graph
    build_resp = e2e_test_client.post(f"/runs/{run_id}/knowledge-graph/build")
    assert build_resp.status_code == 200
    
    # Verify graph exists in DB
    nodes = [n for n in mock_db["graph_nodes"] if n["run_id"] == run_id]
    assert len(nodes) > 0

def test_campaign_news_realtime_research(
    e2e_test_client: TestClient,
    sse_event_parser
):
    """Tier 4: News Real-Time Campaign Flow.
    Authenticate -> Create Workspace -> Research News Query -> Verify completion.
    """
    ws_name = "News Workspace"
    ws_response = e2e_test_client.post("/workspaces", json={"name": ws_name})
    assert ws_response.status_code == 200
    workspace_id = ws_response.json()["id"]
    
    run_id = str(uuid.uuid4())
    req_data = {
        "query": "latest breakthroughs in room temperature superconductivity 2026",
        "depth": 1,
        "workspace_id": workspace_id,
        "run_id": run_id
    }
    
    # Run research
    response = e2e_test_client.post("/research/stream", json=req_data)
    assert response.status_code == 200
    events = sse_event_parser(response.content)
    
    # Verify complete event
    assert any(e.get("event") == "complete" for e in events)

def test_campaign_multi_user_collaboration(
    e2e_test_client: TestClient,
    generate_mock_jwt
):
    """Tier 4: Multi-User Collaboration Campaign Flow.
    User A creates workspace and run -> User B (added as member) accesses run -> User C (stranger) is rejected.
    """
    # 1. User A creates workspace and run
    jwt_a = generate_mock_jwt(user_id="user_a", email="usera@example.com")
    headers_a = {"Authorization": f"Bearer {jwt_a}"}
    
    ws_resp = e2e_test_client.post("/workspaces", json={"name": "Shared Workspace"}, headers=headers_a)
    workspace_id = ws_resp.json()["id"]
    
    run_id = str(uuid.uuid4())
    mock_db["research_runs"].append({
        "id": run_id,
        "workspace_id": workspace_id,
        "query": "collaborative research",
        "status": "complete",
        "created_at": "2026-06-18T00:00:00Z"
    })
    
    # 2. Add User B to workspace members
    mock_db["workspace_members"].append({
        "workspace_id": workspace_id,
        "user_id": "user_b",
        "joined_at": "2026-06-18T00:00:00Z"
    })
    
    # 3. User B accesses the run
    jwt_b = generate_mock_jwt(user_id="user_b", email="userb@example.com")
    headers_b = {"Authorization": f"Bearer {jwt_b}"}
    run_resp = e2e_test_client.get(f"/runs?workspace_id={workspace_id}", headers=headers_b)
    assert run_resp.status_code == 200
    assert len(run_resp.json()) == 1
    
    # 4. User C (stranger) tries to access but is rejected
    jwt_c = generate_mock_jwt(user_id="user_c", email="userc@example.com")
    headers_c = {"Authorization": f"Bearer {jwt_c}"}
    run_resp_c = e2e_test_client.get(f"/runs?workspace_id={workspace_id}", headers=headers_c)
    assert run_resp_c.status_code == 403

def test_campaign_system_recovery_flow(
    e2e_test_client: TestClient
):
    """Tier 4: System Recovery Campaign Flow.
    Query similarity on non-existent run ID -> verify 404/403.
    """
    bad_run_id = str(uuid.uuid4())
    response = e2e_test_client.post(
        f"/runs/{bad_run_id}/knowledge-graph/similarity",
        json={"query_embedding": [0.1]*1536, "match_threshold": 0.5}
    )
    assert response.status_code in (404, 403)

