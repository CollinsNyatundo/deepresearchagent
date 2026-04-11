# CLAUDE.md — Deep Research Agent

## Project Overview

A general-purpose deep research engine that performs multi-step web research, produces citation-backed Markdown reports, and visualizes results as interactive mindmaps. Built for local-first operation with no Docker dependency.

## Architecture

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

## Tech Stack

### Backend (Python 3.11 + pip)
- **Agent**: Re-implemented DRE (Deep Researcher Reflect Evolve) algorithm — fully async
- **Scraping**: Scrapling (StealthyFetcher → DynamicFetcher → Fetcher fallback chain)
- **LLM**: OpenRouter API via `langchain-openai` (`ChatOpenAI` with custom `base_url`)
- **Default model**: `nvidia/nemotron-3-super-120b-a12b:free` (1M context, Mamba-Transformer MoE)
- **Search**: DuckDuckGo (default, free) + Tavily + Brave Search
- **API**: FastAPI with CORS for frontend
- **CLI**: Typer + Rich
- **Config**: TOML (`config.toml`) + env vars + per-request overrides

### Frontend (Vite + React + TypeScript)
- **UI**: Mantine v7 (AppShell, Tabs, forms, theming)
- **Graph**: AntV G6 v5 (mindmap layout, `@antv/g6-extension-react`)
- **Markdown**: `react-markdown` + `remark-gfm`
- **Icons**: `@tabler/icons-react`

## Key Conventions

### Python
- **All I/O is async** — use `async/await` everywhere (LLM calls, scraping, search)
- **Pydantic v2** for all data models (`research_engine/models.py`)
- **Type hints** on all function signatures
- **Model is per-request** — never hardcode a model ID; accept it as a parameter
- **Config hierarchy**: `config.toml` → env vars → CLI args → per-request API body
- **Error handling**: Scrapling uses a 3-tier fallback chain; always gracefully degrade

### TypeScript/React
- **Mantine** for all UI components — no raw HTML forms or ad-hoc CSS
- **AntV G6** for graph visualization only
- **Types** in `src/types/api.ts` must mirror backend Pydantic models
- **API client** in `src/api/client.ts` — all fetch calls go through this

### File Layout
```
research_engine/           # Python backend package
  config.py                # Config loading
  models.py                # ALL Pydantic models
  agent/                   # DRE algorithm modules
  llm/                     # LLM provider + prompts
  sources/                 # Web search + Scrapling scraper
  output/                  # Report formatter + mindmap builder + storage
  cli.py                   # CLI entrypoint
  api.py                   # FastAPI server

frontend/                  # React frontend
  src/components/layout/   # AppShell
  src/components/runs/     # RunList, RunHeader
  src/components/views/    # ReportView, MindmapView
  src/components/mindmap/  # G6MindmapGraph, NodeDetailsPanel
```

## Quick Start

```bash
# Backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
pip install -e .[browser]  # Optional for Scrapling stealth (large download)
python -m playwright install chromium
python -m camoufox fetch
cp config.example.toml config.toml  # Add your API keys
research "Your query" --depth 5

# API server
research serve

# Frontend
cd frontend && npm install && npm run dev
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key |
| `TAVILY_API_KEY` | No | Tavily search API key |
| `BRAVE_SEARCH_API_KEY` | No | Brave Search API key |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/runs` | List past research runs |
| `GET` | `/runs/{id}/report` | Get Markdown report |
| `GET` | `/runs/{id}/mindmap` | Get mindmap graph (G6 format) |
| `POST` | `/research` | Start new research `{query, model, depth}` |
| `POST` | `/runs/{id}/mindmap/expand` | Drill deeper on a node `{node_id}` |
| `POST` | `/validate-model` | Validate an OpenRouter model ID |

## Default Research Settings

- **Depth**: 5 (exhaustive) — up to 30 research cycles
- **Pages per query**: 5
- **Content per page**: 20,000 chars (Nemotron's 1M context allows this)
- **Crossover**: Enabled (3 candidates)
- **Progress threshold**: 90%
