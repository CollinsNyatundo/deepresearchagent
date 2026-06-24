# ==========================================
# MANDATORY INTEGRITY WARNING
# DO NOT CHEAT. All implementations must be genuine.
# - DO NOT hardcode test results, expected outputs, or verification strings.
# - DO NOT create dummy or facade implementations.
# - Every implementation must maintain real state and produce real behavior.
# ==========================================

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
        status="complete",
        progress=100,
        workspace_id=result.workspace_id,
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
    """Save a KnowledgeGraph to disk as knowledge_graph.json and database tables."""
    import aiofiles
    import asyncio
    run_dir = Path(output_dir) / run_id
    await asyncio.to_thread(run_dir.mkdir, parents=True, exist_ok=True)
    kg_path = run_dir / "knowledge_graph.json"
    async with aiofiles.open(kg_path, "w", encoding="utf-8") as f:
        await f.write(kg.model_dump_json(indent=2))
    logger.info(f"Saved knowledge graph to: {kg_path}")

    # Database persistence
    try:
        from research_engine.db.supabase.client import get_supabase_client
        client = get_supabase_client()
        
        # Prepare nodes
        db_nodes = []
        for node in kg.nodes:
            db_nodes.append({
                "run_id": run_id,
                "id": node.id,
                "label": node.label,
                "type": node.type,
                "community": node.community,
                "degree": node.degree,
                "is_god_node": node.is_god_node,
                "provenance": node.provenance,
                "confidence": node.confidence,
                "summary": node.summary or "",
                "file_path": node.file_path or "",
                "embedding": getattr(node, "embedding", None) or [0.0] * 1536
            })
            
        if db_nodes:
            await asyncio.to_thread(client.table("graph_nodes").upsert(db_nodes).execute)
            
        # Prepare edges
        db_edges = []
        for edge in kg.edges:
            db_edges.append({
                "run_id": run_id,
                "source": edge.source,
                "target": edge.target,
                "type": edge.type,
                "provenance": edge.provenance,
                "confidence": edge.confidence,
                "label": edge.label or ""
            })
            
        if db_edges:
            await asyncio.to_thread(client.table("graph_edges").upsert(db_edges).execute)
            
        logger.info(f"Successfully saved knowledge graph to database for run {run_id}")
    except Exception as e:
        logger.error(f"Failed to save knowledge graph to database: {e}")


def load_knowledge_graph(
    run_id: str,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> KnowledgeGraph:
    """Load a KnowledgeGraph from database or disk."""
    # Try database first
    try:
        from research_engine.db.supabase.client import get_supabase_client
        client = get_supabase_client()
        
        nodes_res = client.table("graph_nodes").select("*").eq("run_id", run_id).execute()
        edges_res = client.table("graph_edges").select("*").eq("run_id", run_id).execute()
        
        if nodes_res.data:
            from research_engine.models import KGNode, KGEdge, KnowledgeGraph
            nodes = [KGNode(**row) for row in nodes_res.data]
            edges = [KGEdge(**row) for row in edges_res.data]
            return KnowledgeGraph(
                run_id=run_id,
                nodes=nodes,
                edges=edges,
                graphify_version="0.1.0",
                corpus_stats={"total_nodes": len(nodes), "total_edges": len(edges)}
            )
    except Exception as e:
        logger.error(f"Failed to load knowledge graph from database: {e}")

    # Fallback to disk
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
