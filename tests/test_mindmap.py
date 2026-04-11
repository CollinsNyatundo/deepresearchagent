"""Tests for mindmap builder."""

from research_engine.models import (
    Citation,
    ResearchPlan,
    ResearchResult,
    ResearchStep,
    SearchAnswer,
    SearchQuery,
)
from research_engine.output.mindmap import build_mindmap_graph


def _make_result() -> ResearchResult:
    """Create a minimal ResearchResult for testing."""
    from datetime import datetime, timezone

    return ResearchResult(
        run_id="test-run-001",
        query="Test research query",
        model_used="test/model",
        plan=ResearchPlan(steps=["Step 1", "Step 2"]),
        final_plan=ResearchPlan(steps=["Step 1", "Step 2"]),
        report=(
            "# Test Report\n\n"
            "## Executive Summary\n\nThis is a test summary.\n\n"
            "## Section One\n\nContent for section one [1].\n\n"
            "### Sub Point A\n\nDetail about sub point A.\n\n"
            "## Section Two\n\nContent for section two [2].\n\n"
        ),
        citations=[
            Citation(id="c1", url="https://example.com/1", title="Source 1", domain="example.com"),
            Citation(id="c2", url="https://example.com/2", title="Source 2", domain="example.com"),
        ],
        progress=90,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )


def test_build_mindmap_graph():
    """Mindmap should have root + section + detail nodes."""
    result = _make_result()
    graph = build_mindmap_graph(result)

    assert graph.run_id == "test-run-001"
    assert len(graph.nodes) >= 3  # root + 2 sections minimum
    assert graph.nodes[0].id == "root"
    assert graph.nodes[0].type == "root"

    # Check section nodes exist
    section_nodes = [n for n in graph.nodes if n.type == "section"]
    assert len(section_nodes) >= 2

    # Check edges connect root to sections
    root_edges = [e for e in graph.edges if e.source == "root"]
    assert len(root_edges) >= 2


def test_mindmap_has_citations():
    """Section nodes should have citation references."""
    result = _make_result()
    graph = build_mindmap_graph(result)

    # At least one node should reference citations
    nodes_with_citations = [n for n in graph.nodes if n.citations]
    assert len(nodes_with_citations) >= 1
