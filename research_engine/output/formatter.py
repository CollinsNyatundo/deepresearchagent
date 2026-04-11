"""Report formatter — generates structured Markdown reports."""

from __future__ import annotations

import logging

from research_engine.models import ResearchResult

logger = logging.getLogger(__name__)


def format_json_summary(result: ResearchResult) -> dict:
    """Create a machine-readable summary of the research result.

    Returns a dict with key findings, citations, and metadata.
    """
    return {
        "run_id": result.run_id,
        "query": result.query,
        "model_used": result.model_used,
        "total_cycles": len(result.steps),
        "total_citations": len(result.citations),
        "progress": result.progress,
        "started_at": result.started_at.isoformat(),
        "completed_at": result.completed_at.isoformat(),
        "duration_seconds": (result.completed_at - result.started_at).total_seconds(),
        "citations": [
            {
                "id": c.id,
                "url": c.url,
                "title": c.title,
                "domain": c.domain,
            }
            for c in result.citations
        ],
        "errors": result.errors,
    }
