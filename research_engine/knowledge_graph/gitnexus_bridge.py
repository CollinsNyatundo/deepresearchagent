"""GitNexus → Graphify Bridge.

Extracts the codebase architecture from the local GitNexus eval-server
(POST /tool/cypher on http://127.0.0.1:4848) and converts the result into
the standard KnowledgeGraph Pydantic model so the React Graphify frontend
can render it unchanged.

Design choices (per user preferences):
- Data is extracted from the GitNexus eval-server REST API (not subprocess
  Markdown parsing — we still parse the markdown table the API returns).
- The graph JSON is generated periodically by a background scheduler
  (see gitnexus_scheduler.py), not on-demand.
- Before building the graph, `npx gitnexus analyze` is triggered to
  ensure the index is fresh (orchestrated by the scheduler / API endpoint).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp

from research_engine.models import (
    KGCommunity,
    KGEdge,
    KGNode,
    KnowledgeGraph,
    SurpriseEdge,
)

logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────

EVAL_SERVER_URL = "http://127.0.0.1:4848"
EVAL_SERVER_HEALTH = f"{EVAL_SERVER_URL}/health"
EVAL_SERVER_CYPHER = f"{EVAL_SERVER_URL}/tool/cypher"

REPO_NAME = "DeepResearchAgent"

# Where we persist the built graph JSON so the API can serve it
GRAPH_OUTPUT_PATH = Path("outputs/gitnexus_graph.json")

# Cypher queries
NODE_QUERY = """
MATCH (n)
WHERE n.name IS NOT NULL
RETURN
  labels(n) AS label,
  n.name     AS name,
  n.filePath AS filePath,
  n.id       AS id
LIMIT 5000
"""

EDGE_QUERY = """
MATCH (a)-[r:CodeRelation]->(b)
WHERE a.id IS NOT NULL AND b.id IS NOT NULL
RETURN
  a.id   AS source_id,
  r.type AS rel_type,
  b.id   AS target_id
LIMIT 10000
"""

COMMUNITY_QUERY = """
MATCH (c:Community)
RETURN
  c.heuristicLabel AS label,
  c.symbolCount    AS symbolCount,
  c.keywords       AS keywords,
  c.description    AS description
LIMIT 500
"""


# ─── Markdown Table Parser ────────────────────────────────────────────────────

def _parse_markdown_table(markdown: str) -> list[dict[str, str]]:
    """Parse a pipe-delimited markdown table into a list of dicts.

    GitNexus eval-server always returns:
        | col1 | col2 | ...
        | ---  | ---  | ...
        | val1 | val2 | ...

    Returns an empty list when there are no data rows.
    """
    rows: list[dict[str, str]] = []
    lines = [ln for ln in markdown.strip().splitlines() if ln.strip().startswith("|")]

    if len(lines) < 3:  # header + separator + at least one data row
        return rows

    # Parse header columns
    header_line = lines[0]
    headers = [h.strip() for h in header_line.strip("|").split("|")]

    # lines[1] is the separator row (| --- | --- | …) — skip it
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))

    return rows


# ─── Eval-server Client ───────────────────────────────────────────────────────

async def _cypher(session: aiohttp.ClientSession, query: str) -> list[dict[str, str]]:
    """Run a Cypher query via the GitNexus eval-server and return parsed rows."""
    payload = {"repo": REPO_NAME, "query": query.strip()}
    async with session.post(EVAL_SERVER_CYPHER, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise RuntimeError(f"Eval-server cypher error {resp.status}: {text}")
        # The eval-server appends "---\nNext: ..." after the JSON body.
        # We extract only the JSON object portion.
        raw = await resp.text(encoding="utf-8")

    # Strip trailing hint section: everything from '---' onwards
    json_part = raw.split("\n---")[0].strip()
    data = json.loads(json_part)

    markdown = data.get("markdown", "")
    return _parse_markdown_table(markdown)


async def is_eval_server_running() -> bool:
    """Return True if the GitNexus eval-server is reachable."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(EVAL_SERVER_HEALTH, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                return resp.status == 200
    except Exception:
        return False


# ─── Core Bridge ─────────────────────────────────────────────────────────────

async def build_gitnexus_graph() -> KnowledgeGraph:
    """Extract codebase topology from GitNexus and return a KnowledgeGraph.

    Steps:
    1. Query all node types (File, Function, Class, Method, Interface …)
    2. Query all CALLS / IMPORTS / EXTENDS / IMPLEMENTS edges
    3. Query community clusters
    4. Map everything into the KnowledgeGraph Pydantic model

    Raises:
        RuntimeError: if the eval-server is not reachable.
    """
    if not await is_eval_server_running():
        raise RuntimeError(
            "GitNexus eval-server is not running. "
            "Start it with: npx gitnexus eval-server --port 4848"
        )

    async with aiohttp.ClientSession() as session:
        node_rows, edge_rows, community_rows = await asyncio.gather(
            _cypher(session, NODE_QUERY),
            _cypher(session, EDGE_QUERY),
            _cypher(session, COMMUNITY_QUERY),
        )

    # ── Build KGNodes ────────────────────────────────────────────────────────
    nodes: dict[str, KGNode] = {}
    for row in node_rows:
        raw_id = row.get("id", "").strip()
        name = row.get("name", "").strip()
        label = row.get("label", "").strip()
        file_path = row.get("filePath", "").strip()

        if not raw_id or not name:
            continue

        node_id = raw_id or f"{label}:{name}"
        node_type = _map_node_type(label)

        nodes[node_id] = KGNode(
            id=node_id,
            label=name,
            node_type=node_type,
            file_path=file_path,
            provenance="EXTRACTED",
            confidence=1.0,
        )

    # ── Build KGEdges ────────────────────────────────────────────────────────
    edges: list[KGEdge] = []
    degree: dict[str, int] = {}

    for row in edge_rows:
        src = row.get("source_id", "").strip()
        tgt = row.get("target_id", "").strip()
        rel = row.get("rel_type", "CALLS").strip()

        if not src or not tgt:
            continue

        edge_type = _map_edge_type(rel)
        edges.append(KGEdge(
            source=src,
            target=tgt,
            type=edge_type,
            label=rel,
            provenance="EXTRACTED",
            confidence=1.0,
        ))

        degree[src] = degree.get(src, 0) + 1
        degree[tgt] = degree.get(tgt, 0) + 1

    # Annotate degree and god-node status
    top_n = 10
    sorted_by_degree = sorted(degree.items(), key=lambda x: x[1], reverse=True)
    god_node_ids = {nid for nid, _ in sorted_by_degree[:top_n]}

    for nid, node in nodes.items():
        node.degree = degree.get(nid, 0)
        node.is_god_node = nid in god_node_ids

    # ── Build Communities ────────────────────────────────────────────────────
    communities: list[KGCommunity] = []
    for idx, row in enumerate(community_rows):
        label = row.get("label", f"Cluster {idx}").strip()
        count_str = row.get("symbolCount", "0").strip()
        keywords_raw = row.get("keywords", "").strip()
        description = row.get("description", "").strip()

        # keywords may be a JSON array string like '["auth","user"]'
        keywords: list[str] = []
        if keywords_raw:
            try:
                keywords = json.loads(keywords_raw)
            except (json.JSONDecodeError, TypeError):
                keywords = [k.strip() for k in re.split(r"[,;]", keywords_raw) if k.strip()]

        communities.append(KGCommunity(
            id=idx,
            label=label,
            node_count=int(count_str) if count_str.isdigit() else 0,
            keywords=keywords,
            description=description,
        ))

    # ── Surprise Edges (cross-cluster connections) ───────────────────────────
    surprise_edges = _detect_surprise_edges(edges, nodes)

    kg = KnowledgeGraph(
        run_id="gitnexus",
        nodes=list(nodes.values()),
        edges=edges,
        communities=communities,
        god_nodes=list(god_node_ids),
        surprise_edges=surprise_edges,
        built_at=datetime.now(timezone.utc),
        graphify_version="gitnexus-bridge-1.0",
    )

    logger.info(
        "GitNexus graph built: %d nodes, %d edges, %d communities",
        len(kg.nodes), len(kg.edges), len(kg.communities),
    )
    return kg


async def build_and_save() -> Path:
    """Build the GitNexus graph and persist it to disk.

    Returns the path where the JSON was written.
    """
    kg = await build_gitnexus_graph()
    GRAPH_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    GRAPH_OUTPUT_PATH.write_text(
        kg.model_dump_json(indent=2),
        encoding="utf-8",
    )
    logger.info("GitNexus graph saved → %s", GRAPH_OUTPUT_PATH)
    return GRAPH_OUTPUT_PATH


def load_cached_graph() -> KnowledgeGraph | None:
    """Load the previously built graph from disk, or None if not available."""
    if not GRAPH_OUTPUT_PATH.exists():
        return None
    try:
        data = json.loads(GRAPH_OUTPUT_PATH.read_text(encoding="utf-8"))
        return KnowledgeGraph.model_validate(data)
    except Exception as e:
        logger.warning("Failed to load cached GitNexus graph: %s", e)
        return None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _map_node_type(label: str) -> str:
    """Map a GitNexus label to a Graphify node type."""
    mapping = {
        "File": "concept",
        "Function": "finding",
        "Class": "concept",
        "Method": "finding",
        "Interface": "concept",
        "Module": "concept",
        "Community": "concept",
        "Process": "concept",
        "Route": "finding",
        "Tool": "finding",
    }
    return mapping.get(label, "concept")


def _map_edge_type(rel: str) -> str:
    """Map a GitNexus relation type to a Graphify edge type."""
    mapping = {
        "CALLS": "calls",
        "IMPORTS": "imports",
        "EXTENDS": "extends",
        "IMPLEMENTS": "implements",
        "DEFINES": "defines",
        "CONTAINS": "contains",
        "HAS_METHOD": "has_method",
        "HAS_PROPERTY": "has_property",
        "MEMBER_OF": "member_of",
        "STEP_IN_PROCESS": "step_in_process",
        "HANDLES_ROUTE": "handles_route",
        "FETCHES": "fetches",
        "OVERRIDES": "overrides",
    }
    return mapping.get(rel, "semantically_similar_to")


def _detect_surprise_edges(
    edges: list[KGEdge],
    nodes: dict[str, KGNode],
    top_n: int = 10,
) -> list[SurpriseEdge]:
    """Flag edges that cross expected domain boundaries.

    Heuristic: edges connecting nodes from very different file paths
    (e.g., frontend/ ↔ research_engine/) are surfaced as surprises.
    """
    surprises: list[tuple[str, str, float]] = []

    for edge in edges:
        src_node = nodes.get(edge.source)
        tgt_node = nodes.get(edge.target)
        if not src_node or not tgt_node:
            continue
        src_dir = src_node.file_path.split("/")[0] if src_node.file_path else ""
        tgt_dir = tgt_node.file_path.split("/")[0] if tgt_node.file_path else ""
        if src_dir and tgt_dir and src_dir != tgt_dir:
            score = 1.0  # all cross-boundary edges get equal score
            surprises.append((edge.source, edge.target, score))

    surprises.sort(key=lambda x: x[2], reverse=True)
    return [
        SurpriseEdge(
            source=s,
            target=t,
            reason=f"Cross-boundary dependency: {s.split(':')[1] if ':' in s else s} → {t.split(':')[1] if ':' in t else t}",
            score=sc,
        )
        for s, t, sc in surprises[:top_n]
    ]
