# DeepResearchAgent — System Architecture

> **Last Updated:** 2026-06-27
> **Version:** Production
> **Scope:** Full system — backend, frontend, database, and infrastructure

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Module Breakdown](#3-module-breakdown)
4. [Data Flow](#4-data-flow)
5. [Database Architecture](#5-database-architecture)
6. [API Reference Summary](#6-api-reference-summary)
7. [Authentication & Authorization](#7-authentication--authorization)
8. [LLM Gateway Design](#8-llm-gateway-design)
9. [Scraping Layer](#9-scraping-layer)
10. [Streaming Architecture (SSE)](#10-streaming-architecture-sse)
11. [Knowledge Graph Subsystem](#11-knowledge-graph-subsystem)
12. [Research Formats Subsystem](#12-research-formats-subsystem)
13. [Skills Loader & Execution Engine](#13-skills-loader--execution-engine)
14. [Database Operations Layer (SupabaseOps)](#14-database-operations-layer-supabaseops)
15. [Frontend Architecture](#15-frontend-architecture)
16. [Configuration Reference](#16-configuration-reference)
17. [Deployment](#17-deployment)
18. [Key Design Decisions](#18-key-design-decisions)

---

## 1. System Overview

**DeepResearchAgent (DRA)** is a multi-module AI-powered research platform that performs deep, iterative web research with LLM synthesis, maintains a personal knowledge base with wiki-style linking, and provides document Q&A via an embedded OpenKB knowledge base.

### Core Modules

| Module | Purpose | Key UI Features |
|--------|---------|-----------------|
| **Research** | Iterative deep-web research with LLM synthesis | Plan review, SSE streaming, mindmap (G6 v5), citations, export, knowledge graph |
| **Notes** | Personal wiki with backlinks and graph | `[[wiki-link]]` syntax, D3 force-directed graph, auto-save (400ms), moon phase widget |
| **Documents** | OpenKB document ingestion & Q&A | Upload, full-text search, multi-turn chat, wiki browser, skill factory |

### Technology Stack Summary

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 · FastAPI · Pydantic v2 · Supabase (PostgreSQL + JWT) |
| Frontend | React 19 · TypeScript 5.9 · Vite 8 · Tailwind CSS v3 · Radix UI · D3 · AntV G6 v5 |
| Database | PostgreSQL (Supabase) · pgvector (1536-dim embeddings) · tsvector full-text search |
| LLM | OpenRouter (langchain-openai ChatOpenAI, custom base_url) · Groq fallback |
| Scraping | Scrapling (Camoufox → Playwright → Basic HTTP, 3-tier fallback) |
| Search | DuckDuckGo (default) · Tavily · Brave Search (optional) |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                             │
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌───────────────────────────┐  │
│  │  Research  │  │   Notes    │  │       Documents           │  │
│  │  (SSE)     │  │  (D3 Graph)│  │  Chat · Wiki · Skills     │  │
│  └─────┬──────┘  └─────┬──────┘  └─────────────┬─────────────┘  │
│        └───────────────┴─────────────────────────┘               │
│                  React 19 + TypeScript 5.9                       │
│                  Tailwind CSS v3 · Radix UI                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP / SSE (port 8000)
                               │ JWT Auth Header
┌──────────────────────────────▼──────────────────────────────────┐
│              FastAPI  (research_engine/api.py)                    │
│                    ~2700 lines · All endpoints                    │
│                                                                   │
│  Orchestrator → Planner → Searcher → Scraper → Synthesizer       │
│       ↑                                              ↓            │
│  RetryAgent ←── ConfidenceScorer ←── CrossoverAgent              │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ LLM      │  │ Sources  │  │Knowledge │  │ Utils          │  │
│  │ OpenRtr  │  │ Search   │  │ Graph    │  │ OpenKB         │  │
│  │ Groq     │  │ Scraper  │  │ Graphify │  │ WikiLinks      │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
           ┌────────────────────┼────────────────────┐
           │                    │                     │
 ┌─────────▼────────┐  ┌────────▼───────┐  ┌────────▼────────────┐
 │ Supabase         │  │ OpenRouter API │  │ Local Filesystem     │
 │ PostgreSQL       │  │ (LLM Gateway)  │  │ openkb/{ws_id}/      │
 │ pgvector · RLS   │  │                │  │ outputs/ graphify-out/│
 └──────────────────┘  └────────────────┘  └─────────────────────┘
```

### Webhook Worker (Separate Process)

A standalone FastAPI app (`worker.py`) handles HMAC-verified webhook triggers for async research execution. It does **not** share memory with the main API process.

---

## 3. Module Breakdown

### 3.1 Backend (`research_engine/`)

```
research_engine/
├── api.py                  # FastAPI routes — ALL endpoints
├── auth.py                 # JWT verification + workspace membership
├── cli.py                  # CLI entry point
├── config.py               # Configuration loader (TOML + env vars)
├── models.py               # Pydantic v2 models — SOURCE OF TRUTH
├── worker.py               # Webhook worker (separate FastAPI app)
├── setup_shims.py          # Compatibility shims
│
├── agent/
│   ├── orchestrator.py     # Main research loop
│   ├── planner.py          # Research plan generation
│   ├── searcher.py         # Search + scrape coordination
│   ├── router.py           # Intent classification router
│   ├── crossover.py        # Cross-domain connection detection
│   ├── retry.py            # Protocol-H retry
│   └── context.py          # ResearchContext
│
├── formats/                # Pluggable Research Formats Engine
│   ├── __init__.py         # Formats package interface
│   ├── registry.py         # Format registration and discovery
│   └── pipelines.py        # Specialized report synthesis pipelines
│
├── skills/                 # Dynamic Skill Execution Engine
│   ├── __init__.py         # Skills package interface
│   ├── registry.py         # Skill execution and built-in registration
│   └── external_loader.py  # Loads skills from external plugins
│
├── db/supabase/
│   ├── client.py           # Sync client (wrapped in asyncio.to_thread)
│   ├── ops.py              # SupabaseOps DB layer (async wrapper)
│   └── migrations/         # SQL migrations
│
├── llm/
│   ├── provider.py         # LLMProvider (OpenRouter gateway)
│   └── prompts.py          # All prompt templates
│
├── sources/
│   ├── web_scraper.py      # Scrapling 3-tier fallback
│   ├── web_search.py       # Search providers (DuckDuckGo etc.)
│   ├── github_search.py    # GitHub API search
│   ├── reranker.py         # Result reranking
│   ├── cache.py            # SQLite TTL caching
│   └── circuit_breaker.py  # Failure isolation
│
├── knowledge_graph/
│   ├── builder.py          # Graphify subprocess + LLM fallback
│   ├── enricher.py         # KG enrichment (aiofiles)
│   ├── gitnexus_bridge.py  # GitNexus integration
│   └── mcp_bridge.py       # MCP bridge
│
├── output/
│   ├── exporter.py         # Export (JSON, Markdown, PDF, DOCX, XLSX)
│   ├── formatter.py        # Report formatting
│   ├── mindmap.py          # G6 mindmap data generation
│   └── storage.py          # File output storage
│
├── citations/              # Citation extraction and verification
├── quality/                # Report quality assessment
├── cost/                   # Token cost tracking
├── sse/                    # SSE event emission helpers
└── utils/
    ├── openkb.py           # OpenKB operations
    └── wiki_links.py       # Wiki link parsing
```

### 3.2 Frontend (`frontend/src/`)

```
frontend/src/
├── App.tsx                 # Route definition + lazy loading + Suspense
├── main.tsx                # React entry point
├── index.css               # Global styles
├── api/client.ts           # All API calls — FRONTEND SOURCE OF TRUTH
├── types/api.ts            # TypeScript types (mirror of models.py)
│
├── modules/                # Thin module containers (compose components)
│   ├── research/ResearchModule.tsx
│   ├── notes/NotesModule.tsx
│   └── documents/DocumentsModule.tsx
│
├── components/             # Shared components by domain
│   ├── Auth/               # AuthModal, WorkspaceSelector
│   ├── backgrounds/        # 4 GPU backgrounds + renderer + switcher
│   ├── knowledge-graph/    # KnowledgeGraphView, KGQueryPanel, KGStatsPanel
│   ├── landing/            # TerminalDemo
│   ├── layout/             # Layout, Sidebar, Header
│   ├── mindmap/            # G6MindmapGraph, NodeDetailsPanel
│   ├── notes/              # MarkdownPreview, NoteGraph (D3), MoonPhaseWidget
│   ├── runs/               # RunList (virtualized)
│   ├── views/              # ReportView, CitationsView, ExportPanel, PlanReview
│   ├── ErrorBoundary.tsx
│   └── LoadingSkeletons.tsx
│
├── hooks/
│   ├── useBackground.tsx   # Background mode switching (4 modes)
│   └── useVirtualList.ts   # Fixed-height list virtualization
│
└── lib/
    ├── authContext.tsx     # Auth context + Supabase auth
    ├── supabase.ts         # Supabase client singleton
    └── utils.ts            # cn() utility
```

---

## 4. Data Flow

### 4.1 Research Run (Primary Flow)

```
1. POST /research/comprehensive → returns run_id immediately (async)
2. Background task:
     classify_intent()
     → generate_plan()
     ← SSE: plan_ready
     → decompose_queries()
     → Loop up to 30 cycles:
         search() → DuckDuckGo/Tavily/Brave
         scrape() → Scrapling 3-tier
         evaluate_relevance() → LLM pointwise
         synthesize_answer() → LLM
         score_confidence() → LLM
         reflect_on_plan() → LLM (periodic)
         check_progress() → LLM (periodic)
         ← SSE: cycle_complete
     → Format Pipeline Synthesis (based on selected format e.g. Academic, Business, Product)
     → build_mindmap() → LLM
     → build_knowledge_graph() → Graphify / LLM fallback
     → save to Supabase + filesystem
     ← SSE: complete
3. Frontend: POST /research/stream {run_id} → ReadableStream SSE
```

### 4.2 Notes Flow

```
Create/Edit → POST /notes or PATCH /notes/{id}
              ├── 400ms debounce auto-save
              ├── Ctrl+S shortcut
              └── Supabase persistence

Wiki links:   [[Title]] → clickable → navigate to note
Backlinks:    GET /notes/{id}/backlinks
Graph:        GET /notes/graph → D3 force-directed
Cross-module: "Research" button → POST /research/comprehensive
```

### 4.3 Documents Flow

```
Upload → POST /documents/upload → OpenKB ingestion → openkb/{workspace_id}/
Query  → POST /documents/query  → PostgreSQL tsvector
Chat   → POST /documents/chat   → multi-turn (session_id in-memory)
Wiki   → GET /documents/wiki    → browse generated pages
Skills → POST /documents/skills → generate from wiki
Export → GET /documents/wiki/download → Obsidian ZIP
```

---

## 5. Database Architecture

### 5.1 Schema Overview

| Table | Migration | Purpose |
|-------|-----------|---------|
| `workspaces` | 1 | Workspace registry |
| `workspace_members` | 1 | User ↔ Workspace link |
| `research_runs` | 1 & 5 | Research run metadata + report + checkpoints |
| `graph_nodes` | 1 | KG nodes (pgvector 1536-dim) |
| `graph_edges` | 1 | KG edges between nodes |
| `notes` | 2 | Personal notes (tsvector FTS) |
| `documents` | 2 | OpenKB document metadata |
| `document_tags` | 2 | Many-to-many tagging |
| `citation_verifications` | 3 | Persistent citation cross-verification results |
| `checkpoints` | 4 | Research checkpoint snapshots for recovery/resume |

### 5.2 Entity Relationships

```
workspaces ──< workspace_members >── auth.users
    │
    ├──< research_runs
    │         ├──< graph_nodes (embedding: vector(1536))
    │         ├──< graph_edges
    │         ├──< citation_verifications
    │         └──< checkpoints
    │
    ├──< notes (tsvector search_vector, tags JSONB)
    └──< documents
              └──< document_tags
```

### 5.3 Row-Level Security

**All 10 tables** have RLS enabled. Pattern applied universally:

```sql
USING (
    EXISTS (
        SELECT 1 FROM workspace_members
        WHERE workspace_members.workspace_id = <table>.workspace_id
        AND workspace_members.user_id = auth.uid()
    )
)
```

> [!CAUTION]
> The backend uses the **service_role** key (bypasses RLS).
> Never use the anon key on the backend — it causes 403s because `auth.uid()` returns NULL.

### 5.4 Vector Search (pgvector)

```sql
SELECT match_graph_nodes(
    query_embedding := '<vector(1536)>',
    match_threshold := 0.7,
    match_count := 10
);
-- Uses cosine distance: 1 - (embedding <=> query_embedding)
```

### 5.5 Full-Text Search

```sql
-- Notes: auto-generated STORED tsvector
search_vector tsvector GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(title,'') || ' ' || coalesce(content,''))
) STORED;
CREATE INDEX idx_notes_search ON notes USING GIN(search_vector);
```

---

## 6. API Reference Summary

### Research

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/research/comprehensive` | Start run (async, returns `run_id`, accepts `format` query param) |
| `POST` | `/research/stream` | SSE stream (`{run_id}` body) |
| `POST` | `/research/plan` | Generate plan preview |
| `POST` | `/research/approve` | Approve plan & start execution |
| `GET`  | `/runs` | List workspace runs |
| `GET`  | `/runs/{run_id}` | Retrieve run details |
| `GET`  | `/runs/{run_id}/report` | Get final report |
| `GET`  | `/runs/{run_id}/mindmap` | Get G6 mindmap data |
| `GET`  | `/runs/{run_id}/export/{format}` | Export report (JSON/MD/PDF/etc.) |
| `POST` | `/runs/{run_id}/mindmap/expand` | Drill into mindmap node |
| `GET`  | `/runs/{run_id}/knowledge-graph` | Get full KG |
| `POST` | `/runs/{run_id}/knowledge-graph/query` | BFS/DFS KG query |
| `POST` | `/runs/{run_id}/resynthesize` | Re-synthesize without re-search |
| `POST` | `/runs/{run_id}/resume` | Resume run from a saved checkpoint |
| `DELETE` | `/runs/{run_id}` | Delete run |
| `GET`  | `/models` | List available LLM models |
| `GET`  | `/telemetry` | Cache + circuit breaker stats |

### Notes

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/notes` | List notes |
| `POST` | `/notes` | Create note |
| `GET`  | `/notes/{id}` | Get note |
| `PATCH`| `/notes/{id}` | Update note |
| `DELETE`| `/notes/{id}` | Delete note |
| `GET`  | `/notes/{id}/backlinks` | Backlink notes |
| `GET`  | `/notes/graph` | D3 graph data |
| `POST` | `/notes/search` | Full-text search |

### Documents

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/documents/upload` | Upload + ingest |
| `POST` | `/documents/query` | Full-text query |
| `POST` | `/documents/chat` | Multi-turn chat |
| `GET`  | `/documents/wiki` | Browse wiki |
| `GET`  | `/documents/stats` | OpenKB metrics |
| `GET`  | `/documents/wiki/download` | Download Obsidian ZIP |

> All endpoints require `Authorization: Bearer <supabase_jwt>` and `workspace_id`.

---

## 7. Authentication & Authorization

```
Browser → Supabase Auth → JWT (access_token)
Browser → FastAPI (Authorization: Bearer <jwt>)
        → verify_supabase_jwt()        # extracts user_id, raises 401 if invalid
        → verify_workspace_membership() # raises 403 if not a member
```

- Auth is **not** a FastAPI Depends — it's called **inline** inside each route handler.
- `DEV_AUTH_BYPASS=true` skips auth in development (MUST be false in production).

---

## 8. LLM Gateway Design

All LLM calls go through `LLMProvider._get_llm()` which returns a `langchain-openai` `ChatOpenAI` instance pointed at `https://openrouter.ai/api/v1`. Models are **never hardcoded** — selected at runtime from: request body → CLI flag → config default.

**Structured output pattern (always with fallback):**

```python
try:
    result = await chain.with_structured_output(MyModel).ainvoke(prompt)
except Exception:
    raw = await chain.ainvoke(prompt)
    result = MyModel.model_validate_json(raw.content)
```

---

## 9. Scraping Layer

```
Tier 1: StealthyFetcher (Camoufox)   — Cloudflare / bot detection
Tier 2: DynamicFetcher (Playwright)  — JavaScript rendering
Tier 3: Fetcher (Basic HTTP)         — Always available
```

**Rule:** `Scrapling` is the sole scraping library. Never add `requests`, `httpx`, or `urllib3`.

Caching: SQLite TTL cache (search: 12h, pages: 24h). Circuit breaker prevents cascading failures.

---

## 10. Streaming Architecture (SSE)

### POST-based SSE (not GET)

```typescript
const response = await fetch('/research/stream', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ run_id })
});
// Consume ReadableStream
```

### Research State Machine

```
INITIALIZING → CLASSIFYING_INTENT → PLANNING → PLAN_READY
→ DECOMPOSING → SEARCHING → SCRAPING → VALIDATING
→ SYNTHESIZING → REFLECTING → [RETRYING] → CYCLE_COMPLETE
→ [repeat] → GENERATING_REPORT → COMPLETE
```

---

## 11. Knowledge Graph Subsystem

```
Research completes → export corpus to graphify-out/
→ Graphify subprocess:
    - AST analysis (fast mode)
    - LLM semantic edges (deep mode)
    - Leiden community detection
    - God node identification (top-N degree)
    - Surprise edge detection
→ (fallback) LLM extracts entities from report text
→ Store: Supabase graph_nodes/graph_edges + local JSON
→ Optional: Graphify MCP server (port 8765) for BFS/DFS
```

Node types: `function | class | concept | paper | diagram`
Edge types: `calls | imports | rationale_for | semantically_similar_to`

---

## 12. Research Formats Subsystem

The **Research Formats Engine** supports generating highly specialized reports tailored to specific research intents (e.g., Academic Paper, Business Briefing, Product Spec, or Technical Report).

```
Research Loop Done 
    → Formats Registry (`formats/registry.py`) matches query param `format`
    → Invokes the designated pipeline in `formats/pipelines.py`
    → Formats pipeline runs custom prompts to structure sections, summaries, and styles
    → Returns the formatted report markdown to save in the database
```

### Core Formats

- **Academic**: Exhaustive review of literature with rigorous sections (Abstract, Methodology, Analysis, Discussion).
- **Business**: Executive summary, SWOT details, market segments, pricing models, and actionable takeaways.
- **Product**: Product requirements, user stories (JTBD format), mockup notes, and implementation checklist.
- **Technical**: Technical architecture, coding standards, API specifications, and database schema mappings.

---

## 13. Skills Loader & Execution Engine

The **Skills Loader & Execution Engine** allows the agent to execute actions based on reusable, structured skills. It supports both **built-in skills** (defined in code) and **external plugins** (loaded from `external/pm-skills` using a validator script).

```
Registry loads skills from:
  1. Built-in skill templates (JSON/YAML)
  2. External plugins under `external/pm-skills/`
       - Schema verified by `external/pm-skills/validate_plugins.py`
       - Loaded at server startup via `skills/external_loader.py`
       - Accessible for agent runtime execution
```

---

## 14. Database Operations Layer (SupabaseOps)

The backend wraps Supabase queries in an async database operation wrapper located in `research_engine/db/supabase/ops.py`. 

```
FastAPI Endpoints (api.py)
    → SupabaseOps Instance (`ops.py`)
        → wrapped in `asyncio.to_thread()` to run the sync Supabase Client concurrently
            → Supabase REST/Postgrest endpoint
```

### Purpose
- **Thread Safety**: Prevents the sync Supabase client from blocking FastAPI's main async event loop.
- **Workspace Isolation**: Encapsulates workspace filtering `eq("workspace_id", workspace_id)` into clean, reusable database access routines.
- **Unified Error Handling**: Wraps database errors into custom `SupabaseError` exceptions for consistent HTTP status responses.

---

## 15. Frontend Architecture

### Design System

| Property | Value |
|----------|-------|
| Background | `#000000` (pure black) |
| Primary Accent | `#c8956c` (amber) |
| Glass Effect | `liquid-glass` — `backdrop-filter: blur(6px) saturate(140%)` |
| Font | Fira Sans (300–700) + Fira Code (mono) |
| Icons | lucide-react exclusively |

### Rules

- Tailwind CSS utilities only — no custom CSS outside `index.css`
- Radix UI for a11y-critical components
- `liquid-glass` class on all panels/cards
- `React.lazy()` + `Suspense` for all route modules
- `ErrorBoundary` wrapping all modules
- D3 for Notes graph · G6 for Research mindmap (do not swap)

---

## 16. Configuration Reference

```toml
[llm]
provider = "openrouter"
default_model = "..."
temperature = 0.2
max_tokens = 16384

[search]
default_provider = "duckduckgo"  # duckduckgo | tavily | brave
max_results = 10

[scraping]
max_concurrent = 5
fetcher_tier = "stealthy"

[research]
default_depth = 5     # 1=quick 3=standard 5=exhaustive
max_cycles = 30

[api]
port = 8000
cors_origins = ["http://localhost:5173"]

[graphify]
enabled = true
mode = "deep"         # fast | deep
```

### Required Environment Variables

| Variable | Required |
|----------|----------|
| `SUPABASE_URL` | ✅ |
| `SUPABASE_KEY` (service_role) | ✅ |
| `OPENROUTER_API_KEY` | ✅ |
| `TAVILY_API_KEY` | Optional |
| `BRAVE_SEARCH_API_KEY` | Optional |
| `GROQ_API_KEY` | Optional |

---

## 17. Deployment

```bash
# Development
uvicorn research_engine.api:app --reload --port 8000
cd frontend && npm run dev   # Vite on :5173

# Production
gunicorn research_engine.api:app -w 4 -k uvicorn.workers.UvicornWorker
uvicorn research_engine.worker:app --port 8001  # Optional webhook worker
```

---

## 18. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| DRE re-implemented (not vendored) | Original coupled to Gemini + Tavily; ours uses OpenRouter + DuckDuckGo |
| Exhaustive depth=5 default | Up to 30 research cycles — do not lower without user consent |
| OpenRouter as LLM gateway | All models via one API; no vendor lock-in |
| Structured output with fallback | Free models may not support JSON schema mode |
| Workspace-scoped data everywhere | All tables have `workspace_id` FK |
| Supabase sync client wrapped in `asyncio.to_thread()` | Official Python client is sync-only |
| POST-based SSE | JWT cannot be sent in GET URL params |
| Scrapling-only for scraping | 3-tier fallback superior to any single library |
| Components in `components/` not `modules/` | Enables cross-module reuse |
| Service role key on backend | RLS requires `auth.uid()`; service role bypasses for server-side ops |

---

*Generated: 2026-06-27 | Source: Codebase analysis, AGENTS.md, migrations, models.py*
