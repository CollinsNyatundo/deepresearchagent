# DRA Integration Plan — File Analysis & Cross-Section Mapping

## File Inventory

| File | Type | Size | Summary |
|------|------|------|---------|
| `dra_integration_plan.md` | Markdown | ~34,500 bytes | Comprehensive 4-phase integration plan proposing capabilities from 5 external repos into DRA |

---

## Per-Section Extraction

### Section 1: Source Repositories Analysis (Lines 5-13)

**Core Themes:** Capability mapping, phased integration strategy, repository selection rationale

**Key Claims:**
- 5 repositories can be integrated across 4 phases (P0-P3)
- Each repo provides distinct, non-overlapping capabilities
- Total effort estimate: ~10-13 weeks

**Technical Details:**
- Phase assignments: opendraft (P0,P1,P2), academic-research-skills (P0,P1,P2), AI-Researcher (P1,P3), headroom (P2), public-apis (P2)

**Gaps Noted:**
- No overlap analysis between repos — some capabilities may duplicate (e.g., citation verification is in both opendraft and academic-research-skills)
- No dependency graph between phases

---

### Section 2: Phase 0 — Citation Verification + Review Agents (Lines 17-124)

**Core Themes:** Citation integrity, multi-perspective quality assurance, frontend visualization

**Key Claims:**
- Citation verification can be done inline (quick) and post-synthesis (deep)
- 4 database adapters needed: CrossRef, OpenAlex, Semantic Scholar, arXiv
- 3 review agents: FactChecker, Devil's Advocate, QualityScorer
- Integration point: `synthesize → citation_verify → review → mindmap`

**Technical Requirements:**
- 7 new Python files in `research_engine/citations/`
- 1 new file in `research_engine/agent/reviewer.py`
- Modifications to 4 existing files: `orchestrator.py`, `models.py`, `prompts.py`, `api.py`
- 5 new frontend components: `CitationBadge.tsx`, `QualityTab.tsx`, plus modifications to `ReportView.tsx`, `ResearchProgress.tsx`, `api.ts`, `client.ts`
- New SSE events: `citation_verification_start`, `citation_verification_complete`, `review_start`, `review_complete`

**Data Model Additions:**
- `Citation`, `VerificationResult`, `VerificationReport`
- `QualityReport` (confidence_score, citation_verification_rate, source_diversity_score, reviewer_feedback, improvement_suggestions)
- `CitationStatus` enum

**Effort Estimate:** Medium (~2-3 weeks)

**Gaps/Risks:**
- No mention of handling rate limits across 4 APIs concurrently
- No caching strategy for citation verification results
- Semantic Scholar's rate limit (100 req/5min) could be a bottleneck for large reports
- LLM-based citation parsing fallback may be expensive and slow
- No mention of how to handle citations that don't exist in any DB (common for web sources)
- Devil's Advocate requires deep reasoning — may add significant latency per research run

---

### Section 3: Phase 1 — Checkpoint/Resume + Versioning + Quality Scoring (Lines 128-181)

**Core Themes:** Resilience, iterative improvement, state persistence, quality benchmarking

**Key Claims:**
- Checkpoints save state at each phase boundary
- Resume skips completed phases automatically
- Versioning tracks report revisions with diff computation
- Quality benchmarking inspired by Scientist-Bench (from AI-Researcher)

**Technical Requirements:**
- `CheckpointManager` class with Supabase `research_checkpoints` table
- `VersionManager` with Supabase `report_versions` table
- `benchmark.py` with LLM-as-judge scoring framework
- New endpoints: `POST /research/{run_id}/resume`, `GET /research/{run_id}/checkpoints`, `POST /research/{run_id}/revise`, `GET /research/{run_id}/versions`
- Frontend: `VersionHistory.tsx`, modifications to `ReportView.tsx`

**Effort Estimate:** Medium (~2 weeks)

**Gaps/Risks:**
- `state_json` in checkpoints could become very large (accumulated sources, search results, partial reports) — no size limits mentioned
- No mention of checkpoint cleanup strategy (could accumulate indefinitely)
- Diff computation for large reports (20k+ words) could be expensive
- LLM-as-judge quality scoring adds cost and latency to every run
- No rollback mechanism if a revision makes quality worse

---

### Section 4: Phase 2 — Token Compression + Academic APIs + Export Formats (Lines 185-252)

**Core Themes:** Cost optimization, source diversity, professional document export, systematic review compliance

**Key Claims:**
- Token compression reduces OpenRouter costs by 60-95%
- Rust extension module required for "performance-critical compression"
- Academic search providers: arXiv, PubMed, CORE, Unpaywall, BASE
- PRISMA compliance for systematic reviews
- Export formats: Word, LaTeX, BibTeX, RIS, Obsidian Vault

**Technical Requirements:**
- 7 new files in `research_engine/compression/` including `rust_core/`
- `setup_headroom.py` script for Rust toolchain installation
- `AcademicSearchProvider` in `research_engine/sources/academic_search.py`
- `PrismaWorkflowManager` in `research_engine/agent/prisma.py`
- Export additions: `export_docx()`, `export_latex()`, `export_bibtex()`, `export_ris()`, `export_obsidian_vault()`
- Dependencies: `python-docx`, `pylatex`, `maturin`

**Effort Estimate:** High (~3-4 weeks)

**Gaps/Risks (CRITICAL):**
- **MAJOR CONCERN**: The plan claims headroom requires a "Rust extension module" but our search reveals headroom is primarily a Python/TypeScript library installable via `pip install headroom-ai[all]`. The Rust toolchain requirement may be unnecessary over-engineering.
- The plan's `scripts/setup_headroom.py` is likely redundant — headroom installs cleanly via pip
- `pylatex` is listed as a dependency but the plan doesn't show any actual LaTeX generation code using it
- PRISMA compliance is a complex domain — the plan's `PrismaWorkflowManager` description is too vague
- No mention of how academic search providers interact with existing DuckDuckGo search
- Export format testing matrix (5 formats × multiple paper types) is large and untested

---

### Section 5: Phase 3 — Docker Sandbox + Cross-Agent Memory (Lines 256-303)

**Core Themes:** Experimental validation, code execution safety, multi-session memory

**Key Claims:**
- Docker sandbox for isolated code execution per experiment
- Cross-run shared context with deduplication using CCR
- Session memory to prevent redundant work
- `learn.py` mines failed runs for correction patterns

**Technical Requirements:**
- 4 new files in `research_engine/sandbox/`: `executor.py`, `builder.py`, `models.py`, `security.py`
- 3 new files in `research_engine/memory/`: `shared_context.py`, `session.py`, `learn.py`
- New endpoints: `POST /research/{run_id}/experiment`, `GET /research/{run_id}/experiments`, `GET /research/{run_id}/experiments/{exp_id}/output`
- Frontend: `ExperimentPanel.tsx`, `ResearchMemory.tsx`
- Dependency: `docker` Python SDK

**Effort Estimate:** High (~3-4 weeks)

**Gaps/Risks:**
- Docker requirement adds significant infrastructure complexity to DRA's currently lightweight architecture (FastAPI + BackgroundTasks)
- No mention of Docker daemon availability checks or fallback if Docker is unavailable
- Resource limits (CPU, memory, network, timeout) need careful tuning to prevent abuse
- GPU passthrough configuration is complex and varies by host
- `learn.py` concept is vague — "mines failed runs to generate correction patterns" needs concrete algorithm
- Cross-agent memory security: storing findings from one workspace vs. another needs isolation guarantees
- The plan says "uses CCR (from compression module) for storage efficiency" but this creates a Phase 2 → Phase 3 dependency that may block P3 if P2 is delayed

---

### Section 6: Database Migrations (Lines 307-384)

**Core Themes:** Schema design, data persistence, workspace scoping

**Key Claims:**
- 6 new tables: `citation_verifications`, `quality_reports`, `research_checkpoints`, `report_versions`, `sandbox_experiments`, `research_memory`
- All tables have `workspace_id` FK and `run_id` FK where applicable
- All use UUID primary keys with `gen_random_uuid()`

**Technical Requirements:**
- 6 CREATE TABLE statements with JSONB columns for flexible metadata
- `CHECK` constraints on status enums
- `UNIQUE(run_id, version)` for report versions

**Gaps/Risks:**
- `research_checkpoints.state_json` is unbounded TEXT — could store megabytes per checkpoint
- No index recommendations for query performance
- `research_memory.compressed_context` stores compressed text but no decompression function is defined
- No migration rollback strategy mentioned
- `sandbox_experiments.code` stores raw code — security implications if XSS is possible through experiment results
- No RLS policy updates mentioned for new tables

---

### Section 7: Verification Plan (Lines 389-426)

**Core Themes:** Testing strategy, quality assurance, manual validation

**Key Claims:**
- Unit tests for each module
- Integration tests for live API calls (rate-limited)
- Docker required for sandbox integration tests
- Frontend build check for TypeScript parity

**Gaps/Risks:**
- No mention of mocking strategy for external APIs (CrossRef, OpenAlex, etc.) in CI/CD
- Integration tests calling live APIs will be flaky and slow
- No performance benchmarks (token savings, latency impact)
- No security testing for Docker sandbox
- No mention of frontend integration testing (Cypress, Playwright, etc.)

---

### Section 8: Dependencies (Lines 430-447)

**Core Themes:** Dependency management, build toolchain

**Key Claims:**
- Python: `aiohttp`, `python-docx`, `pylatex`, `maturin`, `docker`
- Rust: rustup + PyO3 + maturin
- Frontend: no new dependencies

**Gaps/Risks:**
- `aiohttp` is listed but DRA already has async HTTP via `httpx` or could use `aiohttp` — potential conflict
- `maturin` and Rust toolchain is a heavy build dependency for a Python project
- `pylatex` may not be the best choice — `python-docx` + manual LaTeX templating might be more reliable
- No version pinning specified
- No mention of Windows-specific build considerations (Rust on Windows can be tricky)

---

### Section 9: Deeper Repo Extraction Findings (Lines 464-549)

**Core Themes:** Advanced integration patterns, academic paper quality, provenance tracking, API ecosystem

**Key Claims:**
- IHDS (Iterative Checkpointed Hierarchical Document Synthesis) from AI-Researcher enables NeurIPS-quality output
- Section-specific composers: IntroductionComposer, RelatedWorkComposer, ExperimentsComposer, ConclusionComposer, AbstractComposer
- Material Passports map every claim to exact source
- repro_lock provides auditable paper trail
- 25+ zero-auth APIs for diverse data sources

**Technical Requirements:**
- Abstract `SectionComposer` class with specialized subclasses
- `material_passport.json` artifact generation
- Lockfile metadata stored in Supabase
- API adapters for 25+ services

**Gaps/Risks:**
- IHDS is extremely complex — implementing 5+ section-specific composers with LaTeX output is a massive undertaking
- The plan claims AI-Researcher achieved "NeurIPS 2025 spotlight" quality but doesn't specify how much of that is due to IHDS vs. the Docker sandbox + experiment validation
- Material Passport requires every claim to have a mapped source — this is a fundamental change to how DRA synthesizes reports
- 25 API adapters is a significant maintenance burden — many of these APIs may change or break
- The plan uses "Nightglass" as the product name in Section 9 but DRA elsewhere — inconsistency

---

## Cross-Section Mapping

### Overlapping Themes

| Theme | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Deeper Findings |
|-------|---------|---------|---------|---------|-----------------|
| Citation Verification | ✅ (primary) | — | ✅ (academic search) | — | ✅ (Material Passport) |
| Quality Scoring | ✅ (Review Agents) | ✅ (Benchmark) | — | — | ✅ (IHDS quality) |
| State Persistence | ✅ (orchestrator SSE) | ✅ (checkpoints) | — | ✅ (memory) | ✅ (repro_lock) |
| Export/Output | — | ✅ (versioning) | ✅ (formats) | — | ✅ (LaTeX) |
| Cost Optimization | — | — | ✅ (compression) | — | — |
| Code Execution | — | — | — | ✅ (sandbox) | ✅ (IHDS experiments) |

### Contradictions Detected

1. **License Conflict**: academic-research-skills is CC-BY-NC 4.0 (non-commercial) but DRA is likely intended for commercial use. The plan doesn't address this.

2. **Rust Over-Engineering**: The plan claims headroom requires a Rust toolchain and custom `rust_core/` module, but headroom's actual implementation is pip-installable Python. This is a significant misalignment.

3. **Effort Underestimation**: Phase 2 alone includes: compression module, academic search, PRISMA workflow, 5 export formats. The "3-4 weeks" estimate seems optimistic given the scope.

4. **Phase 3 Dependency on Phase 2**: Cross-agent memory "uses CCR (from compression module)" — this creates a hard dependency that could block P3.

5. **Product Name Inconsistency**: "Nightglass" appears in Section 9 but nowhere else in the document.

### Complementary Information

- Phase 0's citation verification provides the foundation for Phase 1's quality benchmarking
- Phase 2's token compression makes Phase 3's cross-agent memory more feasible (smaller storage)
- The Deeper Findings section's IHDS concept complements Phase 1's versioning and Phase 2's export formats
- public-apis catalog from Phase 2 directly supports the 25+ API list in Deeper Findings

---

## Gap Analysis

### Critical Gaps (Must Address Before Implementation)

1. **License Compliance**: CC-BY-NC 4.0 of academic-research-skills prevents commercial use. Need to either:
   - Re-implement the review agent concepts from scratch (not copy code)
   - Negotiate with author for commercial license
   - Find MIT/Apache alternatives

2. **Rust Dependency Reality Check**: Headroom does NOT require a Rust toolchain. The plan should be updated to use `pip install headroom-ai[all]` instead.

3. **API Rate Limiting Strategy**: No comprehensive rate-limiting plan for 4 citation DBs + 25+ public APIs + existing DuckDuckGo search.

4. **Security Model for Docker Sandbox**: No mention of how to prevent malicious code execution, resource exhaustion, or network abuse in sandboxed containers.

5. **Database Performance**: `state_json` and `code` columns are unbounded TEXT — need size limits and cleanup policies.

### Important Gaps (Should Address)

6. **Missing Dependency Analysis**: No analysis of how new features interact with existing DRA modules (Scrapling, OpenKB, Knowledge Graph).

7. **No Fallback Strategy**: If citation verification fails (all 4 DBs down), what happens? If Docker is unavailable, what happens?

8. **Frontend Performance**: Citation badges inline in markdown reports could significantly impact render performance for large reports.

9. **Testing Strategy Gaps**: No end-to-end test plan, no performance benchmarks, no security testing.

10. **Operational Concerns**: No monitoring, alerting, or observability plan for the new components.

### Minor Gaps (Nice to Have)

11. **Documentation**: No plan for updating AGENTS.md or user-facing docs.

12. **Migration Strategy**: No plan for migrating existing research runs to new schema.

13. **Feature Flags**: No mention of gradual rollout or feature flags for risky features (Docker sandbox).

---

## Consolidated Theme List (Research Dimensions)

Based on the file analysis and landscape scan, the following themes emerge as distinct research dimensions for deeper investigation:

1. **Citation Verification Architecture** — Technical design, API adapters, rate limiting, caching
2. **Multi-Perspective Review Agent Design** — FactChecker, Devil's Advocate, QualityScorer implementation
3. **Checkpoint/Resume & State Persistence** — State serialization, storage limits, resume logic
4. **Token Compression & Cost Optimization** — Headroom integration, realistic compression gains
5. **Academic Document Export Pipeline** — DOCX, LaTeX, BibTeX, RIS, Obsidian implementations
6. **Docker Sandbox & Code Execution** — Security model, resource isolation, GPU support
7. **Cross-Agent Memory & Learning** — Shared context, session deduplication, failure mining
8. **Public API Integration Strategy** — 25+ API adapters, maintenance burden, rate limiting
9. **Hierarchical LaTeX Composition (IHDS)** — Section composers, LaTeX generation, BibTeX management
10. **Provenance Tracking & Reproducibility** — Material Passports, repro_lock, audit trail
11. **Frontend UI/UX Changes** — Citation badges, quality tabs, version history, experiment panel
12. **Database Schema & Migration Strategy** — Table design, indexing, RLS, cleanup policies
13. **Testing & Verification Strategy** — Unit tests, integration tests, performance benchmarks
14. **License & Legal Compliance** — CC-BY-NC issue, MIT/Apache compatibility, attribution requirements
15. **Integration Complexity & Risk Assessment** — Effort realism, dependency graph, phased rollout

