# Dimension Decomposition: DRA Multi-Repo Integration

## Overview

This document decomposes the DRA integration research into 12 distinct dimensions, each approaching the problem from a unique angle. Each dimension covers current state, key evidence, tensions/counter-arguments, and requires ≥20 independent searches.

---

## Dimension 01: Citation Verification Architecture & API Adapters

**Scope:** Technical design of the 4-database citation verification system (CrossRef, OpenAlex, Semantic Scholar, arXiv), including rate limiting, caching, error handling, and fallback strategies.

**Angle:** Technical architecture and feasibility

**Expected Sources:** API documentation, GitHub issues on rate limiting, blog posts on citation verification, existing implementations (Zotero, Mendeley integration patterns)

**Overlap with:** Dim 02 (review agents use verification results), Dim 10 (provenance tracking), Dim 14 (license compliance)

---

## Dimension 02: Multi-Perspective Review Agent Design

**Scope:** Design and implementation of FactChecker, Devil's Advocate, and QualityScorer agents, including prompt engineering, aggregation logic, and SSE integration. Addresses the CC-BY-NC license concern of academic-research-skills.

**Angle:** AI agent design and quality assurance methodology

**Expected Sources:** Academic papers on LLM-as-judge, multi-agent review systems, prompt engineering guides, Claude Code skill architecture, alternative MIT-licensed review tools

**Overlap with:** Dim 01 (uses citation verification), Dim 03 (checkpoint after review), Dim 10 (provenance tracking)

---

## Dimension 03: Checkpoint/Resume & State Persistence

**Scope:** State serialization at phase boundaries, Supabase storage strategy, resume logic, and cleanup policies. Includes database performance and storage limits.

**Angle:** System resilience and fault tolerance

**Expected Sources:** FastAPI background task patterns, Supabase JSONB best practices, Celery vs BackgroundTasks comparison, state machine design patterns

**Overlap with:** Dim 05 (export pipeline uses versioned state), Dim 06 (sandbox state persistence), Dim 12 (database schema)

---

## Dimension 04: Token Compression & Cost Optimization Reality

**Scope:** Realistic assessment of headroom integration, actual compression ratios achievable in DRA's context, Rust vs Python implementation trade-offs, and cost savings validation.

**Angle:** Cost engineering and technical feasibility

**Expected Sources:** Headroom documentation, LLM context compression research, OpenRouter pricing, token optimization benchmarks, PyO3/maturin complexity

**Overlap with:** Dim 07 (cross-agent memory uses compression), Dim 15 (integration complexity)

---

## Dimension 05: Academic Document Export Pipeline

**Scope:** Implementation of 5 export formats (DOCX, LaTeX, BibTeX, RIS, Obsidian Vault), including library selection, formatting challenges, and quality assurance.

**Angle:** Document engineering and output formatting

**Expected Sources:** python-docx documentation, pylatex vs manual LaTeX generation, BibTeX format spec, RIS format spec, Obsidian vault structure, WeasyPrint alternatives

**Overlap with:** Dim 09 (IHDS generates LaTeX), Dim 10 (provenance exports), Dim 12 (database stores versions)

---

## Dimension 06: Docker Sandbox Security & Code Execution

**Scope:** Security model for isolated code execution, resource limits, network isolation, GPU passthrough, and fallback when Docker is unavailable. Addresses the AI-Researcher sandbox pattern.

**Angle:** Security engineering and infrastructure

**Expected Sources:** Docker SDK Python documentation, container security best practices, gVisor/firecracker alternatives, sandbox escape prevention, resource limit tuning

**Overlap with:** Dim 03 (checkpoints for experiment state), Dim 09 (IHDS experiments need sandbox), Dim 15 (risk assessment)

---

## Dimension 07: Cross-Agent Memory & Learning

**Scope:** Shared context storage, session deduplication, failure pattern mining, and memory isolation between workspaces. Based on headroom's SharedContext and learn features.

**Angle:** Memory systems and agent learning

**Expected Sources:** Vector database comparison, embedding caching, cross-session memory research, agent failure analysis, deduplication algorithms

**Overlap with:** Dim 04 (uses compression for storage), Dim 03 (checkpoints are per-session memory), Dim 10 (provenance is long-term memory)

---

## Dimension 08: Public API Integration Strategy

**Scope:** 25+ zero-auth API adapters, maintenance burden, rate limiting, and selection criteria. Based on public-apis catalog.

**Angle:** API ecosystem integration and maintenance

**Expected Sources:** API documentation for each service, OpenAPI specs, rate limit documentation, API deprecation history, adapter pattern best practices

**Overlap with:** Dim 01 (academic APIs overlap), Dim 09 (IHDS may need data APIs), Dim 14 (legal terms of service)

---

## Dimension 09: Hierarchical LaTeX Composition (IHDS)

**Scope:** Section-specific composers, LaTeX generation pipeline, BibTeX management, and integration with DRA's existing markdown-based output. Based on AI-Researcher's IHDS pattern.

**Angle:** Academic document generation and LaTeX engineering

**Expected Sources:** AI-Researcher paper (NeurIPS 2025), LaTeX programmatic generation, pandoc vs custom generation, academic paper structure standards, arXiv submission requirements

**Overlap with:** Dim 05 (export formats include LaTeX), Dim 06 (experiments need sandbox for figures), Dim 10 (provenance tracks LaTeX sources)

---

## Dimension 10: Provenance Tracking & Reproducibility

**Scope:** Material Passports, repro_lock files, claim-to-source mapping, and audit trail generation. Based on academic-research-skills patterns.

**Angle:** Research integrity and reproducibility

**Expected Sources:** Academic reproducibility literature, PROV-O standard, W3C provenance specs, scientific workflow systems (Galaxy, Taverna), data lineage tools

**Overlap with:** Dim 01 (citation verification feeds provenance), Dim 02 (review agents verify provenance), Dim 03 (checkpoints store provenance)

---

## Dimension 11: License Compliance & Legal Risk

**Scope:** CC-BY-NC 4.0 implications, MIT/Apache compatibility, attribution requirements, and re-implementation strategy for non-commercial components.

**Angle:** Legal and compliance engineering

**Expected Sources:** Creative Commons legal guides, open source license compatibility matrices, FSF license comparison, commercial use case law, clean room implementation guidelines

**Overlap with:** Dim 02 (review agents need license-safe implementation), Dim 15 (risk assessment)

---

## Dimension 12: Integration Complexity & Risk Assessment

**Scope:** Realistic effort estimation, dependency graph analysis, phased rollout strategy, feature flags, and fallback mechanisms.

**Angle:** Project management and risk engineering

**Expected Sources:** Software integration complexity studies, microservices vs monolith trade-offs, feature flag patterns, phased rollout case studies, technical debt management

**Overlap with:** All other dimensions (synthesizes risk across all)

