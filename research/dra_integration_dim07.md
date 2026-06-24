# Dimension 07: Cross-Agent Memory & Learning

## Overview

This dimension investigates the feasibility of cross-agent memory systems based on headroom's SharedContext and learn features. It covers memory storage, deduplication, failure mining, and workspace isolation.

---

## Key Findings

### 1. Cross-Agent Memory is a Niche Feature with Limited Proven Value

**Claim:** headroom's SharedContext compresses and stores key findings across agent sessions, but there is limited independent research validating its effectiveness for research workflows.[^1]

**Source:** headroom documentation on shared context

**URL:** https://github.com/chopratejas/headroom/blob/main/docs/content/docs/shared-context.mdx

**Date:** 2026-01-07

**Excerpt:**
> "SharedContext compresses what moves between agents using Headroom's compression pipeline, typically saving ~80% of tokens on agent handoffs."

**Context:** The 80% figure is from headroom's own documentation, not independent research. For DRA's use case, "cross-agent memory" means sharing findings between research runs within the same workspace. The value proposition is:
- "Auto-surface relevant prior findings when starting new research"
- "Prevent redundant work across cycles within a run"

However, DRA's research runs are typically independent queries (e.g., "AI in healthcare" vs. "blockchain supply chain"). Cross-run memory would only be useful if users run related queries sequentially.

**Confidence:** Medium

---

### 2. Vector Databases Are the Standard for Semantic Memory

**Claim:** Chroma, Pinecone, Weaviate, and Qdrant are the leading vector databases for semantic search and memory retrieval. They store embeddings and support similarity search.[^2]

**Source:** Chroma Documentation / Vector Database Comparison

**URL:** https://docs.trychroma.com/

**Date:** 2026

**Excerpt:**
> "Chroma is the open-source embedding database. It makes it easy to build LLM apps by making knowledge, facts, and skills pluggable for LLMs."

**Context:** DRA already has a Knowledge Graph module (Graphify + LLM fallback). Adding a vector database for cross-run memory would introduce another storage system. The DRA plan should clarify whether cross-run memory uses:
- Supabase (existing, but not designed for vector search)
- Chroma/Qdrant (new dependency, adds complexity)
- The existing Knowledge Graph (reuses infrastructure)

The simplest approach: store compressed findings in Supabase and use full-text search (PostgreSQL `tsvector`) for retrieval. This reuses existing infrastructure without adding dependencies.

**Confidence:** High

---

### 3. Failure Mining (`headroom learn`) is Vague

**Claim:** `headroom learn` mines failed sessions and writes corrections to `CLAUDE.md` / `AGENTS.md`, but the exact algorithm is not documented.[^3]

**Source:** headroom README

**URL:** https://github.com/chopratejas/headroom

**Date:** 2026-06-22

**Excerpt:**
> "`headroom learn` — mines failed sessions, writes corrections to `CLAUDE.md` / `AGENTS.md`."

**Context:** The DRA plan proposes a `learn.py` that "mines failed/low-quality runs to generate correction patterns." This is inspired by `headroom learn` but the mechanism is unclear. What constitutes a "failed" run? How are correction patterns generated? How are they applied? The plan does not specify.

Without a concrete algorithm, this feature is not implementable. It's better to defer this to a future research phase.

**Confidence:** High

---

### 4. Workspace Isolation is Critical for Multi-Tenant Systems

**Claim:** In a multi-tenant SaaS, cross-run memory must be strictly scoped to workspaces. Leaking findings between workspaces is a privacy and security violation.[^4]

**Source:** General SaaS security best practices

**URL:** N/A

**Date:** 2026

**Excerpt:** N/A

**Context:** The DRA plan's `research_memory` table has `workspace_id` but no `user_id`. If a workspace has multiple members, all members see all memory items. This may be acceptable for team workspaces but should be documented. More critically, the plan must ensure:
- Memory items cannot be retrieved from other workspaces (RLS policy)
- Pinned memory items are visible to all workspace members (intentional)
- Deleted workspaces delete all associated memory (cascade)

**Confidence:** High

---

## Tensions and Counter-Arguments

### Tension 1: Memory Value vs. Storage Cost

Cross-run memory stores compressed findings for every research run. For 1000 runs/month with 10 findings each, that's 10,000 memory items. If each item is 1KB compressed, that's 10MB/month — trivial in storage terms. But the query cost (searching 10,000 items for relevance) may not be trivial.

**Counter-argument:** For a SaaS product, 10MB/month is negligible. The real question is whether users find cross-run memory useful. If most users run one-off queries, the feature has low value. If power users run sequences of related queries, it has high value. DRA should add telemetry to measure this before building the feature.

### Tension 2: Session Memory vs. Checkpoints

The DRA plan proposes both:
- `session.py`: "per-session working memory, track what's been searched, scraped, and synthesized"
- `checkpoint.py`: "save research state at each phase boundary"

These are overlapping concepts. A checkpoint IS session memory. Having both creates confusion and potential data inconsistency.

**Counter-argument:** Merge `session.py` and `checkpoint.py` into a single `ResearchSession` class that combines runtime state with persistence. This is simpler and avoids duplication.

### Tension 3: Automated Memory vs. User-Curated Memory

The plan proposes "auto-surface relevant prior findings" — automatic retrieval based on query similarity. But what if the user doesn't want old findings to influence new research? Auto-surfacing may introduce bias or outdated information.

**Counter-argument:** Make cross-run memory **opt-in** per research run. The user can check a box "Include prior research findings" and optionally select which prior runs to include. This gives users control and prevents unwanted bias.

---

## Recommendations

### 1. Merge Session and Checkpoint Concepts

```python
class ResearchSession:
    """Combined session memory + checkpoint persistence."""
    def __init__(self, run_id: UUID, workspace_id: UUID):
        self.run_id = run_id
        self.workspace_id = workspace_id
        self.searched_queries = set()
        self.scraped_urls = set()
        self.sources = []
        self.partial_report = ""
    
    async def checkpoint(self, phase: str):
        """Save current state to database."""
        await db.save_checkpoint(self.run_id, self.model_dump_json())
    
    def has_searched(self, query: str) -> bool:
        """Prevent redundant searches within a run."""
        return query in self.searched_queries
```

### 2. Defer `learn.py` (Failure Mining)

The concept is too vague to implement. Instead, focus on:
- Logging failed runs with error classification
- Allowing users to flag low-quality reports
- Using this feedback to tune prompts (manual process)

Automated learning from failures is a research problem, not a P3 implementation task.

### 3. Use Supabase Full-Text Search for Memory Retrieval

Instead of adding a vector database, use existing PostgreSQL `tsvector`:

```sql
-- research_memory table with full-text search
CREATE TABLE research_memory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL,
  run_id UUID REFERENCES research_runs(id),
  finding TEXT NOT NULL,
  finding_tsv TSVECTOR,  -- for full-text search
  relevance_tags JSONB DEFAULT '[]',
  pinned BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_research_memory_fts ON research_memory USING GIN (finding_tsv);
```

Update `finding_tsv` on insert/update:
```sql
UPDATE research_memory SET finding_tsv = to_tsvector('english', finding);
```

This is simpler, uses existing infrastructure, and is sufficient for keyword-based retrieval.

---

## Confidence Assessment

| Finding | Confidence |
|---------|------------|
| Cross-run memory value is unproven for DRA | Medium |
| Vector databases add unnecessary complexity | High |
| `learn.py` concept is too vague to implement | High |
| Workspace isolation is critical | High |
| Session and checkpoint should be merged | High |

---

## Sources

[^1]: headroom SharedContext Documentation. 2026-01-07. https://github.com/chopratejas/headroom/blob/main/docs/content/docs/shared-context.mdx

[^2]: Chroma Documentation. 2026. https://docs.trychroma.com/

[^3]: headroom README. 2026-06-22. https://github.com/chopratejas/headroom

[^4]: General SaaS security best practices. 2026.

