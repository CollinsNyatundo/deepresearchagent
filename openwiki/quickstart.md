## 🔬 Deep Research Agent (DRA) Quickstart

A multi-module AI-powered research platform featuring deep iterative web research, workspace-isolated personal wiki notes, and intelligent document ingestion. This documentation will guide you through the key components and usage patterns of the DRA platform.

### Key Modules

| Module | Purpose | Key Features |
|--------|---------|--------------|
| **Research** | Autonomous deep web research engine | SSE streaming, plan review, mindmap (G6 v5), knowledge graph, multi-format export |
| **Notes** | Personal wiki with backlinks and graph | `[[wiki-link]]` syntax, D3 force-directed graph, 400ms auto-save, Moon Phase widget |
| **Documents** | OpenKB document ingestion & Q&A | Workspace-isolated `openkb/{ws_id}/`, tsvector FTS, multi-turn chat, Skill Factory |
| **Settings** | User-configurable defaults | LLM/provider selection, API key management, research defaults, appearance, workspace |

## 🚀 Quick Start

### Prerequisites
- Python ≥ 3.11
- Node.js ≥ 18
- OpenRouter API key (or Groq)
- Supabase project (URL, **service_role** key, JWT secret)

### 1. Clone & Install
```bash
git clone https://github.com/CollinsNyatundo/deepresearchagent.git
cd deepresearchagent

# Backend
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
# source .venv/bin/activate  # macOS / Linux
pip install -e .
pip install -e .[browser]    # optional: stealth scraping
python -m playwright install chromium
python -m camoufox fetch

# Environment
cp .env.example .env
# Edit .env with your keys
```

### 2. Configure Environment (`.env`)
```ini
OPENROUTER_API_KEY=sk-or-v1-your-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-service-role-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
# Optional:
TAVILY_API_KEY=...
BRAVE_SEARCH_API_KEY=...
GROQ_API_KEY=...
```

### 3. Run
```bash
# Terminal 1: Backend (FastAPI on :8000)
research serve
# or: uvicorn research_engine.api:app --reload --port 8000

# Terminal 2: Frontend (Vite on :5173)
cd frontend && npm install && npm run dev
```

Open `http://localhost:5173` — sign in with Supabase Auth, select/create a workspace, and start researching.

## 📂 OpenWiki Documentation Structure

```
openwiki/
├── quickstart.md              # ← You are here
├── architecture/
│   ├── overview.md            # High-level system design
│   ├── backend.md             # research_engine/ package structure
│   ├── frontend.md            # React modules & component architecture
│   ├── database.md            # Supabase schema, RLS, pgvector
│   └── decisions.md           # Key architectural choices (do not reverse)
├── workflows/
│   ├── research.md            # DRE loop, SSE streaming, plan review
│   ├── notes.md               # Wiki linking, auto-save, D3 graph
│   ├── documents.md           # OpenKB ingestion, chat, Skill Factory
│   └── knowledge-graph.md     # Graphify, MCP bridge, GitNexus
├── domain/
│   ├── research-formats.md    # Academic/Business/Product/Technical pipelines
│   ├── skills.md              # Built-in + external skill engine
│   └── citations.md           # Verification (CrossRef, OpenAlex, arXiv)
├── api/
│   ├── rest.md                # REST endpoints (runs, notes, docs, KG)
│   ├── sse.md                 # POST-based SSE event stream
│   └── auth.md                # Supabase JWT, workspace membership
├── data-models/
│   ├── models.md              # Pydantic v2 models (source of truth)
│   ├── migrations.md          # SQL migration history
│   └── rls.md                 # Row-level security patterns
├── operations/
│   ├── setup.md               # Local dev, env, migrations
│   ├── deployment.md          # Production (gunicorn, worker, worker)
│   └── debugging.md           # Common issues, logs, health checks
└── testing/
    ├── strategy.md            # Test organization, coverage gaps
    ├── e2e.md                 # Playwright E2E scenarios
    └── running.md             # pytest, live vs mocked tests
```

## 🗺️ Where to Go Next

| Goal | Start Here |
|------|------------|
| Understand the system architecture | [Architecture Overview](architecture/overview.md) |
| Learn the research workflow | [Research Workflow](workflows/research.md) |
| Work with notes/wiki | [Notes Workflow](workflows/notes.md) |
| Ingest & query documents | [Documents Workflow](workflows/documents.md) |
| Add a new API endpoint | [API Reference](api/rest.md) + [Backend Patterns](architecture/backend.md) |
| Understand data models | [Pydantic Models](data-models/models.md) |
| Run tests locally | [Testing Guide](testing/running.md) |
| Deploy to production | [Deployment](operations/deployment.md) |

## 🔑 Critical Conventions

| Rule | Details |
|------|---------|
| **All backend I/O is async** | LLM calls, Scrapling, file I/O, DB (wrapped in `asyncio.to_thread()`) |
| **Models are runtime params** | Never hardcode model IDs — use `LLMProvider._get_llm(model=...)` |
| **Scrapling is the only scraper** | 3-tier: Camoufox → Playwright → Basic HTTP |
| **Pydantic models = source of truth** | `research_engine/models.py` → mirror to `frontend/src/types/api.ts` |
| **Workspace-scoped everywhere** | All tables have `workspace_id` FK; all endpoints require it |
| **Service role key on backend** | RLS requires `auth.uid()`; service role bypasses for server ops |
| **POST-based SSE** | JWT cannot go in GET URL params |
| **Component organization** | Domain-based in `frontend/src/components/`, not inside `modules/` |

## 📚 Existing Documentation

The repo includes extensive developer docs in `/docs/`:
- `ARCHITECTURE.md` — Full system architecture (this wiki synthesizes it)
- `DATABASE_SCHEMA.md` — Tables, indexes, RLS, RPCs, triggers
- `DEVELOPER_GUIDE.md` — Setup, workflow, patterns, testing
- `SECURITY_GUIDE.md` / `SECURITY_AUDIT_REPORT.md` — RLS, injection mitigations
- `TESTING_STRATEGY_REPORT.md` — 489-test suite evaluation

---

*This wiki serves as an opinionated map and synthesis layer. For implementation details, always refer to the source files linked in each page.*