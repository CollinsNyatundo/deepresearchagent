"""Pydantic v2 data models — source of truth for all data structures."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ─── Request / Config ────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    """Input to start a new research run."""

    query: str
    model: str | None = None  # Per-request OpenRouter model ID override
    depth: int = 5  # 1=quick, 3=standard, 5=exhaustive
    max_pages: int = 5
    enable_crossover: bool = True
    search_provider: str | None = None  # Per-request override


# ─── Research Planning ───────────────────────────────────────────────

class ResearchPlan(BaseModel):
    """A structured research plan with ordered steps."""

    steps: list[str]


class SearchQuery(BaseModel):
    """A generated search query with rationale."""

    query: str
    rationale: str = ""


class ResearchPlanReflection(BaseModel):
    """Reflection on whether the plan needs updates."""

    should_update: bool
    updates: str = ""


class ResearchProgress(BaseModel):
    """Estimated research completion percentage."""

    progress: int = Field(ge=0, le=100)


# ─── Search & Scraping ───────────────────────────────────────────────

class SearchResult(BaseModel):
    """A single web search result (URL + snippet)."""

    url: str
    title: str = ""
    snippet: str = ""
    score: float = 0.0


class ScrapedPage(BaseModel):
    """Content scraped from a single web page via Scrapling."""

    url: str
    title: str | None = None
    content: str = ""  # Markdown / text content
    status_code: int | None = None
    content_length: int = 0
    success: bool = True
    error: str | None = None
    fetcher_used: str = ""  # "stealthy" | "dynamic" | "basic"


# ─── Citations & Answers ─────────────────────────────────────────────

class Citation(BaseModel):
    """A citation with source metadata."""

    id: str  # e.g. "c1"
    url: str
    title: str = ""
    domain: str = ""
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    snippet: str = ""


class SearchAnswer(BaseModel):
    """Synthesized answer from research with inline citations."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)


# ─── Research Trace ──────────────────────────────────────────────────

class ResearchStep(BaseModel):
    """A single cycle in the research loop."""

    cycle: int
    query: SearchQuery
    search_results: list[SearchResult] = Field(default_factory=list)
    scraped_pages: list[ScrapedPage] = Field(default_factory=list)
    answer: SearchAnswer
    reflection: ResearchPlanReflection | None = None
    plan_updated: bool = False
    progress: int | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResearchResult(BaseModel):
    """Complete output of a research run."""

    run_id: str
    query: str
    model_used: str
    plan: ResearchPlan
    final_plan: ResearchPlan
    steps: list[ResearchStep] = Field(default_factory=list)
    report: str = ""  # Final Markdown report
    citations: list[Citation] = Field(default_factory=list)
    progress: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    errors: list[str] = Field(default_factory=list)


class RunSummary(BaseModel):
    """Lightweight summary of a research run for listing."""

    id: str
    query: str
    created_at: str
    model_used: str = ""


# ─── Mindmap (G6 Graph) ─────────────────────────────────────────────

class MindmapNode(BaseModel):
    """A node in the mindmap graph."""

    id: str
    label: str
    type: str  # "root" | "section" | "detail"
    level: int
    summary: str = ""
    citations: list[str] = Field(default_factory=list)  # Citation IDs


class MindmapEdge(BaseModel):
    """An edge in the mindmap graph."""

    source: str
    target: str
    label: str = "subtopic"


class MindmapGraph(BaseModel):
    """Complete mindmap graph for a research run (G6 compatible)."""

    nodes: list[MindmapNode] = Field(default_factory=list)
    edges: list[MindmapEdge] = Field(default_factory=list)
    run_id: str = ""


class NodeExpansion(BaseModel):
    """Result of expanding / drilling deeper into a node."""

    new_nodes: list[MindmapNode] = Field(default_factory=list)
    new_edges: list[MindmapEdge] = Field(default_factory=list)


class ExpandRequest(BaseModel):
    """Request body for node expansion."""

    node_id: str
    model: str | None = None


# ─── SSE Streaming Events (Phase 2) ─────────────────────────────────

class ResearchState(str, Enum):
    """Explicit state machine for research execution (Protocol-H inspired).

    Each state transition is emitted as an SSE event for real-time frontend updates.
    """

    INITIALIZING = "initializing"
    PLANNING = "planning"
    PLAN_READY = "plan_ready"
    DECOMPOSING = "decomposing"        # Query decomposition into sub-queries
    SEARCHING = "searching"
    SCRAPING = "scraping"
    VALIDATING = "validating"          # Result validation before synthesis
    SYNTHESIZING = "synthesizing"
    REFLECTING = "reflecting"
    RETRYING = "retrying"              # Reflective retry (Protocol-H)
    CYCLE_COMPLETE = "cycle_complete"
    GENERATING_REPORT = "generating_report"
    COMPLETE = "complete"
    ERROR = "error"


class ResearchEvent(BaseModel):
    """A single Server-Sent Event during research streaming.

    Emitted by the orchestrator at each state transition. The frontend
    consumes these via fetch + ReadableStream (POST-based SSE).
    """

    event: str  # ResearchState value or custom event name
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Protocol-H Patterns (Phase 6) ──────────────────────────────────

class ConfidenceScore(BaseModel):
    """LLM self-assessed confidence for an answer (Protocol-H pattern).

    After synthesis, the LLM rates its own answer. Low scores trigger
    additional research or retry with a broader query.
    """

    score: float = Field(ge=0.0, le=1.0, default=0.5)
    reasoning: str = ""
    needs_more_research: bool = False


class RetryCorrection(BaseModel):
    """Autonomous error recovery suggestion (Protocol-H reflective retry).

    When a research step fails, the LLM analyzes the error and suggests
    a corrective action (rephrased query, alternative strategy, etc.).
    """

    corrected_query: str | None = None
    alternative_strategy: str | None = None
    reasoning: str = ""
    should_skip: bool = False


# ─── Intelligence Upgrades (Phase 3) ────────────────────────────────

class QueryDecomposition(BaseModel):
    """Decomposed sub-queries from a complex research topic.

    The planner breaks complex queries into focused sub-queries
    for better search coverage.
    """

    sub_queries: list[str] = Field(default_factory=list, min_length=1, max_length=6)
    reasoning: str = ""


# ─── Interactive Plan Review (Phase 4) ───────────────────────────────

class PlanPreview(BaseModel):
    """Generated research plan for user review before execution.

    The frontend renders this as an editable plan editor. Users can
    add/remove/reorder steps, modify sub-queries, and select export formats.
    """

    plan: ResearchPlan
    sub_queries: list[str] = Field(default_factory=list)
    estimated_cycles: int = 0
    estimated_duration_minutes: float = 0.0
    output_formats: list[str] = Field(
        default_factory=lambda: ["markdown", "pdf", "docx", "xlsx", "mindmap_json"]
    )


class PlanApproval(BaseModel):
    """User-modified plan submitted for execution.

    After reviewing the PlanPreview, users can edit steps, sub-queries,
    and export format preferences before approving execution.
    """

    query: str
    plan: ResearchPlan
    sub_queries: list[str] = Field(default_factory=list)
    model: str | None = None
    depth: int = 5
    max_pages: int = 5
    enable_crossover: bool = True
    search_provider: str | None = None
    export_formats: list[str] = Field(default_factory=lambda: ["markdown", "pdf"])
