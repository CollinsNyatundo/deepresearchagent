# DeepResearchAgent — Documentation Index

> **Repository:** `DeepResearchAgent`
> **Last Updated:** 2026-06-27

---

## Core Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture, module breakdown, data flows, API summary |
| [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) | Local setup, development workflow, coding patterns, formats, and skills registries |
| [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) | Full schema reference — tables (including checkpoints), indexes, RLS, RPCs |
| [SECURITY_GUIDE.md](./SECURITY_GUIDE.md) | Known vulnerabilities, mitigations, security checklist |

---

## Existing Audit Reports

| Report | Description |
|--------|-------------|
| [BEST_PRACTICES_REPORT.md](./BEST_PRACTICES_REPORT.md) | Best practices assessment and async/await compliance recommendations |
| [COMPREHENSIVE_CODE_REVIEW_REPORT.md](./COMPREHENSIVE_CODE_REVIEW_REPORT.md) | Full code review findings, static analysis, and code quality hotspots |
| [FINAL_COMPREHENSIVE_REVIEW_REPORT.md](./FINAL_COMPREHENSIVE_REVIEW_REPORT.md) | Final consolidated review, progress status, and Sprint plans |
| [PERFORMANCE_ANALYSIS_REPORT.md](./PERFORMANCE_ANALYSIS_REPORT.md) | Performance bottlenecks and thread pool optimizations |
| [SECURITY_AUDIT_REPORT.md](./SECURITY_AUDIT_REPORT.md) | Security audit findings (SQL injection analysis & path traversal mitigations) |
| [TESTING_STRATEGY_REPORT.md](./TESTING_STRATEGY_REPORT.md) | Testing strategy evaluation and analysis of the expanded 489-test suite |

---

## Quick Reference

### System Modules

| Module | Purpose | Key Entry Points |
|--------|---------|-----------------|
| **Research** | Iterative deep-web research + LLM synthesis | `POST /research/comprehensive` → `POST /research/stream` |
| **Notes** | Personal wiki with backlinks | `GET/POST/PATCH /notes` |
| **Documents** | Document Q&A (OpenKB) | `POST /documents/upload` → `POST /documents/query` |

### Critical Rules

1. **Supabase key:** Always `service_role` on the backend — never `anon`.
2. **All Database operations:** Must be executed via the async `SupabaseOps` layer (`research_engine/db/supabase/ops.py`), which delegates sync client calls to thread pools.
3. **No hardcoded models:** Use `LLMProvider._get_llm(model=...)` with runtime model selection.
4. **Scraping only via Scrapling:** Never add `requests`, `httpx`, or `urllib3`.
5. **Models are source of truth:** Update `models.py` → then `types/api.ts` → then `client.ts`.
6. **Wiki links:** `[[Title]]` | `[[run:uuid]]` | `[[doc:filename]]` | `[[wiki:Concept]]`.

### Database Tables (10 Total)

1. `workspaces` (Root multi-tenant registry)
2. `workspace_members` (Composite mapping of users to workspaces)
3. `research_runs` (Research query, status, plan, mindmap, report)
4. `graph_nodes` (pgvector 1536-dim concepts/entities)
5. `graph_edges` (Relationships between nodes)
6. `notes` (Wiki notes with FTS index)
7. `documents` (Uploaded document metadata)
8. `document_tags` (Ingested document category tags)
9. `citation_verifications` (CrossRef/OpenAlex verification cache)
10. `checkpoints` (Research loop recovery snapshots)

---

## Contributing

1. Read [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) for setup and patterns
2. Read [SECURITY_GUIDE.md](./SECURITY_GUIDE.md) before touching auth/DB code
3. Check [ARCHITECTURE.md](./ARCHITECTURE.md) for system design context
4. See `AGENTS.md` in the project root for the definitive project rules (maintained by the team)

---

*Documentation generated 2026-06-27. Maintained alongside the codebase.*
