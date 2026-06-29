# DeepResearchAgent — Developer Guide

> **Audience:** Contributors and developers working on this codebase
> **Last Updated:** 2026-06-27

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Local Setup](#2-local-setup)
3. [Development Workflow](#3-development-workflow)
4. [Backend Patterns](#4-backend-patterns)
5. [Frontend Patterns](#5-frontend-patterns)
6. [Database Operations Pattern (SupabaseOps)](#6-database-operations-pattern-supabaseops)
7. [Research Formats Development](#7-research-formats-development)
8. [Skills Development & Plugin Loading](#8-skills-development--plugin-loading)
9. [Testing](#9-testing)
10. [Common Tasks](#10-common-tasks)
11. [Debugging Tips](#11-debugging-tips)
12. [Code Quality Gates](#12-code-quality-gates)

---

## 1. Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Use `pyenv` or `mise` |
| Node.js | 18+ | Use `nvm` |
| uv | latest | `pip install uv` |
| Git | 2.40+ | — |
| Supabase CLI | optional | For local DB dev |

---

## 2. Local Setup

### 2.1 Clone and Install Backend

```bash
git clone <repo>
cd DeepResearchAgent

# Create virtual env + install dependencies
uv sync

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1
# Activate (bash/zsh)
source .venv/bin/activate
```

### 2.2 Configure Environment

```bash
# Copy example config
cp config.example.toml config.toml

# Set required env vars (PowerShell)
$env:SUPABASE_URL  = "https://your-project.supabase.co"
$env:SUPABASE_KEY  = "eyJ..."    # service_role key — NOT the anon key!
$env:OPENROUTER_API_KEY = "sk-or-..."

# Or create a .env file (never commit it):
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJ...
OPENROUTER_API_KEY=sk-or-...
```

> [!CAUTION]
> Always use the **service_role** key for `SUPABASE_KEY` — never the anon key.
> The anon key triggers RLS which blocks all backend queries with `auth.uid() = NULL`.

### 2.3 Run Database Migrations

Apply the migration scripts in `research_engine/db/supabase/migrations/` sequentially in your Supabase dashboard SQL editor, or via CLI:

```bash
supabase db push
```

### 2.4 Start Backend

```bash
uvicorn research_engine.api:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### 2.5 Install and Start Frontend

```bash
cd frontend
npm install
npm run dev
# App: http://localhost:5173
```

### 2.6 Verify Setup

```bash
# Health check
curl http://localhost:8000/health

# Run test suite
.\.venv\Scripts\pytest
```

---

## 3. Development Workflow

### Branch Strategy

```
main          ← stable, deployable
feat/<name>   ← feature branches
fix/<name>    ← bug fixes
chore/<name>  ← maintenance
```

### Commit Convention

```
feat: add citation verification to research runs
fix: resolve SQL injection in wiki_links.find_backlinks
refactor: extract KG service from orchestrator
test: add unit tests for confidence scorer
chore: update ruff to 0.5.0
docs: add ARCHITECTURE.md
```

### PR Checklist

- [ ] `ruff check --fix && ruff format` passes
- [ ] `mypy research_engine/` has no new errors
- [ ] New endpoints have `verify_supabase_jwt` + `verify_workspace_membership`
- [ ] Pydantic models updated in both `models.py` AND `frontend/src/types/api.ts`
- [ ] `npm run build` in `frontend/` passes TypeScript
- [ ] Tests pass: `.\.venv\Scripts\pytest`

---

## 4. Backend Patterns

### 4.1 Adding a New API Endpoint

```python
# research_engine/api.py

@app.post("/my-feature")
async def my_feature(
    request: MyRequest,
    auth_result: dict = Depends(verify_supabase_jwt),
) -> MyResponse:
    user_id = auth_result["sub"]
    workspace_id = request.workspace_id

    # ALWAYS call this manually — it's not a Depends
    await verify_workspace_membership(user_id, workspace_id)

    # Use SupabaseOps layer instead of direct client calls
    db = get_db_ops()
    result = await db.get_my_feature_data(workspace_id)
    return MyResponse(...)
```

**After adding:**
```bash
py -m py_compile research_engine/api.py   # syntax check
cd frontend && npm run build               # TypeScript check
```

### 4.2 Adding a Pydantic Model

```python
# research_engine/models.py

class MyFeatureRequest(BaseModel):
    """Request body for my feature."""
    workspace_id: str
    query: str
    limit: int = Field(default=10, ge=1, le=100)

class MyFeatureResponse(BaseModel):
    """Response from my feature."""
    results: list[MyResult]
    total: int
```

Then mirror in TypeScript:

```typescript
// frontend/src/types/api.ts
export interface MyFeatureRequest {
    workspace_id: string;
    query: string;
    limit?: number;
}

export interface MyFeatureResponse {
    results: MyResult[];
    total: number;
}
```

### 4.3 Adding a Prompt

```python
# research_engine/llm/prompts.py

MY_FEATURE_PROMPT = """
You are a research assistant. Given the following context:

{context}

Answer the user's question: {question}

Return a JSON object with:
- answer: string
- confidence: float (0-1)
"""

# Usage in a service:
from research_engine.llm.prompts import MY_FEATURE_PROMPT
from research_engine.models import MyStructuredOutput

async def call_my_feature(context: str, question: str, model: str) -> MyStructuredOutput:
    llm = llm_provider._get_llm(model=model)
    prompt = MY_FEATURE_PROMPT.format(context=context, question=question)
    try:
        result = await llm.with_structured_output(MyStructuredOutput).ainvoke(prompt)
    except Exception:
        raw = await llm.ainvoke(prompt)
        result = MyStructuredOutput.model_validate_json(raw.content)
    return result
```

### 4.4 All I/O Must Be Async

```python
# ✅ Correct — async file I/O
import aiofiles
async with aiofiles.open(path, "r") as f:
    content = await f.read()

# ✅ Correct — DB query via SupabaseOps layer (handles thread-pooling internally)
db = get_db_ops()
rows = await db.get_notes(workspace_id)

# ✅ Correct — parallel async operations
results = await asyncio.gather(task1(), task2(), task3())

# ❌ Wrong — blocking the event loop
import time; time.sleep(2)
import requests; requests.get("https://example.com")
```

---

## 5. Frontend Patterns

### 5.1 Adding a New Component

```typescript
// frontend/src/components/my-domain/MyComponent.tsx
import { useState } from "react";
import { SomeIcon } from "lucide-react";

interface MyComponentProps {
    workspaceId: string;
    onSuccess: (result: MyResult) => void;
}

export default function MyComponent({ workspaceId, onSuccess }: MyComponentProps) {
    const [isLoading, setIsLoading] = useState(false);

    return (
        <div className="liquid-glass rounded-xl p-4">
            {/* Use liquid-glass class on containers */}
            {/* Use lucide-react for ALL icons */}
            <SomeIcon className="w-4 h-4 text-amber-400" />
        </div>
    );
}
```

Rules:
- Place in `frontend/src/components/{domain}/`
- Use `liquid-glass` class on panels/cards
- Never use `<div onClick>` — always `<button>`
- Lazy-load with `React.lazy()` if the component is >100KB or rarely used

### 5.2 Calling the API

```typescript
// frontend/src/api/client.ts — add new function here

export async function myFeature(
    workspaceId: string,
    request: MyFeatureRequest,
    token: string
): Promise<MyFeatureResponse> {
    const response = await fetch(`${API_BASE}/my-feature`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ workspace_id: workspaceId, ...request }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail ?? `HTTP ${response.status}`);
    }

    return response.json() as Promise<MyFeatureResponse>;
}
```

---

## 6. Database Operations Pattern (SupabaseOps)

To maintain safety and thread-concurrency (since the python `supabase` SDK is synchronous), all database operations must go through the **SupabaseOps** repository layer (`research_engine/db/supabase/ops.py`).

### 6.1 Calling Database Operations

```python
from research_engine.db.supabase.ops import SupabaseOps
from research_engine.db.supabase.client import get_supabase_client

# Instantiate the ops layer (typically handled by a global provider helper or directly in routes)
client = get_supabase_client()
db = SupabaseOps(client)

# Execute queries asynchronously
notes = await db.list_notes(workspace_id)
note = await db.get_note(note_id)
new_note = await db.create_note({"workspace_id": ws_id, "title": "New Title", "content": "..."})
```

### 6.2 Writing a New Database Operation

Add the method to `SupabaseOps` in `ops.py`. Implement async execution using `self._execute()`, which wraps the sync SDK queries in `asyncio.to_thread`:

```python
# research_engine/db/supabase/ops.py

async def get_recent_runs(self, workspace_id: str, limit: int = 10) -> list[dict]:
    """Retrieve recent research runs for a workspace."""
    result = await self._execute(
        self._client.table("research_runs")
        .select("*")
        .eq("workspace_id", workspace_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    return result.get("data", [])
```

---

## 7. Research Formats Development

Research formats define the structural output of research reports. They are stored under `research_engine/formats/`.

### 7.1 Creating a Research Format

1. Define a pipeline class in `research_engine/formats/pipelines.py` that inherits from `BaseFormatPipeline`.
2. Implement the `run` method, defining prompt templates and sections:

```python
# research_engine/formats/pipelines.py

class MyCustomFormatPipeline(BaseFormatPipeline):
    async def run(self, context: ResearchContext) -> str:
        # 1. Gather research sources and summaries
        # 2. Call LLM using formatting prompts
        # 3. Structure and return markdown report
        ...
```

3. Register your pipeline in `research_engine/formats/registry.py`:

```python
# research_engine/formats/registry.py

from research_engine.formats.pipelines import MyCustomFormatPipeline

register_format(
    name="my-custom-format",
    pipeline_class=MyCustomFormatPipeline,
    description="My custom formatted research report structure"
)
```

---

## 8. Skills Development & Plugin Loading

The system executes agent-level skills registered via `research_engine/skills/`.

### 8.1 Registering a Built-in Skill

Built-in skills are registered directly in `research_engine/skills/registry.py` under the appropriate domain namespace.

### 8.2 Adding an External Plugin Skill

External plugins are loaded from `external/pm-skills/`.
1. Create your skill files under a subdirectory in `external/pm-skills/` (e.g. `external/pm-skills/my-plugin/`).
2. Implement your skill schema metadata in `.claude-plugin/plugin.json` or as documented.
3. Validate your plugin setup:
```bash
python external/pm-skills/validate_plugins.py
```
Valid plugins are discovered and loaded at runtime by `research_engine/skills/external_loader.py`.

---

## 9. Testing

The codebase implements a comprehensive test suite of 489 tests across unit, database, integration, and E2E boundaries.

### Running Tests

```bash
# All tests
.\.venv\Scripts\pytest

# With coverage
.\.venv\Scripts\pytest --cov=research_engine --cov-report=html

# Running a specific test category
.\.venv\Scripts\pytest tests/db/ -v
```

### Test Directory Structure

```
tests/
├── checkpoints/              # Checkpoint management tests
├── citations/                # Citation verifier and adapter tests
├── cost/                     # Token usage and cache alignment tests
├── db/                       # SupabaseOps unit & workspace isolation tests
│   └── supabase/
│       └── test_ops.py
├── e2e/                      # End-to-end user scenarios and mock client tests
├── export/                   # Report export format tests
├── quality/                  # Quality metrics and reviewer tests
├── research/                 # Research formats, pipelines, and registries tests
├── sources/                  # Scrapers, caches, and search adapters tests
├── sse/                      # Server-Sent Events stream tests
└── test_auth.py etc.         # Legacy base test suite
```

---

## 10. Common Tasks

### Run Linting and Auto-Fix

```bash
# Python
ruff check --fix research_engine/
ruff format research_engine/

# TypeScript (when ESLint is configured)
cd frontend && npx eslint src/ --fix
```

### Build Frontend (Type Check)

```bash
cd frontend && npm run build
```

---

## 11. Debugging Tips

### 403 Errors on All Requests

Almost always caused by using the **anon** key instead of the **service_role** key for `SUPABASE_KEY`. The anon key triggers RLS, and `auth.uid()` returns NULL for service-level calls, blocking everything.

### SSE Not Streaming

- Check CORS: `cors_origins` in `config.toml` must include `http://localhost:5173`.
- Check that the frontend is using POST (not GET) for the stream endpoint.
- Check that `run_id` exists in the database before streaming.

---

## 12. Code Quality Gates

These must pass before merging:

| Gate | Command | Threshold |
|------|---------|-----------|
| Linting | `ruff check research_engine/` | 0 errors |
| Formatting | `ruff format --check research_engine/` | Pass |
| Type Check | `mypy research_engine/ --ignore-missing-imports` | < 50 errors |
| Frontend Build | `cd frontend && npm run build` | Pass |
| Tests | `.\.venv\Scripts\pytest` | All pass |
| API Syntax | `py -m py_compile research_engine/api.py` | Exit 0 |

---

*Generated: 2026-06-27 | Maintained with the codebase*
