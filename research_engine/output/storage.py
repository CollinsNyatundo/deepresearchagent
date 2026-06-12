"""File storage — save/load research runs, reports, and mindmaps."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from research_engine.models import (
    KnowledgeGraph,
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
    import asyncio
    import aiofiles

    base = Path(output_dir)
    run_dir = base / result.run_id
    await asyncio.to_thread(run_dir.mkdir, parents=True, exist_ok=True)

    # Save Markdown report
    report_path = run_dir / "report.md"
    async with aiofiles.open(report_path, "w", encoding="utf-8") as f:
        await f.write(result.report)

    # Save summary JSON (lightweight, for listing)
    summary = RunSummary(
        id=result.run_id,
        query=result.query,
        created_at=result.started_at.isoformat(),
        model_used=result.model_used,
    )
    summary_path = run_dir / "summary.json"
    async with aiofiles.open(summary_path, "w", encoding="utf-8") as f:
        await f.write(summary.model_dump_json(indent=2))

    # Save full trace JSON
    trace_path = run_dir / "trace.json"
    async with aiofiles.open(trace_path, "w", encoding="utf-8") as f:
        await f.write(result.model_dump_json(indent=2))

    # Save mindmap JSON (for frontend G6 visualization)
    mindmap_path = run_dir / "mindmap.json"
    async with aiofiles.open(mindmap_path, "w", encoding="utf-8") as f:
        await f.write(mindmap.model_dump_json(indent=2))

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


# ─── Knowledge Graph (Graphify) ──────────────────────────────────────

async def save_knowledge_graph(
    kg: KnowledgeGraph,
    run_id: str,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> None:
    """Save a KnowledgeGraph to disk as knowledge_graph.json."""
    import aiofiles
    run_dir = Path(output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    kg_path = run_dir / "knowledge_graph.json"
    async with aiofiles.open(kg_path, "w", encoding="utf-8") as f:
        await f.write(kg.model_dump_json(indent=2))
    logger.info(f"Saved knowledge graph to: {kg_path}")


def load_knowledge_graph(
    run_id: str,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> KnowledgeGraph:
    """Load a KnowledgeGraph from disk."""
    run_dir = Path(output_dir) / run_id
    kg_path = run_dir / "knowledge_graph.json"

    if not kg_path.exists():
        raise FileNotFoundError(f"Knowledge graph not found for run: {run_id}")

    data = json.loads(kg_path.read_text(encoding="utf-8"))
    return KnowledgeGraph.model_validate(data)


def knowledge_graph_available(
    run_id: str,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> bool:
    """Return True if a knowledge_graph.json exists for this run."""
    return (Path(output_dir) / run_id / "knowledge_graph.json").exists()


def graph_html_available(
    run_id: str,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> bool:
    """Return True if a graph.html exists for this run."""
    return (Path(output_dir) / run_id / "graph.html").exists()



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
