"""Strategy A — Knowledge Graph Builder.

Converts a completed ResearchResult into a Graphify knowledge graph by:
1. Exporting the research corpus to a temp directory
2. Running `graphify <corpus_dir>` as a subprocess  
3. Parsing graphify-out/graph.json into our KnowledgeGraph Pydantic model
4. Copying graph.html to the run output directory

Architecture note:
- All I/O is async (asyncio.create_subprocess_exec, aiofiles)
- Graphify never touches raw source files — only markdown/text corpus
- If graphify is not installed, falls back to a lightweight LLM-based graph
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import sys
import tempfile
from pathlib import Path

import aiofiles

from research_engine.models import (
    KGCommunity,
    KGEdge,
    KGNode,
    KnowledgeGraph,
    ResearchResult,
    SurpriseEdge,
)

logger = logging.getLogger(__name__)

# Max god nodes to surface (highest-degree nodes)
GOD_NODE_TOP_N = 10
# Max surprise edges to surface
SURPRISE_EDGE_TOP_N = 10


async def build_knowledge_graph(
    result: ResearchResult,
    run_dir: Path,
    graphify_mode: str = "deep",
) -> KnowledgeGraph:
    """Build a knowledge graph from a completed research result.

    Exports the research corpus to a temp directory, runs graphify,
    then parses the output into a KnowledgeGraph model.

    Args:
        result: The completed research result.
        run_dir: The run output directory (e.g. outputs/{run_id}/).
        graphify_mode: 'fast' (AST only) or 'deep' (AST + LLM-inferred).

    Returns:
        KnowledgeGraph with nodes, edges, communities, god nodes, surprises.
    """
    logger.info(f"Building knowledge graph for run: {result.run_id}")

    # Check if graphify is available
    if not _graphify_available():
        logger.warning("graphify CLI not found — falling back to lightweight graph builder")
        return await _build_lightweight_graph(result, run_dir)

    with tempfile.TemporaryDirectory(prefix="dra_graphify_") as tmp_str:
        corpus_dir = Path(tmp_str) / "corpus"
        await _export_corpus(result, corpus_dir)

        graphify_out = Path(tmp_str) / "graphify-out"
        success = await _run_graphify(corpus_dir, graphify_out, mode=graphify_mode)

        if not success:
            logger.warning("graphify subprocess failed — falling back to lightweight graph")
            return await _build_lightweight_graph(result, run_dir)

        kg = await _parse_graphify_output(graphify_out, result.run_id)

        # Copy graph.html to the permanent run dir for serving
        html_src = graphify_out / "graph.html"
        if html_src.exists():
            html_dst = run_dir / "graph.html"
            shutil.copy2(html_src, html_dst)
            kg.graph_html_available = True
            logger.info(f"Copied graph.html → {html_dst}")

        # Copy GRAPH_REPORT.md
        report_src = graphify_out / "GRAPH_REPORT.md"
        if report_src.exists():
            shutil.copy2(report_src, run_dir / "GRAPH_REPORT.md")

    logger.info(
        f"Knowledge graph built: {len(kg.nodes)} nodes, "
        f"{len(kg.edges)} edges, {len(kg.communities)} communities"
    )
    return kg


# ─── Private Helpers ────────────────────────────────────────────────────────


async def _export_corpus(result: ResearchResult, corpus_dir: Path) -> None:
    """Export research output into a structured corpus directory for Graphify."""
    corpus_dir.mkdir(parents=True, exist_ok=True)

    # findings/ — one file per research cycle answer
    findings_dir = corpus_dir / "findings"
    findings_dir.mkdir(exist_ok=True)
    for i, step in enumerate(result.steps):
        step_path = findings_dir / f"cycle_{i+1:02d}_{_slugify(step.query.query)[:40]}.md"
        content = f"# Cycle {i+1}: {step.query.query}\n\n"
        content += f"**Rationale**: {step.query.rationale}\n\n"
        content += f"## Answer\n\n{step.answer.answer}\n"
        if step.answer.citations:
            content += "\n## Sources\n"
            for c in step.answer.citations:
                content += f"- [{c.title or c.url}]({c.url})\n"
        async with aiofiles.open(step_path, "w", encoding="utf-8") as f:
            await f.write(content)

    # sources/ — scraped page content (non-empty, successful pages only)
    sources_dir = corpus_dir / "sources"
    sources_dir.mkdir(exist_ok=True)
    seen_urls: set[str] = set()
    for step in result.steps:
        for page in step.scraped_pages:
            if not page.success or not page.content or page.url in seen_urls:
                continue
            seen_urls.add(page.url)
            safe_name = _slugify(page.url)[:60]
            page_path = sources_dir / f"{safe_name}.md"
            content = f"# {page.title or page.url}\n\nURL: {page.url}\n\n{page.content[:8000]}"
            async with aiofiles.open(page_path, "w", encoding="utf-8") as f:
                await f.write(content)

    # meta/ — research plan, queries, final report
    meta_dir = corpus_dir / "meta"
    meta_dir.mkdir(exist_ok=True)

    plan_content = f"# Research Plan: {result.query}\n\n"
    plan_content += "\n".join(f"- {step}" for step in result.plan.steps)
    async with aiofiles.open(meta_dir / "plan.md", "w", encoding="utf-8") as f:
        await f.write(plan_content)

    queries = "\n".join(
        f"- Cycle {s.cycle + 1}: {s.query.query}"
        for s in result.steps
    )
    async with aiofiles.open(meta_dir / "queries.md", "w", encoding="utf-8") as f:
        await f.write(f"# Research Queries\n\n{queries}")

    async with aiofiles.open(meta_dir / "final_report.md", "w", encoding="utf-8") as f:
        await f.write(result.report)

    # citations index
    if result.citations:
        cit_lines = "\n".join(
            f"- [{c.title or c.url}]({c.url}): {c.snippet[:100]}"
            for c in result.citations
        )
        async with aiofiles.open(meta_dir / "citations.md", "w", encoding="utf-8") as f:
            await f.write(f"# Citations\n\n{cit_lines}")

    logger.info(
        f"Corpus exported: {len(result.steps)} cycles, "
        f"{len(seen_urls)} unique sources → {corpus_dir}"
    )


async def _run_graphify(
    corpus_dir: Path,
    output_dir: Path,
    mode: str = "deep",
) -> bool:
    """Run the graphify CLI as an async subprocess.

    Returns True if successful, False on failure.
    """
    args = [
        sys.executable, "-m", "graphify",
        str(corpus_dir),
        "--output", str(output_dir),
    ]
    if mode == "deep":
        args += ["--mode", "deep"]

    logger.info(f"Running: {' '.join(args)}")

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        if proc.returncode != 0:
            logger.error(
                f"graphify failed (exit {proc.returncode}):\n"
                f"stdout: {stdout.decode()[:500]}\n"
                f"stderr: {stderr.decode()[:500]}"
            )
            return False

        logger.debug(f"graphify stdout: {stdout.decode()[:200]}")
        return True

    except asyncio.TimeoutError:
        logger.error("graphify timed out (>5 min)")
        if "proc" in locals():
            proc.kill()
        return False
    except Exception as e:
        logger.error(f"graphify subprocess error: {e}")
        return False


async def _parse_graphify_output(output_dir: Path, run_id: str) -> KnowledgeGraph:
    """Parse graphify-out/graph.json into our KnowledgeGraph model."""
    graph_json_path = output_dir / "graph.json"

    if not graph_json_path.exists():
        logger.warning(f"graph.json not found in {output_dir}")
        return KnowledgeGraph(run_id=run_id)

    async with aiofiles.open(graph_json_path, encoding="utf-8") as f:
        raw = await f.read()
    data = json.loads(raw)

    nodes: list[KGNode] = []
    edges: list[KGEdge] = []
    communities: list[KGCommunity] = []
    god_nodes: list[str] = []
    surprise_edges: list[SurpriseEdge] = []

    # Parse nodes — graphify graph.json uses 'nodes' array
    raw_nodes = data.get("nodes", [])
    degree_map: dict[str, int] = {}

    # Count degrees from edges first
    for raw_edge in data.get("edges", []):
        src = str(raw_edge.get("source", raw_edge.get("u", "")))
        tgt = str(raw_edge.get("target", raw_edge.get("v", "")))
        degree_map[src] = degree_map.get(src, 0) + 1
        degree_map[tgt] = degree_map.get(tgt, 0) + 1

    # Find god nodes (top N by degree)
    sorted_by_degree = sorted(degree_map.items(), key=lambda x: x[1], reverse=True)
    god_node_ids = {nid for nid, _ in sorted_by_degree[:GOD_NODE_TOP_N]}

    for raw_node in raw_nodes:
        node_id = str(raw_node.get("id", raw_node.get("n", "")))
        if not node_id:
            continue
        degree = degree_map.get(node_id, 0)
        nodes.append(KGNode(
            id=node_id,
            label=str(raw_node.get("label", raw_node.get("name", node_id))),
            type=str(raw_node.get("type", raw_node.get("kind", "concept"))),
            community=int(raw_node.get("community", raw_node.get("cluster", 0))),
            degree=degree,
            is_god_node=node_id in god_node_ids,
            provenance=str(raw_node.get("provenance", "EXTRACTED")),
            confidence=float(raw_node.get("confidence", 1.0)),
            summary=str(raw_node.get("summary", raw_node.get("description", ""))),
            file_path=str(raw_node.get("file_path", raw_node.get("path", ""))),
        ))

    god_nodes = list(god_node_ids)

    # Parse edges
    for raw_edge in data.get("edges", []):
        src = str(raw_edge.get("source", raw_edge.get("u", "")))
        tgt = str(raw_edge.get("target", raw_edge.get("v", "")))
        if not src or not tgt:
            continue
        edges.append(KGEdge(
            source=src,
            target=tgt,
            type=str(raw_edge.get("type", raw_edge.get("label", "semantically_similar_to"))),
            provenance=str(raw_edge.get("provenance", "EXTRACTED")),
            confidence=float(raw_edge.get("confidence", 1.0)),
            label=str(raw_edge.get("label", "")),
        ))

    # Parse communities
    raw_communities = data.get("communities", data.get("clusters", {}))
    if isinstance(raw_communities, dict):
        for cid_str, cdata in raw_communities.items():
            communities.append(KGCommunity(
                id=int(cid_str),
                label=str(cdata.get("label", cdata.get("name", f"Community {cid_str}"))),
                node_count=int(cdata.get("size", cdata.get("node_count", 0))),
                keywords=list(cdata.get("keywords", [])),
                description=str(cdata.get("description", "")),
            ))
    elif isinstance(raw_communities, list):
        for i, cdata in enumerate(raw_communities):
            communities.append(KGCommunity(
                id=i,
                label=str(cdata.get("label", f"Community {i}")),
                node_count=int(cdata.get("size", cdata.get("node_count", 0))),
                keywords=list(cdata.get("keywords", [])),
            ))

    # Parse surprise edges
    for raw_surprise in data.get("surprises", data.get("surprise_edges", []))[:SURPRISE_EDGE_TOP_N]:
        surprise_edges.append(SurpriseEdge(
            source=str(raw_surprise.get("source", raw_surprise.get("u", ""))),
            target=str(raw_surprise.get("target", raw_surprise.get("v", ""))),
            reason=str(raw_surprise.get("reason", raw_surprise.get("why", ""))),
            score=float(raw_surprise.get("score", 0.0)),
        ))

    # Compute corpus stats and token estimates
    n_nodes = len(nodes)
    n_edges = len(edges)
    # Rough estimate: 300 tokens per raw content block, 1.7k for a BFS query
    naive_cost = len(raw_nodes) * 300
    graph_cost = 1700
    compression = round(naive_cost / graph_cost, 1) if graph_cost > 0 else 0.0

    return KnowledgeGraph(
        run_id=run_id,
        nodes=nodes,
        edges=edges,
        communities=communities,
        god_nodes=god_nodes,
        surprise_edges=surprise_edges,
        graphify_version=str(data.get("graphify_version", data.get("version", ""))),
        corpus_stats={
            "total_nodes": n_nodes,
            "total_edges": n_edges,
            "total_communities": len(communities),
        },
        naive_token_cost=naive_cost,
        graph_token_cost=graph_cost,
        compression_ratio=compression,
    )


async def _build_lightweight_graph(result: ResearchResult, run_dir: Path) -> KnowledgeGraph:
    """Fallback: Build a minimal knowledge graph from our own models without graphify.

    Used when graphifyy is not installed. Creates a graph where:
    - Each research step = a node
    - Citations = linked nodes
    - The final report's sections = section nodes
    """
    nodes: list[KGNode] = []
    edges: list[KGEdge] = []

    # Root node
    root_id = "root"
    nodes.append(KGNode(
        id=root_id,
        label=result.query[:80],
        type="concept",
        community=0,
        degree=len(result.steps),
        is_god_node=True,
        summary=f"Research query: {result.query}",
    ))

    # Cycle nodes
    for i, step in enumerate(result.steps):
        node_id = f"cycle_{i}"
        nodes.append(KGNode(
            id=node_id,
            label=step.query.query[:60],
            type="concept",
            community=0,
            degree=1 + len(step.answer.citations),
        ))
        edges.append(KGEdge(source=root_id, target=node_id, type="has_step"))

        # Citation nodes attached to this cycle
        for cit in step.answer.citations[:3]:
            cit_id = f"cit_{cit.id}"
            if not any(n.id == cit_id for n in nodes):
                nodes.append(KGNode(
                    id=cit_id,
                    label=(cit.title or cit.url)[:60],
                    type="paper",
                    community=1,
                    degree=1,
                    file_path=cit.url,
                ))
            edges.append(KGEdge(source=node_id, target=cit_id, type="references"))

    return KnowledgeGraph(
        run_id=result.run_id,
        nodes=nodes,
        edges=edges,
        communities=[
            KGCommunity(id=0, label="Research Steps", node_count=len(result.steps) + 1),
            KGCommunity(id=1, label="Citations", node_count=len(result.citations)),
        ],
        god_nodes=[root_id],
        naive_token_cost=len(result.steps) * 300,
        graph_token_cost=1700,
        compression_ratio=round(len(result.steps) * 300 / 1700, 1),
    )


def _graphify_available() -> bool:
    """Check if the graphify CLI is available in the current Python environment."""
    import importlib
    try:
        importlib.import_module("graphify")
        return True
    except ImportError:
        return False


def _slugify(text: str) -> str:
    """Convert text to a safe filename slug."""
    import re
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s-]+", "_", text).strip("_")
