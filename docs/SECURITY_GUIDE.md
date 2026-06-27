# DeepResearchAgent — Security Guide

> **Last Updated:** 2026-06-26
> **Security Contact:** (internal team)
> **Scope:** Backend, database, authentication, and dependency risks

---

## 1. Security Posture Summary

| Severity | Count | Status |
|----------|-------|--------|
| 🔴 Critical (P0) | 2 | **Open — requires immediate remediation** |
| 🟠 High (P1) | 3 | Open |
| 🟡 Medium (P2) | 4 | Open |
| 🟢 Low (P3) | 3 | Mitigated / Accepted |

---

## 2. Critical Vulnerabilities (P0)

### 2.1 SQL Injection — `wiki_links.py`

**Location:** `research_engine/utils/wiki_links.py`

**Risk:** Direct string interpolation of user input into SQL queries. An attacker who controls a wiki-link target (e.g., `[[note:'; DROP TABLE notes;--]]`) can execute arbitrary SQL against the Supabase PostgreSQL instance.

**Remediation:**

```python
# ❌ Vulnerable (current):
query = f"SELECT * FROM notes WHERE title = '{user_input}'"

# ✅ Safe — use parameterized queries via Supabase client:
result = supabase.table("notes").select("*").eq("title", user_input).execute()
# The Supabase Python client uses parameterized queries internally.
```

**Workaround (temporary):** Validate/sanitize `user_input` with `re.sub(r"[^\w\s-]", "", text)` before any DB use. This is not a permanent fix.

---

### 2.2 SQL Injection — `api.py` (Dynamic Query Construction)

**Location:** `research_engine/api.py` — multiple endpoints

**Risk:** Dynamic SQL string construction using f-strings with unvalidated request parameters. Specific endpoints that accept `filter`, `order`, or `search` query params are highest risk.

**Remediation:**

- **All DB access must use the Supabase Python client** (`.select()`, `.eq()`, `.ilike()`, etc.) which passes parameters safely.
- If raw SQL is required (e.g., `match_graph_nodes` RPC), use the Supabase `.rpc()` method with named parameters:

```python
# ✅ Safe RPC call
result = await asyncio.to_thread(
    lambda: supabase.rpc("match_graph_nodes", {
        "query_embedding": embedding,
        "match_threshold": 0.7,
        "match_count": 10,
    }).execute()
)
```

---

## 3. High Severity Vulnerabilities (P1)

### 3.1 Path Traversal — `storage.py`

**Location:** `research_engine/output/storage.py`

**Risk:** User-controlled filenames or workspace IDs could potentially traverse the filesystem (e.g., `workspace_id = "../../etc/passwd"`).

**Status:** Partially mitigated — workspace IDs are UUIDs validated by Supabase. However, filenames derived from research query strings are not fully sanitized.

**Remediation:**

```python
import re
from pathlib import Path

def safe_filename(name: str) -> str:
    """Strip path-unsafe characters from user-provided names."""
    return re.sub(r"[^\w\s.-]", "_", name)[:200]

def safe_workspace_path(base: Path, workspace_id: str) -> Path:
    """Ensure workspace path doesn't escape the base directory."""
    # UUID validation
    import uuid
    uuid.UUID(workspace_id)  # raises ValueError for invalid UUIDs
    path = base / workspace_id
    # Resolve and assert it's under base
    resolved = path.resolve()
    if not str(resolved).startswith(str(base.resolve())):
        raise ValueError(f"Path traversal detected: {workspace_id}")
    return path
```

---

### 3.2 Missing Rate Limiting

**Location:** All API endpoints in `research_engine/api.py`

**Risk:** No rate limiting on research endpoints — a single actor can exhaust OpenRouter API credits or overload the LLM pipeline.

**Remediation:** Add slowapi or similar middleware:

```python
# requirements.txt: slowapi
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Per-endpoint (tighter on expensive operations):
@app.post("/research/comprehensive")
@limiter.limit("10/hour")   # research runs are expensive
async def start_research(...):
    ...

@app.get("/notes")
@limiter.limit("200/minute")
async def list_notes(...):
    ...
```

---

### 3.3 DEV_AUTH_BYPASS Must Never Reach Production

**Location:** `research_engine/auth.py`

**Risk:** `DEV_AUTH_BYPASS=true` disables all JWT verification, allowing unauthenticated access to all endpoints.

**Status:** Enforced by convention, not by code. There is no runtime check that prevents this env var from being set in production.

**Remediation:**

```python
# research_engine/auth.py — add production guard:
import os

DEV_AUTH_BYPASS = os.getenv("DEV_AUTH_BYPASS", "false").lower() == "true"

if DEV_AUTH_BYPASS:
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    if ENVIRONMENT == "production":
        raise RuntimeError(
            "DEV_AUTH_BYPASS=true is not allowed in production. "
            "Set ENVIRONMENT=production and DEV_AUTH_BYPASS=false."
        )
    import warnings
    warnings.warn("DEV_AUTH_BYPASS=true — authentication is DISABLED", stacklevel=2)
```

---

## 4. Medium Severity Vulnerabilities (P2)

### 4.1 CORS Misconfiguration Risk

**Configuration:** `cors_origins` in `config.toml`

**Risk:** If deployed with `cors_origins = ["*"]`, any website can make authenticated requests using the user's JWT (CSRF-like).

**Requirement:** Always explicitly list origins:
```toml
cors_origins = ["https://your-app.vercel.app"]
```

Never use `["*"]` in production.

---

### 4.2 Supabase `anon` Key in Frontend

**Location:** `frontend/src/lib/supabase.ts`

**Risk:** The anon key is public (in the browser bundle). This is expected by Supabase design — RLS enforces security. However, if RLS policies have gaps, data leaks are possible.

**Requirement:** Audit all RLS policies after any schema change. Every table must have the workspace-scoped RLS pattern applied.

---

### 4.3 Document Upload — Missing File Type Validation

**Location:** `POST /documents/upload`

**Risk:** No server-side file type validation. Accepting arbitrary files could allow script uploads or XML entity expansion (XXE) attacks through document parsers.

**Remediation:**

```python
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

async def validate_upload(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}")
    # Also check file size
    if file.size > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")
```

---

### 4.4 In-Memory Chat Sessions Not Persisted

**Location:** Documents module chat (`POST /documents/chat`)

**Risk:** `session_id`-keyed chat history is stored in a process-level Python dict. This is not a security vulnerability per se, but it means:
- Sessions are lost on process restart
- Memory grows unbounded if sessions are not expired
- Cannot be shared across multiple worker processes

**Remediation:** Persist sessions in Supabase or Redis with a TTL.

---

## 5. Low Severity / Accepted Risks (P3)

### 5.1 Knowledge Graph Local File Access

**Risk:** The knowledge graph builder writes files to `graphify-out/` on the local filesystem. These files contain research data but are not exposed via any API endpoint.

**Status:** Accepted. Files are workspace-scoped by directory path.

---

### 5.2 SQLite Cache is Process-Local

**Risk:** The SQLite TTL cache (`cache.py`) is not shared across multiple API worker processes. Multiple workers will re-fetch the same content.

**Status:** Accepted for now. Remediation: migrate to Redis cache.

---

### 5.3 HMAC Webhook Secret Rotation

**Risk:** The webhook HMAC secret in `worker.py` does not have an automated rotation mechanism.

**Status:** Accepted. Rotate manually via environment variable re-deployment.

---

## 6. Security Checklist for New Code

When adding new features, verify:

- [ ] All SQL access uses Supabase client methods (not raw f-string queries)
- [ ] All file paths are validated against a base directory
- [ ] New endpoints call `verify_supabase_jwt` + `verify_workspace_membership`
- [ ] File uploads validate MIME type and size
- [ ] No secrets are logged or included in error responses
- [ ] Rate limits are applied to new expensive endpoints
- [ ] RLS policy added for new tables

---

## 7. Dependency Security

```bash
# Audit Python dependencies
pip-audit  # or: uv audit

# Audit Node.js dependencies
cd frontend && npm audit

# Check for outdated packages
pip list --outdated
cd frontend && npm outdated
```

Key high-risk dependencies to keep updated:

| Package | Risk Area |
|---------|-----------|
| `scrapling` | Browser automation (Camoufox/Playwright) |
| `langchain-openai` | LLM API client |
| `supabase` | Database client |
| `fastapi` | Web framework |
| `pydantic` | Data validation |

---

## 8. Secrets Management

| Secret | Where | How |
|--------|-------|-----|
| `SUPABASE_KEY` (service_role) | Env var | Never commit. Rotate via Supabase dashboard |
| `OPENROUTER_API_KEY` | Env var | Never commit. Rotate via OpenRouter dashboard |
| `WEBHOOK_HMAC_SECRET` | Env var | Rotate by redeploying with new value |
| Supabase JWT secret | Supabase internal | Auto-rotated by Supabase |

**Never:**
- Log API keys or JWTs
- Commit `config.toml` to version control
- Include secrets in error messages
- Store secrets in the frontend bundle

---

*Generated from security audit. See also: `docs/SECURITY_AUDIT_REPORT.md`*
