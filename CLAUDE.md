# CLAUDE.md — Deep Research Agent

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Key Commands

### Setup
```bash
# Backend
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -e .
pip install -e .[browser]  # Optional for stealth scraping
python -m playwright install chromium
python -m camoufox fetch
cp .env.example .env  # Add API keys
cp config.example.toml config.toml  # Adjust as needed

# Frontend
cd frontend
npm install
```

### Development
# Backend API server
research serve

# Quick research query (CLI)
research run "Your research topic" --depth 3

# Frontend dev server
cd frontend && npm run dev

# Run all tests
pytest tests/ -v --asyncio-mode=auto

# Backend linting/formatting
ruff check research_engine/
ruff format research_engine/

# Frontend type check & build
cd frontend && npm run build

### GitNexus (Code Intelligence)
# Start/stop GitNexus server (via API or manually)
# Auto-started when visiting Code Architecture tab in UI
npx gitnexus serve --port 4747  # Manual control

# Analyze codebase (run after git changes)
npx gitnexus analyze

# Impact analysis (BEFORE editing any symbol)
gitnexus_impact({target: "symbolName", direction: "upstream"})

# Detect changes (BEFORE committing)
gitnexus_detect_changes()
```

## Architecture Overview

```
User → CLI / React Frontend → FastAPI API → Orchestrator (DRE algorithm)
                                ├── Planner (plan/reflect/update)
                                ├── Searcher (query gen + synthesis)
                                │     ├── Web Search (DDG/Tavily/Brave)
                                │     └── Web Scraper (Scrapling async)
                                ├── Crossover (candidate evolution)
                                └── Output (report + mindmap + storage)
                                      └── LLM Provider (OpenRouter)
```

**Key Modules:**
- `research_engine/agent/` - DRE algorithm (planner, searcher, crossover, etc.)
- `research_engine/sources/` - Web search, scraping (Scrapling), GitHub MCP
- `research_engine/knowledge_graph/` - Graphify integration, MCP bridge
- `research_engine/output/` - Report formatting, mindmap, storage
- `frontend/src/` - React frontend with Tailwind CSS and Radix UI

## Critical Conventions

### Python Backend
- **All I/O is async** – Use `await` for LLM calls, scraping, file I/O (`aiofiles`)
- **Database calls** – Supabase client is synchronous; wrap in `asyncio.to_thread()`
- **Model per request** – Never hardcode LLM IDs; accept as parameter
- **Pydantic v2** – All data models in `research_engine/models.py`
- **Config hierarchy** – `config.toml` → env vars → CLI args → per-request API body
- **Error handling** – Scrapling uses 3-tier fallback; always degrade gracefully

### TypeScript/Frontend (React)
- **Tailwind CSS v3.4.19** for all styling – no custom CSS files unless global (go in `index.css`)
- **Radix UI primitives** for accessibility-critical components (dialogs, dropdowns, tabs, etc.)
- **Lucide React icons** exclusively – no emojis, SVG icons, or custom icon sets
- **TypeScript types** in `src/types/api.ts` must mirror backend Pydantic models exactly
- **API client** in `src/api/client.ts` – all fetch calls go through this
- **Liquid glass styling** – Use `liquid-glass` class for panels/containers (see `index.css`)
- **State** – React hooks + `localStorage`; no external state libraries
- **Routing** – React Router v7.6.1
- **Markdown** – `react-markdown` + `remark-gfm`
- **Graph Visualization** – AntV G6 v5 for mindmap/knowledge graph only
- **Virtualization** – Use `useVirtualList` hook for lists >20 items with fixed item heights
- **Error boundaries** – Wrap modules with `ErrorBoundary` (class-based, in `components/ErrorBoundary.tsx`)
- **Code splitting** – Use `React.lazy()` + `Suspense` with `LoadingFallback` for route modules

### File Layout
```
research_engine/           # Python backend
  config.py                # Config loading
  models.py                # ALL Pydantic models
  agent/                   # DRE algorithm modules
  llm/                     # LLM provider + prompts
  sources/                 # Web search + Scrapling scraper
  output/                  # Report formatter + mindmap builder + storage
  cli.py                   # CLI entrypoint
  api.py                   # FastAPI server

frontend/                  # React frontend
  src/
    main.tsx               # Entry point (React Router)
    App.tsx                # Route definition + lazy loading + Suspense
    index.css              # Global styles (Tailwind, liquid glass, fonts, HSL vars)
    api/
      client.ts            # Frontend API client (SOURCE OF TRUTH)
    types/
      api.ts               # TypeScript types (mirror of models.py)
    modules/               # Thin module containers (compose shared components)
      research/
        ResearchModule.tsx
      notes/
        NotesModule.tsx
      documents/
        DocumentsModule.tsx
    components/            # Shared components organized by domain
      Auth/                # AuthModal, WorkspaceSelector
      backgrounds/         # 4 GPU backgrounds + renderer + switcher
      code-arch/           # GitNexusWebView.tsx
      knowledge-graph/     # KG visualization components
      layout/              # Layout, Sidebar, Header
      mindmap/             # G6MindmapGraph.tsx, NodeDetailsPanel.tsx
      notes/               # MarkdownPreview, NoteGraph, MoonPhaseWidget
      runs/                # RunList.tsx
      ui/                  # EMPTY — shadcn placeholder (never used)
      views/               # ReportView, CitationsView, ExportPanel, etc.
      ErrorBoundary.tsx    # React error boundary (class-based)
      LoadingSkeletons.tsx # Skeleton loaders
    hooks/
      useBackground.tsx    # Background mode switching
      useVirtualList.ts    # Fixed-height list virtualization
    lib/
      authContext.tsx      # Auth context + Supabase auth
      supabase.ts          # Supabase client singleton
      utils.ts             # Utility functions (cn, etc.)
```

### GitNexus Mandatory Practices
1. **Before editing any symbol**: Run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report blast radius
2. **Before committing**: Run `gitnexus_detect_changes()` to verify expected impact
3. **Never** use find-and-replace for renaming – use `gitnexus_rename`
4. **Explore code** with `gitnexus_query({query: "concept"})` instead of grepping
5. **Get full context** with `gitnexus_context({name: "symbolName"})`

### Current Focus (optimize/reduce-latency branch)
This branch focuses on latency optimization through:
- Persistent browser instance reuse in WebScraper
- Skipping redundant batch search result reranking
- Fallback to all search results on relevance filter failure
- Async I/O optimizations throughout the DRE pipeline

When working on this branch, prioritize benchmarking with `tests/benchmark_latency.py` and profiling critical paths in `research_engine/agent/` and `research_engine/sources/`.

--- 
*Remember: Always run GitNexus impact analysis before edits and verify changes with `detect_changes()` before committing.*

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
