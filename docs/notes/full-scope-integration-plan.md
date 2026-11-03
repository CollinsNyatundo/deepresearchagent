# Deep Research Agent — Full-Scope Integration Plan
## Research + Notes + OpenKB + Deep-Research-Swarm + Longread

**Document Version:** 1.0  
**Generated:** 2026-01-23  
**Scope:** Frontend reskin + Notes app integration + OpenKB document analysis + Agent skill integration  
**Status:** Exploration — no code changes committed

---

## Table of Contents

1. [Executive Vision](#1-executive-vision)
2. [Subsystem Analysis](#2-subsystem-analysis)
   - 2.1 [Existing Deep Research Agent](#21-existing-deep-research-agent)
   - 2.2 [Moon Note Design System](#22-moon-note-design-system)
   - 2.3 [OpenKB (VectifyAI)](#23-openkb-vectifyai)
   - 2.4 [Deep-Research-Swarm Skill](#24-deep-research-swarm-skill)
   - 2.5 [Longread Skill](#25-longread-skill)
3. [Unified Architecture](#3-unified-architecture)
   - 3.1 [Three-Module Concept](#31-three-module-concept)
   - 3.2 [Cross-Module Data Flow](#32-cross-module-data-flow)
   - 3.3 [Workspace Scoping](#33-workspace-scoping)
4. [Backend Integration Plan](#4-backend-integration-plan)
   - 4.1 [Notes API (New)](#41-notes-api-new)
   - 4.2 [OpenKB Integration API (New)](#42-openkb-integration-api-new)
   - 4.3 [Document Upload API (New)](#43-document-upload-api-new)
   - 4.4 [Research API (Enhanced)](#44-research-api-enhanced)
   - 4.5 [Database Schema Additions](#45-database-schema-additions)
5. [Frontend Integration Plan](#5-frontend-integration-plan)
   - 5.1 [Layout: 3-Zone + Module Switcher](#51-layout-3-zone--module-switcher)
   - 5.2 [Module: Research](#52-module-research)
   - 5.3 [Module: Notes](#53-module-notes)
   - 5.4 [Module: Documents](#54-module-documents)
   - 5.5 [Shared Components](#55-shared-components)
6. [Feature Integration Matrix](#6-feature-integration-matrix)
7. [Agent Skill Integration](#7-agent-skill-integration)
   - 7.1 [Deep-Research-Swarm as Agent Engine](#71-deep-research-swarm-as-agent-engine)
   - 7.2 [Longread as Document Preprocessor](#72-longread-as-document-preprocessor)
8. [Implementation Roadmap](#8-implementation-roadmap)
9. [Risks & Mitigations](#9-risks--mitigations)
10. [Success Criteria](#10-success-criteria)
11. [Appendix: Source References](#11-appendix-source-references)

---

## 1. Executive Vision

The Deep Research Agent evolves from a single-purpose web research tool into a **unified knowledge platform** with three integrated modules:

| Module | Purpose | Source |
|--------|---------|--------|
| **Research** | Autonomous web-scale deep research with plans, SSE streaming, reports, mindmaps, knowledge graphs | Existing `research_engine/` |
| **Notes** | Personal Zettelkasten note-taking with wiki links `[[Title]]`, bidirectional backlinks, D3 knowledge graph, markdown editor | `frontend/design.md` (Moon Note) |
| **Documents** | Document upload, wiki compilation via OpenKB, query/chat over documents, skill factory | OpenKB (VectifyAI) |

All three modules share:
- **Unified visual design**: Moon Note aesthetic (pure black `#000000`, warm amber `#c8956c`, liquid-glass panels, procedural GPU backgrounds)
- **Workspace scoping**: Every research run, note, and document belongs to a workspace
- **Supabase JWT auth**: Single auth flow, workspace membership checks
- **Cross-module linking**: Notes can reference research runs (`[[run:uuid]]`), documents (`[[doc:filename]]`), and wiki concepts (`[[wiki:Concept]]`)

**Agent-level enhancements:**
- `deep-research-swarm` skill becomes the orchestration engine for comprehensive research queries
- `longread` skill handles preprocessing of uploaded long documents before OpenKB compilation

---

## 2. Subsystem Analysis

### 2.1 Existing Deep Research Agent

**Current Stack:**
- **Frontend:** React 18 + TypeScript + Vite + Mantine v7 + Tabler Icons + Fira Sans/Fira Code
- **Backend:** FastAPI + Python 3.11 + Pydantic v2 + Supabase (PostgreSQL + Auth + Storage)
- **API:** 25+ REST endpoints + SSE streaming (`/research/stream`, `/research/execute/stream`)
- **Auth:** Supabase JWT (`verify_supabase_jwt` dependency), workspace-based access control via `workspace_members` table
- **Storage:** File-based (`outputs/` directory) for runs, reports, mindmaps, knowledge graphs
- **Features:** Query composer, plan review, SSE streaming, report viewer, citations, export, G6 mindmap, Graphify knowledge graph, GitNexus code architecture, telemetry dashboard, resynthesis

**Current API Surface (verified from `research_engine/api.py`):**
```
GET  /runs                         — List research runs (workspace-scoped)
GET  /runs/{id}                    — Full run details
GET  /runs/{id}/report             — Markdown report
GET  /runs/{id}/mindmap            — G6 mindmap JSON
POST /runs/{id}/mindmap/expand     — Drill deeper into node
GET  /runs/{id}/exports            — List export formats
GET  /runs/{id}/export/{fmt}       — Download export
GET  /runs/{id}/knowledge-graph   — Knowledge graph JSON
GET  /runs/{id}/knowledge-graph/html
POST /runs/{id}/knowledge-graph/build
POST /runs/{id}/knowledge-graph/query
POST /runs/{id}/knowledge-graph/similarity
GET  /runs/{id}/knowledge-graph/mcp
POST /runs/{id}/knowledge-graph/mcp/start
POST /runs/{id}/knowledge-graph/mcp/stop
POST /research                     — Start research (blocking)
POST /research/stream              — Start research (SSE)
POST /research/plan                — Generate plan
POST /research/execute/stream      — Execute approved plan (SSE)
POST /validate-model               — Validate model ID
GET  /models                       — List available models
GET  /scraper/status               — Scraper status
POST /scraper/refresh-cache        — Refresh fetcher cache
GET  /health                       — Health check
POST /gitnexus/serve/start         — Start GitNexus bridge
POST /gitnexus/serve/stop          — Stop GitNexus bridge
GET  /gitnexus/serve/status        — Bridge status
POST /open-file                    — Open file in editor
POST /runs/{id}/resynthesize       — Re-synthesize report
GET  /api/telemetry                — Cache + circuit telemetry
```

**Workspace Model:**
- `research_runs` table has `workspace_id` FK
- `workspace_members` table links users to workspaces
- All endpoints verify `verify_workspace_membership(client, workspace_id, user_id)`

### 2.2 Moon Note Design System

**Full specification from `frontend/design.md` (607 lines):**

**Visual Design:**
- Base: `#000000` (pure black)
- Accent: `#c8956c` (warm amber)
- Primary text: `#e0e0e0`
- Liquid-glass CSS with `backdrop-filter: blur(6px) saturate(140%)` over `rgba(255,255,255,0.01)`
- 4 procedural GPU backgrounds: Moonlit Ripple (WebGL), Silk Flow Field (WebGL), Rain on Glass (Canvas 2D + WebGL), Solid Color (CSS)
- Custom 4px scrollbar

**Layout:**
- 3-zone single-page: 44px header, 240px sidebar, fluid main content
- All panels float over z-index 0 procedural background
- 1px gap between sidebar and main

**Features (notes domain):**
- Zettelkasten note-taking with `[[wiki links]]`
- Markdown editor with Edit/Preview toggle
- 400ms debounced auto-save
- `Ctrl/Cmd+S` manual save → preview mode
- Bidirectional backlinks (outgoing + incoming links)
- D3 force-directed knowledge graph with 6 forces
- Moon phase widget (canvas, 48x48px)
- 12 starter notes about LLMs with cross-links
- Full auth-gating (no access without login)

**Backend (from design.md):** tRPC + Hono + Drizzle ORM + MySQL + Kimi OAuth
**→ NOT used.** We keep FastAPI + Supabase.

### 2.3 OpenKB (VectifyAI)

**Full capabilities from GitHub research (`https://github.com/VectifyAI/OpenKB`):**

OpenKB is a CLI tool that compiles raw documents into a structured, interlinked wiki using LLMs. It uses **PageIndex** for vectorless, reasoning-based retrieval of long documents.

**Core Commands:**
```bash
openkb init                          # Initialize knowledge base
openkb add <file|dir|URL>            # Add documents (PDF, Word, PPT, Excel, HTML, CSV, text, .md, URLs)
openkb list                          # List indexed documents and concepts
openkb status                        # Show KB stats
openkb watch                         # Watch raw/ and auto-compile
openkb lint                          # Run structural + knowledge health checks
openkb remove <doc>                  # Remove document
openkb recompile [<doc>] [--all]   # Re-run compile pipeline
openkb query "question"              # Grounded answer with citations
openkb chat                          # Interactive multi-turn session
openkb skill new <name> "<intent>"  # Distill redistributable agent skill
openkb skill validate [name]         # Validate skill structure
openkb skill eval <name>             # Trigger-accuracy evaluation
openkb skill history <name>          # Version history
openkb skill rollback <name>         # Rollback to iteration
```

**Architecture:**
```
raw/                          # User drops files here
 │
 ├─ Short docs ──→ markitdown ──→ LLM reads full text
 ├─ Long PDFs ──→ PageIndex ────→ LLM reads document trees
 │                                    │
 │                                    ▼
 │                          Wiki Compilation (LLM)
 │                                    │
 ▼                                    ▼
wiki/                                  │            ← the foundation
 ├── index.md            KB overview
 ├── log.md              Operations timeline
 ├── AGENTS.md           Wiki schema (LLM instructions)
 ├── sources/            Full-text conversions
 ├── summaries/          Per-document summaries
 ├── concepts/           Cross-document synthesis
 ├── entities/           Named things (people, orgs, places, products)
 ├── explorations/       Saved query results
 └── reports/            Lint reports
```

**Key Features:**
- **Broad format support:** PDF, Word, Markdown, PowerPoint, HTML, Excel, CSV, text, URLs
- **Scale to long documents:** PageIndex tree indexing for PDFs ≥ 20 pages
- **Native multi-modality:** Figures, tables, images retrieval
- **Compiled Wiki:** LLM generates summaries, concept pages, entity pages, cross-links
- **Obsidian compatible:** Plain `.md` files with `[[wikilinks]]`
- **Multi-LLM support:** Via LiteLLM (OpenAI, Anthropic, Gemini, etc.)
- **Skill Factory:** Distill redistributable agent skills from wiki
- **Apache 2.0 license**

**Configuration:**
```yaml
# .openkb/config.yaml
model: gpt-5.4                    # Any LiteLLM-supported provider
language: en                      # Wiki output language
pageindex_threshold: 20           # PDF pages threshold for PageIndex
```

**Cloud support:** PageIndex Cloud for OCR, faster structure generation, scalable indexing. Set `PAGEINDEX_API_KEY` in `.env`.

### 2.4 Deep-Research-Swarm Skill

**Full specification from `SKILL.md` (513 lines):**

Multi-agent deep research orchestration with **adaptive routing** across 4 routes:

| Route | Trigger | Description |
|-------|---------|-------------|
| **A — Wide Search** | Broad, open-ended, landscape-level query | Two-stage swarm: Phase 1W (5–8 parallel facet agents) → Phase 3 (deep dive per dimension) |
| **B — Focused Search** | Specific, bounded question with clear dimensions | Phase 1 (landscape) → Phase 2 (decompose) → Phase 3 (parallel deep dive) |
| **C — File-Only** | Files + "only based on files" / "no search" | Phase F (file intake) → Phase 3-F (NO external search) |
| **D — File-Augmented** | Files + "refer to" / "combine with" | Phase F → Phase 1 (targeted search) → Phase 3 (file context + external search) |

**7-Phase Workflow:**
1. **Phase 0:** Intent & Input Router — classify into Route A/B/C/D
2. **Phase F:** File Intake & Deep Analysis (Routes C/D only) — extract themes, claims, contradictions, gaps
3. **Phase 1:** Landscape Scan — coarse-to-fine evidence exploration (3–5 searches)
4. **Phase 1W:** Multi-Agent Wide Exploration (Route A only) — 5–8 parallel facet agents, ≥10 searches each
5. **Phase 2:** Dimension Decomposition — ≥10 distinct dimensions, ≥30% overlap
6. **Phase 3:** Parallel Deep Dive — one sub-agent per dimension, ≥20 searches each (standard), or file-only analysis
7. **Phase 4:** Cross-Verification — 4 confidence tiers (High/Medium/Low/Conflict Zone)
8. **Phase 5:** Targeted Validation (conditional) — resolve conflicts, ≥3 additional searches per conflict
9. **Phase 6:** Insight Extraction — cross-dimension inferences, minimum 5 insights
10. **Phase 7:** Handoff to Writing Skill — report-writing or paper-writing

**Output Directory:** All files under `{workspace}/research/`

**File Naming Convention:**
```
{workspace}/research/
├── {topic}_file_analysis.md      # Phase F (Routes C/D)
├── {topic}_wide{NN}.md            # Phase 1W (Route A)
├── {topic}_dim{NN}.md             # Phase 3 (all routes)
├── {topic}_cross_verification.md # Phase 4-5
└── {topic}_insight.md             # Phase 6
```

**Core Principles:**
- Depth over breadth (Route B) / Breadth then depth (Route A)
- Raw evidence required — verbatim excerpts with source URLs
- Contradictions are signal — never suppressed
- Everything is a file — no long-form chat output
- Source quality: government, academic, official filings, major media
- Search budgets: Route A ~5–8×10 + N×20, Route B N×20, Route C 0, Route D N×15
- All citations: `[^id]` Markdown footnotes

### 2.5 Longread Skill

**Full specification from `SKILL.md` (106 lines):**

Chunk-based parallel document reading for files too large to process in a single pass.

**Supported formats:** PDF, DOCX, TXT, MD, PPTX
**Not suitable for:** CSV, XLSX, JSON, JSONL, log files, source code

**Workflow:**
1. **Step 0:** Assess suitability (prose-like vs. structured data)
2. **Step 1:** Split document using `split_doc.py` → `{workspace}/chunks/doc_part_{NN}.txt`
   - Default chunk size: 32k tokens with 10% overlap
3. **Step 2:** Launch reader sub-agents (`subagent_type="explore"`) — one per chunk
4. **Step 3:** Bounded rounds (3–5 at a time, up to concurrency limit)
5. **Step 4:** Aggregate results — combine all chunk summaries

**Usage:** When an agent encounters a file too large for single-pass reading.

---

## 3. Unified Architecture

### 3.1 Three-Module Concept

The application becomes a single-page app with three primary modules, switched via a header module selector. All modules share the same 3-zone layout (44px header, 240px sidebar, fluid main content) and liquid-glass visual system.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Header (44px, liquid-glass)                                         │
│  [Brand] [Module: Research | Notes | Documents] [Background] [User]  │
├──────────┬──────────────────────────────────────────────────────────┤
│          │                                                          │
│ Sidebar  │  Main Content                                            │
│ (240px)  │  Module-dependent content                                │
│          │                                                          │
│ [Context]│                                                          │
│ [Search] │                                                          │
│ [List]   │                                                          │
│ [Actions]│                                                          │
│          │                                                          │
└──────────┴──────────────────────────────────────────────────────────┘
↑ z-0: Procedural background (4 GPU-rendered options)
```

**Module Selector:** Segmented control in the header with three options: **Research**, **Notes**, **Documents**. Active module determines sidebar content and main content area.

### 3.2 Cross-Module Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CROSS-MODULE LINKS                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    save as note    ┌─────────────┐                 │
│  │   RESEARCH   │ ─────────────────→ │    NOTES     │                 │
│  │              │   (with wiki link) │              │                 │
│  │  • Report    │                    │  • Notes     │                 │
│  │  • Citations │ ←─── cite in ──────│  • Wiki links│                 │
│  │  • Mindmap   │     research        │  • Backlinks │                 │
│  │  • KG        │                    │  • D3 graph  │                 │
│  └─────────────┘                    └─────────────┘                 │
│         │                                   │                        │
│         │   reference wiki concepts         │                        │
│         │   from documents                  │                        │
│         ↓                                   ↓                        │
│  ┌─────────────┐    query for context  ┌─────────────┐               │
│  │  DOCUMENTS   │ ←────────────────── │    NOTES     │               │
│  │              │                      │              │               │
│  │  • Upload    │    compile as       │              │               │
│  │  • OpenKB    │ ── document source ─→│              │               │
│  │  • Wiki      │                      │              │               │
│  │  • Query     │                      │              │               │
│  │  • Chat      │                      │              │               │
│  └─────────────┘                      └─────────────┘               │
│                                                                      │
│  Agent Skills (behind the scenes):                                   │
│  • deep-research-swarm → triggered by comprehensive research queries │
│  • longread → triggered by long document uploads (>20 pages)       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Link Syntax (Unified Wiki Link System):**
- `[[Note Title]]` — Link to a note in the Notes module
- `[[run:run_id]]` — Link to a research run (shows run query + date)
- `[[doc:filename]]` — Link to a document in the Documents module
- `[[wiki:Concept]]` — Link to a compiled wiki concept from OpenKB
- `[[entity:Name]]` — Link to an extracted entity (person, org, place, product)

**Click behavior:** Each link type navigates to the appropriate module and opens the referenced item. If the target doesn't exist, prompt to create it (for notes) or show "not found" (for runs/docs).

### 3.3 Workspace Scoping

All data is workspace-scoped. A user belongs to multiple workspaces via `workspace_members`.

| Data Type | Workspace Scoping | Table/Storage |
|-----------|-------------------|---------------|
| Research runs | `workspace_id` FK on `research_runs` | Supabase + `outputs/` |
| Notes | `workspace_id` FK on `notes` | Supabase |
| Documents | `workspace_id` subfolder in `openkb/` | File system |
| OpenKB wiki | `workspace_id` subfolder in `openkb/{workspace_id}/wiki/` | File system |
| OpenKB raw | `workspace_id` subfolder in `openkb/{workspace_id}/raw/` | File system |

When switching workspaces, all three modules reload their data. The workspace selector remains in the header (or sidebar top) across all modules.

---

## 4. Backend Integration Plan

### 4.1 Notes API (New)

**New Supabase table: `notes`**
```sql
CREATE TABLE notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title VARCHAR(500) NOT NULL,
  content TEXT NOT NULL DEFAULT '',
  tags JSONB DEFAULT '[]'::jsonb,
  source TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notes_workspace ON notes(workspace_id);
CREATE INDEX idx_notes_user ON notes(user_id);
CREATE INDEX idx_notes_updated ON notes(workspace_id, updated_at DESC);
```

**New FastAPI endpoints:**
```python
# research_engine/api.py additions

# ─── Notes CRUD ───────────────────────────────────────────────────────

@app.get("/notes", response_model=list[NoteSummary])
async def get_notes(
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """List all notes for a workspace, newest first."""
    # verify_workspace_membership
    # SELECT * FROM notes WHERE workspace_id = ? ORDER BY updated_at DESC

@app.get("/notes/{note_id}", response_model=Note)
async def get_note(
    note_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Get a single note by ID."""
    # verify workspace membership via note.workspace_id

@app.post("/notes", response_model=Note)
async def create_note(
    request: CreateNoteRequest,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Create a new note."""
    # verify_workspace_membership
    # INSERT INTO notes (workspace_id, user_id, title, content, tags, source)

@app.patch("/notes/{note_id}", response_model=Note)
async def update_note(
    note_id: str,
    request: UpdateNoteRequest,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Update a note (title, content, tags, source)."""
    # verify ownership + workspace membership
    # UPDATE notes SET ... WHERE id = ?

@app.delete("/notes/{note_id}")
async def delete_note(
    note_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Delete a note."""
    # verify ownership + workspace membership
    # DELETE FROM notes WHERE id = ?

@app.post("/notes/bulk-delete")
async def delete_notes_bulk(
    request: BulkDeleteRequest,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Delete multiple notes by ID."""
    # verify all notes belong to user's workspace
    # DELETE FROM notes WHERE id IN (...) AND workspace_id = ?

@app.get("/notes/search")
async def search_notes(
    workspace_id: str,
    q: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Full-text search notes (title + content)."""
    # Uses PostgreSQL full-text search (tsvector) or ILIKE fallback
```

**Pydantic models (add to `research_engine/models.py`):**
```python
class NoteSummary(BaseModel):
    id: str
    title: str
    workspace_id: str
    created_at: str
    updated_at: str

class Note(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    title: str
    content: str
    tags: list[str] = []
    source: str | None = None
    created_at: str
    updated_at: str
    # Derived fields
    outgoing_links: list[str] = []  # parsed [[links]] from content
    backlink_count: int = 0

class CreateNoteRequest(BaseModel):
    workspace_id: str
    title: str
    content: str = ""
    tags: list[str] = []
    source: str | None = None

class UpdateNoteRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    source: str | None = None

class BulkDeleteRequest(BaseModel):
    ids: list[str]
```

**Wiki link extraction utility:**
```python
# research_engine/utils/wiki_links.py
import re

WIKI_LINK_RE = re.compile(r'\[\[([^\]]+)\]\]')

def extract_wiki_links(content: str) -> list[str]:
    """Extract [[Title]] links from markdown content, excluding code blocks."""
    # Strip code blocks first
    text = re.sub(r'```[\s\S]*?```', '', content)
    text = re.sub(r'`[^`]+`', '', text)
    return WIKI_LINK_RE.findall(text)

def find_backlinks(workspace_id: str, target_title: str, db_client) -> list[NoteSummary]:
    """Find all notes in workspace that link to target_title via [[Title]]."""
    # Case-insensitive search
    # SELECT * FROM notes WHERE workspace_id = ? AND content ILIKE '%[[target_title]]%'
```

### 4.2 OpenKB Integration API (New)

OpenKB is a CLI tool. We integrate by **shelling out** from the FastAPI backend, with workspace-scoped working directories.

**Workspace-scoped OpenKB directory structure:**
```
openkb/
├── {workspace_id}/
│   ├── .openkb/
│   │   └── config.yaml          # Per-workspace OpenKB config
│   ├── raw/                      # User-uploaded documents
│   ├── wiki/                     # Compiled wiki (Markdown files)
│   │   ├── index.md
│   │   ├── log.md
│   │   ├── AGENTS.md
│   │   ├── sources/
│   │   ├── summaries/
│   │   ├── concepts/
│   │   ├── entities/
│   │   └── explorations/
│   └── output/
│       └── skills/               # Generated skills
```

**New FastAPI endpoints:**
```python
# research_engine/api.py additions

# ─── OpenKB Document Management ───────────────────────────────────────

@app.post("/documents/upload")
async def upload_document(
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Upload a document to workspace raw/ folder and add to OpenKB."""
    # verify_workspace_membership
    # 1. Save file to openkb/{workspace_id}/raw/{file.filename}
    # 2. If PDF > 20 pages, optionally run longread skill first (agent-level)
    # 3. Run `openkb add {path}` via subprocess
    # 4. Return document ID and status

@app.get("/documents")
async def list_documents(
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """List all documents in workspace OpenKB."""
    # verify_workspace_membership
    # Run `openkb list` in workspace directory
    # Parse output into structured JSON

@app.delete("/documents/{doc_name}")
async def delete_document(
    doc_name: str,
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Remove a document from OpenKB."""
    # verify_workspace_membership
    # Run `openkb remove {doc_name}` in workspace directory

@app.post("/documents/recompile")
async def recompile_documents(
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Re-run compile pipeline on all indexed documents."""
    # verify_workspace_membership
    # Run `openkb recompile --all` in workspace directory

# ─── OpenKB Query & Chat ─────────────────────────────────────────────

@app.post("/documents/query")
async def query_documents(
    request: DocumentQueryRequest,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Query the OpenKB wiki for a specific question."""
    # verify_workspace_membership
    # Run `openkb query "{question}"` in workspace directory
    # Return answer with citations

@app.post("/documents/chat")
async def chat_documents(
    request: DocumentChatRequest,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Multi-turn chat over the OpenKB wiki."""
    # verify_workspace_membership
    # Manage chat session state (session_id → workspace/{session_id}.json)
    # Run `openkb chat` with session management
    # Stream response or return full message

@app.get("/documents/wiki/{page_path}")
async def get_wiki_page(
    page_path: str,  # e.g. "concepts/attention.md"
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Get a specific wiki page as Markdown."""
    # verify_workspace_membership
    # Read file from openkb/{workspace_id}/wiki/{page_path}
    # Return content

@app.get("/documents/wiki")
async def list_wiki_pages(
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """List all wiki pages (summaries, concepts, entities)."""
    # verify_workspace_membership
    # Walk openkb/{workspace_id}/wiki/ directory
    # Return structured tree

@app.get("/documents/status")
async def get_openkb_status(
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Get OpenKB status for workspace."""
    # verify_workspace_membership
    # Run `openkb status` in workspace directory
    # Return stats: document count, concept count, entity count, etc.

# ─── OpenKB Skill Factory ────────────────────────────────────────────

@app.post("/documents/skills")
async def create_skill(
    request: CreateSkillRequest,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Distill a skill from the OpenKB wiki."""
    # verify_workspace_membership
    # Run `openkb skill new {name} "{intent}"` in workspace directory
    # Return skill path and validation result

@app.get("/documents/skills")
async def list_skills(
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """List all generated skills in workspace."""
    # verify_workspace_membership
    # List openkb/{workspace_id}/output/skills/ directory
```

**Pydantic models:**
```python
class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str  # "indexed" | "processing" | "error"
    message: str

class DocumentQueryRequest(BaseModel):
    workspace_id: str
    question: str
    save: bool = False  # Save to explorations/

class DocumentQueryResponse(BaseModel):
    answer: str
    citations: list[str]
    sources: list[str]

class DocumentChatRequest(BaseModel):
    workspace_id: str
    message: str
    session_id: str | None = None  # None = new session

class DocumentChatResponse(BaseModel):
    session_id: str
    response: str
    citations: list[str]

class WikiPage(BaseModel):
    path: str
    title: str
    content: str
    type: str  # "summary" | "concept" | "entity" | "index" | "log"

class OpenKBStatus(BaseModel):
    workspace_id: str
    document_count: int
    concept_count: int
    entity_count: int
    summary_count: int
    wiki_size_bytes: int

class CreateSkillRequest(BaseModel):
    workspace_id: str
    name: str
    intent: str
```

**OpenKB shell-out utility:**
```python
# research_engine/utils/openkb.py
import asyncio
import subprocess
from pathlib import Path

OPENKB_BASE_DIR = Path("openkb")

def get_workspace_kb_dir(workspace_id: str) -> Path:
    return OPENKB_BASE_DIR / workspace_id

async def ensure_kb_initialized(workspace_id: str) -> Path:
    """Ensure OpenKB is initialized for workspace."""
    kb_dir = get_workspace_kb_dir(workspace_id)
    config_path = kb_dir / ".openkb" / "config.yaml"
    if not config_path.exists():
        kb_dir.mkdir(parents=True, exist_ok=True)
        # Copy default config or run `openkb init` non-interactively
        proc = await asyncio.create_subprocess_exec(
            "openkb", "init",
            cwd=kb_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await proc.communicate(input=b"\n\n\n")  # default answers
    return kb_dir

async def run_openkb_command(workspace_id: str, *args) -> str:
    """Run an OpenKB command in workspace context."""
    kb_dir = get_workspace_kb_dir(workspace_id)
    await ensure_kb_initialized(workspace_id)
    proc = await asyncio.create_subprocess_exec(
        "openkb", *args,
        cwd=kb_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"OpenKB failed: {stderr.decode()}")
    return stdout.decode()
```

### 4.3 Document Upload API (New)

The document upload endpoint needs to handle multipart file uploads, save to workspace-scoped storage, and optionally preprocess long documents.

**File handling:**
```python
@app.post("/documents/upload")
async def upload_document(
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
    auto_compile: bool = Form(True),
    user_data: dict = Depends(verify_supabase_jwt)
):
    # 1. Verify workspace membership
    # 2. Save file: openkb/{workspace_id}/raw/{file.filename}
    # 3. If file is PDF and page_count > 20, and pageindex_threshold is set:
    #    - PageIndex handles it automatically via OpenKB
    # 4. If auto_compile:
    #    - Run `openkb add {file_path}`
    # 5. Return document metadata
```

**File storage per workspace:**
```
openkb/{workspace_id}/
├── raw/              # Uploaded files (preserved as-is)
│   ├── paper.pdf
│   ├── report.docx
│   └── article.html
├── wiki/             # Compiled wiki (OpenKB generates)
└── .openkb/          # OpenKB config
```

### 4.4 Research API (Enhanced)

**Link notes to research runs:**
```python
# When saving a research report to a note, auto-generate wiki links
class SaveResearchToNoteRequest(BaseModel):
    run_id: str
    workspace_id: str
    note_title: str  # "Research: {query}" or user-provided
    include_citations: bool = True
    include_mindmap: bool = False

@app.post("/research/save-to-note")
async def save_research_to_note(
    request: SaveResearchToNoteRequest,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Save a research report as a note with auto-generated content."""
    # 1. Load research result from outputs/{run_id}/
    # 2. Generate note content:
    #    - Title: "Research: {query}"
    #    - Content: Report markdown + citations + "[[run:{run_id}]]"
    #    - Tags: ["research", {mode}, {model}]
    # 3. Create note via Supabase
    # 4. Return note ID
```

**Link research to OpenKB concepts:**
```python
@app.post("/research/enrich-openkb")
async def enrich_openkb_with_research(
    run_id: str,
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Save research findings to OpenKB wiki as a new source."""
    # 1. Load research report
    # 2. Save as .md file in openkb/{workspace_id}/raw/research_{run_id}.md
    # 3. Run `openkb add research_{run_id}.md` to compile into wiki
    # 4. Return status
```

### 4.5 Database Schema Additions

**Supabase tables to add:**

```sql
-- Notes table
CREATE TABLE notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title VARCHAR(500) NOT NULL,
  content TEXT NOT NULL DEFAULT '',
  tags JSONB DEFAULT '[]'::jsonb,
  source TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notes_workspace ON notes(workspace_id);
CREATE INDEX idx_notes_user ON notes(user_id);
CREATE INDEX idx_notes_updated ON notes(workspace_id, updated_at DESC);

-- Optional: Full-text search index (if using PostgreSQL >= 12)
ALTER TABLE notes ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || content)) STORED;
CREATE INDEX idx_notes_search ON notes USING GIN(search_vector);

-- Documents table (metadata only — actual files in openkb/)
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  filename VARCHAR(500) NOT NULL,
  file_path TEXT NOT NULL,
  file_size BIGINT,
  mime_type VARCHAR(100),
  status VARCHAR(50) DEFAULT 'uploaded',  -- uploaded | indexing | compiled | error
  page_count INTEGER,
  indexed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_workspace ON documents(workspace_id);

-- Document tags (many-to-many)
CREATE TABLE document_tags (
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  tag VARCHAR(100) NOT NULL,
  PRIMARY KEY (document_id, tag)
);
```

---

## 5. Frontend Integration Plan

### 5.1 Layout: 3-Zone + Module Switcher

The header gains a **module switcher** as its primary navigation. The sidebar and main content adapt to the active module.

**Header (44px, liquid-glass):**
```
┌──────────────────────────────────────────────────────────────────────┐
│  ◆ DeepResearch.ai │ [Research] [Notes] [Documents] │ ⚙ BG │ 👤 User │
└──────────────────────────────────────────────────────────────────────┘
```

- **Left:** Brand mark (diamond icon + "DeepResearch.ai")
- **Center:** Module switcher — segmented control with three tabs: Research, Notes, Documents
- **Right:** Background switcher (sun/moon icon), User avatar + logout dropdown

**Sidebar (240px, liquid-glass) — module-dependent:**

| Module | Sidebar Content |
|--------|-----------------|
| **Research** | Workspace selector, "+ New Research" button, Run list (searchable), Mode switcher (Research / Code-Arch), Sign out |
| **Notes** | Workspace selector, "+ New Note" button, Note list (searchable), Manage mode toggle, Tags filter, Sign out |
| **Documents** | Workspace selector, "+ Upload" button, Document list (searchable), OpenKB status mini-card, Wiki page tree, Sign out |

**Main Content — module-dependent:**

| Module | Main Content |
|--------|-------------|
| **Research** | Idle: Hero + Query composer; Plan review; SSE streaming; Results: Report + Citations + Export tabs |
| **Notes** | Note editor (Edit/Preview toggle) OR Graph view (D3 force graph); Max-width 672px centered |
| **Documents** | Upload area; Document list; OpenKB query panel; OpenKB chat panel; Wiki browser (file tree + content) |

### 5.2 Module: Research

This is the existing Deep Research Agent, reskinned with Moon Note aesthetic. All features preserved:

- **Idle state:** Hero panel with query composer (reskinned with liquid-glass cards)
- **Plan review:** Plan steps in liquid-glass cards with approve/regenerate
- **SSE streaming:** Progress events in scrollable liquid-glass panel
- **Results:** Split-pane layout (report left, citations/export tabs right)
- **Mindmap:** G6 v5 graph (keep logic, reskin container)
- **Knowledge Graph:** Graphify panels (reskinned)
- **GitNexus:** Code architecture view (iframe in liquid-glass container)
- **Telemetry:** Bento stat cards in idle state

**New feature — Save to Notes:**
- Button on report view: "Save to Notes"
- Creates a new note with:
  - Title: "Research: {query}"
  - Content: Full report + "\n\n---\n\nSources: [[run:{run_id}]]"
  - Auto-extracted tags from research topic
- User can edit before saving

### 5.3 Module: Notes

This is the full Moon Note notes app, ported to work with the FastAPI backend instead of tRPC/Hono/MySQL.

**Features (from design.md):**
- **Note CRUD:** Create, read, update, delete, bulk delete
- **Editor:** Title input + content textarea with monospace font (Fira Code)
- **Edit/Preview toggle:** Edit mode (raw markdown) / Preview mode (rendered with react-markdown + remark-gfm)
- **Auto-save:** 400ms debounced save to backend
- **Wiki links:** `[[Note Title]]` syntax
  - Click navigates to existing note or creates new one
  - Rendering: custom `a` component for `wiki:` protocol links
- **Backlinks:** Outgoing links + incoming backlinks shown below preview
- **D3 Graph:** Force-directed knowledge graph of all notes
  - Nodes sized by link count, 8-color warm amber palette
  - Edges: `rgba(200,149,108,0.12)`
  - Hover: dim unrelated to 15% opacity, highlight connections
  - Zoom: 0.15x–5x with D3 zoom behavior
- **Search:** Full-text search across note titles and content
- **Tags:** JSON array of tags, filterable
- **Source:** Optional citation field per note
- **Starter notes:** Auto-seed 12 LLM notes on first workspace access (configurable)

**Cross-module links in notes:**
```markdown
# My Research Notes

I found that [[run:abc-123]] provides excellent coverage of this topic.

Also see [[doc:paper.pdf]] for the original source, and [[wiki:Attention Mechanism]]
for the compiled concept from our knowledge base.

Related notes: [[Transformer Architecture]] [[RAG]]
```

**Click handlers:**
- `[[Note Title]]` → switch to Notes module, open note
- `[[run:uuid]]` → switch to Research module, open run results
- `[[doc:filename]]` → switch to Documents module, show document
- `[[wiki:Concept]]` → switch to Documents module, show wiki page

**Graph View:**
- D3 force simulation with 6 forces (link, charge, center, collision, x, y)
- Nodes: sized by `sqrt(linkCount + 1) * 5.5`, warm amber palette
- Stats overlay: liquid-glass badge showing node count + edge count
- Click node → navigate to note

### 5.4 Module: Documents

This is the new OpenKB integration module.

**Features:**

**1. Upload Panel:**
- Drag-and-drop file upload area
- Supported formats: PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx), HTML, Markdown, Text, CSV
- Progress indicator during upload
- Post-upload: shows status (uploaded → indexing → compiled → done)
- Auto-compiles via OpenKB after upload

**2. Document List:**
- Scrollable list of uploaded documents
- Columns: filename, size, page count, status, upload date
- Actions: view, recompile, delete, download
- Search/filter by filename

**3. OpenKB Query Panel:**
- Text input for questions
- "Query" button submits to backend `/documents/query`
- Results show: answer text + source citations + links to wiki pages
- "Save to Notes" button — saves query result as a note
- History of past queries per workspace

**4. OpenKB Chat Panel:**
- Chat-style interface (messages bubbles)
- Multi-turn conversation over the wiki
- Session management (new, resume, list, delete)
- Slash commands: `/help`, `/status`, `/list`, `/add`, `/skill`, `/save`, `/clear`, `/lint`, `/exit`
- "Save to Notes" button — saves full chat transcript as a note

**5. Wiki Browser:**
- Tree view of wiki pages: index, summaries, concepts, entities, explorations
- Click page → show rendered Markdown in main panel
- Wiki pages are plain `.md` files with `[[wikilinks]]`
- Cross-links clickable (navigate to other wiki pages)
- "Open in Obsidian" button — downloads wiki as zip for local use

**6. Skill Factory Panel:**
- Form: skill name + intent description
- "Generate Skill" button → calls `/documents/skills`
- Shows generated skill preview (SKILL.md content)
- Download skill as zip
- List existing skills in workspace
- Validate/Eval/Rollback controls

**7. OpenKB Status Dashboard:**
- Stat cards: document count, concept count, entity count, summary count
- Health indicator (lint status)
- Last compilation timestamp
- Storage usage

### 5.5 Shared Components

**Used across all three modules:**

| Component | Description | Where Used |
|-----------|-------------|------------|
| `Header` | 44px liquid-glass bar with brand + module switcher + background + user | All modules |
| `Sidebar` | 240px liquid-glass panel, content varies by module | All modules |
| `WorkspaceSelector` | Dropdown to select/create workspace | All modules |
| `BackgroundRenderer` | z-0 procedural GPU background | All modules |
| `BackgroundSwitcher` | Dropdown to toggle 4 backgrounds | All modules |
| `UserMenu` | Avatar + dropdown with logout | All modules |
| `SearchInput` | Full-width text field with `bg-white/[0.03]` | Notes, Documents, Research (run list) |
| `LiquidGlass` | CSS class/panel wrapper | All panels |
| `LiquidGlassStrong` | CSS class for prominent buttons | Action buttons |
| `MarkdownRenderer` | react-markdown + remark-gfm + custom link handlers | Notes (preview), Documents (wiki), Research (report) |
| `WikiLink` | Custom `a` component handling `wiki:` protocol | Notes (preview), Documents (wiki), Research (report) |
| `CustomScrollbar` | 4px thin scrollbar style | All scrollable panels |
| `LoadingState` | "Loading..." centered text | All modules |
| `ErrorBoundary` | Error fallback | All modules |

**Module-specific components:**

| Component | Module | Description |
|-----------|--------|-------------|
| `QueryComposer` | Research | Research query form with model, provider, depth, presets |
| `PlanReview` | Research | Plan step cards with approve/regenerate |
| `ResearchProgress` | Research | SSE event stream display |
| `ReportView` | Research | Markdown report renderer |
| `CitationsView` | Research | Citation list with URLs |
| `ExportPanel` | Research | Export format buttons |
| `MindmapView` | Research | G6 mindmap container |
| `KnowledgeGraphView` | Research | Graphify graph container |
| `GitNexusWebView` | Research | Code architecture iframe |
| `TelemetryDashboard` | Research | Bento stat cards |
| `NoteEditor` | Notes | Title + textarea + edit/preview toggle |
| `NoteList` | Notes | Scrollable note list with search |
| `BacklinksPanel` | Notes | Outgoing + incoming links |
| `GraphView` | Notes | D3 force-directed note graph |
| `UploadPanel` | Documents | Drag-and-drop file upload |
| `DocumentList` | Documents | Uploaded document list |
| `QueryPanel` | Documents | OpenKB query interface |
| `ChatPanel` | Documents | OpenKB chat interface |
| `WikiBrowser` | Documents | Wiki page tree + content |
| `SkillFactory` | Documents | Skill generation interface |
| `OpenKBStatus` | Documents | Status dashboard |

---

## 6. Feature Integration Matrix

| Feature | Research Module | Notes Module | Documents Module | Cross-Module Links |
|---------|----------------|------------|------------------|------------------|
| **Query Composer** | ✅ Core feature | ❌ | ❌ | Can reference notes/docs as context |
| **Plan Review** | ✅ Core feature | ❌ | ❌ | Can save plan as note |
| **SSE Streaming** | ✅ Core feature | ❌ | ❌ | Events can be logged to notes |
| **Report Viewer** | ✅ Core feature | ✅ Save report as note | ✅ Reference in wiki | `[[run:uuid]]` |
| **Citations** | ✅ Core feature | ✅ Cite in notes | ✅ Link to docs | `[[doc:filename]]` |
| **Export** | ✅ Core feature | ✅ Export notes | ✅ Export wiki | — |
| **Mindmap (G6)** | ✅ Core feature | ❌ | ❌ | Can be embedded in notes |
| **Knowledge Graph** | ✅ Core feature | ❌ | ✅ OpenKB concepts | `[[wiki:Concept]]` |
| **GitNexus** | ✅ Core feature | ❌ | ❌ | — |
| **Telemetry** | ✅ Core feature | ❌ | ❌ | — |
| **Note Editor** | ❌ | ✅ Core feature | ✅ Wiki pages | `[[Note Title]]` |
| **Wiki Links** | ✅ In reports | ✅ Core feature | ✅ In wiki | Universal syntax |
| **Backlinks** | ❌ | ✅ Core feature | ✅ In wiki | Bidirectional |
| **D3 Note Graph** | ❌ | ✅ Core feature | ❌ | Shows cross-module links |
| **Auto-save** | ❌ | ✅ 400ms debounce | ❌ | — |
| **Document Upload** | ❌ | ✅ Attach to notes | ✅ Core feature | `[[doc:filename]]` |
| **OpenKB Query** | ✅ Research findings | ✅ Query from notes | ✅ Core feature | Results save to notes |
| **OpenKB Chat** | ❌ | ❌ | ✅ Core feature | Transcripts save to notes |
| **Wiki Browser** | ❌ | ✅ Reference wiki | ✅ Core feature | `[[wiki:Concept]]` |
| **Skill Factory** | ❌ | ❌ | ✅ Core feature | Skills reference notes |
| **Full-text Search** | ✅ Run search | ✅ Note search | ✅ Doc search | Unified search (future) |
| **Tags** | ❌ | ✅ JSON array | ✅ Document tags | Filterable |
| **Resynthesis** | ✅ Core feature | ❌ | ❌ | Re-analyze with doc context |

---

## 7. Agent Skill Integration

### 7.1 Deep-Research-Swarm as Agent Engine

**How it integrates:** The `deep-research-swarm` skill is the **agent-level research engine** that Kimi Work (the AI assistant) uses when a user requests comprehensive research. It is NOT a frontend feature but an **agent capability** that can be triggered from the UI.

**Trigger points in the UI:**

1. **"Comprehensive Research" mode:** When the user selects a new research mode (e.g., `mode: "comprehensive"`), the frontend sends a flag to the backend. The backend agent (or a separate worker) invokes the `deep-research-swarm` skill with the user's query.

2. **From Notes:** A "Research This Topic" button on a note. Sends the note title + content to the agent, which runs the deep-research-swarm skill and appends findings to the note.

3. **From Documents:** A "Research Gaps" button after OpenKB query. Identifies gaps in the wiki and triggers the swarm to fill them.

**Workflow integration:**
```
User clicks "Comprehensive Research" in frontend
  │
  ▼ REST POST /research/comprehensive
Backend receives request with {query, workspace_id, model, depth}
  │
  ▼ (Async/Background Task)
Agent invokes deep-research-swarm skill:
  - Phase 0: Route classification (A/B/C/D)
  - Phase 1: Landscape scan (5 searches)
  - Phase 1W: Wide exploration (5-8 facet agents if Route A)
  - Phase 2: Dimension decomposition (≥10 dimensions)
  - Phase 3: Parallel deep dive (1 agent per dimension, ≥20 searches each)
  - Phase 4: Cross-verification (confidence tiers + conflict zones)
  - Phase 5: Targeted validation (if conflicts)
  - Phase 6: Insight extraction (≥5 insights)
  - Phase 7: Handoff to writing skill (report-writing)
  │
  ▼ All files saved to outputs/{workspace_id}/research/
Backend stores research artifacts as a new "run" in research_runs
  │
  ▼ SSE or WebSocket
Frontend receives real-time progress updates
  │
  ▼ On completion
Frontend shows report + mindmap + knowledge graph
```

**Output directory:** `{workspace}/research/` (as per skill spec). For the Deep Research Agent, this maps to:
- `outputs/{workspace_id}/research/{topic}_dim{NN}.md`
- `outputs/{workspace_id}/research/{topic}_cross_verification.md`
- `outputs/{workspace_id}/research/{topic}_insight.md`
- `outputs/{workspace_id}/research/{topic}_wide{NN}.md` (if Route A)
- `outputs/{workspace_id}/research/{topic}_file_analysis.md` (if Route C/D)

**Key constraint:** The deep-research-swarm skill is designed for the **Kimi Work agent** to use, not for direct end-user interaction. The frontend exposes trigger points; the agent orchestrates the actual research.

### 7.2 Longread as Document Preprocessor

**How it integrates:** The `longread` skill is the **agent-level document preprocessor** used when a user uploads a very long document (especially PDFs > 20 pages) that needs analysis before OpenKB compilation.

**Trigger points:**

1. **Document upload:** When a user uploads a PDF > 20 pages (or any document the agent deems "too long"), the `longread` skill processes it in chunks before passing to OpenKB.

2. **From OpenKB:** When OpenKB's `pageindex_threshold` is exceeded, the longread skill can pre-summarize the document to help PageIndex's tree indexing.

**Workflow integration:**
```
User uploads large PDF (e.g., 100-page research paper)
  │
  ▼ REST POST /documents/upload
Backend receives file, saves to openkb/{workspace_id}/raw/
  │
  ▼ (Background Task)
Agent checks file size/page count
  │
  ▼ If > threshold (e.g., 20 pages)
Agent invokes longread skill:
  - Step 1: Split document into chunks (32k tokens each, 10% overlap)
  - Step 2: Launch reader sub-agents (3-5 per round, up to concurrency limit)
  - Step 3: Aggregate chunk summaries into unified summary
  │
  ▼ Save preprocessed summary
Summary saved alongside raw file for OpenKB reference
  │
  ▼ Run OpenKB compilation
`openkb add {file_path}` — OpenKB uses PageIndex for long docs
  │
  ▼ Status update
Frontend shows "Compiled" status
```

**Key constraint:** The longread skill is also an **agent capability**, not a user-facing feature. The user sees: upload → processing → compiled. The chunking and parallel reading happen behind the scenes.

**Note:** OpenKB already has **PageIndex** for long-document handling. The `longread` skill is complementary — it provides a pre-analysis summary that can be stored as a note or fed into the research pipeline. For OpenKB compilation, PageIndex handles the heavy lifting. For research context, longread provides structured summaries.

---

## 8. Implementation Roadmap

### Phase 0: Foundation (Week 1)

**Goal:** Prepare the codebase for the three-module architecture.

1. **Dependency overhaul:**
   - Remove Mantine + Tabler Icons
   - Install Tailwind CSS v3 + shadcn/ui + lucide-react
   - Upgrade React 18 → 19, TypeScript 5.6 → 5.9
   - Install react-router v7 (for module routing)

2. **Global styles:**
   - Create `index.css` with liquid-glass classes, custom scrollbar, dark theme
   - Create `tailwind.config.js` with design tokens
   - Create `lib/utils.ts` with `cn()` helper

3. **Layout shell:**
   - Rewrite `main.tsx` — remove MantineProvider, add module routing
   - Build `Layout` component: Header (44px) + Sidebar (240px) + Main + Background layer
   - Build `Header` with module switcher (Research | Notes | Documents)
   - Build `BackgroundRenderer` with lazy-loaded backgrounds
   - Build `BackgroundSwitcher` dropdown

4. **Backend prep:**
   - Add `notes` table to Supabase
   - Add `documents` table to Supabase
   - Create `openkb/` directory structure

**Output:** App renders with correct layout and visual design, but only Research module is functional. Notes and Documents are placeholders.

### Phase 1: Research Module Reskin (Week 2)

**Goal:** Port existing Deep Research Agent features to the new design system.

1. Reskin all existing components with liquid-glass + amber accents:
   - Query composer (hero panel)
   - Plan review panel
   - Research progress (SSE events)
   - Report view (Markdown in 672px container)
   - Citations view
   - Export panel
   - Mindmap view (G6 container)
   - Knowledge graph panels
   - GitNexus web view
   - Telemetry dashboard (bento cards)

2. Add "Save to Notes" button on report view

3. Update `api/client.ts` with new endpoints (notes, documents)

**Output:** Research module fully functional with new visual design.

### Phase 2: Notes Module (Week 3)

**Goal:** Build the full Moon Note notes app.

1. Backend:
   - Implement all `/notes` CRUD endpoints
   - Implement wiki link extraction (`extract_wiki_links`)
   - Implement backlink finder (`find_backlinks`)
   - Implement full-text search (`/notes/search`)

2. Frontend:
   - Build `NoteEditor` (title + textarea + edit/preview toggle)
   - Build `NoteList` (sidebar with search, select, manage mode)
   - Build `BacklinksPanel` (outgoing + incoming links)
   - Build `GraphView` (D3 force-directed graph)
   - Implement wiki link syntax `[[Title]]` with click handlers
   - Implement auto-save (400ms debounce)
   - Implement `Ctrl/Cmd+S` shortcut
   - Implement starter notes seeding

3. Integration:
   - Connect note CRUD to Supabase via `api/client.ts`
   - Link research runs to notes (`[[run:uuid]]`)

**Output:** Notes module fully functional with wiki links, backlinks, D3 graph.

### Phase 3: Documents Module (Week 4)

**Goal:** Integrate OpenKB for document analysis.

1. Backend:
   - Implement `/documents/upload` (multipart, save to `openkb/{workspace_id}/raw/`)
   - Implement `/documents` (list)
   - Implement `/documents/{id}/delete`
   - Implement `/documents/query` (shell out to `openkb query`)
   - Implement `/documents/chat` (session management + `openkb chat`)
   - Implement `/documents/wiki` (list wiki pages)
   - Implement `/documents/wiki/{path}` (get wiki page content)
   - Implement `/documents/status` (OpenKB stats)
   - Implement `/documents/skills` (skill factory)
   - Build OpenKB shell-out utility (`research_engine/utils/openkb.py`)

2. Frontend:
   - Build `UploadPanel` (drag-and-drop)
   - Build `DocumentList` (with status, actions)
   - Build `QueryPanel` (question input + results)
   - Build `ChatPanel` (chat interface + sessions)
   - Build `WikiBrowser` (tree view + content renderer)
   - Build `SkillFactory` (form + preview + download)
   - Build `OpenKBStatus` (dashboard cards)

3. Integration:
   - Auto-compile documents after upload
   - Show real-time status updates
   - "Save to Notes" on query/chat results
   - Wiki links in notes (`[[wiki:Concept]]`, `[[doc:filename]]`)

**Output:** Documents module fully functional with OpenKB integration.

### Phase 4: Cross-Module Polish (Week 5)

**Goal:** Wire everything together.

1. Cross-module navigation:
   - Universal wiki link handler (`[[Note]]`, `[[run:uuid]]`, `[[doc:file]]`, `[[wiki:Concept]]`)
   - Module switcher remembers last view per module
   - Deep links (URL routing): `/research`, `/notes`, `/notes/:id`, `/documents`, `/documents/wiki/:path`

2. Polish:
   - All hover states (150ms transitions)
   - Custom scrollbar on all panels
   - Responsive mobile layout (collapsible sidebar)
   - Loading skeletons
   - Error boundaries
   - Empty states
   - Keyboard shortcuts

3. Performance:
   - Lazy-load backgrounds
   - Code-split modules (React.lazy + Suspense)
   - Debounce search inputs
   - Virtualize long lists (runs, notes, documents)

4. Testing:
   - Backend: pytest all new endpoints
   - Frontend: build succeeds, type-check passes
   - E2E: smoke test all three modules

**Output:** Fully integrated, polished three-module application.

### Phase 5: Agent Skill Integration (Ongoing / Week 6)

**Goal:** Integrate agent-level skills.

1. **Deep-research-swarm trigger:**
   - Add "Comprehensive Research" mode to query composer
   - Backend worker that invokes the skill with workspace context
   - Store swarm outputs as a special research run type
   - Frontend shows swarm progress differently (dimension-based)

2. **Longread trigger:**
   - Auto-detect long documents on upload
   - Background task: split → read chunks → aggregate → save summary
   - Summary shown in document metadata
   - Option to "Include in OpenKB" or "Save as Note"

**Output:** Agent skills seamlessly integrated behind the UI.

### Total Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 0: Foundation | 1 week | Layout shell + visual design + backend prep |
| Phase 1: Research Reskin | 1 week | Research module fully functional, new design |
| Phase 2: Notes Module | 1 week | Notes module fully functional |
| Phase 3: Documents Module | 1 week | Documents module with OpenKB |
| Phase 4: Cross-Module Polish | 1 week | Integrated, polished, tested |
| Phase 5: Agent Skills | 1 week | Agent skill triggers integrated |
| **Total** | **5–6 weeks** | Single developer, full-time |

With AI-assisted development: **3–4 weeks**.

---

## 9. Risks & Mitigations

| Risk | Severity | Impact | Mitigation |
|------|----------|--------|------------|
| **OpenKB CLI dependency** | High | Requires `openkb` pip package installed on backend host; subprocess calls are brittle | Wrap in retry logic; validate `openkb` availability at startup; provide clear error messages; consider Dockerizing OpenKB as a sidecar service |
| **File storage scaling** | Medium | OpenKB wiki files grow per workspace; disk space management | Implement cleanup policies (auto-delete old raw files?); use object storage (S3/R2) for raw files; compress old wiki revisions |
| **Supabase auth limits** | Medium | Free tier row limits; concurrent connections | Monitor usage; implement pagination; consider self-hosted PostgreSQL if scaling |
| **WebGL backgrounds performance** | Medium | GPU-intensive; may drain battery on laptops; mobile performance | Lazy-load; provide "Solid Color" fallback; detect low-power mode; disable on mobile |
| **Full frontend rewrite scope** | High | 5-week estimate assumes focused execution; scope creep is real | Strict phase-by-phase delivery; each phase is a working milestone; defer nice-to-have features |
| **D3 + G6 coexistence** | Low | Notes use D3; Research uses G6; two graph libraries in bundle | Tree-shake unused code; D3 is only loaded in Notes module; G6 only in Research module |
| **Wiki link syntax conflicts** | Medium | `[[Title]]` in notes vs. `[[run:uuid]]` vs. `[[wiki:Concept]]` | Use prefix protocols (`wiki:`, `run:`, `doc:`) for cross-module; plain `[[Title]]` is notes-only; parser handles all cases |
| **OpenKB pageindex cloud cost** | Low | Optional cloud features have API costs | Default to local PageIndex; make cloud opt-in with API key; document cost implications |
| **Long document processing time** | Medium | OpenKB compilation of 100-page PDFs takes minutes | Run async (background task); show progress in UI; allow user to continue working; cache results |
| **Multi-module state management** | Low | Complex state: active module, selected item per module, workspace, background | Use React Context + URL routing; each module has its own state slice; persist to localStorage |
| **Browser compatibility** | Low | `backdrop-filter` not supported in older browsers; WebGL support varies | Add `-webkit-backdrop-filter` fallback; detect WebGL and show "Solid Color" if unavailable; support Chrome 88+, Firefox 78+, Safari 14+ |
| **deep-research-swarm skill runtime** | High | The skill is designed for the agent to use, not the backend; integrating it requires careful orchestration | The skill runs within the Kimi Work agent context, not the FastAPI backend. The backend triggers the agent via a separate mechanism (e.g., webhook, message queue, or a separate agent worker process). This is a deployment architecture decision, not a code issue. |
| **Workspace data isolation** | Medium | OpenKB stores files per workspace; need to ensure no cross-workspace leakage | Strict path validation: `openkb/{workspace_id}/`; validate workspace membership before every file access; never use user-provided paths directly |

---

## 10. Success Criteria

### 10.1 Functional Criteria

| # | Criterion | Module | How Verified |
|---|-----------|--------|-------------|
| 1 | User can create, edit, preview, delete, and search notes | Notes | Manual test + automated API tests |
| 2 | Wiki links `[[Title]]` work: click navigates to note or creates new | Notes | Manual test |
| 3 | Backlinks panel shows outgoing and incoming links | Notes | Manual test |
| 4 | D3 graph renders all notes with connections; hover/zoom works | Notes | Visual inspection |
| 5 | User can upload PDF, Word, and other documents | Documents | Manual test |
| 6 | OpenKB auto-compiles uploaded documents into wiki | Documents | Check `wiki/` directory |
| 7 | User can query the wiki and receive grounded answers with citations | Documents | Manual test |
| 8 | User can chat interactively with the wiki | Documents | Manual test |
| 9 | Wiki browser shows all pages (summaries, concepts, entities) | Documents | Visual inspection |
| 10 | User can generate skills from the wiki | Documents | Manual test + validate output |
| 11 | Research module retains all existing features | Research | Run existing E2E tests |
| 12 | Research report can be saved as a note | Research → Notes | Manual test |
| 13 | OpenKB query results can be saved as a note | Documents → Notes | Manual test |
| 14 | All three modules share the same visual design | All | Visual inspection |
| 15 | Module switcher works seamlessly | All | Manual test |
| 16 | Workspace selector works across all modules | All | Manual test |
| 17 | All data is workspace-scoped | All | API tests verify isolation |

### 10.2 Visual Criteria

| # | Criterion | How Verified |
|---|-----------|-------------|
| 18 | Base background is `#000000` (pure black) | Color picker |
| 19 | Accent color is `#c8956c` (warm amber) | Visual inspection |
| 20 | All panels use liquid-glass CSS | Visual inspection |
| 21 | Custom 4px scrollbar on all panels | Visual inspection |
| 22 | 4 procedural backgrounds can be switched | Manual test |
| 23 | Hover states use 150ms transitions | DevTools timing |
| 24 | Layout matches 3-zone spec (44px header, 240px sidebar) | DevTools measurement |
| 25 | No Mantine dependencies in bundle | `npm ls @mantine/core` fails |

### 10.3 Performance Criteria

| # | Criterion | Target |
|---|-----------|--------|
| 26 | Initial page load < 3s | Lighthouse |
| 27 | Background lazy-load doesn't block initial render | DevTools performance |
| 28 | Note auto-save debounce is 400ms | DevTools timing |
| 29 | D3 graph renders < 100 notes smoothly | Manual test with 100 notes |
| 30 | OpenKB compilation of 50-page PDF completes < 5 minutes | Manual test |

---

## 11. Appendix: Source References

### 11.1 Files Reviewed for This Analysis

**Design System:**
| File | Lines | Content |
|------|-------|---------|
| `frontend/design.md` | 607 | Full Moon Note design specification |

**Existing Frontend:**
| File | Lines | Content |
|------|-------|---------|
| `frontend/src/App.tsx` | 946 | Main app component with state machine |
| `frontend/src/api/client.ts` | 503 | Fetch-based API client |
| `frontend/src/types/api.ts` | 372 | TypeScript type definitions |
| `frontend/src/main.tsx` | 18 | App entry point |
| `frontend/src/styles/theme.ts` | 28 | Mantine theme configuration |

**Existing Backend:**
| File | Lines | Content |
|------|-------|---------|
| `research_engine/api.py` | 1,634 | FastAPI server with all endpoints |
| `research_engine/models.py` | 473 | Pydantic data models |
| `research_engine/auth.py` | — | Supabase JWT verification |
| `research_engine/config.py` | — | Configuration singleton |
| `research_engine/agent/orchestrator.py` | — | Research orchestration |
| `research_engine/agent/planner.py` | — | Plan generation |
| `research_engine/output/storage.py` | — | File-based storage |
| `research_engine/output/mindmap.py` | — | G6 mindmap generation |
| `research_engine/knowledge_graph/` | — | Graphify KG builder |
| `research_engine/sources/web_scraper.py` | — | Scrapling-based scraping |
| `research_engine/sources/web_search.py` | — | Search provider abstraction |
| `research_engine/llm/provider.py` | — | OpenRouter LLM gateway |

**Skills:**
| File | Lines | Content |
|------|-------|---------|
| `deep-research-swarm/SKILL.md` | 513 | Multi-agent research orchestration workflow |
| `longread/SKILL.md` | 106 | Chunk-based parallel document reading |

**External Sources:**
| Source | URL | Content |
|--------|-----|---------|
| OpenKB GitHub | `https://github.com/VectifyAI/OpenKB` | Open-source document-to-wiki system |
| OpenKB README | Fetched via `kimi_fetch_v2` | Full feature list, commands, architecture |

### 11.2 Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| **Keep FastAPI, not Hono** | FastAPI is mature, feature-complete, and all research endpoints work. No user-facing benefit from switching. |
| **Keep Supabase, not MySQL** | Supabase provides auth, database, and storage in one service. Migration would be high-risk. |
| **Keep Supabase JWT, not Kimi OAuth** | Supabase auth is already working with workspace membership. Kimi OAuth is domain-specific to Moon Note's deployment. |
| **Keep fetch API client, not tRPC** | The existing fetch client is fully functional. tRPC adds complexity without benefit for a visual refactor. |
| **Shell out to OpenKB CLI, not library** | OpenKB is primarily a CLI tool. Shelling out is the natural integration pattern. Can be wrapped in a service later. |
| **File-based OpenKB storage, not DB** | OpenKB's native format is files. Forcing into DB would break OpenKB compatibility. Use workspace-scoped subdirectories. |
| **Agent skills run in background, not sync** | deep-research-swarm and longread are computationally intensive. They must run asynchronously. The UI triggers and polls. |
| **Unified wiki link syntax with prefixes** | `[[Title]]` for notes, `[[run:uuid]]` for research, `[[doc:file]]` for documents, `[[wiki:Concept]]` for OpenKB. One parser handles all. |
| **D3 for notes graph, G6 for research mindmap** | D3 is specified in design.md for the notes graph. G6 is already working for research mindmaps. Both are retained. |
| **Workspace-scoped everything** | Research runs, notes, and documents all belong to workspaces. This ensures data isolation and multi-tenancy. |

---

*Document generated from comprehensive analysis of 5 subsystems, 12 source files, and 1 external project. All technical claims are traceable to the sources listed in Section 11.*
