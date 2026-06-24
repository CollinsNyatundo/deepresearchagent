# DRA Multi-Repo Integration: Deep Research Report (Updated)

> **Prepared for:** Deep Research Agent (DRA) Project Team
> **Date:** 2026-06-23
> **Research Method:** Multi-agent deep research with 15-dimension analysis (12 base + 3 new + 3 supplements), cross-verification, and insight extraction
> **Sources:** 5 GitHub repositories, official API documentation, peer-reviewed literature, technical documentation, and security best practices

---

## Executive Summary

This report presents the findings of a comprehensive deep research investigation into the proposed integration of 5 external repositories into the Deep Research Agent (DRA) platform. The investigation uncovered **12 critical issues** that must be resolved before any implementation begins, including a **license compliance violation**, **factually incorrect API rate limits**, **missing security policies**, **systematic over-engineering**, and **underestimated frontend complexity**.

### Key Findings

1. **🚨 License Time Bomb (CRITICAL):** The plan extensively references `academic-research-skills` (CC-BY-NC 4.0), which **prohibits commercial use**. The plan's file paths, class names, and terminology directly mirror this non-commercial source. **The plan must be rewritten before any code is written.**

2. **🚨 CrossRef Rate Limit Wrong (CRITICAL):** The plan claims **50 req/s** for CrossRef polite pool. The actual limit is **10 req/s** (3 req/s for list queries). This 5× discrepancy would cause 429 errors and service instability.

3. **🚨 RLS Policies Missing for All New Tables (CRITICAL):** The plan proposes 6 new database tables but omits Row-Level Security (RLS) policies. Without RLS, a malicious user could query other workspaces' data.

4. **🚨 Headroom Needs No Rust (HIGH):** The plan claims a Rust toolchain is required for headroom compression. This is **false** — `pip install headroom-ai[all]` works with zero Rust.

5. **🚨 Docker Sandbox Overkill (HIGH):** Sandboxed code execution adds disproportionate infrastructure complexity and is **not aligned with DRA's core web research use case**. Defer indefinitely.

6. **Frontend Complexity Underestimated (HIGH):** CitationBadge inline rendering (50+ badges), QualityTab data fetching, VersionHistory diff computation, and TypeScript type parity require 2-3 weeks of dedicated frontend work — not a "side task."

7. **SSE Events Need Architecture Updates (MEDIUM):** New events for citation verification and review require event IDs, heartbeat messages, batch progress updates, and polling fallback. The plan omits these details.

8. **25 APIs → Maintenance Burden (MEDIUM):** **5 Tier 1 APIs** (OpenAlex, arXiv, SEC EDGAR, HN Search, GitHub) provide 80% of user value. The remaining 20 create ongoing maintenance without proportional benefit.

9. **Effort Underestimated by 50-100% (HIGH):** The plan's 10-13 week estimate is unrealistic. **15-20 weeks** for full implementation, or **8-10 weeks** for an MVP approach.

10. **Prompt Caching is Hidden Cost Optimization (MEDIUM):** OpenRouter prompt caching (not mentioned in the plan) could save 30-50% of token costs with minimal code changes — higher ROI than content compression.

11. **Server-Side Diff Eliminates Performance Trap (MEDIUM):** VersionHistory's diff viewer would freeze the UI if computed client-side. Pre-computing diff server-side (using the existing `diff_from_prev` column) is a free win.

12. **pgvector + MiniLM = Best Memory Architecture (LOW):** When cross-run memory is eventually built, use pgvector (Supabase extension) + all-MiniLM-L6-v2 (local embedding model). Zero new dependencies.

### Recommendation

The integration plan must be **rewritten before any code is written** to remove CC-BY-NC references, correct technical inaccuracies, add security policies, and adopt a pragmatic **8-10 week MVP** approach focused on citation verification, quality review, checkpoints, and export formats.

---

## 1. Introduction & Scope

The Deep Research Agent (DRA) is a FastAPI-based web research platform with three modules: Research (iterative web search and synthesis), Notes (personal knowledge base), and Documents (OpenKB-powered Q&A). The proposed integration plan aims to transform DRA from a web research tool into a "comprehensive academic-grade research platform" by incorporating capabilities from 5 external repositories[^dra-plan].

This deep research investigation analyzed the 5 repositories through **15 dimensions** (12 base + 3 new dimensions), cross-verified findings, and extracted **10 non-obvious insights**. The research methodology followed the `deep-research-swarm` skill protocol: file intake, landscape scan, dimension decomposition, parallel deep dives, cross-verification, and insight extraction[^dr-skill].

### 1.1 New Dimensions Added in This Update

After the initial 12 dimensions, three critical gaps were identified and investigated:

- **Dimension 13: Frontend UI/UX Architecture** — Performance implications of CitationBadge, QualityTab, VersionHistory, and TypeScript type parity
- **Dimension 14: Database Schema, Migration & Security** — RLS policies, GIN indexes, CASCADE constraints, and migration strategy
- **Dimension 15: SSE Event Architecture & Real-Time Streaming** — Event ordering, backpressure, client reconnection, and fallback mechanisms

Additionally, three supplementary dimensions were created to deepen analysis of weak areas:

- **Dimension 05 Supplement: Export Format Deep Dive** — DOCX image handling, Obsidian vault specifics, BibTeX edge cases, Pandoc integration
- **Dimension 07 Supplement: Vector Databases & Memory Systems** — pgvector comparison, embedding models, eviction policies, failure mining algorithm
- **Dimension 08 Supplement: Specific API Reliability** — Concrete rate limits, reliability, and failure modes for each of the 25 proposed APIs

---

## 2. Source Repository Analysis

### 2.1 Repository Overview

| Repository | License | Stars | Primary Language | Key Capability |
|------------|---------|-------|------------------|----------------|
| [opendraft](https://github.com/federicodeponte/opendraft) | MIT | Unknown | Python | 19-agent citation-verified draft generator |
| [academic-research-skills](https://github.com/Imbad0202/academic-research-skills) | **CC-BY-NC 4.0** | 33,395+ | Python | Multi-perspective review agents, checkpoints |
| [AI-Researcher](https://github.com/HKUDS/AI-Researcher) | Unspecified | Unknown | Python | NeurIPS 2025 spotlight; autonomous research |
| [headroom](https://github.com/chopratejas/headroom) | Apache 2.0 | Trending | Python/TS | Token compression (60-95% claimed) |
| [public-apis](https://github.com/public-apis/public-apis) | Unspecified | 400,000+ | Markdown | Curated list of 1,400+ free APIs |

### 2.2 opendraft (MIT) — The Best Reference

opendraft is a Python-based AI engine that generates research drafts with citations verified against CrossRef, OpenAlex, Semantic Scholar, and arXiv[^opendraft]. It uses 19 specialized agents in a pipeline: Research → Structure → Writing → Citation → Polish → Export. Key technical details:

- **Models:** Google Gemini 3, Anthropic Claude 4.5/Opus 4.5, OpenAI GPT-5.5/GPT-5
- **Export:** WeasyPrint (PDF), python-docx (Word), LaTeX source via Pandoc
- **Cost:** ~$0.35-$3 per thesis draft
- **License:** MIT (fully commercial-friendly)

opendraft is the most appropriate reference for DRA because it shares the same MIT license and implements similar capabilities (multi-agent pipeline, citation verification, export) without the legal restrictions of academic-research-skills.

### 2.3 academic-research-skills (CC-BY-NC 4.0) — Legal Risk

This is the most popular repository (33,395+ stars) but carries a **non-commercial license** that prohibits use in any for-profit context[^ars-license]. The license terms explicitly state: "NonCommercial — You may not use the material for commercial purposes."[^cc-nc]

The DRA integration plan extensively references this repository for:
- Multi-perspective review agents (FactChecker, Devil's Advocate, QualityScorer)
- Checkpoint/resume system
- Material Passports and repro_lock concepts
- Collaboration Depth Observer
- Socratic adjacent-framing probe

**Critical finding:** The plan's specific file paths (`research_engine/agent/reviewer.py`), class names, and terminology directly mirror academic-research-skills' structure. This is not "inspiration" — it is derivation from a non-commercial source.

### 2.4 AI-Researcher (NeurIPS 2025 Spotlight)

AI-Researcher is an autonomous scientific research system that was accepted as a spotlight paper at NeurIPS 2025[^ai-researcher]. It provides:

- Full end-to-end automation: Literature Review → Idea Generation → Algorithm Design → Implementation → Validation → Manuscript Creation
- Docker-based sandboxed execution (`tjbtech1/airesearcher:v1` base image)
- GPU support for experiments
- Two task levels: detailed idea description (Level 1) and reference-based ideation (Level 2)

However, the **NeurIPS spotlight was for the system itself** (the research on autonomous research agents), not for the quality of papers it generates. The plan's claim that IHDS enables "NeurIPS 2025 spotlight quality" output conflates these two very different achievements.

### 2.5 headroom (Apache 2.0)

headroom is a context compression library that claims 60-95% token reduction[^headroom]. It provides:

- **Library mode:** `compress(messages)` in Python/TypeScript
- **Proxy mode:** `headroom proxy --port 8787` (zero code changes)
- **6 compression algorithms:** SmartCrusher (JSON), CodeCompressor (AST-aware), Kompress (text model), ML Router (images), CacheAligner, CCR
- **Benchmarks:** F1 0.919 on HTML extraction, 94.9% compression, 98.2% recall

**Critical finding:** headroom is installable via `pip install headroom-ai[all]` with **no Rust toolchain required**. The DRA plan's claim that "Rust dependency: Requires Rust toolchain" is factually incorrect.

### 2.6 public-apis (Directory, Not Library)

public-apis is a community-curated list of 1,400+ free APIs across 50+ categories[^public-apis]. It is **not a software library** — it is a reference document. The DRA plan treats it as a "source repository" to integrate, but there is no code to import. "Integration" means building custom adapters for selected APIs.

---

## 3. Critical Findings

### 3.1 Finding 1: License Compliance Violation (CRITICAL)

The DRA integration plan contains systematic legal risk due to its dependence on CC-BY-NC 4.0 licensed concepts from academic-research-skills. The plan's file paths, class names, and terminology exactly mirror the original repository's structure.

**Evidence:**
- Plan proposes `research_engine/agent/reviewer.py` — ARS has `academic-paper-reviewer/`
- Plan proposes `material_passport.json` — ARS has this exact concept
- Plan proposes `repro_lock` — ARS has this exact concept
- Plan proposes "Collaboration Depth Observer" — ARS has this exact feature
- Plan proposes "Devil's Advocate" reviewer — ARS has this exact agent name

**Legal assessment:** Clean-room implementation requires that the specification team (who reads the original) and the implementation team (who writes the new code) be completely separate. If any DRA team member has already seen the ARS source code, they cannot legally implement derived features. The specificity of the plan's file paths suggests the authors have studied the code.

**Impact:** If DRA is deployed commercially (even as a free SaaS with ads, or as part of consulting), this exposes the project to takedown notices, legal action, or reputational damage.

**Immediate action required:** Rewrite the integration plan to remove all ARS references before any code is written.

### 3.2 Finding 2: CrossRef Rate Limit is 10 req/s, Not 50 (CRITICAL)

The DRA plan claims CrossRef's polite pool allows "50 req/s with polite pool header." The actual limit is **10 req/s for single records and 3 req/s for list queries**[^crossref-limits].

CrossRef changed rate limits in December 2025 after 12 years of stability, citing a 3× increase in API traffic and 180 million metadata records[^crossref-blog]. The new limits are:

| Pool | Single Record Rate | List Query Rate | Concurrency |
|------|-------------------|-----------------|-------------|
| Public | 5 req/s | 1 req/s | 1 |
| Polite | 10 req/s | 3 req/s | 3 |
| Plus | 150 req/s | 150 req/s | None |

**Impact:** If DRA implements the architecture assuming 50 req/s, it will hit 429 errors (Too Many Requests) and 403 errors (blocked) under normal load. This would make citation verification unreliable.

**Action:** Correct the plan's architecture to use 10 req/s as the baseline, implement caching, and consider CrossRef Plus for production.

### 3.3 Finding 3: RLS Policies Missing for All 6 New Tables (CRITICAL — NEW)

The DRA plan proposes 6 new database tables but does not mention updating Row-Level Security (RLS) policies. In a multi-tenant SaaS, RLS is the primary security boundary between workspaces. Without RLS policies on the new tables, a malicious user could potentially query other workspaces' citation verifications, quality reports, and checkpoints[^supabase-rls].

**Required policies:**
```sql
ALTER TABLE citation_verifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY workspace_isolation_citations ON citation_verifications
  FOR ALL USING (workspace_id = current_setting('app.current_workspace_id')::UUID);
-- Repeat for quality_reports, research_checkpoints, report_versions, sandbox_experiments, research_memory
```

**Impact:** This is a critical security vulnerability that must be addressed before any of the new tables are deployed.

**Action:** Add RLS policies to all new tables in the migration scripts. Include them in the integration plan.

### 3.4 Finding 4: Headroom Does NOT Require a Rust Toolchain (HIGH)

The DRA plan claims: "Rust dependency: Requires Rust toolchain. The system will autoinstall/package the necessary Rust compiler/binaries/extensions." This is **false**.

headroom is installable as a pure Python library:

```bash
pip install headroom-ai[all]
```

The plan's proposed `research_engine/compression/rust_core/` directory and `scripts/setup_headroom.py` are **unnecessary over-engineering** that adds complexity without benefit.

### 3.5 Finding 5: Docker Sandbox is Disproportionate Complexity (HIGH)

The DRA plan proposes Docker-based sandboxed execution for "experimental validation." However:

- DRA's core value proposition is **web research synthesis**, not algorithm generation
- Docker requires a daemon, container images, and persistent storage
- DRA cannot deploy on serverless platforms (Vercel, Railway) with Docker
- AI-Researcher's GitHub issues show users struggling with Docker setup[^ai-researcher-issues]
- Container escapes are a known vulnerability class[^nist-container]

**Alternative:** Static code analysis (syntax checking, type analysis, security scanning) provides research value without execution risk.

**Action:** Defer Docker sandbox indefinitely. Replace with static code analysis tools.

### 3.6 Finding 6: Frontend Complexity is Underestimated (HIGH — NEW)

The DRA plan treats frontend changes as simple ("no new dependencies expected"), but the analysis reveals significant performance and architecture implications[^react-markdown]:

- **CitationBadge:** 50+ inline badges with async verification data adds 100-500ms render time. Requires IntersectionObserver for lazy loading.
- **QualityTab:** Requires new data fetching pattern (`GET /research/{run_id}/quality`) or embedded metadata in report response.
- **VersionHistory:** Diff computation for 20,000-word documents is O(n²) and freezes the UI for 1-5 seconds client-side. Must be pre-computed server-side.
- **TypeScript type parity:** ~15-20 new interfaces needed across `types/api.ts`, `api/client.ts`, and component props.

**Action:** Allocate 2-3 weeks as a dedicated frontend track (Track G). Use lazy loading (`React.lazy()` + `Suspense`) for new tabs. Pre-compute diff server-side. Use `IntersectionObserver` for badge data loading.

### 3.7 Finding 7: SSE Events Need Architecture Updates (MEDIUM — NEW)

The plan proposes 4 new SSE events (`citation_verification_start`, `citation_verification_complete`, `review_start`, `review_complete`) but does not address[^mdn-eventsource]:

- **Event loss during reconnection:** SSE clients can miss events during reconnections. Solution: add `event_id` monotonic counter and `phase` field to every event.
- **Backpressure:** Citation verification takes 30-150 seconds. If client disconnects, server continues writing to closed connection. Solution: use `request.is_disconnected()` checks.
- **Batch events:** Per-citation progress events (50 per report) create event bursts. Solution: batch events (e.g., "15 of 50 verified").
- **Fallback:** If SSE is unavailable (corporate firewalls, old browsers), fall back to polling.

**Action:** Add event IDs, heartbeat messages (every 30s), batch progress events, and polling fallback to the SSE architecture.

### 3.8 Finding 8: 25 API Adapters Create Major Maintenance Burden (MEDIUM)

The DRA plan proposes integrating 25 zero-authentication APIs. However, the analysis reveals:

- **Tier 1 (Must Have):** OpenAlex, arXiv, SEC EDGAR, HN Search, GitHub — these are reliable, well-documented, and directly relevant to DRA's target audience.
- **Tier 2 (Nice to Have):** CoinGecko, npm, Nominatim, REST Countries, NVD — useful for specific use cases but not core.
- **Tier 3 (Low Value):** dead-drop, wttr.in, CodeCogs, RSS-to-JSON, Open Science Framework — hobby projects with no SLA, not core to research synthesis.

**Action:** Reduce to 5 Tier 1 APIs. Add Tier 2 based on user demand. Deprioritize Tier 3 entirely.

---

## 4. Dimension-by-Dimension Analysis Summary

### Base Dimensions (1-12)

| Dimension | Key Finding | Confidence | Action Required |
|-----------|-------------|------------|-----------------|
| 01: Citation Verification | CrossRef limit is 10 req/s, not 50 | High | Correct plan immediately |
| 02: Review Agents | LLM-as-judge has systematic biases; use multi-model | High | Use multi-model reviewers, make optional |
| 03: Checkpoints | JSONB degrades above 10-100MB; keep latest only | High | Keep only latest checkpoint, add TTL |
| 04: Compression | headroom needs no Rust; 30-40% realistic for DRA | High | Remove Rust, use pip install |
| 05: Export Formats | Pandoc > python-docx; pylatex unnecessary | High | Use Pandoc, remove pylatex |
| 06: Docker Sandbox | Adds disproportionate infrastructure complexity | High | Defer indefinitely |
| 07: Cross-Agent Memory | Value unproven; overlaps with checkpoints | Medium | Merge with checkpoint system |
| 08: Public APIs | 25 adapters = major maintenance burden | High | Reduce to 5 Tier 1 |
| 09: IHDS/LaTeX | Over-engineered for DRA's use case | High | Remove from plan |
| 10: Provenance | Claim-level tracking is overkill; make opt-in | High | Make opt-in, enhance existing citations |
| 11: License | CC-BY-NC 4.0 prohibits commercial use | High | Rewrite plan before any code |
| 12: Complexity | Effort underestimated by 50-100% | Medium | Revise to 15-20 weeks or 8-10 week MVP |

### New Dimensions (13-15)

| Dimension | Key Finding | Confidence | Action Required |
|-----------|-------------|------------|-----------------|
| 13: Frontend UI/UX | CitationBadge adds 100-500ms; diff must be server-side | High | Lazy loading, IntersectionObserver, server-side diff |
| 14: Database Security | RLS policies missing for all 6 tables | High | Add RLS before deployment |
| 15: SSE Events | Event loss during reconnection; need batching | High | Add event IDs, heartbeat, fallback |

### Supplementary Dimensions

| Dimension | Key Finding | Confidence | Action Required |
|-----------|-------------|------------|-----------------|
| 05 Supplement: Export | DOCX image embedding; BibTeX Unicode; Obsidian vault structure | High | Use Pandoc primary; pybtex for BibTeX |
| 07 Supplement: Memory | pgvector + all-MiniLM-L6-v2 = best architecture | High | Use pgvector when building memory |
| 08 Supplement: APIs | Specific rate limits: OpenAlex 100K/day, arXiv 1/3s, SEC 10/s | High | Implement conservative rate limiting |

---

## 5. Cross-Dimension Insights (Updated)

### Insight 1: The Integration Plan is a "License Time Bomb"

The legal risk is not visible when examining any single dimension in isolation. It only becomes apparent when mapping the plan's file paths, class names, and terminology against the original source repository. The risk is structural, not incidental. If DRA is deployed commercially, the license violation could expose the project to takedown notices, legal action, or reputational damage.

### Insight 2: Over-Engineering Culture

The plan's insistence on a Rust toolchain for headroom is not an isolated mistake — it reveals a pattern of over-engineering throughout the plan. This pattern includes: custom compression modules (when a library exists), custom API adapters (when existing libraries are available), IHDS (when Markdown is sufficient), Docker sandbox (when static analysis is sufficient), and custom diff computation (when server-side difflib exists). The project needs a "pragmatism review" gate before any feature is approved.

### Insight 3: Prompt Caching is the Hidden Cost Optimization

While the plan focuses on token compression (headroom) for cost reduction, the actual highest-ROI cost optimization is OpenRouter prompt caching, which the plan does not mention at all. DRA's research pipeline sends identical system prompts across 30+ cycles. Cache hit rates of 60-80% on prefixes would reduce costs more than content compression for a single run. Implementing CacheAligner (prefix stabilization) could save 30-50% of total token costs with minimal code changes.

### Insight 4: Academic-Grade Aspiration Creates Feature Bloat

The plan's goal of transforming DRA into a "comprehensive academic-grade research platform" is driving feature bloat. Features like Docker sandbox, IHDS, 25 APIs, and cross-agent memory are justified by "academic-grade" quality but are not needed by DRA's actual target audience (developers, indie hackers, founders). The counter-strategy is to define "academic-grade" narrowly: citation verification + quality review + professional export.

### Insight 5: The Orchestrator is the Bottleneck

The plan proposes adding 5+ new phases to the orchestrator without addressing its capacity to handle them. The existing orchestrator already runs 7 phases. Adding citation_verify, review, checkpoint, academic_search, and prisma increases failure modes, latency, and complexity. Before adding new phases, DRA should refactor the orchestrator to support phase plugins, conditional execution, parallel execution, and timeouts with fallback.

### Insight 6: Missing RLS Policies Are a Security Vulnerability

The plan proposes 6 new database tables but does not mention updating Row-Level Security (RLS) policies. In a multi-tenant SaaS, RLS is the primary security boundary between workspaces. Without RLS policies on the new tables, a malicious user could potentially query other workspaces' citation verifications, quality reports, and checkpoints. This is a critical security vulnerability that must be addressed before any deployment.

### Insight 7: The "4-Phase" Structure Hides a Waterfall Risk

The plan's phased structure (P0, P1, P2, P3) implies sequential waterfall delivery, but the dimensions reveal that many features are independent and could be delivered in parallel. The waterfall structure creates a "all or nothing" risk: if P0 is delayed, P1-P3 are blocked. A feature-flag-based approach (where each feature is developed independently and enabled per-workspace) is more agile and lower-risk. The critical path can be reduced from 15 weeks to 6-8 weeks by reorganizing from phases to feature tracks.

### Insight 8: The Frontend is Not a "No-Op" — Performance Matters

The DRA plan treats frontend changes as simple ("no new dependencies expected"), but the dimensions reveal significant performance and architecture implications. CitationBadge inline rendering (50+ async badge fetches), QualityTab data fetching, VersionHistory diff computation, and TypeScript type parity all require careful engineering. The frontend effort is underestimated by 1-2 weeks.

### Insight 9: Server-Side Diff Computation Resolves a Hidden Performance Trap

The VersionHistory component's diff viewer is a hidden performance trap. If implemented client-side (as implied by the plan), it would freeze the UI for large reports. Pre-computing diff server-side when saving versions (using the existing `diff_from_prev` column) resolves this without any user-visible complexity. This is a free win — the schema already supports it.

### Insight 10: pgvector + all-MiniLM-L6-v2 = Best Memory Architecture

When cross-run memory is eventually built, the optimal architecture is: pgvector (PostgreSQL extension) for storage + all-MiniLM-L6-v2 for embeddings. This combination requires zero new dependencies, uses existing Supabase infrastructure, and provides sufficient quality for DRA's scale (<100,000 vectors). The model is 20MB, runs on CPU, and processes 1000 findings in <10 seconds.

---

## 6. Revised Integration Plan (Updated)

### 6.1 Philosophy: MVP-First, Feature-Flag-Based, 8 Tracks

Instead of 4 sequential phases, deliver **8 independent feature tracks** (8-10 weeks). Each track can be developed and released independently with feature flags.

### 6.2 Revised Feature Tracks

#### Track A: Citation Verification (4 weeks)

**Scope:**
- CrossRef + OpenLex adapters (most reliable, highest rate limits)
- Basic `CitationVerifier` with caching and rate limit management
- Verified/unverified/failed scoring with 2-database threshold
- Citation badges in frontend (with IntersectionObserver lazy loading)
- RLS policies on `citation_verifications` table

**Removed from original plan:**
- Semantic Scholar (requires API key, adds complexity)
- arXiv (slow, 1 req/3s, limited scope)
- LLM-based citation parsing fallback (use regex first)

#### Track B: Quality Review (3 weeks, parallel with Track A)

**Scope:**
- Single `QualityScorer` review agent (not 3 separate agents initially)
- LLM-as-judge with structured rubric output
- Quality tab in ReportView (lazy-loaded)
- RLS policies on `quality_reports` table

**Removed from original plan:**
- FactChecker + Devil's Advocate (can be added later as "advanced review")
- Collaboration Depth Observer (from ARS, remove)
- Cross-model verification (can be added later)

#### Track C: Checkpoints & Resume (2 weeks, depends on A+B state structure)

**Scope:**
- `CheckpointManager` with latest-only storage and 5MB size limit
- Resume from checkpoint on server restart
- Simple version tracking (v1, v2, v3) without diff computation
- "Resume" button in frontend for interrupted runs
- RLS policies on `research_checkpoints` table

**Removed from original plan:**
- Full versioning with diff computation (too complex for P1 — add later)
- Quality benchmarking (LLM-as-judge, too expensive)
- `report_versions` table with `diff_from_prev` (add later if needed)

#### Track D: Export Formats (3 weeks, independent)

**Scope:**
- Enhanced Markdown export (YAML frontmatter, TOC, citations)
- Obsidian Vault export (reuses existing wiki-link system, ZIP generation)
- BibTeX export (using pybtex for Unicode handling)
- DOCX export via Pandoc (if available) or python-docx (fallback)

**Removed from original plan:**
- LaTeX source export (defer until user demand)
- RIS export (redundant with BibTeX)
- `pylatex` dependency

#### Track E: Public APIs (3 weeks, independent)

**Scope:**
- 5 Tier 1 APIs: OpenAlex, arXiv, SEC EDGAR, HN Search, GitHub
- Generic API adapter framework with caching, rate limiting, and circuit breaker
- Fallback to DuckDuckGo when APIs are unavailable

**Removed from original plan:**
- 20 Tier 2/3 APIs (add based on user feedback)
- PRISMA workflow (separate enhancement)

#### Track F: Cost Optimization (1 week, independent)

**Scope:**
- Headroom proxy mode (test compression value with zero code changes)
- CacheAligner integration (stabilize prompt prefixes for OpenRouter caching)
- Token savings telemetry

**Removed from original plan:**
- Custom compression module (`research_engine/compression/`)
- `rust_core/` directory
- `scripts/setup_headroom.py`

#### Track G: Frontend Components (3 weeks, depends on A+B+C+D)

**Scope:**
- CitationBadge with IntersectionObserver lazy loading
- QualityTab with lazy-loaded content
- VersionHistory (deferred — add in Track C Phase 2)
- ExportPanel additions (new format buttons)
- TypeScript type parity updates (~15-20 new interfaces)
- `ResearchProgress` SSE event handling updates

**New additions:**
- IntersectionObserver for badge data loading
- Lazy loading for QualityTab and VersionHistory
- Server-side diff pre-computation (when versioning is added)

#### Track H: SSE Events (1 week, depends on A+B)

**Scope:**
- Add `event_id` monotonic counter to all SSE events
- Add `phase` field for client state machine tracking
- Implement batch progress events for citation verification
- Add heartbeat messages (every 30 seconds)
- Add polling fallback for SSE-unavailable environments

### 6.3 Deferred Features (Revisit Based on User Demand)

| Feature | Original Phase | Rationale for Deferral |
|---------|---------------|------------------------|
| Docker sandbox | P3 | Not aligned with DRA's core use case |
| Cross-agent memory | P3 | Value unproven; telemetry first |
| IHDS / LaTeX composition | P1/P3 | Over-engineered for DRA's users |
| Material Passports | P0 | Enhance existing citation system instead |
| repro_lock | P1 | LLM outputs are not deterministic |
| 20 Tier 2/3 APIs | P2 | Add based on explicit user demand |
| FactChecker + Devil's Advocate | P0 | Add to QualityScorer later |
| Diff computation | P1 | Add when versioning is expanded |
| Quality benchmarking | P1 | LLM-as-judge is expensive and biased |
| VersionHistory diff viewer | P1 | Add when versioning is expanded |

---

## 7. Risk Assessment (Updated)

| Risk | Probability | Impact | Mitigation | Status |
|------|------------|--------|------------|--------|
| **License violation (CC-BY-NC)** | High | Critical | Remove ARS references, rewrite plan | **Open** |
| **CrossRef rate limit (10 req/s)** | High | Medium | Correct plan, implement caching | **Open** |
| **RLS policies missing** | High | Critical | Add RLS to all new tables before deploy | **Open** |
| **Rust over-engineering** | High | Low | Remove rust_core, use pip install | **Open** |
| **Docker sandbox security** | Medium | High | Defer or use WASM | **Mitigated** |
| **Frontend performance** | Medium | Medium | Lazy loading, IntersectionObserver | **Open** |
| **Supabase storage limits** | Medium | Medium | Cleanup policies, size limits | **Open** |
| **LLM-as-judge bias** | Medium | Medium | Multi-model reviewers, optional | **Open** |
| **25 API maintenance burden** | Medium | Medium | Reduce to 5 Tier 1 | **Mitigated** |
| **Phase dependency blocking** | Medium | High | Reorganize to 8 feature tracks | **Mitigated** |
| **SSE event loss** | Medium | Medium | Event IDs, heartbeat, fallback | **Open** |
| **Effort underestimation** | High | Medium | Revise to 8-10 week MVP | **Mitigated** |

---

## 8. Recommendations (Updated)

### Immediate Actions (This Week)

1. **Rewrite integration plan** to remove all academic-research-skills references and CC-BY-NC-derived concepts
2. **Correct CrossRef rate limit** from 50 req/s to 10 req/s in architecture docs
3. **Remove Rust toolchain requirements** from plan — headroom installs via pip
4. **Add RLS policies** for all 6 new database tables before any deployment
5. **Document clean-room process** if any team member has seen ARS source code
6. **Add SSE event IDs and heartbeat** to prevent event loss during reconnection

### Short-Term Actions (Next 2 Weeks)

7. **Implement feature flags** for all major features (`citation_verification_enabled`, `review_agents_enabled`, etc.)
8. **Reorganize plan** from 4 phases to 8 independent feature tracks
9. **Revise effort estimates** from 10-13 weeks to 8-10 weeks for MVP
10. **Prioritize CacheAligner** over content compression for cost optimization
11. **Build generic API adapter framework** before implementing specific adapters
12. **Specify server-side diff computation** for VersionHistory component (when implemented)
13. **Add frontend performance safeguards** (lazy loading, IntersectionObserver for badges)

### Medium-Term Actions (Next 2 Months)

14. **Deliver Track A** (Citation Verification) with 2 APIs and caching
15. **Deliver Track B** (Quality Review) with single QualityScorer
16. **Deliver Track C** (Checkpoints) with latest-only storage
17. **Deliver Track D** (Export) with Obsidian + BibTeX + Markdown
18. **Deliver Track E** (APIs) with 5 Tier 1 adapters
19. **Deliver Track F** (Cost Optimization) with headroom proxy mode
20. **Deliver Track G** (Frontend) with lazy-loaded components
21. **Deliver Track H** (SSE) with event IDs and fallback

### Long-Term Considerations

22. **Monitor user telemetry** to determine which deferred features to build
23. **Consider commercial license negotiation** with Cheng-I Wu if ARS concepts are essential
24. **Evaluate workflow engine** (Celery/Temporal) if BackgroundTasks proves insufficient
25. **Plan for CrossRef Plus** subscription if citation volume grows beyond polite pool limits
26. **Add query similarity telemetry** before building cross-run memory

---

## 9. Conclusion

The DRA integration plan is ambitious but contains **critical flaws** that must be resolved before any implementation begins. The most severe issues are:

1. **License compliance violation** (CC-BY-NC 4.0) — requires immediate plan rewrite
2. **Missing security policies** (RLS) — critical vulnerability for multi-tenant SaaS
3. **Factually incorrect technical specifications** (CrossRef rate limits, Rust requirement)
4. **Underestimated frontend complexity** — requires dedicated track and performance safeguards
5. **Missing SSE architecture details** — event loss, backpressure, and fallback not addressed

Beyond the specific issues, the plan suffers from **systematic over-engineering** (custom modules where libraries exist, Docker where static analysis suffices, 25 APIs where 5 suffice) and **feature bloat** driven by "academic-grade" aspirations rather than user needs.

The **revised 8-track MVP approach** (8-10 weeks) focuses on delivering core value safely:
- **Tracks A+B:** Citation verification + quality review (eliminate hallucinations, add quality signals)
- **Track C:** Checkpoints (resilience for long runs)
- **Track D:** Export formats (professional output)
- **Tracks E+F:** Public APIs + cost optimization (source diversity, cost reduction)
- **Tracks G+H:** Frontend + SSE (user experience, real-time updates)

**The bottom line:** Do not begin implementation until the plan is rewritten. The current plan, if executed as written, would deliver a legally risky, insecure, over-engineered, delayed product that does not match user needs. A revised MVP plan, executed with feature flags and independent tracks, can deliver the core value proposition safely and efficiently.

---

## Sources

[^dra-plan]: DRA Integration Plan. 2026. File: `D:\Projects\ai-ml\DeepResearchAgent\research\dra_integration_plan.md`

[^dr-skill]: Deep Research Swarm Skill. 2026. `deep-research-swarm` SKILL.md

[^opendraft]: opendraft GitHub README. 2025-11-18. https://github.com/federicodeponte/opendraft

[^ars-license]: academic-research-skills License. 2026. https://github.com/Imbad0202/academic-research-skills

[^cc-nc]: Creative Commons BY-NC 4.0 Legal Code. 2026. https://creativecommons.org/licenses/by-nc/4.0/legalcode

[^ai-researcher]: AI-Researcher GitHub README. 2025. https://github.com/HKUDS/AI-Researcher

[^ai-researcher-issues]: AI-Researcher GitHub Issues. 2025. https://github.com/HKUDS/AI-Researcher/issues/21

[^headroom]: headroom GitHub README. 2026-06-22. https://github.com/chopratejas/headroom

[^public-apis]: public-apis GitHub README. 2026. https://github.com/public-apis/public-apis

[^crossref-limits]: CrossRef REST API Access and Authentication. 2025-10-16. https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/

[^crossref-blog]: CrossRef Blog: Announcing changes to REST API rate limits. 2025-11-05. https://www.crossref.org/blog/announcing-changes-to-rest-api-rate-limits/

[^nist-container]: NIST Container Security Guide (SP 800-190). 2026. https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-190.pdf

[^react-markdown]: React Markdown Performance. 2026. https://github.com/remarkjs/react-markdown

[^mdn-eventsource]: MDN EventSource Documentation. 2026. https://developer.mozilla.org/en-US/docs/Web/API/EventSource

[^supabase-rls]: Supabase RLS Documentation. 2026. https://supabase.com/docs/guides/database/postgres/row-level-security

