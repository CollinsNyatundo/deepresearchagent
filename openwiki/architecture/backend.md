# Backend Architecture

## Package layout

```
research_engine/
├── api.py                    # ~2,700 lines — ALL FastAPI endpoints (REST + SSE + KG + GitNexus)
├── auth.py                   # Supabase JWT verification + workspace membership check
├── cli.py                    # Typer CLI entry point
├── config.py                 # Pydantic config models (LLM, Search, Scraping, Research, API, GitHub, Graphify)
├── models.py                 # Pydantic v2 models — SOURCE OF TRUTH for all data structures
├── worker.py                 # Separate FastAPI webhook worker (HMAC verified)
├── setup_shims.py            # Compatibility shims
│
├── agent/                    # DRE (Deep Research Reflect Evolve) orchestrator
│   ├── orchestrator.py       # Main async research loop (30 cycles, SSE, crossover, retry)
│   ├── planner.py            # Research plan generation
│   ├── searcher.py           # Search + scrape coordination, reranking, validation
│   ├── router.py             # Intent classification router (web/github)
│   ├── crossover.py          # Cross-domain connection detection
│   ├── retry.py              # Protocol-H reflective retry
│   └── context.py            # ResearchContext state management
│
├── formats/                  # Pluggable Research Formats Engine
│   ├── registry.py           # Format registration/discovery
│   └── pipelines.py          # Specialized synthesis pipelines per format
│
├── skills/                   # Dynamic Skill Execution Engine
│   ├── registry.py           # Built-in + dynamic skill registry
│   └── external_loader.py    # External plugin skill loading
│
├── db/supabase/
│   ├── client.py             # Sync Supabase client (wrapped in asyncio.to_thread)
│   ├── ops.py                # SupabaseOps — async DB layer
│   └── migrations/           # SQL migrations
│
├── export/                   # Multi-format export (MD, PDF, DOCX, XLSX, JSON)
├── citations/                # Citation extraction + verification (CrossRef, OpenAlex, Semantic Scholar, arXiv)
├── quality/                  # Report quality assessment
├── cost/                     # Token cost tracking
├── sse/                      # SSE event emission + streaming helpers
├── output/                   # File storage + mindmap (G6) + report formatting
├── utils/                    # openkb.py, wiki_links.py
├── llm/                      # LLMProvider (OpenRouter gateway), prompts.py
├── sources/                  # Search & scraping layer
└── knowledge_graph/          # Graphify integration
```

## Key modules

### `api.py` — The endpoint surface

- Single FastAPI app instance; all endpoints are defined here.
- Startup/shutdown in `@asynccontextmanager _lifespan`:
  - Creates `outputs/` directory
  - Verifies Supabase connectivity
  - Optionally seeds a dev bypass workspace when `DEV_AUTH_BYPASS=true`
- All endpoints perform inline auth:
  ```python
  user = await verify_supabase_jwt(authorization)
  await verify_workspace_membership(user.id, workspace_id)
  ```
- Uses `asyncio.to_thread()` to run the synchronous Supabase client without blocking the event loop.

### `agent/orchestrator.py` — The research loop

- Runs up to 30 cycles driven by `ResearchContext`.
- Emits SSE events at every state transition via `ResearchState` enum.
- Phases: intent classification → planning → decomposition → search → scrape → validate → synthesize → reflect → (retry) → cycle complete.
- Generates mindmap and knowledge graph artifacts at the end.

### `sources/web_scraper.py` — Scrapling 3-tier fallback

| Tier | Fetcher | Purpose |
|------|---------|---------|
| 1 | `StealthyFetcher` (Camoufox) | Cloudflare / bot detection |
| 2 | `DynamicFetcher` (Playwright) | JavaScript rendering |
| 3 | `Fetcher` (Basic HTTP) | Static pages — always available |

Never add `requests`, `httpx`, or `urllib3` for scraping — Scrapling is the sole layer.

### `knowledge_graph/builder.py` — Graphify integration

- Exports research corpus to `graphify-out/`
- Spawns Graphify subprocess (fast AST mode or deep LLM mode)
- Falls back to LLM-based KG extraction if Graphify is unavailable
- Stores nodes/edges in Supabase (`graph_nodes`, `graph_edges`) plus local JSON

### `db/supabase/ops.py` — SupabaseOps

Async wrapper around the sync Supabase client:
- Encapsulates workspace filtering (`eq("workspace_id", ...)`)
- Unified error handling via `SupabaseError`
- Used by every endpoint in `api.py`

## Config & models

- `config.py` loads `config.toml` + environment variables via `pydantic-settings`.
- `models.py` is the **single source of truth** for all request/response/event shapes.
- Frontend TypeScript types in `frontend/src/types/api.ts` **must mirror** `models.py` exactly.

## Change guidance

| Change | What to update |
|--------|----------------|
| New API endpoint | `api.py`, `models.py` (request/response), `frontend/src/types/api.ts`, `frontend/src/api/client.ts` |
| New model field | `models.py` → `types/api.ts` → `npm run build` in `frontend/` |
| New research state | `models.py` (`ResearchState` enum) → orchestrator state machine → frontend SSE handler |
| New format | `formats/registry.py` + `formats/pipelines.py` → `models.py` format field |