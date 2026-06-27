# DeepResearchAgent — Documentation Index

> **Repository:** `DeepResearchAgent`
> **Last Updated:** 2026-06-26

---

## Core Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture, module breakdown, data flows, API summary |
| [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) | Local setup, development workflow, coding patterns |
| [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) | Full schema reference — tables, indexes, RLS, RPCs |
| [SECURITY_GUIDE.md](./SECURITY_GUIDE.md) | Known vulnerabilities, mitigations, security checklist |

---

## Existing Audit Reports

| Report | Description |
|--------|-------------|
| [BEST_PRACTICES_REPORT.md](./BEST_PRACTICES_REPORT.md) | Best practices assessment and recommendations |
| [COMPREHENSIVE_CODE_REVIEW_REPORT.md](./COMPREHENSIVE_CODE_REVIEW_REPORT.md) | Full code review findings |
| [FINAL_COMPREHENSIVE_REVIEW_REPORT.md](./FINAL_COMPREHENSIVE_REVIEW_REPORT.md) | Final consolidated review |
| [PERFORMANCE_ANALYSIS_REPORT.md](./PERFORMANCE_ANALYSIS_REPORT.md) | Performance bottlenecks and optimizations |
| [SECURITY_AUDIT_REPORT.md](./SECURITY_AUDIT_REPORT.md) | Security audit findings |

---

## Quick Reference

### System Modules

| Module | Purpose | Key Entry Points |
|--------|---------|-----------------|
| **Research** | Deep web research + LLM synthesis | `POST /research/comprehensive` → `POST /research/stream` |
| **Notes** | Personal wiki with backlinks | `GET/POST/PATCH /notes` |
| **Documents** | Document Q&A (OpenKB) | `POST /documents/upload` → `POST /documents/query` |

### Critical Rules

1. **Supabase key:** Always `service_role` on the backend — never `anon`
2. **All I/O:** Must be `async` — wrap Supabase calls in `asyncio.to_thread()`
3. **No hardcoded models:** Use `LLMProvider._get_llm(model=...)` with runtime model selection
4. **Scraping only via Scrapling:** Never add `requests`, `httpx`, or `urllib3`
5. **Models are source of truth:** Update `models.py` → then `types/api.ts` → then `client.ts`
6. **Wiki links:** `[[Title]]` | `[[run:uuid]]` | `[[doc:filename]]` | `[[wiki:Concept]]`

### Known P0 Security Issues (Must Fix)

- ⚠️ SQL injection in `wiki_links.py` — use parameterized Supabase client methods
- ⚠️ SQL injection in `api.py` — avoid dynamic f-string SQL construction

### Architecture Decision Summary

| Decision | Rule |
|----------|------|
| DRE implementation | Re-implemented (not vendored) — original coupled to Gemini + Tavily |
| Research depth | Default=5 (exhaustive, 30 cycles) — do not lower without consent |
| SSE pattern | POST-based (not GET) — JWT can't be in URL params |
| Visualization | D3 for Notes graph, G6 for Research mindmap — do not swap |
| Components | Live in `components/`, not `modules/` — modules are thin containers |

---

## Contributing

1. Read [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) for setup and patterns
2. Read [SECURITY_GUIDE.md](./SECURITY_GUIDE.md) before touching auth/DB code
3. Check [ARCHITECTURE.md](./ARCHITECTURE.md) for system design context
4. See `AGENTS.md` in the project root for the definitive project rules (maintained by the team)

---

*Documentation generated 2026-06-26. Maintained alongside the codebase.*
