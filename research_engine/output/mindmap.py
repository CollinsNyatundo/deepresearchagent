"""Mindmap builder — transforms ResearchResult into G6-compatible mindmap graph.

This is a pure projection layer: it takes the existing ResearchResult
(with its Markdown report and citations) and produces a MindmapGraph
(nodes + edges) that the frontend renders with AntV G6 mindmap layout.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from research_engine.llm.provider import LLMProvider
from research_engine.llm.prompts import MINDMAP_EXPANSION_TEMPLATE
from research_engine.models import (
    Citation,
    MindmapEdge,
    MindmapGraph,
    MindmapNode,
    NodeExpansion,
    ResearchResult,
)

logger = logging.getLogger(__name__)


def build_mindmap_graph(result: ResearchResult) -> MindmapGraph:
    """Convert a ResearchResult into a G6-compatible mindmap graph.

    Structure:
    - Root node = research query
    - Level 1 = main sections from the report (## headings)
    - Level 2 = key points / subsections from the report (### headings or bullets)

    Citations are attached to nodes based on inline citation markers [1], [2], etc.
    """
    nodes: list[MindmapNode] = []
    edges: list[MindmapEdge] = []

    # Root node
    root_summary = _extract_executive_summary(result.report)
    nodes.append(MindmapNode(
        id="root",
        label=_truncate_label(result.query, 60),
        type="root",
        level=0,
        summary=root_summary or f"Research on: {result.query}",
        citations=[],
    ))

    # Parse report into sections → sub-points
    sections = _parse_report_sections(result.report)

    for i, section in enumerate(sections):
        sec_id = f"sec{i}"
        sec_citations = _find_citation_ids(section["content"], result.citations)

        nodes.append(MindmapNode(
            id=sec_id,
            label=_truncate_label(section["title"], 50),
            type="section",
            level=1,
            summary=_extract_summary(section["content"], max_sentences=3),
            citations=sec_citations,
        ))
        edges.append(MindmapEdge(source="root", target=sec_id))

        # Sub-points from subsections or bullet points
        sub_points = _extract_sub_points(section["content"])
        for j, point in enumerate(sub_points):
            pt_id = f"sec{i}-pt{j}"
            pt_citations = _find_citation_ids(point["text"], result.citations)

            nodes.append(MindmapNode(
                id=pt_id,
                label=_truncate_label(point["title"], 45),
                type="detail",
                level=2,
                summary=point["text"][:300],
                citations=pt_citations,
            ))
            edges.append(MindmapEdge(source=sec_id, target=pt_id, label="detail"))

    logger.info(
        f"Built mindmap: {len(nodes)} nodes, {len(edges)} edges "
        f"for run {result.run_id}"
    )

    return MindmapGraph(
        nodes=nodes,
        edges=edges,
        run_id=result.run_id,
    )


async def expand_node(
    node: MindmapNode,
    research_context: str,
    *,
    llm: LLMProvider,
    model: str | None = None,
) -> NodeExpansion:
    """Drill deeper: generate child nodes for a given mindmap node using LLM.

    Called when a user clicks "Drill deeper" on a node in the frontend.
    """
    prompt = MINDMAP_EXPANSION_TEMPLATE.format(
        node_label=node.label,
        node_summary=node.summary,
        research_context=research_context[:5000],  # Trim to avoid huge prompts
    )

    try:
        raw = await llm.call(prompt, model=model)
        points = _parse_expansion_response(raw)

        new_nodes: list[MindmapNode] = []
        new_edges: list[MindmapEdge] = []

        for k, point in enumerate(points):
            child_id = f"{node.id}-exp{k}"
            new_nodes.append(MindmapNode(
                id=child_id,
                label=_truncate_label(point["label"], 45),
                type="detail",
                level=node.level + 1,
                summary=point.get("summary", ""),
                citations=[],
            ))
            new_edges.append(MindmapEdge(
                source=node.id, target=child_id, label="expanded"
            ))

        logger.info(f"Expanded node '{node.id}': {len(new_nodes)} new nodes")
        return NodeExpansion(new_nodes=new_nodes, new_edges=new_edges)

    except Exception as e:
        logger.error(f"Node expansion failed for '{node.id}': {e}")
        return NodeExpansion()


# ─── Helper Functions ────────────────────────────────────────────────

def _parse_report_sections(report: str) -> list[dict[str, str]]:
    """Parse a Markdown report into sections (## headings)."""
    sections: list[dict[str, str]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in report.split("\n"):
        if line.startswith("## "):
            # Save previous section
            if current_title:
                sections.append({
                    "title": current_title,
                    "content": "\n".join(current_lines).strip(),
                })
            current_title = line.lstrip("# ").strip()
            current_lines = []
        elif current_title:
            current_lines.append(line)

    # Save last section
    if current_title:
        sections.append({
            "title": current_title,
            "content": "\n".join(current_lines).strip(),
        })

    return sections


def _extract_sub_points(content: str) -> list[dict[str, str]]:
    """Extract sub-points from section content (### headings or bullet points)."""
    points: list[dict[str, str]] = []

    # Try ### subsections first
    subsections = re.split(r"\n### ", content)
    if len(subsections) > 1:
        for sub in subsections[1:]:  # Skip pre-heading content
            lines = sub.split("\n", 1)
            title = lines[0].strip()
            text = lines[1].strip() if len(lines) > 1 else ""
            if title:
                points.append({"title": title, "text": text[:500]})
        return points[:6]  # Max 6 sub-points

    # Fallback: extract bullet points
    bullets = re.findall(r"^[\-\*]\s+\*?\*?(.+?)(?:\*?\*?\s*$)", content, re.MULTILINE)
    for bullet in bullets[:6]:
        text = bullet.strip().rstrip("*")
        points.append({"title": text[:80], "text": text})

    return points


def _extract_executive_summary(report: str) -> str:
    """Extract the executive summary section from the report."""
    match = re.search(
        r"(?:##\s*Executive\s*Summary|##\s*Summary|##\s*Overview)\s*\n(.*?)(?=\n##|\Z)",
        report,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        return match.group(1).strip()[:500]
    # Fallback: first paragraph
    paragraphs = [p.strip() for p in report.split("\n\n") if p.strip() and not p.startswith("#")]
    return paragraphs[0][:500] if paragraphs else ""


def _extract_summary(content: str, max_sentences: int = 3) -> str:
    """Extract the first N sentences from content."""
    # Simple sentence splitting
    sentences = re.split(r"(?<=[.!?])\s+", content)
    summary_sentences = [s for s in sentences[:max_sentences] if s.strip()]
    return " ".join(summary_sentences)[:500]


def _find_citation_ids(text: str, citations: list[Citation]) -> list[str]:
    """Find citation IDs referenced in a text block via [1], [2], etc."""
    # Match [N] patterns
    matches = re.findall(r"\[(\d+)\]", text)
    found_ids: list[str] = []
    for num in matches:
        cid = f"c{num}"
        if any(c.id == cid for c in citations):
            found_ids.append(cid)
    return list(set(found_ids))


def _truncate_label(text: str, max_len: int = 50) -> str:
    """Truncate a label to max length with ellipsis."""
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len - 1] + "…"


def _parse_expansion_response(raw: str) -> list[dict[str, str]]:
    """Parse the LLM's expansion response into sub-points."""
    import json

    try:
        # Try JSON parsing first
        cleaned = raw.strip()
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1)

        data = json.loads(cleaned)
        if isinstance(data, dict) and "points" in data:
            return data["points"]
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, KeyError):
        pass

    # Fallback: extract bullet points
    bullets = re.findall(r"[\-\*]\s+\*?\*?(.+?)(?:\*?\*?\s*$)", raw, re.MULTILINE)
    return [{"label": b.strip()[:80], "summary": b.strip()} for b in bullets[:5]]
