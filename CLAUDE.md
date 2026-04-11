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

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **DeepResearchAgent** (914 symbols, 3140 relationships, 77 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/DeepResearchAgent/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/DeepResearchAgent/context` | Codebase overview, check index freshness |
| `gitnexus://repo/DeepResearchAgent/clusters` | All functional areas |
| `gitnexus://repo/DeepResearchAgent/processes` | All execution flows |
| `gitnexus://repo/DeepResearchAgent/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## Keeping the Index Fresh

After committing code changes, the GitNexus index becomes stale. Re-run analyze to update it:

```bash
npx gitnexus analyze
```

If the index previously included embeddings, preserve them by adding `--embeddings`:

```bash
npx gitnexus analyze --embeddings
```

To check whether embeddings exist, inspect `.gitnexus/meta.json` — the `stats.embeddings` field shows the count (0 means no embeddings). **Running analyze without `--embeddings` will delete any previously generated embeddings.**

> Claude Code users: A PostToolUse hook handles this automatically after `git commit` and `git merge`.

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
