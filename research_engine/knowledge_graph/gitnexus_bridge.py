"""GitNexus → Graphify Bridge.

Extracts the codebase architecture from the local GitNexus eval-server
(POST /tool/cypher on http://127.0.0.1:4848) and converts the result into
the standard KnowledgeGraph Pydantic model so the React Graphify frontend
can render it unchanged.

Design choices (per user preferences):
- The bridge is REPO-AGNOSTIC: every function accepts ``repo_name`` as a
  required parameter so any repository indexed in GitNexus can be visualised.
- Data is extracted from the GitNexus eval-server REST API (not subprocess).
- The graph JSON is cached per-repo as outputs/gitnexus_graph_{repo}.json.
- Before building the graph, ``npx gitnexus analyze`` should be run to keep
  the index fresh (orchestrated by the scheduler / API endpoint).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

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

GRAPH_OUTPUT_DIR = Path("outputs")


def graph_output_path(repo_name: str) -> Path:
    """Return the per-repo cache path: outputs/gitnexus_graph_{repo}.json"""
    safe = re.sub(r"[^\w\-]", "_", repo_name)
    return GRAPH_OUTPUT_DIR / f"gitnexus_graph_{safe}.json"


# ─── Cypher queries (no repo baked in — repo is sent as a payload field) ─────

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

    GitNexus eval-server returns:
        | col1 | col2 | ...
        | ---  | ---  | ...
        | val1 | val2 | ...

    Returns an empty list when there are no data rows.
    """
    rows: list[dict[str, str]] = []
    lines = [ln for ln in markdown.strip().splitlines() if ln.strip().startswith("|")]

    if len(lines) < 3:  # header + separator + at least one data row
        return rows

    headers = [h.strip() for h in lines[0].strip("|").split("|")]

    for line in lines[2:]:  # skip separator row
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))

    return rows


# ─── Eval-server Helpers ──────────────────────────────────────────────────────

async def is_eval_server_running() -> bool:
    """Return True if the GitNexus eval-server is reachable."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(EVAL_SERVER_HEALTH, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                return resp.status == 200
    except Exception:
        return False


async def list_indexed_repos() -> list[str]:
    """Return the list of repo names currently loaded in the eval-server.

    Parses the /health endpoint which returns JSON like:
        {"status": "ok", "repos": ["RepoA", "RepoB"]}
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(EVAL_SERVER_HEALTH, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    return []
                raw = await resp.text(encoding="utf-8")
                # The eval-server may return PowerShell-style text or JSON
                json_part = raw.split("\n---")[0].strip()
                data = json.loads(json_part)
                repos = data.get("repos", [])
                # repos may be a list or a set-like object serialized as array
                if isinstance(repos, list):
                    return [r for r in repos if r]
                return []
    except Exception as exc:
        logger.warning("list_indexed_repos failed: %s", exc)
        return []


async def _cypher(
    session: aiohttp.ClientSession,
    repo_name: str,
    query: str,
) -> list[dict[str, str]]:
    """Run a Cypher query for *repo_name* and return parsed rows."""
    payload = {"repo": repo_name, "query": query.strip()}
    async with session.post(
        EVAL_SERVER_CYPHER,
        json=payload,
        timeout=aiohttp.ClientTimeout(total=60),
    ) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise RuntimeError(f"Eval-server cypher error {resp.status}: {text}")
        # The eval-server appends "---\nNext: ..." after the JSON body.
        raw = await resp.text(encoding="utf-8")

    json_part = raw.split("\n---")[0].strip()
    data = json.loads(json_part)
    return _parse_markdown_table(data.get("markdown", ""))


# ─── Core Bridge ─────────────────────────────────────────────────────────────

async def build_gitnexus_graph(repo_name: str) -> KnowledgeGraph:
    """Extract codebase topology for *repo_name* from GitNexus.

    Args:
        repo_name: The exact name of the repository as indexed in GitNexus
                   (e.g. "DeepResearchAgent", "ComplianceGaurd").  Use
                   ``list_indexed_repos()`` to discover available names.

    Returns:
        A ``KnowledgeGraph`` ready for the Graphify frontend.

    Raises:
        RuntimeError: if the eval-server is not reachable.
        ValueError: if *repo_name* is empty.
    """
    if not repo_name:
        raise ValueError("repo_name must not be empty")

    if not await is_eval_server_running():
        raise RuntimeError(
            "GitNexus eval-server is not running. "
            "Start it with: npx gitnexus eval-server --port 4848"
        )

    logger.info("Building GitNexus graph for repo: %s", repo_name)

    async with aiohttp.ClientSession() as session:
        node_rows, edge_rows, community_rows = await asyncio.gather(
            _cypher(session, repo_name, NODE_QUERY),
            _cypher(session, repo_name, EDGE_QUERY),
            _cypher(session, repo_name, COMMUNITY_QUERY),
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

        node_id = raw_id
        node_type = _map_node_type(label)

        nodes[node_id] = KGNode(
            id=node_id,
            label=name,
            node_type=node_type,
            file_path=file_path,
            provenance="EXTRACTED",
            confidence=1.0,
        )

    # ── Build KGEdges + compute degree ───────────────────────────────────────
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

    # Annotate degree and god-node status (top-10 by total connections)
    sorted_by_degree = sorted(degree.items(), key=lambda x: x[1], reverse=True)
    god_node_ids = {nid for nid, _ in sorted_by_degree[:10]}

    for nid, node in nodes.items():
        node.degree = degree.get(nid, 0)
        node.is_god_node = nid in god_node_ids

    # ── Build Communities ────────────────────────────────────────────────────
    communities: list[KGCommunity] = []
    for idx, row in enumerate(community_rows):
        lbl = row.get("label", f"Cluster {idx}").strip()
        count_str = row.get("symbolCount", "0").strip()
        keywords_raw = row.get("keywords", "").strip()
        description = row.get("description", "").strip()

        keywords: list[str] = []
        if keywords_raw:
            try:
                keywords = json.loads(keywords_raw)
            except (json.JSONDecodeError, TypeError):
                keywords = [k.strip() for k in re.split(r"[,;]", keywords_raw) if k.strip()]

        communities.append(KGCommunity(
            id=idx,
            label=lbl,
            node_count=int(count_str) if count_str.isdigit() else 0,
            keywords=keywords,
            description=description,
        ))

    # Assign community membership by partitioning nodes into equal-ish groups
    # (GitNexus community membership is in the graph but not trivially
    #  queryable by Cypher without MEMBER_OF edges — assign index-based buckets
    #  so the frontend colour-codes them correctly)
    if communities:
        per_community = max(1, len(nodes) // len(communities))
        for i, node in enumerate(nodes.values()):
            node.community = i // per_community

    # ── Surprise Edges ───────────────────────────────────────────────────────
    surprise_edges = _detect_surprise_edges(edges, nodes)

    kg = KnowledgeGraph(
        run_id=f"gitnexus:{repo_name}",
        nodes=list(nodes.values()),
        edges=edges,
        communities=communities,
        god_nodes=list(god_node_ids),
        surprise_edges=surprise_edges,
        built_at=datetime.now(timezone.utc),
        graphify_version=f"gitnexus-bridge-1.1/{repo_name}",
    )

    logger.info(
        "GitNexus graph built for '%s': %d nodes, %d edges, %d communities",
        repo_name, len(kg.nodes), len(kg.edges), len(kg.communities),
    )
    return kg


async def build_and_save(repo_name: str) -> Path:
    """Build the GitNexus graph for *repo_name* and persist it to disk.

    Returns the path where the JSON was written.
    """
    kg = await build_gitnexus_graph(repo_name)
    out_path = graph_output_path(repo_name)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(kg.model_dump_json(indent=2), encoding="utf-8")
    logger.info("GitNexus graph saved → %s", out_path)
    return out_path


def load_cached_graph(repo_name: str) -> KnowledgeGraph | None:
    """Load a previously-built graph for *repo_name* from disk.

    Returns None if not cached yet.
    """
    path = graph_output_path(repo_name)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return KnowledgeGraph.model_validate(data)
    except Exception as e:
        logger.warning("Failed to load cached GitNexus graph for '%s': %s", repo_name, e)
        return None


def cache_age_seconds(repo_name: str) -> float | None:
    """Return how many seconds ago the cache was written, or None if absent."""
    path = graph_output_path(repo_name)
    if not path.exists():
        return None
    return (datetime.now(timezone.utc) - datetime.fromtimestamp(
        path.stat().st_mtime, tz=timezone.utc
    )).total_seconds()


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
    """Surface edges that cross top-level directory boundaries (front-end ↔ backend, etc.)."""
    surprises: list[tuple[str, str, float]] = []

    for edge in edges:
        src_node = nodes.get(edge.source)
        tgt_node = nodes.get(edge.target)
        if not src_node or not tgt_node:
            continue
        src_dir = src_node.file_path.split("/")[0] if src_node.file_path else ""
        tgt_dir = tgt_node.file_path.split("/")[0] if tgt_node.file_path else ""
        if src_dir and tgt_dir and src_dir != tgt_dir:
            surprises.append((edge.source, edge.target, 1.0))

    surprises.sort(key=lambda x: x[2], reverse=True)
    return [
        SurpriseEdge(
            source=s,
            target=t,
            reason=(
                f"Cross-boundary dependency: "
                f"{s.split(':')[1] if ':' in s else s} → "
                f"{t.split(':')[1] if ':' in t else t}"
            ),
            score=sc,
        )
        for s, t, sc in surprises[:top_n]
    ]
