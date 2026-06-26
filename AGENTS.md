# AGENTS.md — Deep Research Agent

> **Project:** Deep Research Agent (DRA)  
> **Repository:** `D:\Projects\ai-ml\DeepResearchAgent`  
> **Indexed by GitNexus:** `deepresearchagent` (3891 symbols, 10587 relationships, 167 execution flows)  
> **Last updated:** 2025-06-21

---

## 1. Project Overview

DRA is a multi-module research platform with three primary modules:

| Module | Purpose | Key Features |
|--------|---------|-------------|
| **Research** | Deep web research with iterative search & synthesis | SSE streaming, plan review, mindmap (G6), citations, export (JSON/Markdown/PDF/Notes), knowledge graph |
| **Notes** | Personal knowledge base with wiki-style linking | Wiki links `[[Title]]`, backlinks, D3 force-directed graph, auto-save (400ms), 12 LLM starter notes, moon phase widget |
| **Documents** | OpenKB-powered document ingestion & Q&A | Upload, query (PostgreSQL full-text), multi-turn chat, wiki browser, skill factory (validate/eval/rollback), status dashboard, Obsidian ZIP export |

All data is **workspace-scoped** via `workspace_id` foreign key. Authentication is Supabase JWT with `workspace_members` table.

---

## 2. Tech Stack

### 2.1 Backend

| Layer | Technology | Version/Notes |
|-------|-----------|-------------|
| Runtime | Python | 3.11 |
| Framework | FastAPI | — |
| Validation | Pydantic | v2 |
| Database | PostgreSQL (Supabase) | With `tsvector` full-text search |
| Auth | Supabase JWT | `verify_supabase_jwt` dependency |
| Storage | Supabase Storage + local filesystem (`openkb/{workspace_id}/`) | — |
| Scraping | Scrapling (Camoufox → Playwright → Basic HTTP) | 3-tier fallback |
| LLM Gateway | OpenRouter via `langchain-openai` `ChatOpenAI` | Custom `base_url` |
| Search | DuckDuckGo (default), GitHub API | — |
| Knowledge Base | OpenKB (workspace-local) | `research_engine/utils/openkb.py` |
| Knowledge Graph | Graphify (subprocess) + LLM fallback | `research_engine/knowledge_graph/` |
| Background Jobs | FastAPI `BackgroundTasks` (webhook worker only) | `worker.py` |
| Webhook Worker | Separate FastAPI app (`worker.py`) | HMAC-verified, async research execution |

### 2.2 Frontend

| Layer | Technology | Version/Notes |
|-------|-----------|-------------|
| Framework | React | 19.2.0 |
| Language | TypeScript | 5.9.3 |
| Build Tool | Vite | 8.0.4 (default config, no `vite.config.ts`) |
| Styling | Tailwind CSS | v3.4.19 |
| UI Primitives | Radix UI | Mixed: `@radix-ui/react-*` v1.x and v2.x (e.g., `dropdown-menu` @ 2.1.0, `separator` @ 1.1.0) |
| Utility Libs | `class-variance-authority`, `clsx`, `tailwind-merge` | Used for `cn()` utility |
| Icons | Lucide React | 0.562.0 |
| State | React hooks + `localStorage` | No external state library |
| Routing | React Router | v7.6.1 |
| Markdown | `react-markdown` + `remark-gfm` | 10.1.0 / 4.0.1 |
| Graph Visualization | D3 (force-directed notes graph) + AntV G6 v5 (mindmap) | 7.9.0 / 5.1.0 |
| Auth | Supabase JS Client | 2.108.2 |
| Type Definitions | `@types/d3` | 7.4.3 |

### 2.3 Styling System

- **Background:** `#000000` (pure black)
- **Primary accent:** `#c8956c` (amber) — HSL `26 36% 60%`
- **Text:** `#e0e0e0` (off-white)
- **Borders:** `rgba(255,255,255,0.06)` — `rgba(255,255,255,0.12)`
- **Liquid glass:** `liquid-glass` class — `backdrop-filter: blur(6px) saturate(140%)` with pseudo-element light refraction (`::before` gradient border, `::after` specular highlights)
- **Liquid glass strong:** `liquid-glass-strong` — `blur(40px) saturate(150%)` for modals/panels
- **Custom scrollbar:** 4px thin, `rgba(255,255,255,0.08)` thumb, transparent track
- **Font:** System stack (`-apple-system`, `Segoe UI`, etc.) + `Fira Sans` (weights 300-700) + `Fira Code` (monospace)
- **CSS variables:** HSL-based theming in `:root` for `background`, `foreground`, `primary`, `secondary`, `muted`, `accent`, `destructive`, `border`, `input`, `ring`, `radius`

> **Note on PostCSS:** The project uses `postcss.config.js` (ESM, active config) with `tailwindcss` and `autoprefixer`. A legacy `postcss.config.cjs` containing `postcss-preset-mantine` and `postcss-simple-vars` exists but is **not the active config**. Do not install Mantine.

---

## 3. Critical Rules

### 3.1 Backend I/O

**All backend I/O must be async.** Use `await` for:
- LLM calls (`ainvoke` on LangChain chains)
- Scrapling fetches (`async_fetch` on all Fetcher tiers)
- File I/O (`aiofiles` in `knowledge_graph/`, `pathlib` elsewhere)
- Database queries: The Supabase client is **sync** — wrap in `asyncio.to_thread()` (used 57× in `api.py`)

**Never use blocking calls** (`requests`, `urllib`, `time.sleep`) in the FastAPI event loop.

### 3.2 Model Selection

Model IDs are **runtime parameters**, not hardcoded. The LLM is selected per-request via:
- API body: `model` field (e.g., `openrouter/deepseek/deepseek-chat`, `groq/llama-3.1-70b`)
- CLI flag: `--model`
- Config default: `config.toml` under `[llm]`

Code must **never assume a specific model**. Use `LLMProvider._get_llm(model=...)` pattern.

### 3.3 Scraping Layer

**Scrapling is the sole scraping layer.** Do NOT add `requests`, `httpx`, `urllib3`, or other scraping libraries. All web content fetching goes through `sources/web_scraper.py` which uses Scrapling's tiered fallback:

| Tier | Class | Use Case | Fallback Trigger |
|------|-------|----------|------------------|
| 1 | `StealthyFetcher.async_fetch()` | Camoufox — handles Cloudflare, bot detection | Binary missing or fetch fails |
| 2 | `DynamicFetcher.async_fetch()` | Playwright — JS rendering | Browser not installed or fetch fails |
| 3 | `Fetcher.async_fetch()` | Basic HTTP — static pages | Always available |

### 3.4 Secrets Management

**Never commit secrets.** API keys live in:
- `config.toml` (git-ignored) — development defaults
- Environment variables — production overrides
- `config.example.toml` — placeholder values only, checked into git

### 3.5 Data Models as Source of Truth

**Pydantic models in `research_engine/models.py` are the source of truth.** All data structures are defined there. Frontend TypeScript types in `frontend/src/types/api.ts` must mirror these exactly.

**When modifying a model:**
1. Update `research_engine/models.py` (Pydantic v2 syntax)
2. Update `frontend/src/types/api.ts` (TypeScript interfaces)
3. Update `frontend/src/api/client.ts` if API shape changes
4. Run `npm run build` in `frontend/` to verify type parity

### 3.6 Frontend Component Architecture

- **Use Tailwind CSS utility classes** for all styling. No custom CSS files unless global (go in `index.css`).
- **Use Radix UI primitives** for accessibility-critical components (dialogs, dropdowns, tabs, tooltips, sliders, progress bars, accordions, scroll areas, separators).
- **Use `lucide-react` for all icons.** No emojis, no SVG icons, no custom icon sets.
- **Use `liquid-glass` class** for all panel/card containers. This is the project's visual identity.
- **All buttons must be `<button>` elements** with `cursor-pointer`, `bg-transparent`, and `border-none` where needed. Never use `<div>` for clickable elements.
- **Error boundaries:** Wrap all modules with `ErrorBoundary` (class-based, in `components/ErrorBoundary.tsx`).
- **Module code-splitting:** All route modules use `React.lazy()` + `Suspense` with `LoadingFallback`.
- **Components are organized by domain in `frontend/src/components/`**, not inside `modules/`. Each module file (`ResearchModule.tsx`, etc.) is a thin container that composes shared components.

### 3.7 Wiki Link Syntax

The Notes and Documents modules share a wiki-link syntax for cross-referencing. Parsed by `research_engine/utils/wiki_links.py` (`WIKI_LINK_RE = re.compile(r'\[\[([^\]]+)\]\]')`).

| Syntax | Type | Target | Example |
|--------|------|--------|---------|
| `[[Note Title]]` | `note` | Note title | `[[Project Architecture]]` |
| `[[run:uuid]]` | `run` | Research run ID | `[[run:abc-123]]` |
| `[[doc:filename]]` | `doc` | Document filename (not ID) | `[[doc:report.pdf]]` |
| `[[wiki:Concept]]` | `wiki` | Wiki page concept | `[[wiki:Machine Learning]]` |
| `[[entity:Name]]` | `entity` | Named entity | `[[entity:OpenAI]]` |

> **Note:** `entity:` is documented in `wiki_links.py` but **not yet implemented** in frontend `handleWikiNavigate` handlers. Only `note`, `run`, `doc`, and `wiki` have active handlers.

---

## 4. Architecture Decisions (Do Not Reverse)

| Decision | Rationale |
|----------|-----------|
| **DRE is re-implemented, not vendored** | Original repo has no package distribution and is coupled to Gemini + Tavily. Our implementation is in `research_engine/agent/`. |
| **Exhaustive depth (5) is the default** | Up to 30 research cycles. Do not lower without user consent. |
| **OpenRouter is the LLM gateway** | All models accessed via `https://openrouter.ai/api/v1` using `langchain-openai`'s `ChatOpenAI` with custom `base_url`. |
| **Structured output has a fallback** | Free models may not support JSON schema mode. Always try `with_structured_output()` first, then fall back to raw completion + Pydantic `model_validate_json()`. |
| **Workspace-scoped data** | All tables have `workspace_id` FK. No global data. All endpoints require `workspace_id`. |
| **OpenKB is workspace-local** | Each workspace gets its own directory at `openkb/{workspace_id}/`. No shared global KB. |
| **Frontend components are domain-organized in `components/`**, not in `modules/` | Each module file (`ResearchModule.tsx`, `NotesModule.tsx`, `DocumentsModule.tsx`) is a thin container composing shared components. This avoids duplication and enables cross-module reuse. |
| **React Router v7 with `useSearchParams`** | Module-internal navigation (tab selection, note selection) uses URL query params for persistence and cross-module linking. |
| **D3 for Notes graph, G6 for Research mindmap** | D3 provides force-directed layout for backlinks. G6 v5 provides hierarchical mindmap layout. Do not swap these. |
| **Knowledge Graph via Graphify subprocess** | `knowledge_graph/builder.py` runs `graphify` CLI on exported corpus. Falls back to LLM-based graph if Graphify is not installed. |
| **Webhook worker is separate** | `worker.py` is a standalone FastAPI app for HMAC-verified webhook triggers. It uses `BackgroundTasks`. The main `api.py` does not. |

---

## 5. Module Structure

> **Important:** Components are NOT inside `modules/*/components/`. They live in `frontend/src/components/` organized by domain. Each module file is a thin container.

### 5.1 Research Module (`frontend/src/modules/research/ResearchModule.tsx`)

Thin container composing these shared components:

```
frontend/src/components/
├── views/
│   ├── ReportView.tsx          # Markdown report + tabs (Citations, Export)
│   ├── CitationsView.tsx       # Citation list with source links
│   ├── ExportPanel.tsx         # Export format selector (Markdown, PDF, JSON, etc.)
│   ├── MindmapView.tsx         # G6 mindmap container
│   ├── PlanReview.tsx          # Interactive plan approval/editing
│   ├── ResearchProgress.tsx    # SSE event stream display (search, scrape, validate phases)
│   └── ResearchProgress.tsx    # Real-time progress with per-phase detail
├── mindmap/
│   ├── G6MindmapGraph.tsx      # G6 v5 mindmap implementation
│   └── NodeDetailsPanel.tsx    # Drill-down panel for mindmap nodes
├── runs/
│   └── RunList.tsx             # Virtualized run list sidebar
├── landing/
│   └── TerminalDemo.tsx        # Landing page terminal animation
├── code-arch/
│   └── GitNexusWebView.tsx     # Code architecture visualization
└── knowledge-graph/
    ├── KnowledgeGraphView.tsx  # Knowledge graph visualization
    ├── KGQueryPanel.tsx        # KG query interface
    ├── KGStatsPanel.tsx        # KG statistics display
    └── CommunityLegend.tsx     # Community detection legend
```

**Data flow:**
1. User submits query → `POST /research/comprehensive` (async, returns `run_id`)
2. Frontend connects to `POST /research/stream` (SSE, body: `{run_id}`)
3. Backend: `classify_intent` → `plan` → `decompose` → `search` → `scrape` → `validate` → `synthesize` → `mindmap`
4. Each phase emits SSE event → frontend updates `progress` + `status`
5. Final report saved to DB → `report` field contains Markdown
6. Mindmap saved to `knowledge_graph` table
7. Knowledge graph built via `knowledge_graph/builder.py` (Graphify subprocess or LLM fallback)

### 5.2 Notes Module (`frontend/src/modules/notes/NotesModule.tsx`)

Thin container composing these shared components:

```
frontend/src/components/notes/
├── MarkdownPreview.tsx         # Renders markdown + wiki links
├── NoteGraph.tsx               # D3 force-directed graph (lazy-loaded, ~66KB chunk)
└── MoonPhaseWidget.tsx         # Canvas moon phase renderer (sidebar)
```

**Data flow:**
1. Create/edit note → `POST /notes` or `PATCH /notes/{id}`
2. Auto-save: 400ms debounce + Ctrl+S keyboard shortcut
3. Wiki links parsed on render: `[[Title]]` → clickable `<button>`
4. Backlinks fetched from `GET /notes/{id}/backlinks`
5. Graph: `GET /notes/graph` returns nodes + edges for D3
6. Cross-module: "Research" button (Sparkles icon) → `POST /research/comprehensive` with note title

### 5.3 Documents Module (`frontend/src/modules/documents/DocumentsModule.tsx`)

Thin container reusing `MarkdownPreview` from `components/notes/`.

**Data flow:**
1. Upload → `POST /documents/upload` → OpenKB ingestion
2. Query → `POST /documents/query` → PostgreSQL `tsvector` full-text search with websearch fallback
3. Chat → `POST /documents/chat` → multi-turn with `session_id` persistence (in-memory, not persisted across server restarts)
4. Wiki → `GET /documents/wiki` → browse generated pages
5. Skills → `POST /documents/skills` → generate from wiki
6. Stats → `GET /documents/stats` → OpenKB metrics
7. Cross-module: "Research Gaps" button → `POST /research/comprehensive` with gap query
8. Cross-module: "Open in Obsidian" → `GET /documents/wiki/download` (ZIP of entire wiki)

---

## 6. Common Patterns

### 6.1 Adding a New Search Provider

1. Create a class implementing `SearchProvider` protocol in `sources/web_search.py`
2. Add it to the `get_search_provider()` factory
3. Add its config key to `config.example.toml` under `[search]`
4. Update `ResearchRequest` model in `models.py` and `types/api.ts`

### 6.2 Adding a New Prompt

1. Add the template string to `llm/prompts.py`
2. If it requires structured output, define the Pydantic model in `models.py`
3. Call it via `llm_provider.call_structured(prompt, schema, model=model)`
4. Update frontend types if the response shape changes

### 6.3 Adding a New API Endpoint

1. Add the route in `research_engine/api.py` with proper `verify_supabase_jwt` dependency
2. Call `verify_workspace_membership()` manually inside the route handler (it is NOT a FastAPI dependency — it is a regular async function called inline)
3. Add the corresponding async function in `frontend/src/api/client.ts`
4. Add the return type to both `models.py` and `types/api.ts`
5. Add the frontend UI in the relevant module (composing shared components from `frontend/src/components/`)
6. Run `py -m py_compile research_engine/api.py` to verify syntax
7. Run `npm run build` in `frontend/` to verify TypeScript

### 6.4 Adding a New Frontend Component

1. Place in `frontend/src/components/{domain}/` (e.g., `notes/`, `runs/`, `layout/`, `views/`)
2. Use Tailwind CSS for styling. No custom CSS files unless global (go in `index.css`)
3. Use `liquid-glass` class for containers
4. Use `lucide-react` icons exclusively
5. Export as default or named export (consistent with existing files)
6. If >100KB or rarely used, lazy-load with `React.lazy()` + `Suspense`
7. Add to the relevant module container (`ResearchModule.tsx`, `NotesModule.tsx`, or `DocumentsModule.tsx`)

### 6.5 Adding a New Database Column

1. Add column to Supabase table via migration or dashboard
2. Update `models.py` Pydantic model
3. Update `frontend/src/types/api.ts` TypeScript type
4. Update queries in `research_engine/db/supabase/` or `api.py`
5. Update frontend components that display/edit the field

---

## 7. File Organization

```
DeepResearchAgent/
├── AGENTS.md                          # This file
├── config.toml                        # Secrets (git-ignored)
├── config.example.toml                # Template (checked in)
├── full-scope-integration-plan.md     # Architecture roadmap
├── frontend/design.md                 # Frontend design system (NOT at root)
├── research/
│   └── browsery-tools-analysis.md     # External research artifacts
├── research_engine/                   # Backend
│   ├── api.py                         # FastAPI routes (all endpoints, 2699 lines)
│   ├── auth.py                        # JWT verification + workspace membership
│   ├── cli.py                         # CLI entry point
│   ├── config.py                      # Configuration loader
│   ├── models.py                      # Pydantic v2 models (SOURCE OF TRUTH)
│   ├── worker.py                      # Webhook worker (BackgroundTasks, separate app)
│   ├── setup_shims.py                 # Compatibility shims
│   ├── agent/                         # DRE implementation (orchestrator, prompts, strategies)
│   ├── db/
│   │   └── supabase/                  # Supabase client + migrations
│   │       ├── client.py              # Sync client singleton (wrapped in asyncio.to_thread)
│   │       └── migrations/            # SQL migrations (2 files: init schema + notes/docs)
│   ├── llm/
│   │   ├── provider.py                # LLMProvider (OpenRouter gateway)
│   │   └── prompts.py                 # All prompt templates
│   ├── sources/
│   │   ├── web_scraper.py             # Scrapling 3-tier fallback
│   │   ├── web_search.py              # Search providers (DuckDuckGo, etc.)
│   │   ├── github_search.py           # GitHub API search
│   │   ├── reranker.py               # Result reranking
│   │   ├── cache.py                  # Response caching
│   │   └── circuit_breaker.py        # Failure circuit breaker
│   ├── knowledge_graph/               # Graphify + LLM fallback KG builder
│   │   ├── builder.py                 # Graphify subprocess builder (uses aiofiles)
│   │   ├── enricher.py                # KG enrichment (uses aiofiles)
│   │   ├── gitnexus_bridge.py         # GitNexus integration
│   │   └── mcp_bridge.py             # MCP (Model Context Protocol) bridge
│   ├── output/                        # Report output formatting
│   │   ├── exporter.py                # Export logic (JSON, Markdown, etc.)
│   │   ├── formatter.py               # Report formatting
│   │   ├── mindmap.py                 # Mindmap generation
│   │   └── storage.py                 # Output storage
│   └── utils/
│       ├── openkb.py                  # OpenKB operations (CRUD, query, stats, validate/eval/rollback)
│       └── wiki_links.py              # Wiki link parsing ([[Title]], [[run:uuid]], etc.)
├── frontend/                          # Frontend
│   ├── index.html
│   ├── postcss.config.js              # ACTIVE config (Tailwind + autoprefixer, ESM)
│   ├── postcss.config.cjs             # LEGACY config (mantine entries, NOT active)
│   ├── tailwind.config.js             # Tailwind config (dark mode, content paths, theme)
│   ├── src/
│   │   ├── main.tsx                   # Entry point (React Router)
│   │   ├── App.tsx                    # Route definition + lazy loading + Suspense
│   │   ├── index.css                  # Global styles (liquid glass, scrollbar, fonts, HSL vars)
│   │   ├── api/
│   │   │   └── client.ts              # All API calls (frontend SOURCE OF TRUTH)
│   │   ├── types/
│   │   │   └── api.ts                 # TypeScript types (mirror of models.py)
│   │   ├── modules/                   # Thin module containers (compose shared components)
│   │   │   ├── research/
│   │   │   │   └── ResearchModule.tsx
│   │   │   ├── notes/
│   │   │   │   └── NotesModule.tsx
│   │   │   └── documents/
│   │   │       └── DocumentsModule.tsx
│   │   ├── components/                # Shared components organized by domain
│   │   │   ├── Auth/                  # AuthModal, WorkspaceSelector
│   │   │   ├── backgrounds/           # 4 GPU backgrounds + renderer + switcher
│   │   │   │   ├── BackgroundRenderer.tsx
│   │   │   │   ├── BackgroundSwitcher.tsx
│   │   │   │   ├── FlowField.tsx
│   │   │   │   ├── MoonlitRipple.tsx
│   │   │   │   ├── RainOnGlass.tsx
│   │   │   │   └── SolidBackground.tsx
│   │   │   ├── code-arch/             # GitNexusWebView.tsx
│   │   │   ├── knowledge-graph/       # KG visualization components
│   │   │   │   ├── CommunityLegend.tsx
│   │   │   │   ├── KGQueryPanel.tsx
│   │   │   │   ├── KGStatsPanel.tsx
│   │   │   │   └── KnowledgeGraphView.tsx
│   │   │   ├── landing/               # TerminalDemo.tsx
│   │   │   ├── layout/                # Layout, Sidebar, Header
│   │   │   ├── mindmap/               # G6MindmapGraph.tsx, NodeDetailsPanel.tsx
│   │   │   ├── notes/                 # MarkdownPreview, NoteGraph, MoonPhaseWidget
│   │   │   ├── runs/                  # RunList.tsx
│   │   │   ├── ui/                    # EMPTY — shadcn placeholder (never used)
│   │   │   ├── views/                 # ReportView, CitationsView, ExportPanel, etc.
│   │   │   │   ├── CitationsView.tsx
│   │   │   │   ├── ExportPanel.tsx
│   │   │   │   ├── MindmapView.tsx
│   │   │   │   ├── PlanReview.tsx
│   │   │   │   ├── ReportView.tsx
│   │   │   │   └── ResearchProgress.tsx
│   │   │   ├── ErrorBoundary.tsx      # React error boundary (class-based)
│   │   │   └── LoadingSkeletons.tsx   # Skeleton loaders
│   │   ├── hooks/
│   │   │   ├── useBackground.tsx      # Background mode switching (4 modes: moonlit/silk/rain/solid)
│   │   │   └── useVirtualList.ts      # Fixed-height list virtualization
│   │   ├── lib/
│   │   │   ├── authContext.tsx        # Auth context + Supabase auth
│   │   │   ├── supabase.ts            # Supabase client singleton
│   │   │   └── utils.ts               # Utility functions (cn, etc.)
│   │   └── styles/                    # (empty directory)
│   └── dist/                          # Build output (Vite)
├── openkb/                            # Workspace-local knowledge bases
│   └── {workspace_id}/
│       ├── documents/                 # Uploaded files
│       ├── wiki/                      # Generated wiki pages
│       └── output/                    # Skills, summaries, etc.
├── tests/                             # Backend tests (pytest)
│   ├── benchmark_latency.py           # Latency benchmarking
│   ├── e2e/                           # End-to-end tests (5 test files + conftest)
│   │   ├── test_environment.py
│   │   ├── test_f1_auth.py
│   │   ├── test_f2_graph.py
│   │   ├── test_f3_webhook.py
│   │   ├── test_f4_realtime.py
│   │   └── test_scenarios.py
│   ├── test_auth.py
│   ├── test_boilerplate.py
│   ├── test_cache.py
│   ├── test_circuit_breaker.py
│   ├── test_config.py
│   ├── test_llm.py
│   ├── test_mindmap.py
│   ├── test_open_file.py
│   ├── test_research_pipeline.py
│   ├── test_resynthesize.py
│   ├── test_router.py
│   ├── test_scraper.py
│   ├── test_search.py
│   └── test_telemetry.py
├── graphify-out/                      # Graphify output directory (git-ignored)
├── docs/                              # Project documentation
├── .agents/                           # Agent configuration
├── .compound-engineering/             # Compound engineering artifacts
├── .vscode/                           # VS Code settings
└── .claude/skills/gitnexus/           # GitNexus code intelligence skills
```

---

## 8. Build & Testing

### 8.1 Backend

```bash
# Syntax check (always run before committing backend changes)
py -m py_compile research_engine/api.py
py -m py_compile research_engine/models.py

# Full backend tests
pytest tests/ -v --asyncio-mode=auto

# E2E tests
pytest tests/e2e/ -v

# Quick smoke test
py -m research_engine.cli "test query" --depth 1 --no-crossover

# Latency benchmark
py tests/benchmark_latency.py
```

### 8.2 Frontend

```bash
cd frontend

# Type check + build (always run before committing frontend changes)
npm run build

# Dev server
npm run dev

# Preview production build
npm run preview
```

**Build requirements on Windows:**
- Use `cmd.exe /c "cd /d ..."` or `"C:/Program Files/nodejs/npm.cmd" run --prefix "..." build`
- Git Bash path normalization: use `pwd -W` to get Windows paths. Convert `/c/...` → `C:\...`, `/d/...` → `D:\...`

---

## 9. Known Gotchas

| Issue | Mitigation |
|-------|-----------|
| **Camoufox binary missing** | Run `python -m camoufox fetch` after first install. Without it, `StealthyFetcher` falls back to `DynamicFetcher`. |
| **Playwright browsers missing** | Run `python -m playwright install chromium`. Without it, `DynamicFetcher` falls back to `Fetcher`. |
| **OpenRouter rate limits** | Free models have rate limits. `LLMProvider` has retry logic with exponential backoff. Exhaustive research (depth=5) may hit limits — add a small delay between cycles if needed. |
| **PostCSS dual config** | `postcss.config.js` (ESM) is the **active config** with `tailwindcss` + `autoprefixer`. `postcss.config.cjs` (CommonJS) contains legacy `postcss-preset-mantine` entries and is **ignored**. Do not install Mantine. |
| **G6 container sizing** | The G6 graph container div MUST have explicit width/height. If it's 0×0, the graph renders invisibly. |
| **D3 graph container** | Same as G6 — must have explicit dimensions. The graph is lazy-loaded as a separate chunk. |
| **Windows path issues** | Always use `pwd -W` in Git Bash. Never use `..` to access files outside the workspace. |
| **Supabase RLS policies** | All tables have RLS enabled. Ensure `workspace_members` relationships exist before querying workspace-scoped data. |
| **OpenKB chat sessions** | Chat sessions are stored in-memory (`_chat_sessions: dict[str, list[dict]] = {}` in `api.py`). Server restart clears session history. |
| **Skill rollback** | Rollback swaps the skill directory with a `.backup` directory. No backup exists until a second version is created. |
| **Virtual list item heights** | `useVirtualList` requires fixed item heights. If item heights vary, virtualization will drift. Use `min-height` to enforce consistency. |
| **Supabase client is sync** | The Supabase client (`db/supabase/client.py`) is synchronous. All DB calls in `api.py` use `asyncio.to_thread()` wrapping. Do not use `await` directly on Supabase methods. |
| **Graphify dependency** | Knowledge graph building requires `graphify` CLI installed. If missing, falls back to LLM-based graph generation (less rich). |
| **Wiki link `entity:` unimplemented** | `[[entity:Name]]` is parsed by `wiki_links.py` but has no frontend handler. Only `note`, `run`, `doc`, and `wiki` types are handled. |
| **\r\n line endings** | `api.py` and other files use Windows CRLF (`\r\n`) line endings. Unix-based tools may show `^M` characters. |

---

## 10. API Endpoint Reference

> **Note:** The docstring at the top of `api.py` is outdated. This table is the authoritative reference.

### Research

| Method | Path | Description |
|--------|------|-------------|
| POST | `/research` | Start research run |
| POST | `/research/comprehensive` | Deep research with comprehensive plan |
| POST | `/research/stream` | SSE stream for run progress (body: `{run_id}`) |
| POST | `/research/abort` | Abort active research run |
| GET | `/research/{run_id}/report` | Get completed report |
| POST | `/research/{run_id}/resynthesize` | Re-synthesize report with new parameters |

### Runs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/runs` | List all runs for workspace |
| GET | `/runs/{run_id}` | Get single run details |
| GET | `/runs/{run_id}/export/{fmt}` | Export run in format (json, md, pdf, etc.) |
| GET | `/runs/{run_id}/exports` | List available export formats |
| POST | `/runs/{run_id}/mindmap/expand` | Expand a mindmap node |
| POST | `/runs/{run_id}/knowledge-graph/similarity` | Find similar nodes in KG |
| GET | `/runs/{run_id}/knowledge-graph/available` | Check if KG is available for run |

### Notes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/notes` | List notes for workspace |
| POST | `/notes` | Create new note |
| GET | `/notes/{note_id}` | Get single note |
| PATCH | `/notes/{note_id}` | Update note |
| DELETE | `/notes/{note_id}` | Delete note |
| GET | `/notes/{note_id}/backlinks` | Get backlinks for note |
| GET | `/notes/search` | Search notes (full-text) |
| POST | `/notes/bulk-delete` | Bulk delete notes |
| POST | `/notes/seed` | Seed 12 starter notes |
| GET | `/notes/graph` | Get graph data (nodes + edges) |

### Documents

| Method | Path | Description |
|--------|------|-------------|
| GET | `/documents` | List documents for workspace |
| POST | `/documents/upload` | Upload document |
| GET | `/documents/{doc_id}` | Get document |
| DELETE | `/documents/{doc_id}` | Delete document |
| GET | `/documents/{doc_id}/download` | Download document file |
| POST | `/documents/{doc_id}/tags` | Update document tags (JSONB) |
| POST | `/documents/query` | Query documents (OpenKB + PostgreSQL) |
| POST | `/documents/chat` | Multi-turn chat with documents |
| GET | `/documents/chat/sessions` | List chat sessions |
| POST | `/documents/recompile` | Recompile all documents |
| GET | `/documents/wiki` | List wiki pages |
| GET | `/documents/wiki/{page}` | Get wiki page |
| GET | `/documents/wiki/download` | Download wiki as ZIP (Obsidian) |
| GET | `/documents/stats` | Get OpenKB statistics |
| POST | `/documents/skills` | Generate skill from wiki |
| GET | `/documents/skills` | List generated skills |
| GET | `/documents/skills/{name}/validate` | Validate skill schema |
| GET | `/documents/skills/{name}/eval` | Evaluate skill coverage |
| POST | `/documents/skills/{name}/rollback` | Rollback skill to previous version |

### System

| Method | Path | Description |
|--------|------|-------------|
| GET | `/models` | List available LLM models |
| GET | `/scraper/status` | Get scraper health status |
| POST | `/scraper/refresh-cache` | Refresh scraper cache |
| POST | `/open-file` | Open file in system default app |
| GET | `/api/telemetry` | Get system telemetry |
| GET | `/health` | Health check |
| POST | `/webhook/trigger` | Trigger webhook (HMAC-verified) |

### Workspaces

| Method | Path | Description |
|--------|------|-------------|
| GET | `/workspaces` | List user's workspaces |
| POST | `/workspaces` | Create workspace |

---

## 11. GitNexus Code Intelligence

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

### Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

### Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

### Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/deepresearchagent/context` | Codebase overview, check index freshness |
| `gitnexus://repo/deepresearchagent/clusters` | All functional areas |
| `gitnexus://repo/deepresearchagent/processes` | All execution flows |
| `gitnexus://repo/deepresearchagent/process/{name}` | Step-by-step execution trace |

### CLI Reference

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

---

## 12. Cross-Module Integration Patterns

| Action | Trigger | Navigation |
|--------|---------|------------|
| Save document query to Notes | Documents "Save to Notes" button | Stays on Documents, shows toast |
| Research a note's topic | Notes "Research" button (Sparkles icon) | `navigate(/research?run={run_id})` |
| Research document gaps | Documents "Research Gaps" button | `navigate(/research?run={run_id})` |
| Click wiki link `[[Note Title]]` | Notes/Docs MarkdownPreview | Notes: `loadNote()` directly; Docs: `navigate(/notes?note={title})` |
| Click wiki link `[[doc:filename]]` | Notes MarkdownPreview | `navigate(/documents?doc={filename})` — uses **filename**, not ID |
| Click wiki link `[[wiki:Concept]]` | Notes MarkdownPreview | `navigate(/documents?wiki={concept})` |
| Click wiki link `[[run:uuid]]` | Notes MarkdownPreview | `navigate(/research?run={run_id})` |
| Click wiki link `[[entity:Name]]` | Notes MarkdownPreview | **Not implemented** — no handler exists |

---

## 13. Performance Guidelines

- **Lazy load everything >100KB:** D3 graph, G6 mindmap, background effects, heavy markdown features
- **Virtualize lists >20 items:** Research runs (`RunList`), notes sidebar (`NotesModule`), document lists (`DocumentsModule`) — use `useVirtualList` with fixed `itemHeight`
- **Debounce inputs:** Search boxes (300ms), auto-save (400ms)
- **Memoize expensive computations:** `useMemo` for graph data, filtered lists, sorted arrays
- **Avoid `useEffect` data fetching:** Use event handlers + loading states instead of `useEffect` + `useState` for user-triggered actions
- **Backend:** Main API handles operations synchronously within async route handlers. The **webhook worker** (`worker.py`) is a separate FastAPI app that uses `BackgroundTasks` for research jobs triggered via `POST /webhook/trigger`.
- **Database:** Use PostgreSQL `tsvector` for full-text search, not `ILIKE` for large datasets. The Supabase client is sync — wrap in `asyncio.to_thread()`.
- **Graphify:** Knowledge graph building is compute-intensive. Run as background task or warn user of delay.

---

*End of AGENTS.md. When in doubt, re-read the relevant section before making changes.*

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **deepresearchagent** (4948 symbols, 11877 relationships, 155 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/deepresearchagent/context` | Codebase overview, check index freshness |
| `gitnexus://repo/deepresearchagent/clusters` | All functional areas |
| `gitnexus://repo/deepresearchagent/processes` | All execution flows |
| `gitnexus://repo/deepresearchagent/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
