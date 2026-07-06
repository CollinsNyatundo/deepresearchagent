# Architecture

This page maps the major runtime pieces of Deep Research Agent and how they fit together.

## System shape

DRA is a **FastAPI + React + Supabase** application with three user-facing workspaces:

- **Research** — the deep research loop, SSE streaming, mindmaps, citations, exports, and knowledge graph generation
- **Notes** — a personal wiki with wiki-style linking and backlinks
- **Documents** — OpenKB-backed ingestion, search, chat, wiki browsing, and skill generation
- **Settings** — workspace-scoped defaults, API keys, appearance, and research preferences

The repository’s main runtime surfaces are:

- `research_engine/api.py` — the FastAPI app and nearly all HTTP endpoints
- `research_engine/agent/` — planning, searching, scraping, synthesis, retries, and state tracking
- `research_engine/llm/` — provider selection and prompt templates
- `research_engine/sources/` — search, scraping, caching, and circuit breaking
- `research_engine/knowledge_graph/` — Graphify integration and MCP bridge
- `frontend/src/` — the React client, modules, and shared UI components
- `supabase/migrations/` and `research_engine/db/supabase/migrations/` — the workspace-scoped PostgreSQL schema

## Source map

| Area | Key files |
|------|-----------|
| Backend entrypoint | `research_engine/api.py`, `research_engine/cli.py`, `research_engine/worker.py` |
| Core state and shapes | `research_engine/models.py` |
| Configuration | `research_engine/config.py`, `config.example.toml` |
| LLM gateway | `research_engine/llm/provider.py`, `research_engine/llm/prompts.py` |
| Search & scraping | `research_engine/sources/web_search.py`, `research_engine/sources/web_scraper.py` |
| Knowledge graph | `research_engine/knowledge_graph/builder.py`, `research_engine/knowledge_graph/mcp_bridge.py` |
| Database layer | `research_engine/db/supabase/client.py`, `research_engine/db/supabase/ops.py` |
| Frontend entrypoint | `frontend/src/App.tsx`, `frontend/src/main.tsx` |
| Main modules | `frontend/src/modules/research/ResearchModule.tsx`, `frontend/src/modules/notes/NotesModule.tsx`, `frontend/src/modules/documents/DocumentsModule.tsx`, `frontend/src/modules/settings/SettingsModule.tsx`, `frontend/src/modules/nodes/NodesModule.tsx` |

## What to watch out for

- The backend is stateful around workspace membership and must enforce Supabase auth and RLS-aware access patterns.
- The LLM provider is runtime-selected; model IDs are not fixed in code.
- Research is not a single request/response flow: it is an iterative loop with streaming updates, plan review, and optional resynthesis.
- The frontend is organized by **module containers** plus **shared domain components** in `frontend/src/components/`; that structure is deliberate and should not be collapsed back into per-module component folders.

## Where to go next

- [Backend architecture](architecture/backend.md)
- [Frontend architecture](architecture/frontend.md)
- [Database architecture](architecture/database.md)
- [Architecture decisions](architecture/decisions.md)
