"""File storage — save/load research runs, reports, and mindmaps."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from research_engine.models import (
    MindmapGraph,
    ResearchResult,
    RunSummary,
)

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path("outputs")


async def save_run(
    result: ResearchResult,
    mindmap: MindmapGraph,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Path:
    """Save a complete research run to disk.

    Creates:
      outputs/{run_id}/
        report.md
        summary.json
        trace.json
        mindmap.json

    Returns the run directory path.
    """
    base = Path(output_dir)
    run_dir = base / result.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Save Markdown report
    report_path = run_dir / "report.md"
    report_path.write_text(result.report, encoding="utf-8")

    # Save summary JSON (lightweight, for listing)
    summary = RunSummary(
        id=result.run_id,
        query=result.query,
        created_at=result.started_at.isoformat(),
        model_used=result.model_used,
    )
    summary_path = run_dir / "summary.json"
    summary_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")

    # Save full trace JSON
    trace_path = run_dir / "trace.json"
    trace_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    # Save mindmap JSON (for frontend G6 visualization)
    mindmap_path = run_dir / "mindmap.json"
    mindmap_path.write_text(mindmap.model_dump_json(indent=2), encoding="utf-8")

    logger.info(f"Saved research run to: {run_dir}")
    return run_dir


def load_run(run_id: str, output_dir: Path | str = DEFAULT_OUTPUT_DIR) -> ResearchResult:
    """Load a research result from disk."""
    run_dir = Path(output_dir) / run_id
    trace_path = run_dir / "trace.json"

    if not trace_path.exists():
        raise FileNotFoundError(f"Run not found: {run_id}")

    data = json.loads(trace_path.read_text(encoding="utf-8"))
    return ResearchResult.model_validate(data)


def load_mindmap(run_id: str, output_dir: Path | str = DEFAULT_OUTPUT_DIR) -> MindmapGraph:
    """Load a mindmap graph from disk."""
    run_dir = Path(output_dir) / run_id
    mindmap_path = run_dir / "mindmap.json"

    if not mindmap_path.exists():
        raise FileNotFoundError(f"Mindmap not found for run: {run_id}")

    data = json.loads(mindmap_path.read_text(encoding="utf-8"))
    return MindmapGraph.model_validate(data)


def save_mindmap(
    mindmap: MindmapGraph,
    run_id: str,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> None:
    """Save an updated mindmap graph to disk."""
    run_dir = Path(output_dir) / run_id
    mindmap_path = run_dir / "mindmap.json"
    mindmap_path.write_text(mindmap.model_dump_json(indent=2), encoding="utf-8")


def load_report(run_id: str, output_dir: Path | str = DEFAULT_OUTPUT_DIR) -> str:
    """Load a report Markdown from disk."""
    run_dir = Path(output_dir) / run_id
    report_path = run_dir / "report.md"

    if not report_path.exists():
        raise FileNotFoundError(f"Report not found for run: {run_id}")

    return report_path.read_text(encoding="utf-8")


def list_runs(output_dir: Path | str = DEFAULT_OUTPUT_DIR) -> list[RunSummary]:
    """List all research runs sorted by creation date (newest first)."""
    base = Path(output_dir)
    if not base.exists():
        return []

    runs: list[RunSummary] = []
    for run_dir in sorted(base.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        summary_path = run_dir / "summary.json"
        if summary_path.exists():
            try:
                data = json.loads(summary_path.read_text(encoding="utf-8"))
                runs.append(RunSummary.model_validate(data))
            except Exception as e:
                logger.warning(f"Failed to load summary for {run_dir.name}: {e}")
                # Create a minimal summary from directory name
                runs.append(RunSummary(
                    id=run_dir.name,
                    query="(unknown)",
                    created_at=run_dir.name,
                ))

    return runs
