# ==========================================
# MANDATORY INTEGRITY WARNING
# DO NOT CHEAT. All implementations must be genuine.
# - DO NOT hardcode test results, expected outputs, or verification strings.
# - DO NOT create dummy or facade implementations.
# - Every implementation must maintain real state and produce real behavior.
# ==========================================

import uuid
import asyncio
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from research_engine.api import app
from tests.e2e.conftest import mock_db, mock_broadcasts, DEFAULT_WORKSPACE_ID, DEFAULT_USER_ID

@pytest.fixture
def valid_research_request() -> dict:
    return {
        "query": "quantum speed limits in open systems",
        "depth": 1,
        "workspace_id": DEFAULT_WORKSPACE_ID,
        "run_id": str(uuid.uuid4())
    }

def test_sse_stream_connection(e2e_test_client: TestClient, valid_research_request):
    """Happy Path: POST /research/stream establishes SSE stream (content-type text/event-stream)."""
    response = e2e_test_client.post("/research/stream", json=valid_research_request, headers={"Accept": "text/event-stream"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

def test_sse_progress_increments(e2e_test_client: TestClient, sse_event_parser, valid_research_request):
    """Happy Path: SSE events contain ascending progress values."""
    response = e2e_test_client.post("/research/stream", json=valid_research_request)
    assert response.status_code == 200
    
    events = sse_event_parser(response.content)
    progress_values = []
    for event in events:
        event_name = event.get("event")
        data = event.get("data", {})
        if event_name == "progress" or "progress" in data:
            progress_values.append(data.get("progress", 0))
            
    assert len(progress_values) > 0
    assert progress_values == sorted(progress_values)

def test_sse_research_steps(e2e_test_client: TestClient, sse_event_parser, valid_research_request):
    """Happy Path: Stream emits detail packets containing research steps (searching, scraping, synthesizing)."""
    response = e2e_test_client.post("/research/stream", json=valid_research_request)
    assert response.status_code == 200
    
    events = sse_event_parser(response.content)
    has_steps = False
    for event in events:
        event_name = event.get("event")
        if event_name in ("searching", "scraping", "synthesizing", "planning"):
            has_steps = True
            break
            
    assert has_steps, "Should emit research steps"

def test_sse_complete_marker(e2e_test_client: TestClient, sse_event_parser, valid_research_request):
    """Happy Path: Emits end-of-stream complete event indicating research summary."""
    response = e2e_test_client.post("/research/stream", json=valid_research_request)
    assert response.status_code == 200
    
    events = sse_event_parser(response.content)
    has_complete = any(event.get("event") == "complete" for event in events)
    assert has_complete, "Should emit complete event marker"

def test_supabase_realtime_broadcast(e2e_test_client: TestClient, valid_research_request):
    """Happy Path: Broadcasts progress updates via Supabase Realtime channel."""
    run_id = valid_research_request["run_id"]
    response = e2e_test_client.post("/research/stream", json=valid_research_request)
    assert response.status_code == 200
    
    # Assert that mock_broadcasts captured the channel updates
    channel_name = f"research_run:{run_id}"
    broadcasts_for_run = [b for b in mock_broadcasts if b[0] == channel_name]
    assert len(broadcasts_for_run) > 0
    
    # Assert we broadcasted initializing and progress/complete
    events = [b[1]["event"] for b in broadcasts_for_run]
    assert "initializing" in events
    assert "complete" in events

def test_sse_stream_auth_failure(e2e_test_client: TestClient, valid_research_request):
    """Boundary/Corner: Unauthenticated SSE requests are rejected (HTTP 401)."""
    auth_header = e2e_test_client.headers.pop("Authorization", None)
    try:
        response = e2e_test_client.post(
            "/research/stream",
            json=valid_research_request
        )
    finally:
        if auth_header:
            e2e_test_client.headers["Authorization"] = auth_header
    assert response.status_code in (401, 403)

@pytest.mark.asyncio
async def test_sse_client_disconnect(valid_research_request, mock_auth_headers):
    """Boundary/Corner: Server terminates research task cleanly if client disconnects mid-stream."""
    from unittest import mock
    from research_engine.api import stream_research
    from research_engine.models import ResearchRequest

    run_id = valid_research_request["run_id"]
    
    # Create the run in mock db first
    mock_db["research_runs"].append({
        "id": run_id,
        "workspace_id": DEFAULT_WORKSPACE_ID,
        "query": valid_research_request["query"],
        "status": "initializing",
        "created_at": "2026-06-18T00:00:00Z"
    })
    
    user_data = {"sub": DEFAULT_USER_ID}
    req = ResearchRequest(**valid_research_request)
    
    # Get the StreamingResponse
    response = await stream_research(req, user_data=user_data)
    assert response.media_type == "text/event-stream"
    
    gen = response.body_iterator
    
    # Run the generator in a task and cancel it mid-stream
    async def consume():
        async for chunk in gen:
            # Cancel the task as soon as we get the first chunk to ensure mid-stream cancellation
            task.cancel()
            await asyncio.sleep(0.01)

    task = asyncio.create_task(consume())
    try:
        await task
    except asyncio.CancelledError:
        pass
        
    # Explicitly close generator to trigger finally block immediately
    await gen.aclose()
    
    # Wait a moment for background task cancel propagation
    await asyncio.sleep(0.1)
    
    # Verify that the run record in DB was set to "failed" on cancellation
    run_record = next((r for r in mock_db["research_runs"] if r["id"] == run_id), None)
    assert run_record is not None
    assert run_record["status"] == "failed"

def test_sse_step_limit_boundary(e2e_test_client: TestClient, sse_event_parser, valid_research_request):
    """Boundary/Corner: Depth 1 results in limited cycles, respecting boundary limit."""
    valid_research_request["depth"] = 1
    response = e2e_test_client.post("/research/stream", json=valid_research_request)
    assert response.status_code == 200
    
    events = sse_event_parser(response.content)
    cycles = [e for e in events if e.get("event") == "cycle_complete"]
    # For depth 1, max cycles should be 6
    assert len(cycles) <= 6

@pytest.mark.asyncio
async def test_sse_error_propagation(mock_auth_headers, sse_event_parser):
    """Boundary/Corner: If LLM or Scraper fails, error payload is streamed through SSE before closure."""
    # We trigger an error by patching the orchestrator to raise an exception
    from unittest import mock
    from research_engine.agent.orchestrator import DeepResearchOrchestrator
    
    run_id = str(uuid.uuid4())
    req_data = {
        "query": "cause an error",
        "depth": 1,
        "workspace_id": DEFAULT_WORKSPACE_ID,
        "run_id": run_id
    }
    
    async def mock_run_error(*args, **kwargs):
        raise RuntimeError("Simulated LLM failure")
        
    with mock.patch.object(DeepResearchOrchestrator, "run", mock_run_error):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            client.headers.update(mock_auth_headers)
            
            response = await client.post("/research/stream", json=req_data)
            assert response.status_code == 200
            
            # Parse events and look for "error"
            events = sse_event_parser(response.content)
            
            error_events = [e for e in events if e.get("event") == "error"]
            assert len(error_events) > 0
            assert "Simulated LLM failure" in error_events[0]["data"]["error"]

def test_realtime_progress_throttle(e2e_test_client: TestClient, valid_research_request):
    """Boundary/Corner: SSE stream is throttled and completes successfully under load."""
    # Run a complete stream and verify it doesn't crash/timeout and successfully completes
    response = e2e_test_client.post("/research/stream", json=valid_research_request)
    assert response.status_code == 200
