# DeepResearchAgent — Developer Guide

> **Audience:** Contributors and developers working on this codebase
> **Last Updated:** 2026-06-26

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Local Setup](#2-local-setup)
3. [Development Workflow](#3-development-workflow)
4. [Backend Patterns](#4-backend-patterns)
5. [Frontend Patterns](#5-frontend-patterns)
6. [Database Patterns](#6-database-patterns)
7. [Testing](#7-testing)
8. [Common Tasks](#8-common-tasks)
9. [Debugging Tips](#9-debugging-tips)
10. [Code Quality Gates](#10-code-quality-gates)

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

Apply `supabase/migrations/combined_migration.sql` in your Supabase dashboard SQL editor, or via CLI:

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
python -m pytest tests/ -v
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
- [ ] Tests pass: `pytest tests/ -v`

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

    # All Supabase calls must be wrapped in asyncio.to_thread()
    result = await asyncio.to_thread(
        lambda: supabase.table("my_table").select("*").execute()
    )
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

# ✅ Correct — Supabase (sync client) wrapped in asyncio.to_thread
result = await asyncio.to_thread(
    lambda: supabase.table("notes").select("*").eq("workspace_id", ws_id).execute()
)

# ✅ Correct — parallel async operations
results = await asyncio.gather(task1(), task2(), task3())

# ❌ Wrong — blocking the event loop
import time; time.sleep(2)
import requests; requests.get("https://example.com")
```

### 4.5 Error Handling Pattern

```python
from fastapi import HTTPException

@app.get("/runs/{run_id}/report")
async def get_report(run_id: str, auth_result: dict = Depends(verify_supabase_jwt)):
    try:
        user_id = auth_result["sub"]
        await verify_workspace_membership(user_id, workspace_id)
        report = await asyncio.to_thread(lambda: fetch_report(run_id))
        if not report:
            raise HTTPException(status_code=404, detail="Run not found")
        return report
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Failed to get report for {run_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### 4.6 Adding a Search Provider

```python
# research_engine/sources/web_search.py

class MySearchProvider:
    """My custom search provider."""

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        # Implement using Scrapling (not requests/httpx)
        ...

# Register in factory:
def get_search_provider(provider: str | None = None) -> SearchProvider:
    match provider or config.search.default_provider:
        case "my_provider":
            return MySearchProvider()
        case _:
            return DuckDuckGoProvider()
```

---

## 5. Frontend Patterns

### 5.1 Adding a New Component

```typescript
// frontend/src/components/my-domain/MyComponent.tsx
import { useState } from "react";
import { SomeIcon } from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";

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

### 5.3 Wiki Link Syntax

Supported in Notes and Documents modules:

| Syntax | Target | Handler |
|--------|--------|---------|
| `[[Note Title]]` | Note by title | `handleWikiNavigate("note", title)` |
| `[[run:uuid]]` | Research run | `handleWikiNavigate("run", runId)` |
| `[[doc:filename]]` | Document | `handleWikiNavigate("doc", filename)` |
| `[[wiki:Concept]]` | Wiki page | `handleWikiNavigate("wiki", concept)` |

> `entity:` is parsed but **not yet implemented** in frontend handlers.

---

## 6. Database Patterns

### 6.1 Adding a New Column

1. Add column to Supabase table (dashboard or migration SQL)
2. Update Pydantic model in `research_engine/models.py`
3. Update TypeScript type in `frontend/src/types/api.ts`
4. Update queries in `research_engine/api.py` or `db/supabase/`
5. Update frontend components that display/edit the field

### 6.2 Supabase Query Patterns

```python
# SELECT
result = await asyncio.to_thread(
    lambda: supabase.table("notes")
        .select("id, title, content, updated_at")
        .eq("workspace_id", workspace_id)
        .order("updated_at", desc=True)
        .limit(50)
        .execute()
)
rows = result.data

# INSERT
result = await asyncio.to_thread(
    lambda: supabase.table("notes")
        .insert({"workspace_id": ws_id, "title": title, "content": content})
        .execute()
)

# UPDATE
await asyncio.to_thread(
    lambda: supabase.table("notes")
        .update({"content": new_content, "updated_at": "now()"})
        .eq("id", note_id)
        .execute()
)

# DELETE
await asyncio.to_thread(
    lambda: supabase.table("notes").delete().eq("id", note_id).execute()
)
```

### 6.3 Full-Text Search

```python
# Notes full-text search
result = await asyncio.to_thread(
    lambda: supabase.table("notes")
        .select("id, title, content, updated_at")
        .eq("workspace_id", workspace_id)
        .text_search("search_vector", query, {"type": "websearch"})
        .limit(20)
        .execute()
)
```

---

## 7. Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=research_engine --cov-report=html

# Specific test file
pytest tests/test_research_pipeline.py -v

# Async tests
pytest tests/ -v --asyncio-mode=auto
```

### Test Structure

```
tests/
├── test_research_pipeline.py   # Integration test — full pipeline
├── test_models.py              # Pydantic model validation
├── test_wiki_links.py          # Wiki link parsing
├── test_cache.py               # Cache behavior
└── conftest.py                 # Shared fixtures
```

### Writing a Test

```python
# tests/test_my_feature.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_supabase():
    with patch("research_engine.api.supabase") as mock:
        mock.table.return_value.select.return_value.execute.return_value.data = []
        yield mock

@pytest.mark.asyncio
async def test_my_feature_success(mock_supabase):
    from research_engine.api import my_feature
    result = await my_feature(...)
    assert result.total == 0
```

---

## 8. Common Tasks

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

### Verify API Syntax

```bash
py -m py_compile research_engine/api.py
```

### Check MyPy Types

```bash
mypy research_engine/ --ignore-missing-imports
```

### Apply Migrations

```bash
# In Supabase SQL Editor — paste contents of:
supabase/migrations/combined_migration.sql
```

### Generate Knowledge Graph Manually

```bash
python -m research_engine.cli kg-build --run-id <uuid>
```

---

## 9. Debugging Tips

### Backend Not Starting

```bash
# Check for import errors
py -m py_compile research_engine/api.py

# Check env vars
python -c "import os; print(os.getenv('SUPABASE_URL'))"

# Check port conflict
netstat -ano | findstr :8000
```

### 403 Errors on All Requests

Almost always caused by using the **anon** key instead of the **service_role** key for `SUPABASE_KEY`. The anon key triggers RLS, and `auth.uid()` returns NULL for service-level calls, blocking everything.

### SSE Not Streaming

- Check CORS: `cors_origins` in `config.toml` must include `http://localhost:5173`
- Check that the frontend is using POST (not GET) for the stream endpoint
- Check that `run_id` exists in the database before streaming

### Supabase Connection Errors

```python
# Test connection
python -c "
from research_engine.db.supabase.client import get_supabase_client
client = get_supabase_client()
print(client.table('workspaces').select('id').limit(1).execute())
"
```

### Scrapling/Browser Errors

```bash
# Install Camoufox binary
python -m camoufox fetch

# Install Playwright browsers
playwright install chromium
```

### Knowledge Graph Not Building

```bash
# Check Graphify is installed
graphify --version

# Check graphify-out directory
ls research_engine/graphify-out/

# Force LLM fallback by setting graphify.enabled = false in config.toml
```

---

## 10. Code Quality Gates

These must pass before merging:

| Gate | Command | Threshold |
|------|---------|-----------|
| Linting | `ruff check research_engine/` | 0 errors |
| Formatting | `ruff format --check research_engine/` | Pass |
| Type Check | `mypy research_engine/ --ignore-missing-imports` | < 50 errors |
| Frontend Build | `cd frontend && npm run build` | Pass |
| Tests | `pytest tests/ -v` | All pass |
| API Syntax | `py -m py_compile research_engine/api.py` | Exit 0 |

### Quick Quality Check Script

```bash
# Run all gates
ruff check --fix research_engine/ && \
ruff format research_engine/ && \
py -m py_compile research_engine/api.py && \
pytest tests/ -v && \
cd frontend && npm run build
```

---

*Generated: 2026-06-26 | Maintained with the codebase*
