"""Tests for the /runs/{run_id}/resynthesize endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from research_engine.api import app
from research_engine.models import (
    Citation,
    ResearchPlan,
    ResearchResult,
    ResearchStep,
    SearchAnswer,
    SearchQuery,
    ScrapedPage,
    SearchResult,
)

client = TestClient(app)


import pytest

@pytest.fixture(autouse=True)
def override_auth():
    from research_engine.auth import verify_supabase_jwt
    app.dependency_overrides[verify_supabase_jwt] = lambda: {"sub": "test-user-id"}
    yield
    app.dependency_overrides.clear()


@patch("research_engine.api.verify_workspace_membership")
@patch("research_engine.api.get_run_workspace_id")
@patch("research_engine.output.storage.load_run")
@patch("research_engine.output.storage.save_run")
@patch("research_engine.output.storage.save_knowledge_graph")
@patch("research_engine.output.mindmap.build_mindmap_graph")
@patch("research_engine.knowledge_graph.builder.build_knowledge_graph")
@patch("research_engine.knowledge_graph.mcp_bridge.stop_mcp_server")
@patch("research_engine.knowledge_graph.mcp_bridge.start_mcp_server")
@patch("research_engine.agent.orchestrator.DeepResearchOrchestrator._generate_report")
def test_resynthesize_endpoint(
    mock_gen_report,
    mock_start_mcp,
    mock_stop_mcp,
    mock_build_kg,
    mock_build_mindmap,
    mock_save_kg,
    mock_save_run,
    mock_load_run,
    mock_get_workspace_id,
    mock_verify_membership,
):
    mock_verify_membership.return_value = True
    mock_get_workspace_id.return_value = "00000000-0000-0000-0000-000000000000"

    # Setup mock data
    mock_run_id = "test-run-123"
    mock_plan = ResearchPlan(steps=["Step 1"])
    mock_citations = [
        Citation(id="c1", url="https://enabled-site.com/page", title="Enabled", domain="enabled-site.com"),
        Citation(id="c2", url="https://disabled-site.com/page", title="Disabled", domain="disabled-site.com"),
    ]
    
    mock_step = ResearchStep(
        cycle=1,
        query=SearchQuery(query="test query"),
        search_results=[
            SearchResult(url="https://enabled-site.com/page", title="Enabled"),
            SearchResult(url="https://disabled-site.com/page", title="Disabled"),
        ],
        scraped_pages=[
            ScrapedPage(url="https://enabled-site.com/page", title="Enabled", content="Some text"),
            ScrapedPage(url="https://disabled-site.com/page", title="Disabled", content="Other text"),
        ],
        answer=SearchAnswer(answer="Answer with [1] and [2]", citations=mock_citations),
    )
    
    mock_result = ResearchResult(
        run_id=mock_run_id,
        query="test query",
        model_used="model",
        plan=mock_plan,
        final_plan=mock_plan,
        steps=[mock_step],
        report="Old report",
        citations=mock_citations,
    )
    
    mock_load_run.return_value = mock_result
    mock_gen_report.return_value = "New regenerated report without disabled domain"
    mock_build_mindmap.return_value = MagicMock()
    mock_save_run.return_value = MagicMock()
    
    # Request body
    payload = {
        "disabled_domains": ["disabled-site.com"],
        "model": "google/gemini-flash-1.5:free",
    }
    
    response = client.post(f"/runs/{mock_run_id}/resynthesize", json=payload)
    assert response.status_code == 200
    
    # Read the SSE stream
    content = response.text
    assert "event: generating_report" in content
    assert "event: complete" in content
    
    # Verify load_run was called with correct ID
    mock_load_run.assert_called_once_with(mock_run_id)
    
    # Verify _generate_report was called and the context passed had filtered scraped pages/citations
    called_context = mock_gen_report.call_args[1]["context"]
    trace = called_context.get_trace()
    assert len(trace) == 1
    # Check that disabled-site.com was filtered out
    assert len(trace[0].scraped_pages) == 1
    assert trace[0].scraped_pages[0].url == "https://enabled-site.com/page"
    
    assert len(trace[0].search_results) == 1
    assert trace[0].search_results[0].url == "https://enabled-site.com/page"
    
    assert len(trace[0].answer.citations) == 1
    assert trace[0].answer.citations[0].url == "https://enabled-site.com/page"
