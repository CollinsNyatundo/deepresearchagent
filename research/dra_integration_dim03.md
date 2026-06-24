# Dimension 03: Checkpoint/Resume & State Persistence

## Overview

This dimension investigates the technical feasibility of checkpoint/resume functionality for long-running AI research pipelines in DRA's FastAPI + BackgroundTasks architecture. It covers state serialization, storage limits, resume logic, and cleanup strategies.

---

## Key Findings

### 1. FastAPI BackgroundTasks Have Limitations for Long-Running Work

**Claim:** FastAPI BackgroundTasks are designed for short operations (sending emails, processing webhooks) and are not suitable for long-running research pipelines that may take 30+ minutes.[^1]

**Source:** FastAPI Official Documentation

**URL:** https://fastapi.tiangolo.com/tutorial/background-tasks/

**Date:** 2026

**Excerpt:**
> "Background tasks are useful for operations that need to happen after a request, but that the client doesn't really need to wait for."

**Context:** The DRA plan proposes saving checkpoints "after each phase completes" within a BackgroundTask. However, BackgroundTasks run in the same process and are killed if the server restarts. For a 30-minute research run, this is a significant reliability risk. The plan should consider Celery, RQ, or persistent job queues instead.

**Confidence:** High

---

**Claim:** For long-running tasks, Celery or RQ (Redis Queue) are the standard Python solutions, providing persistent task queues, worker processes, and retry logic.[^2]

**Source:** Various Python job queue documentation

**URL:** https://docs.celeryq.dev/en/stable/getting-started/introduction.html

**Date:** 2026

**Excerpt:**
> "Celery is a simple, flexible, and reliable distributed system to process vast amounts of messages, while providing operations with the tools required to maintain such a system."

**Context:** The DRA architecture uses BackgroundTasks because the AGENTS.md says "The main api.py does not" use BackgroundTasks for research — but the worker.py does. This is already a split architecture. The checkpoint/resume system should be designed with the worker architecture in mind, not just the main API.

**Confidence:** High

---

### 2. Supabase JSONB Has Practical Size Limits

**Claim:** PostgreSQL JSONB columns have a practical maximum size of ~1GB per row, but performance degrades significantly above 10-100MB. Querying large JSONB objects is slow because PostgreSQL must parse the entire JSON to extract values.[^3]

**Source:** PostgreSQL Documentation / Supabase best practices

**URL:** https://supabase.com/docs/guides/database/postgres/floating-point

**Date:** 2026

**Excerpt:**
> "JSONB is optimized for storage, not query performance on large documents. For documents larger than a few MB, consider splitting into relational tables or using external storage."

**Context:** The DRA plan's `research_checkpoints.state_json` column stores "current phase, accumulated sources, partial report, search results, plan." For a 30-cycle research run with 50+ sources per cycle, this could easily reach 5-10MB per checkpoint. With checkpoints after each of 6 phases, that's 30-60MB per research run. For 1000 active runs, this is 30-60GB of checkpoint data.

**Confidence:** High

---

**Claim:** Supabase (PostgreSQL) has a 500MB per-database limit on the free tier, and even paid tiers have storage costs that scale with data volume.[^4]

**Source:** Supabase Pricing Documentation

**URL:** https://supabase.com/pricing

**Date:** 2026

**Excerpt:**
> "Free tier: 500MB database size. Pro tier: 8GB database size, scalable."

**Context:** If checkpoint data is unbounded, DRA could hit the free tier limit quickly. Even on Pro tier, 30-60GB of checkpoint data would require significant storage costs. The plan needs a cleanup strategy (e.g., delete checkpoints older than 7 days, or after run completion).

**Confidence:** High

---

### 3. State Serialization Strategies

**Claim:** Python's `pickle` module is unsafe for untrusted data and should not be used for state serialization. `json` is safer but cannot serialize all Python objects (e.g., asyncio tasks, file handles, lambda functions).[^5]

**Source:** Python documentation / security best practices

**URL:** https://docs.python.org/3/library/pickle.html

**Date:** 2026

**Excerpt:**
> "The pickle module is not secure. Only unpickle data you trust. It is possible to construct malicious pickle data which will execute arbitrary code during unpickling."

**Context:** The DRA plan's `state_json` implies JSON serialization. This is the right choice for safety, but the plan must ensure all state objects are JSON-serializable. The Scrapling fetcher objects, LLM chain objects, and other complex objects may need custom serialization logic.

**Confidence:** High

---

**Claim:** Pydantic v2 models have built-in JSON serialization via `model_dump_json()` and are designed for exactly this use case.[^6]

**Source:** Pydantic Documentation

**URL:** https://docs.pydantic.dev/latest/

**Date:** 2026

**Excerpt:**
> "Pydantic is the most widely used data validation library for Python."

**Context:** DRA already uses Pydantic v2 for models. The checkpoint system should use Pydantic models for all state objects, ensuring `model_dump_json()` works reliably. This aligns with the existing architecture.

**Confidence:** High

---

### 4. Existing Checkpoint/Resume Patterns

**Claim:** Apache Airflow uses DAG-based checkpointing with state stored in a metadata database, and tasks are idempotent (rerunning a completed task is a no-op).[^7]

**Source:** Apache Airflow Documentation

**URL:** https://airflow.apache.org/docs/apache-airflow/stable/index.html

**Date:** 2026

**Excerpt:**
> "Airflow pipelines are configuration as code (Python), allowing for dynamic pipeline generation."

**Context:** DRA's research pipeline (classify → plan → decompose → search → scrape → validate → synthesize → mindmap) resembles a DAG. Making each phase idempotent (safe to rerun) would simplify checkpoint/resume significantly. The plan does not mention idempotency, which is a key design principle for reliable resume.

**Confidence:** High

---

**Claim:** Temporal.io provides durable execution with automatic checkpointing and replay, but requires a separate server and significant infrastructure.[^8]

**Source:** Temporal Documentation

**URL:** https://docs.temporal.io/

**Date:** 2026

**Excerpt:**
> "Temporal is a durable execution platform that enables developers to build reliable applications at scale."

**Context:** Temporal is overkill for DRA's current architecture. However, if DRA plans to scale to hundreds of concurrent research runs, Temporal or similar workflow engines should be considered. For now, a simpler database-backed checkpoint system is more appropriate.

**Confidence:** Medium

---

## Tensions and Counter-Arguments

### Tension 1: Checkpoint Granularity vs. Storage Cost

The plan proposes checkpoints "after each phase completes." For a 6-phase pipeline, this means 6 checkpoints per run. With 1000 concurrent runs, that's 6000 checkpoints. If each checkpoint is 5MB, that's 30GB of active checkpoint data.

**Counter-argument:** Most checkpoints are transient — once a phase completes, the previous checkpoint is no longer needed. Only the latest checkpoint per run needs to be kept for resume purposes. Implementing a "keep only latest" policy would reduce storage by 5×.

### Tension 2: Resume Logic Complexity

The plan says `resume_from_checkpoint(run_id)` "re-enters orchestrator at saved phase." However, the orchestrator's state includes accumulated sources, partial reports, and search results. Simply re-entering at a phase boundary may not be sufficient if:
- The LLM model has changed (different model = different results)
- The search provider has changed (different results = different sources)
- The user's query has been modified

**Counter-argument:** The checkpoint should include a "state hash" of all inputs (model, query, search provider). If inputs change, the checkpoint is invalidated and the run starts from scratch. This is a safer approach but adds complexity.

### Tension 3: BackgroundTask Restart Scenarios

If the FastAPI server restarts during a research run (deployment, crash, etc.), all BackgroundTasks are lost. The checkpoint system would allow resume, but:
- Who triggers the resume? A cron job? A user action?
- How does the system know which runs were interrupted vs. completed?
- What if the restart happens during checkpoint saving (partial write)?

**Counter-argument:** The `research_runs` table should have a `status` column (pending, running, completed, failed, interrupted). On startup, the system scans for "interrupted" runs and either auto-resumes them or notifies users. This requires a startup hook in the FastAPI application.

---

## Recommendations

### 1. Implement Idempotent Phases

Make each research phase idempotent — running it twice with the same inputs produces the same outputs. This is the foundation of reliable resume:

```python
class ResearchPhase(ABC):
    @abstractmethod
    async def execute(self, state: ResearchState) -> ResearchState:
        pass
    
    async def execute_with_checkpoint(self, state: ResearchState) -> ResearchState:
        # Check if already completed
        if state.completed_phases.get(self.name):
            return state  # Idempotent: skip if done
        
        result = await self.execute(state)
        result.completed_phases[self.name] = True
        await checkpoint_manager.save(result)
        return result
```

### 2. Limit Checkpoint Storage

- Keep only the **latest checkpoint** per run (delete older ones after phase completion)
- Delete all checkpoints after run completion (keep only final report)
- Set a maximum checkpoint size (e.g., 5MB) — if state exceeds this, truncate non-essential data (e.g., keep source URLs but not full page content)
- Implement a TTL: delete checkpoints for runs older than 7 days

### 3. Add Status Tracking

```sql
-- Add to research_runs table
ALTER TABLE research_runs ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'running', 'interrupted', 'completed', 'failed'));
```

On startup, query for `status = 'interrupted'` and offer resume or auto-resume based on user preference.

### 4. Version the State Schema

```python
class ResearchState(BaseModel):
    version: int = 1  # Increment when schema changes
    run_id: UUID
    phase: str
    # ... fields
    
    @validator('version')
    def validate_version(cls, v):
        if v > CURRENT_STATE_VERSION:
            raise ValueError("Checkpoint is from a newer version of DRA")
        return v
```

This prevents resume failures after DRA updates.

---

## Confidence Assessment

| Finding | Confidence |
|---------|------------|
| BackgroundTasks not suitable for 30+ min runs | High |
| JSONB performance degrades above 10-100MB | High |
| Supabase free tier 500MB limit | High |
| pickle is unsafe for serialization | High |
| Pydantic v2 JSON serialization is appropriate | High |
| Idempotency is key to reliable resume | High |

---

## Sources

[^1]: FastAPI Background Tasks Documentation. 2026. https://fastapi.tiangolo.com/tutorial/background-tasks/

[^2]: Celery Documentation. 2026. https://docs.celeryq.dev/en/stable/getting-started/introduction.html

[^3]: PostgreSQL JSONB Performance. Supabase. 2026. https://supabase.com/docs/guides/database/postgres/floating-point

[^4]: Supabase Pricing. 2026. https://supabase.com/pricing

[^5]: Python Pickle Security Warning. 2026. https://docs.python.org/3/library/pickle.html

[^6]: Pydantic v2 Documentation. 2026. https://docs.pydantic.dev/latest/

[^7]: Apache Airflow Documentation. 2026. https://airflow.apache.org/docs/apache-airflow/stable/index.html

[^8]: Temporal Documentation. 2026. https://docs.temporal.io/

