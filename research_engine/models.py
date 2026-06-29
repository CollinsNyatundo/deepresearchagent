# ==========================================
# MANDATORY INTEGRITY WARNING
# DO NOT CHEAT. All implementations must be genuine.
# - DO NOT hardcode test results, expected outputs, or verification strings.
# - DO NOT create dummy or facade implementations.
# - Every implementation must maintain real state and produce real behavior.
# ==========================================

"""Pydantic v2 data models — source of truth for all data structures."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ─── Request / Config ────────────────────────────────────────────────

class ResearchMode(str, Enum):
    """Research mode indicating the target domain."""

    WEB = "web"
    GITHUB = "github"


class ResearchRequest(BaseModel):
    """Input to start a new research run."""

    query: str
    model: str | None = None  # Per-request OpenRouter model ID override
    depth: int = 5  # 1=quick, 3=standard, 5=exhaustive
    max_pages: int = 5
    enable_crossover: bool = True
    search_provider: str | None = None  # Per-request override
    provider: str | None = None  # Per-request LLM provider override (e.g. 'groq' or 'openrouter')
    mode: ResearchMode = ResearchMode.WEB
    workspace_id: str | None = None
    run_id: str | None = None

    # NEW: Format selection (from format taxonomy system)
    format: str = "report"  # "academic", "business", "technical", "product", "literature", "data"
    length: str = "full"    # format-specific length
    audience: str = "general"  # "researcher", "executive", "cto", "pm", etc.
    options: dict[str, Any] = Field(default_factory=dict)  # format-specific options
    export_format: str = "markdown"  # "markdown", "pdf", "docx", "latex"

    # NEW: Skill override (for advanced users)
    skills: list[str] | None = None  # Override auto-resolved skills


# ─── Research Planning ───────────────────────────────────────────────

class ResearchPlan(BaseModel):
    """A structured research plan with ordered steps."""

    steps: list[str]


class SearchQuery(BaseModel):
    """A generated search query with rationale."""

    query: str
    rationale: str = ""


class SearchQueryBatch(BaseModel):
    """A batch of search queries with rationale."""

    queries: list[SearchQuery]



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
    relevance_score: float = 1.0
    eval_rationale: str = ""
    provider: str = ""


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
    original_status: int | None = None
    fallback_attempts: list[str] = Field(default_factory=list)


# ─── Citations & Answers ─────────────────────────────────────────────

class Citation(BaseModel):
    """A citation with source metadata."""

    id: str  # e.g. "c1"
    url: str
    title: str = ""
    domain: str = ""
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
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
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    needs_more_research: bool = False
    confidence_score: float | None = None


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
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    errors: list[str] = Field(default_factory=list)
    workspace_id: str | None = None
    status: str | None = None


class RunSummary(BaseModel):
    """Lightweight summary of a research run for listing."""

    id: str
    query: str
    created_at: str
    model_used: str = ""
    status: str = "initializing"
    progress: int = 0
    workspace_id: str | None = None
    # NEW: Format taxonomy fields
    format: str | None = None
    length: str | None = None
    audience: str | None = None
    export_format: str | None = None
    skills_used: list[str] = []
    options: dict[str, Any] = Field(default_factory=dict)


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


# ─── Knowledge Graph (Graphify Integration) ──────────────────────────

class KGNode(BaseModel):
    """A node in the Graphify knowledge graph."""

    id: str
    label: str
    type: str = "concept"               # function | class | concept | paper | diagram
    community: int = 0                  # Leiden community ID
    degree: int = 0                     # Number of edges (higher = more connected)
    is_god_node: bool = False           # Top-N highest-degree nodes
    provenance: str = "EXTRACTED"       # EXTRACTED | INFERRED | AMBIGUOUS
    confidence: float = 1.0            # 0–1 confidence (relevant for INFERRED)
    summary: str = ""
    file_path: str = ""                 # Source file (for code nodes)


class KGEdge(BaseModel):
    """An edge in the Graphify knowledge graph."""

    source: str
    target: str
    type: str = "semantically_similar_to"  # calls | imports | rationale_for | semantically_similar_to
    provenance: str = "EXTRACTED"
    confidence: float = 1.0
    label: str = ""


class KGCommunity(BaseModel):
    """A Leiden community cluster of related nodes."""

    id: int
    label: str
    node_count: int
    keywords: list[str] = Field(default_factory=list)
    description: str = ""


class SurpriseEdge(BaseModel):
    """An unexpected cross-domain connection flagged by Graphify."""

    source: str
    target: str
    reason: str                         # Plain-English explanation
    score: float = 0.0                  # Surprise score (higher = more unexpected)


class KnowledgeGraph(BaseModel):
    """Complete knowledge graph produced by Graphify for a research run."""

    run_id: str
    nodes: list[KGNode] = Field(default_factory=list)
    edges: list[KGEdge] = Field(default_factory=list)
    communities: list[KGCommunity] = Field(default_factory=list)
    god_nodes: list[str] = Field(default_factory=list)     # Node IDs of highest-degree nodes
    surprise_edges: list[SurpriseEdge] = Field(default_factory=list)
    built_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    graphify_version: str = ""
    graph_html_available: bool = False
    corpus_stats: dict[str, Any] = Field(default_factory=dict)
    # Token compression stats
    naive_token_cost: int = 0           # Tokens to read all raw content
    graph_token_cost: int = 0          # Tokens for a typical BFS query
    compression_ratio: float = 0.0


class KGQueryRequest(BaseModel):
    """Request to query the knowledge graph via Graphify MCP bridge."""

    question: str
    mode: str = "bfs"                   # bfs | dfs
    budget: int = 2000                  # Token budget for response


class SimilarityRequest(BaseModel):
    """Request body for similarity search in knowledge graph."""

    query_embedding: list[float] = Field(..., min_length=1)
    match_threshold: float = 0.0
    match_count: int = 5


class KGQueryResult(BaseModel):
    """Result of a knowledge graph query."""

    answer: str
    nodes_traversed: list[str] = Field(default_factory=list)
    token_cost: int = 0
    query_mode: str = "bfs"


# ─── SSE Streaming Events (Phase 2) ─────────────────────────────────

class ResearchState(str, Enum):
    """Explicit state machine for research execution (Protocol-H inspired).

    Each state transition is emitted as an SSE event for real-time frontend updates.
    """

    INITIALIZING = "initializing"
    CLASSIFYING_INTENT = "classifying_intent"
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
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


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
    run_id: str | None = None


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
    provider: str | None = None
    mode: ResearchMode = ResearchMode.WEB
    export_formats: list[str] = Field(default_factory=lambda: ["markdown", "pdf"])
    workspace_id: str | None = None
    run_id: str | None = None
    # NEW: Format taxonomy fields
    format: str = "report"
    length: str = "full"
    audience: str = "general"
    options: dict[str, Any] = Field(default_factory=dict)
    export_format: str = "markdown"
    skills: list[str] | None = None


class OpenFileRequest(BaseModel):
    """Request payload to open a file in the local editor."""

    path: str


# ─── Phase 1 Architectural Models ───────────────────────────────────

class QueryIntentCategory(str, Enum):
    """Classified intent category for the research query."""

    ACADEMIC = "academic"
    NEWS = "news"
    TECHNICAL = "technical"
    GENERAL = "general"


class QueryIntent(BaseModel):
    """Intent analysis of a user query."""

    category: QueryIntentCategory
    rationale: str
    target_domains: list[str] = Field(default_factory=list)
    avoid_domains: list[str] = Field(default_factory=list)
    steps_override: list[str] | None = None
    sub_queries: list[str] | None = None


class RelevanceEvaluation(BaseModel):
    """Snippet relevance score generated by pointwise LLM evaluation."""

    score: float = Field(ge=0.0, le=1.0)
    rationale: str


class BatchRelevanceItem(BaseModel):
    """Relevance evaluation item within a batch query."""

    index: int
    score: float = Field(ge=0.0, le=1.0)
    rationale: str


class BatchRelevanceEvaluation(BaseModel):
    """Multiple snippet evaluations returned in a single batch LLM call."""

    evaluations: list[BatchRelevanceItem] = Field(default_factory=list)


class TelemetryResponse(BaseModel):
    """Local cache and circuit breaker statistics."""

    total_cached_queries: int
    total_scraped_pages: int
    active_circuit_breakers: list[str]
    scraper_success_rate: float


class ResynthesizeRequest(BaseModel):
    """Input to run research re-synthesis without full search rerun."""

    disabled_domains: list[str] = Field(default_factory=list)
    model: str | None = None
    provider: str | None = None


# ─── Notes Module Models ──────────────────────────────────────────────────

class NoteSummary(BaseModel):
    """Lightweight note for list views."""

    id: str
    title: str
    workspace_id: str
    created_at: str
    updated_at: str


class Note(BaseModel):
    """Full note with content and derived fields."""

    id: str
    workspace_id: str
    user_id: str
    title: str
    content: str
    tags: list[str] = []
    source: str | None = None
    created_at: str
    updated_at: str
    outgoing_links: list[str] = []
    backlink_count: int = 0


class CreateNoteRequest(BaseModel):
    """Create a new note."""

    workspace_id: str
    title: str
    content: str = ""
    tags: list[str] = []
    source: str | None = None


class UpdateNoteRequest(BaseModel):
    """Partial update of a note."""

    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    source: str | None = None


class BulkDeleteRequest(BaseModel):
    """Delete multiple items by ID."""

    ids: list[str]


class NoteSearchResponse(BaseModel):
    """Search results for notes."""

    notes: list[NoteSummary]
    query: str
    total: int


# ─── Citation Verification ─────────────────────────────────────────

class CitationVerificationRequest(BaseModel):
    """Request to verify a citation."""

    citation_text: str


class CitationVerificationResponse(BaseModel):
    """Response from citation verification."""

    status: str  # verified, unverified, failed
    found: bool
    title: str = ""
    authors: list[str] = []
    year: int | None = None
    doi: str = ""
    url: str = ""
    confidence: float = 0.0
    sources: int = 0


class QualityReport(BaseModel):
    """Quality assessment of a research report."""

    confidence_score: float = 0.0
    citation_verification_rate: float = 0.0
    source_diversity_score: float = 0.0
    completeness_score: float = 0.0
    coherence_score: float = 0.0
    improvement_suggestions: list[str] = []
    overall_score: float = 0.0


class QualityReviewRequest(BaseModel):
    """Request to review a research report."""

    report: str
    sources: list[dict] = []


# ─── Settings Models ──────────────────────────────────────────────────────

class AppSettings(BaseModel):
    """User-configurable application settings persisted server-side.

    All fields are optional — PATCH merges with existing values.
    Fields that map to config.toml are *display-only* read via GET;
    write operations update a workspace-scoped settings table.
    """

    # LLM Defaults
    default_provider: str | None = None       # "openrouter" | "groq"
    default_model: str | None = None           # e.g. "qwen/qwen3-235b-a22b:free"
    default_depth: int | None = Field(None, ge=1, le=5)

    # API Keys (write: stored encrypted, read: masked)
    openrouter_api_key: str | None = None      # stored; returned masked
    groq_api_key: str | None = None            # stored; returned masked

    # Research Defaults
    default_format: str | None = None          # academic|business|technical|product|literature|data
    default_length: str | None = None          # abstract|short|full|thesis
    default_audience: str | None = None        # researcher|developer|executive|general

    # Appearance
    background_mode: str | None = None         # moonlit|silk|rain|solid
    accent_color: str | None = None            # hex color string
    sidebar_expanded: bool | None = None

    # Workspace
    default_workspace_id: str | None = None


class SettingsResponse(BaseModel):
    """Settings GET response — API keys returned masked."""

    workspace_id: str
    default_provider: str
    default_model: str
    default_depth: int
    openrouter_api_key_set: bool
    groq_api_key_set: bool
    default_format: str
    default_length: str
    default_audience: str
    background_mode: str
    accent_color: str
    sidebar_expanded: bool
    default_workspace_id: str | None = None
    updated_at: str | None = None
