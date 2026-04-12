# 🔬 Deep Research Agent

> Perplexity-grade, autonomous deep research engine with interactive mindmap visualization, knowledge graph extraction, multi-provider LLM + search support, and code intelligence.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev)
[![Mantine](https://img.shields.io/badge/Mantine-9.0-339AF0?logo=mantine)](https://mantine.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## Overview

Deep Research Agent implements the **DRE (Deep Research Reflect Evolve)** algorithm — a multi-cycle, self-improving research loop that acts as your personal AI research assistant and engineering platform. It autonomously:

1. **Plans** — decomposes your query into targeted sub-questions
2. **Searches** — runs parallel queries across DuckDuckGo, Tavily, and Brave
3. **Scrapes** — extracts full page content via Scrapling's tiered fetcher chain (stealth → JS → basic HTTP)
4. **Validates** — LLM-scores each scraped page for relevance before synthesis
5. **Synthesizes** — generates inline-cited answers and reflects on completeness
6. **Evolves** — re-searches gaps via reflective retry until ≥90% confidence or 30 cycles
7. **Exports** — produces a structured Markdown report + interactive mindmap + knowledge graph

The engine is **fully async**, **streaming over SSE**, exposes a robust REST API consumed by a **React/Mantine frontend**, and is extensible via **MCP (Model Context Protocol)** servers.

---

## Quick Start

### Prerequisites

- Python ≥ 3.11
- Node.js ≥ 18 (for the frontend, and running GitNexus)
- An [OpenRouter](https://openrouter.ai) API key (free tier works)

### Installation

```bash
# 1. Clone and enter the project
git clone https://github.com/CollinsNyatundo/deepresearchagent
cd deepresearchagent

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate       # macOS / Linux

# 3. Install Python dependencies
pip install -e .

# Optional: stealth scraping (Camoufox + Playwright)
pip install -e .[browser]
python -m playwright install chromium
python -m camoufox fetch

# 4. Configure environment
cp .env.example .env
# Edit .env and add your API key(s)

# 5. (Optional) create config.toml for advanced settings
cp config.example.toml config.toml
# Edit config.toml as needed
```

### Running

```bash
# ── CLI (terminal only) ──────────────────────────────────────────
# Quick research run
research run "Your research topic" --depth 3

# Exhaustive research (up to 30 cycles)
research run "Transformer attention mechanisms" --depth 5

# Use a specific model / provider
research run "Quantum computing" --model qwen/qwen3-235b-a22b:free
research run "Rust ownership" --provider groq --model llama-3.3-70b-versatile

# Research a GitHub repository (code-aware mode)
research run "How does authentication work?" --mode github

# List past runs
research list-runs

# ── API Server + Frontend ────────────────────────────────────────
# Terminal 1: Start API server
research serve                     # runs on http://localhost:8000

# Terminal 2: Start frontend
cd frontend && npm install && npm run dev    # runs on http://localhost:5173

# ── Graphify Knowledge Graph (standalone) ───────────────────────
# Build a graph from any local corpus
python -X utf8 graphify-out/build_graph.py

# Query the graph
python -X utf8 -m graphify query "your question" --graph graphify-out/graph.json
python -X utf8 -m graphify query "trace this concept" --dfs --budget 1500
python -X utf8 graphify-out/test_queries.py    # Run all query tests
```

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       Frontend (React)                          │
│     Mantine UI  •  AntV G6  •  SSE streaming                    │
│     Tabs: Runs | Report | Mindmap | Graphify | Code Arch      │
└──────────────────────┬────────────────────────────────┬─────────┘
                       │ HTTP / SSE                     │ HTTP
                       ▼                                ▼
┌───────────────────────────────────────────────┐ ┌────────────────┐
│          FastAPI REST Server (:8000)          │ │  GitNexus      │
│  /research  •  /runs  •  /knowledge-graph     │ │  Server        │
│  /gitnexus/serve (Start/Stop lifecycle API)   │ │  (:4747)       │
└──────────────────────┬────────────────────────┘ └────────────────┘
                       │
          ┌────────────┼──────────────────┐
          ▼            ▼                  ▼
┌─────────────┐ ┌────────────┐  ┌────────────────────┐
│  Orchestrator│ │  LLM Layer │  │  Knowledge Graph   │
│  DRE Loop   │ │  OpenRouter│  │  (Graphify)         │
│  (30 cycles)│ │  / Groq    │  │  Builder+MCP Bridge│
└──────┬──────┘ └────────────┘  └────────────────────┘
       │
  ┌────┴─────────────────────────────┐
  ▼                                  ▼
┌────────┐ ┌───────────────────────────────────────────────┐
│Planner │ │ Search + Scrape + Rerank + MCP Analysis       │
│Crossover│ │ DDG • Tavily • Brave • GitHub MCP Server      │
│Retry   │ │ Scrapling (stealth→JS→HTTP)                   │
└────────┘ └───────────────────────────────────────────────┘
```

### Backend Modules (`research_engine/`)

| Module | Description |
|--------|-------------|
| `agent/orchestrator.py` | Core DRE loop — coordinates all phases. 764 lines |
| `agent/planner.py` | LLM-based query decomposition and plan generation |
| `agent/searcher.py` | Search execution, content validation, query generation |
| `agent/crossover.py` | Evolutionary candidate merging via multiple LLM calls |
| `agent/retry.py` | Protocol-H reflective retry for low-confidence cycles |
| `agent/context.py` | In-memory Q&A history and research state manager |
| `llm/provider.py` | Async OpenRouter/Groq provider with structured output + fallback |
| `llm/prompts.py` | All LLM prompt templates |
| `sources/web_search.py` | DuckDuckGo + Tavily + Brave search providers + aggregator |
| `sources/web_scraper.py` | Scrapling tiered fetcher (stealthy → dynamic → basic) |
| `sources/github_search.py` | GitHub MCP client for code-aware research mode |
| `sources/reranker.py` | LLM-based search result reranking |
| `knowledge_graph/builder.py` | Graphify integration — corpus export → subprocess → parse |
| `knowledge_graph/enricher.py` | ArXiv/PDF corpus enricher for strategy C |
| `knowledge_graph/mcp_bridge.py` | Graphify MCP server lifecycle + query bridge |
| `output/storage.py` | Async run persistence (save/load JSON + markdown) |
| `output/exporter.py` | Multi-format export: MD, PDF (fpdf2), DOCX, XLSX, JSON |
| `output/mindmap.py` | AntV G6-compatible mindmap generator + node expansion |
| `output/formatter.py` | Markdown report formatter with citation inlining |
| `models.py` | Pydantic v2 models — single source of truth for all data |
| `config.py` | TOML + env var config loader with deep merge |
| `api.py` | FastAPI app — 20+ REST/SSE endpoints (including GitNexus process mgmt) |
| `cli.py` | Typer CLI — `research run`, `research serve`, `research list-runs` |

### Frontend Components (`frontend/src/`)

| Component | Description |
|-----------|-------------|
| `App.tsx` | App shell, SSE event handling, global view toggle (Research vs Code-Arch) |
| `components/views/ResearchProgress.tsx` | Live SSE progress display with event timeline |
| `components/views/PlanReview.tsx` | Editable research plan UI (Phase 4) |
| `components/views/ReportView.tsx` | Rendered Markdown report with citations |
| `components/views/MindmapView.tsx` | AntV G6 mindmap with node expansion |
| `components/views/ExportPanel.tsx` | Multi-format download UI |
| `components/knowledge-graph/*` | Force-directed G6 knowledge graph, query panel, metrics |
| `components/code-arch/GitNexusWebView.tsx`| GitNexus codebase explorer iframe UI |
| `components/runs/RunList.tsx` | Past runs sidebar |

### LLM Providers

| Provider | Auth | Best For |
|----------|------|----------|
| **OpenRouter** (default) | `OPENROUTER_API_KEY` | Production research, large models, free tier |
| **Groq** | `GROQ_API_KEY` | Fast inference, local dev, free tier (12k TPM) |

**Free model presets:**

| Name | Model ID | Strengths |
|------|----------|-----------|
| Nemotron 3 Super | `nvidia/nemotron-3-super-120b-a12b:free` | 1M context, agentic (default) |
| GPT-OSS 120B | `openai/gpt-oss-120b:free` | General reasoning |
| Qwen 3 235B | `qwen/qwen3-235b-a22b:free` | RAG, tools, multi-step |
| Gemini Flash 1.5 | `google/gemini-flash-1.5:free` | Fast, multimodal |
| Llama 3.3 70B | `meta-llama/llama-3.3-70b-instruct:free` | Balanced quality/speed |
| DeepSeek R1 | `deepseek/deepseek-r1:free` | Reasoning/math |

### Search Providers

| Provider | API Key Required | Notes |
|----------|-----------------|-------|
| **DuckDuckGo** | No | Free, rate-limit hardened with retry |
| **Tavily** | `TAVILY_API_KEY` | Higher quality results, advanced mode |
| **Brave** | `BRAVE_SEARCH_API_KEY` | Good balance of quality and coverage |
| **Aggregated** (`all`) | Optional | Runs all available providers concurrently, deduplicates |

### Scraping Architecture

Scrapling tiered fetcher chain (automatic fallback):

```
[Tier 1] StealthyFetcher (Camoufox)   — anti-fingerprint, Cloudflare bypass
    ↓ fails
[Tier 2] DynamicFetcher (Playwright)   — JS rendering for SPAs
    ↓ fails  
[Tier 3] Fetcher (httpx)               — fast basic HTTP for static pages
```

> **Note:** Camoufox requires `python -m camoufox fetch` and Playwright requires `python -m playwright install chromium` after initial install.

---

## Code Intelligence (GitNexus Integration)

DeepResearchAgent supports **GitNexus** to index, visualize, and interact with the local repository's codebase. The GitNexus capabilities provide interactive architecture exploration via the frontend.

### How It Works

- **Global Navigation:** The web interface has a toggle for switching between "Research Mode" and "Code Arch" mode.
- **On-Demand Startup:** Navigating to the Code Architecture view triggers `/gitnexus/serve/start`, starting an `npx gitnexus serve --port 4747` background process safely handled by FastAPI.
- **Interactive UI:** The `GitNexusWebView.tsx` component binds to the server running on port 4747, providing a complete graph mapping of the local repository codebase.
- **Shutdown:** Closing the tab or unmounting triggers `/gitnexus/serve/stop` to safely dispose of the bridge process dynamically. 

_Developers writing agents utilizing this repo should check the `AGENTS.md` docs to see how to interface with `npx gitnexus` via its Model Context Protocol._

---

## Knowledge Graph (Graphify Integration)

After each research run, the engine optionally builds a **Graphify knowledge graph** from the research corpus — transforming all findings, scraped pages, and citations into an interconnected, community-clustered knowledge map.

### How It Works

```
ResearchResult
    │
    ▼
_export_corpus()          # Writes findings/ + sources/ + meta/ markdown tree
    │
    ▼
graphify <corpus_dir>     # Subprocess: detect → AST extract → cluster → analyze
    │
    ▼
graph.json + graph.html   # Copied to outputs/{run_id}/
    │
    ▼
KnowledgeGraph model      # Parsed into Pydantic, persisted as knowledge_graph.json
    │
    ▼
Graphify MCP Server       # Started post-build for interactive BFS/DFS queries
```

### Querying the Graph

```bash
# From CLI (research_engine corpus graph)
python -X utf8 -m graphify query "your question" --graph graphify-out/graph.json
python -X utf8 -m graphify query "trace concept" --dfs --budget 1500
python -X utf8 graphify-out/test_queries.py          # Full test suite

# From the frontend
# → Open any completed run → "Knowledge Graph" tab → use KGQueryPanel
```

### Configuration

```toml
[graphify]
enabled = true              # Master switch
mode = "deep"               # "fast" = AST only | "deep" = AST + LLM edges
mcp_enabled = true          # Start MCP server after build
mcp_port = 8765
max_paper_enrichments = 5   # ArXiv/PDF URLs to enrich per run
```

Environment overrides: `GRAPHIFY_ENABLED`, `GRAPHIFY_MODE`, `GRAPHIFY_MCP_ENABLED`

---

## Research Modes

### Web Research (default)

Standard web-based research using the configured search providers + Scrapling.

```bash
research run "History of reinforcement learning" --mode web
```

### GitHub Code Research (MCP Integration)

Uses the `@modelcontextprotocol/server-github` MCP server seamlessly wired into the orchestrator to perform high-grade DRE logic specifically localized to investigating repositories, issues, and codebases.

```bash
# Requires: GITHUB_PERSONAL_ACCESS_TOKEN in .env
research run "How does auth middleware work in this codebase?" --mode github
```

---

## API Reference

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

### Research

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/research` | Start blocking research run (shielded) |
| `POST` | `/research/stream` | Start research with SSE streaming |
| `POST` | `/research/plan` | Generate plan for user review |
| `POST` | `/research/execute/stream` | Execute approved plan with SSE |

### Runs & Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/runs` | List all past runs |
| `GET` | `/runs/{id}/report` | Get Markdown report |
| `GET` | `/runs/{id}/mindmap` | Get mindmap graph (G6 format) |
| `POST` | `/runs/{id}/mindmap/expand` | Drill deeper into a mindmap node |
| `GET` | `/runs/{id}/exports` | List available export formats |
| `GET` | `/runs/{id}/export/{fmt}` | Download export (`markdown`, `pdf`, `docx`, `xlsx`, `mindmap_json`) |

### Knowledge Graph (Graphify)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/runs/{id}/knowledge-graph` | Get knowledge graph (nodes/edges/communities) |
| `GET` | `/runs/{id}/knowledge-graph/html` | Download interactive `graph.html` |
| `GET` | `/runs/{id}/knowledge-graph/available` | Check if KG is built |
| `POST` | `/runs/{id}/knowledge-graph/build` | Trigger manual KG build |
| `POST` | `/runs/{id}/knowledge-graph/query` | BFS/DFS graph traversal query |
| `GET` | `/runs/{id}/knowledge-graph/mcp` | MCP server status |
| `POST` | `/runs/{id}/knowledge-graph/mcp/start` | Start Graphify MCP server |
| `POST` | `/runs/{id}/knowledge-graph/mcp/stop` | Stop Graphify MCP server |

### Code Intelligence (GitNexus)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/gitnexus/serve/status` | Current status of the external proxy server |
| `POST` | `/gitnexus/serve/start` | Launch the proxy to the GitNexus architecture UI |
| `POST` | `/gitnexus/serve/stop` | Safely dispose of the proxy processes |

### Utilities

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/models` | List LLM model presets |
| `POST` | `/validate-model` | Validate an OpenRouter model ID |
| `GET` | `/health` | Health check |

### SSE Events (streaming endpoints)

The streaming endpoints emit these named events:

| Event | Payload |
|-------|---------|
| `initializing` | `{run_id, model}` |
| `planning` | `{message}` |
| `plan_ready` | `{steps, sub_queries}` |
| `searching` | `{cycle, query}` |
| `scraping` | `{cycle, urls, count}` |
| `validating` | `{cycle}` |
| `synthesizing` | `{cycle}` |
| `reflecting` | `{cycle, progress}` |
| `retry` | `{cycle, reason}` |
| `progress` | `{percent}` |
| `cycle_complete` | `{cycle, progress, answer_preview}` |
| `generating_report` | — |
| `knowledge_graph_build` | `{message}` |
| `knowledge_graph_ready` | `{node_count, edge_count, community_count, compression_ratio}` |
| `complete` | `{run_id, report_preview, total_cycles, citations}` |
| `error` | `{error}` |

---

## Configuration

### Environment Variables (`.env`)

```ini
# Required
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Optional — improves search quality
TAVILY_API_KEY=tvly-your-key-here
BRAVE_SEARCH_API_KEY=BSA-your-key-here

# Optional — GitHub code research mode
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your-token-here

# Optional — runtime overrides (can also use config.toml)
LLM_PROVIDER=openrouter           # openrouter | groq
OPENROUTER_MODEL=nvidia/nemotron-3-super-120b-a12b:free
SEARCH_PROVIDER=all               # duckduckgo | tavily | brave | all
GRAPHIFY_ENABLED=true             # true | false
GRAPHIFY_MODE=deep                # fast | deep
GRAPHIFY_MCP_ENABLED=true
```

### `config.toml` (full config reference)

```toml
[llm]
provider = "openrouter"           # "openrouter" | "groq"
default_model = "nvidia/nemotron-3-super-120b-a12b:free"
base_url = "https://openrouter.ai/api/v1"
temperature = 0.2
max_tokens = 16384
groq_max_tokens = 4096            # Capped for Groq free tier (12k TPM limit)
request_timeout = 120             # Seconds before giving up on slow models

[llm.presets]                     # Shown in the frontend model selector
nemotron = "nvidia/nemotron-3-super-120b-a12b:free"
gpt_oss  = "openai/gpt-oss-120b:free"
qwen     = "qwen/qwen3-235b-a22b:free"

[search]
default_provider = "duckduckgo"   # "duckduckgo" | "tavily" | "brave" | "all"
max_results = 10

[scraping]
max_concurrent = 5                # Concurrent page fetches
timeout_ms = 30000
max_content_chars = 20000         # Per-page content truncation
fetcher_tier = "stealthy"         # "stealthy" | "dynamic" | "basic"

[research]
default_depth = 5                 # 1=quick, 3=standard, 5=exhaustive (≤30 cycles)
max_cycles = 30
progress_threshold = 90           # Stop when this % confidence is reached
max_pages_per_query = 5
enable_crossover = true           # Evolutionary answer merging
crossover_candidates = 3

[api]
host = "0.0.0.0"
port = 8000
cors_origins = ["http://localhost:5173"]

[graphify]
enabled = true
mode = "deep"                     # "fast" (AST only) | "deep" (AST + LLM edges)
mcp_enabled = true
mcp_port = 8765
max_paper_enrichments = 5         # Max ArXiv/PDF URLs to enrich per run
```

---

## Output Files

Each research run creates a directory at `outputs/{run_id}/`:

```
outputs/
└── 20260411_152300_abc123/
    ├── report.md              # Final Markdown research report
    ├── result.json            # Full ResearchResult (steps, citations, metadata)
    ├── mindmap.json           # AntV G6 mindmap graph data
    ├── knowledge_graph.json   # Graphify knowledge graph (nodes/edges/communities)
    ├── graph.html             # Interactive Pyvis visualization (open in browser)
    ├── GRAPH_REPORT.md        # God nodes, surprise connections, community labels
    └── export.md / .pdf / .docx / .xlsx   # Cached exports (on demand)
```

---

## Development

### Running Tests

```bash
# All async tests
pytest tests/ -v --asyncio-mode=auto

# Specific tests
pytest tests/test_config.py
pytest tests/test_llm.py
pytest tests/test_mindmap.py
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev          # Dev server on :5173 with HMR
npm run build        # Production build (TypeScript check + Vite bundle)
```

**Stack:** Vite 8, React 19, TypeScript 6, Mantine 9, AntV G6 v5, react-markdown

### Graphify Graph Commands (for development)

```bash
# Build graph from research_engine/ codebase
python -X utf8 graphify-out/build_graph.py

# Run all query types
python -X utf8 graphify-out/test_queries.py

# Direct CLI tests
python -X utf8 -m graphify query "LLM provider model selection" --graph graphify-out/graph.json --budget 800
python -X utf8 -m graphify query "knowledge graph build pipeline" --dfs --graph graphify-out/graph.json
```

> **Windows note:** Always prefix with `python -X utf8` when running graphify CLI — its output contains Unicode arrow/box characters that break Windows `cp1252` encoding without the UTF-8 flag.

### Linting

```bash
ruff check research_engine/
ruff format research_engine/
```

### Adding a New Search Provider

1. Implement the `SearchProvider` protocol in `sources/web_search.py`
2. Add a `case` in `get_search_provider()` factory
3. Add its config key to `config.example.toml` under `[search]`

### Adding a New LLM Prompt

1. Add the template to `llm/prompts.py`
2. If structured output: define the Pydantic model in `models.py`
3. Call via `llm.call_structured(prompt, SchemaClass, model=model)`

### Adding a New API Endpoint

1. Add route in `api.py`
2. Add corresponding method in `frontend/src/api/client.ts`
3. If new return type: add to both `models.py` and `frontend/src/types/api.ts`

---

## Known Gotchas

| Issue | Fix |
|-------|-----|
| Camoufox binary missing | Run `python -m camoufox fetch` |
| Playwright missing | Run `python -m playwright install chromium` |
| OpenRouter rate limits | Depth=5 may hit free tier limits; add delay or use Groq |
| Groq TPM limit (12k) | Kept at 4096 `groq_max_tokens`; don't increase without upgrading |
| Windows Unicode errors in graphify | Use `python -X utf8 -m graphify ...` |
| Mantine styles broken silently | `postcss-preset-mantine` + `postcss-simple-vars` required in devDeps |
| G6 graph renders invisible | Container must have explicit `width`/`height` — never `0×0` |
| `.env` not loading | Ensure `load_dotenv(override=True)` runs before `get_config()` |
| GitNexus index stale | Run `npx gitnexus analyze` after commits |

---

## Project Structure

```
deepresearchagent/
├── research_engine/           # Python backend
│   ├── agent/                 # DRE orchestrator, planner, searcher, crossover, retry
│   ├── llm/                   # OpenRouter/Groq provider + prompts
│   ├── sources/               # Web search, scraper (Scrapling), GitHub MCP, reranker
│   ├── knowledge_graph/       # Graphify builder, corpus enricher, MCP bridge
│   ├── output/                # Storage, exporter (MD/PDF/DOCX/XLSX), mindmap, formatter
│   ├── models.py              # Pydantic v2 data models (single source of truth)
│   ├── config.py              # TOML + env config loader
│   ├── api.py                 # FastAPI server (20+ endpoints)
│   └── cli.py                 # Typer CLI (run / serve / list-runs)
├── frontend/                  # React frontend
│   └── src/
│       ├── components/
│       │   ├── knowledge-graph/   # KG visualization, stats, query panel, legend
│       │   ├── code-arch/         # GitNexus repository explorer
│       │   ├── views/             # Report, Mindmap, Progress, PlanReview, Export
│       │   └── runs/              # Run list sidebar
│       ├── api/client.ts          # Frontend API client
│       ├── types/api.ts           # TypeScript types (mirrors models.py)
│       └── App.tsx                # App shell + SSE event handling
├── graphify-out/              # Pre-built graph of research_engine codebase
│   ├── graph.json             # 429 nodes, 1428 edges
│   ├── graph.html             # Interactive visualization
│   ├── GRAPH_REPORT.md        # God nodes + community analysis
│   ├── build_graph.py         # Repeatable graph build script
│   └── test_queries.py        # Full query test suite
├── tests/                     # pytest async tests
├── outputs/                   # Research run outputs (git-ignored)
├── config.example.toml        # Full config reference
├── .env.example               # Environment variable reference
├── pyproject.toml             # Project metadata + dependencies
├── AGENTS.md                  # Agent implementation guidelines
└── CLAUDE.md                  # Deep architecture documentation
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Related Documentation

- **[AGENTS.md](AGENTS.md)** — Code agent rules, architecture decisions, common patterns, gotchas
- **[CLAUDE.md](CLAUDE.md)** — Deep architecture documentation and implementation notes
- **[config.example.toml](config.example.toml)** — Fully annotated configuration reference
- **[graphify-out/GRAPH_REPORT.md](graphify-out/GRAPH_REPORT.md)** — Knowledge graph analysis of this codebase
