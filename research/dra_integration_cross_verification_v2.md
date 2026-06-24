# Cross-Verification: DRA Multi-Repo Integration (Updated)

## Methodology

All 15 dimension analyses (12 base + 3 new + 3 supplements) were reviewed and findings categorized into four confidence tiers based on source quality, cross-dimensional confirmation, and logical consistency.

---

## High Confidence Findings (Confirmed by ≥2 dimensions or authoritative sources)

### HC-1: CrossRef Rate Limit is 10 req/s (Polite), Not 50 req/s

- **Confirmed by:** Dim 01 (CrossRef docs), Dim 12 (risk matrix)
- **Sources:** CrossRef official documentation (2025-10-16), CrossRef blog (2025-11-05)
- **Impact:** Critical — the DRA plan's architecture assumes 50 req/s, which would lead to 429 errors and service instability.
- **Action:** Correct plan immediately before any implementation begins.

### HC-2: academic-research-skills is CC-BY-NC 4.0 (Non-Commercial)

- **Confirmed by:** Dim 02 (license section), Dim 11 (legal analysis), Dim 12 (risk matrix)
- **Sources:** GitHub LICENSE file, Creative Commons legal code
- **Impact:** Critical — using concepts derived from this work in a commercial DRA deployment violates the license.
- **Action:** Rewrite integration plan to remove all ARS references before any code is written.

### HC-3: Headroom Does NOT Require a Rust Toolchain

- **Confirmed by:** Dim 04 (headroom docs), Dim 12 (risk matrix)
- **Sources:** headroom README (2026-06-22), PyPI listing
- **Impact:** High — the plan's `rust_core/` directory and `setup_headroom.py` are unnecessary over-engineering.
- **Action:** Remove Rust-related content from plan. Use `pip install headroom-ai[all]` instead.

### HC-4: Docker Sandbox Adds Disproportionate Infrastructure Complexity

- **Confirmed by:** Dim 06 (Docker analysis), Dim 12 (revised plan)
- **Sources:** Docker docs, AI-Researcher GitHub issues, NIST container security guide
- **Impact:** High — transforms DRA from lightweight FastAPI app to container orchestration system.
- **Action:** Defer Docker sandbox indefinitely. Use static code analysis instead.

### HC-5: LLM-as-Judge Has Systematic Biases (Sycophancy, Position, Length)

- **Confirmed by:** Dim 02 (review agent analysis), Dim 12 (risk matrix)
- **Sources:** Multiple arXiv papers (2025-2026)
- **Impact:** Medium — review agent quality scores may be unreliable without mitigation.
- **Action:** Use different models per reviewer, make review optional, add anonymization.

### HC-6: The Plan Underestimates Effort by 50-100%

- **Confirmed by:** Dim 12 (synthesis), all dimension analyses
- **Sources:** Synthesis of all 15 dimensions
- **Impact:** High — unrealistic timeline leads to missed deadlines and feature cuts.
- **Action:** Revise plan to 15-20 weeks or implement MVP approach (8-10 weeks).

### HC-7: 25 API Adapters Create Major Maintenance Burden

- **Confirmed by:** Dim 08 (API strategy), Dim 08 Supplement (specific API reliability), Dim 12 (revised plan)
- **Sources:** General software engineering knowledge, public-apis issues, API documentation
- **Impact:** Medium — ongoing maintenance cost exceeds value for Tier 2/3 APIs.
- **Action:** Reduce to 5 Tier 1 APIs, add others based on user demand.

### HC-8: IHDS (LaTeX Composition) is Over-Engineered for DRA's Use Case

- **Confirmed by:** Dim 09 (IHDS analysis), Dim 12 (revised plan)
- **Sources:** AI-Researcher README, opendraft architecture, LaTeX project docs
- **Impact:** Medium — 4-8 weeks of effort for a niche feature.
- **Action:** Remove IHDS from plan. Provide simple Markdown→LaTeX via Pandoc if needed.

### HC-9: RLS Policies Are Missing for All 6 New Tables (NEW)

- **Confirmed by:** Dim 14 (database schema analysis), Dim 12 (security risk matrix)
- **Sources:** Supabase RLS documentation, PostgreSQL security best practices
- **Impact:** Critical — without RLS, a malicious user could query other workspaces' data.
- **Action:** Add RLS policies to all new tables before any deployment.

### HC-10: CitationBadge Inline Rendering Has Performance Implications (NEW)

- **Confirmed by:** Dim 13 (frontend analysis), DRA AGENTS.md (performance requirements)
- **Sources:** React Markdown docs, web.dev virtualized lists
- **Impact:** Medium — 50+ inline badges could add 100-500ms render time.
- **Action:** Use IntersectionObserver for lazy badge loading, virtualize for large reports.

### HC-11: SSE Events Need Connection Health Checks and Fallback (NEW)

- **Confirmed by:** Dim 15 (SSE architecture), MDN EventSource docs
- **Sources:** FastAPI StreamingResponse docs, Node.js backpressure docs
- **Impact:** Medium — lost events during reconnection create stale UI state.
- **Action:** Add event IDs, heartbeat messages, and polling fallback.

### HC-12: pgvector is Best Choice for Cross-Run Memory (NEW)

- **Confirmed by:** Dim 07 Supplement (vector DB comparison), Dim 14 (existing PostgreSQL)
- **Sources:** pgvector docs, DB-Engines ranking, Sentence Transformers docs
- **Impact:** Low — cross-run memory is deferred, but when built, pgvector is the right choice.
- **Action:** Use pgvector extension in Supabase when implementing memory.

---

## Medium Confidence Findings (Confirmed by 1 authoritative source or strong logical inference)

### MC-1: Realistic Token Compression for DRA Reports is 30-40% (Not 60-95%)

- **Source:** Dim 04 (headroom benchmarks + DRA-specific analysis)
- **Reasoning:** Headroom's 60-95% is for HTML extraction. Research reports have dense prose that is harder to compress.
- **Impact:** Medium — cost savings are still meaningful but less than claimed.
- **Action:** Set realistic expectations in plan.

### MC-2: Prompt Caching May Provide More Cost Savings Than Compression

- **Source:** Dim 04 (OpenRouter docs), Dim 12 (risk matrix)
- **Reasoning:** DRA's research pipeline sends similar system prompts across cycles. Cache hit rates of 60-80% on prefixes would save more than content compression for a single run.
- **Impact:** Medium — may change prioritization of cost optimization efforts.
- **Action:** Implement CacheAligner (prefix stabilization) before content compression.

### MC-3: Supabase JSONB Performance Degrades Above 10-100MB

- **Source:** Dim 03 (checkpoint analysis), Dim 14 (size limits)
- **Reasoning:** PostgreSQL documentation + Supabase best practices. Checkpoint `state_json` could reach 5-10MB per checkpoint.
- **Impact:** Medium — requires checkpoint size limits and cleanup policies.
- **Action:** Keep only latest checkpoint per run, set 5MB size limit, implement TTL cleanup.

### MC-4: Semantic Scholar Unauthenticated Pool is Unreliable Under Load

- **Source:** Dim 01 (Semantic Scholar docs), Dim 08 Supplement (specific API reliability)
- **Reasoning:** 1000 RPS shared globally among all unauthenticated users. During peak usage, individual users get throttled.
- **Impact:** Medium — citation verification may fail silently for unauthenticated users.
- **Action:** Make API key mandatory for production, not optional.

### MC-5: opendraft is the Best MIT-Licensed Reference for DRA

- **Source:** Dim 02 (license analysis), Dim 11 (legal analysis), Dim 05 Supplement (Pandoc approach)
- **Reasoning:** opendraft implements multi-agent pipeline, citation verification, and export with MIT license. It aligns closely with DRA's needs.
- **Impact:** High — should replace academic-research-skills as primary reference.
- **Action:** Study opendraft's architecture (MIT) instead of ARS (CC-BY-NC).

### MC-6: Pandoc is the Best Multi-Format Export Engine (NEW)

- **Source:** Dim 05 Supplement (Pandoc analysis), Dim 09 (LaTeX analysis)
- **Reasoning:** Pandoc handles Markdown→DOCX/LaTeX/PDF/HTML with CiteProc citation processing. It reduces code duplication compared to format-specific libraries.
- **Impact:** Medium — changes export implementation strategy.
- **Action:** Make Pandoc primary export engine with python-docx fallback.

### MC-7: Diff Computation Should Be Server-Side (NEW)

- **Source:** Dim 13 (VersionHistory component), diff-match-patch complexity analysis
- **Reasoning:** O(n²) client-side diff for 20,000-word documents freezes the UI for 1-5 seconds.
- **Impact:** Medium — affects user experience of version history feature.
- **Action:** Pre-compute diff in `versioning.py` when saving versions, store in `diff_from_prev` column.

---

## Low Confidence Findings (Weak sourcing, blog-level evidence, or single unverified claim)

### LC-1: AI-Generated Citations Have ~40% Error Rate

- **Source:** Dim 01 (citation workflow docs)
- **Reasoning:** Cited from "Enago Academy research" but primary source not verified. NeurIPS 2025 claim of "100+ hallucinated citations" also needs verification.
- **Impact:** Low — even if the exact figure is wrong, the qualitative point (hallucinations exist) is valid.
- **Action:** Use "significant error rates" rather than specific percentages until verified.

### LC-2: 5 Tier 1 APIs Provide 80% of User Value

- **Source:** Dim 08 (API strategy), Dim 08 Supplement (Tier 1 analysis)
- **Reasoning:** Estimated based on DRA's target audience. No user survey data available.
- **Impact:** Low — if wrong, users may request APIs that were deprioritized.
- **Action:** Add telemetry to measure which APIs users actually need.

### LC-3: Cross-Agent Memory Has Low Value for DRA Users

- **Source:** Dim 07 (memory analysis), Dim 07 Supplement (query similarity analysis)
- **Reasoning:** Assumes users run independent queries. Some power users may run related sequences.
- **Impact:** Low — feature can be deferred without major user impact.
- **Action:** Add telemetry to measure cross-run query similarity before building memory.

### LC-4: Failure Mining Algorithm is Feasible but Untested (NEW)

- **Source:** Dim 07 Supplement (proposed algorithm)
- **Reasoning:** Proposed pattern matching + LLM summarization approach. No real-world validation.
- **Impact:** Low — feature is deferred. When implemented, requires iterative testing.
- **Action:** Start with manual failure analysis before automating.

---

## Conflict Zones

### CZ-1: Verification Threshold — 2 Sources vs. 1 Source

**Conflict:** The DRA plan marks citations as "verified" only if ≥2 sources confirm. However, real citations may exist in only 1 database (e.g., a niche paper only in Semantic Scholar). This creates false negatives.

**Resolution:** Dim 01 proposes a tiered approach:
- Academic sources: 2+ databases = verified, 1 = unverified, 0 = failed
- Web sources: URL check + domain reputation = verified/unverified/failed

**Status:** Resolved with modified scoring logic.

---

### CZ-2: Compression vs. Prompt Caching — Which Saves More?

**Conflict:** Dim 04 claims prompt caching may save more than content compression for DRA's use case. The plan prioritizes compression.

**Resolution:** Both can be implemented. Priority: CacheAligner first (prefix stabilization), then content compression if budget remains. Measure actual savings before committing.

**Status:** Resolved with phased approach.

---

### CZ-3: Docker Sandbox vs. No Sandbox

**Conflict:** The plan includes Docker sandbox (P3). Dim 06 argues it should be deferred indefinitely. Dim 12 (synthesis) agrees with deferral.

**Resolution:** Defer Docker sandbox. Replace with static code analysis (syntax checking, type analysis, security scanning). Revisit only if explicit user demand emerges.

**Status:** Resolved with deferral.

---

### CZ-4: Full Provenance vs. Citation-Only Provenance

**Conflict:** The plan proposes Material Passports (claim-level provenance). Dim 10 argues paragraph-level (existing citations) is sufficient for most users and claim-level is over-engineering.

**Resolution:** Make claim-level provenance opt-in. Enhance existing citation system with optional claim mapping. Don't build a separate Material Passport system.

**Status:** Resolved with opt-in approach.

---

### CZ-5: LaTeX/IHDS vs. Markdown Enhancement

**Conflict:** The plan includes IHDS for NeurIPS-quality LaTeX output. Dim 09 argues this is over-engineered and Markdown is sufficient. Dim 05 Supplement suggests Pandoc for simple Markdown→LaTeX conversion.

**Resolution:** Remove IHDS from plan. Provide Markdown → LaTeX via Pandoc as a simple export option. Invest in Markdown quality enhancements instead.

**Status:** Resolved with removal.

---

### CZ-6: Server-Side vs. Client-Side Diff (NEW)

**Conflict:** The plan proposes a VersionHistory component with diff viewer but doesn't specify where diff is computed. Dim 13 shows client-side diff is O(n²) and freezes the UI. Dim 12's revised plan stores `diff_from_prev` in the database.

**Resolution:** Pre-compute diff server-side when saving versions. Store in `report_versions.diff_from_prev`. Frontend renders pre-computed diff using `react-diff-viewer`.

**Status:** Resolved with server-side approach.

---

### CZ-7: pgvector vs. Dedicated Vector DB (NEW)

**Conflict:** Dim 07 Supplement suggests pgvector for cross-run memory, but dedicated vector databases (Qdrant, Chroma) may offer better performance.

**Resolution:** Start with pgvector (available in Supabase, no new dependency). If scale exceeds 100,000 vectors or query latency exceeds 100ms, migrate to Qdrant. The embedding model and query code remain the same.

**Status:** Resolved with pgvector-first approach.

---

## Summary Statistics

| Tier | Count | Key Actions |
|------|-------|-------------|
| High Confidence | 12 | 4 critical actions (rate limit, license, Rust, RLS, Docker, SSE, frontend, pgvector) |
| Medium Confidence | 7 | 4 architectural changes (compression, checkpoints, API strategy, Pandoc, diff) |
| Low Confidence | 4 | 3 telemetry additions, 1 wording change, 1 deferred algorithm |
| Conflict Zones | 7 | All resolved with modifications or deferrals |

---

## Recommended Immediate Actions (Updated)

1. **Rewrite integration plan** to remove all academic-research-skills references and CC-BY-NC-derived concepts
2. **Correct CrossRef rate limit** from 50 req/s to 10 req/s in architecture docs
3. **Remove Rust toolchain requirements** from plan — headroom installs via pip
4. **Add RLS policies** for all 6 new database tables before any deployment
5. **Document clean-room process** if any team member has seen ARS source code
6. **Add SSE event IDs and heartbeat** to prevent event loss during reconnection
7. **Specify server-side diff computation** for VersionHistory component
8. **Add frontend performance safeguards** (lazy loading, IntersectionObserver for badges)

