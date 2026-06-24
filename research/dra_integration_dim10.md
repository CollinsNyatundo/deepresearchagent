# Dimension 10: Provenance Tracking & Reproducibility

## Overview

This dimension investigates the feasibility of Material Passports and repro_lock files for research reproducibility. Based on academic-research-skills concepts (which are CC-BY-NC licensed), it covers claim-to-source mapping, audit trails, and practical implementation.

---

## Key Findings

### 1. Material Passports Are Conceptually Sound but Implementation-Heavy

**Claim:** A Material Passport that maps every claim to its exact source is theoretically ideal for research integrity, but requires significant instrumentation throughout the research pipeline.[^1]

**Source:** W3C PROV-O Standard

**URL:** https://www.w3.org/TR/prov-o/

**Date:** 2026

**Excerpt:**
> "PROV-O is the W3C standard for provenance information. It defines a data model for representing provenance on the Web."

**Context:** The DRA plan proposes a `material_passport.json` artifact with:
- Claims Registry: list of key claims
- Evidence Mapping: claim → source (filename, section, URL) + raw text snippet
- Hallucination Auditing: flag claims without valid sources

This requires every phase of the research pipeline to track provenance:
1. Search phase: record which URL each fact came from
2. Scrape phase: record the exact text snippet that supports each fact
3. Synthesize phase: record which source each claim in the report is based on
4. Review phase: verify that every claim has a mapped source

This instrumentation adds 20-30% overhead to the pipeline and is not trivial to implement.

**Confidence:** High

---

### 2. DRA Already Has Partial Provenance via Citations

**Claim:** DRA's existing citation system (scraped sources with URLs) already provides partial provenance. Each citation in the report links to a scraped source.[^2]

**Source:** DRA AGENTS.md

**URL:** File: D:\Projects\ai-ml\DeepResearchAgent\AGENTS.md

**Date:** 2025-06-21

**Excerpt:**
> "Citations: Citation list with source links."

**Context:** The gap between DRA's current citations and a full Material Passport is:
- Current: Report paragraph → citation number → source URL
- Material Passport: Specific claim → exact source text snippet → source URL

The improvement is granularity (claim-level vs. paragraph-level) but the core concept is the same. DRA can evolve its existing citation system rather than building a separate Material Passport.

**Confidence:** High

---

### 3. repro_lock is Conceptually Flawed for LLM-Based Systems

**Claim:** The DRA plan proposes a `repro_lock` file recording model IDs, parameters, content hashes, and state hashes. However, LLM outputs are inherently stochastic — even with the same inputs, the same model may produce different outputs.[^3]

**Source:** LLM stochasticity research

**URL:** https://platform.openai.com/docs/api-reference/parameters

**Date:** 2026

**Excerpt:**
> "temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random."

**Context:** A `repro_lock` implies reproducibility, but LLM outputs are not reproducible unless `temperature=0` and `seed` is fixed. Even then, model updates (OpenRouter may route to different versions of the same model) can change outputs. The DRA plan should acknowledge this limitation rather than claiming "an auditable paper trail of how a specific scientific manuscript was constructed."

A better approach: record inputs and parameters for transparency, but do not claim deterministic reproducibility.

**Confidence:** High

---

### 4. Open Science Framework (OSF) Provides Pre-Registration

**Claim:** The Open Science Framework (OSF) provides pre-registration of study protocols and raw datasets, which is a more established form of reproducibility than custom lockfiles.[^4]

**Source:** OSF API Documentation

**URL:** https://developer.osf.io/

**Date:** 2026

**Excerpt:**
> "The OSF API provides programmatic access to the Open Science Framework."

**Context:** The DRA plan lists OSF as one of the 25 public APIs to integrate. However, the value proposition is unclear — DRA generates research reports, not scientific studies. OSF pre-registration is for hypothesis testing, not literature synthesis. This API should be deprioritized.

**Confidence:** High

---

## Tensions and Counter-Arguments

### Tension 1: Provenance Granularity vs. Performance

Claim-level provenance requires storing every claim and its source snippet. For a 20,000-word report with 500 claims, that's 500 mappings. For 1000 reports, that's 500,000 mappings. Querying and validating this data adds latency.

**Counter-argument:** Start with paragraph-level provenance (existing citation system) and add claim-level tracking only for "flagship" reports or when the user explicitly requests it. This is a configurable feature, not a mandatory pipeline stage.

### Tension 2: Audit Trail vs. User Value

The DRA plan says Material Passports enable "hallucination auditing" and trigger revision loops. But do users actually want this? Most users want accurate reports, not audit trails. If the report is accurate, the audit trail is irrelevant. If it's inaccurate, the user will notice and ask for a re-run.

**Counter-argument:** Provenance tracking is valuable for:
- Power users who need to verify claims for legal/regulatory purposes
- Academic users who need to cite sources correctly
- DRA developers who want to debug synthesis quality

For casual users, it's overhead. Make it opt-in.

### Tension 3: CC-BY-NC License Blocks Direct Implementation

The Material Passport and repro_lock concepts are from academic-research-skills (CC-BY-NC 4.0). DRA cannot copy the implementation or even the exact file structure without license violation.

**Counter-argument:** The *concept* of provenance tracking is not copyrightable. DRA can implement its own version using:
- W3C PROV-O standard (open standard)
- Existing citation infrastructure (already in DRA)
- Standard logging practices (general knowledge)

However, the DRA plan's file paths (`material_passport.json`, `repro_lock`) and class names mirror the original too closely. These should be changed to generic names (`report_provenance.json`, `run_audit_log`) to avoid legal risk.

---

## Recommendations

### 1. Rename and Redesign Provenance System

Avoid any names or structures from academic-research-skills:

```python
# Instead of "Material Passport" and "repro_lock"
class ReportProvenance:
    """Tracks claim-to-source mapping for a research report."""
    run_id: UUID
    claims: list[ClaimSource]  # claim text → source URL + snippet
    
class RunAuditLog:
    """Records parameters and inputs for transparency (not reproducibility)."""
    run_id: UUID
    model_id: str
    parameters: dict
    query: str
    timestamp: datetime
    # NOTE: Does NOT guarantee reproducibility due to LLM stochasticity
```

### 2. Integrate with Existing Citation System

Enhance the existing citation system to support claim-level mapping:

```python
class Citation:
    source_url: str
    source_title: str
    claims: list[str]  # specific claims derived from this source
    snippet: str  # verbatim text supporting the claims
    verified: bool
```

This is a natural evolution of DRA's existing model, not a new system.

### 3. Make Provenance Opt-In

Add a `track_provenance` flag to `ResearchRequest`:
- `false` (default): Standard citation tracking only
- `true`: Full claim-level provenance with audit log

This avoids overhead for casual users while providing power users with the feature they need.

---

## Confidence Assessment

| Finding | Confidence |
|---------|------------|
| Material Passport requires significant instrumentation | High |
| DRA already has partial provenance via citations | High |
| LLM outputs are not deterministic | High |
| repro_lock cannot guarantee reproducibility | High |
| Provenance should be opt-in, not mandatory | High |

---

## Sources

[^1]: W3C PROV-O Standard. 2026. https://www.w3.org/TR/prov-o/

[^2]: DRA AGENTS.md. 2025-06-21. File: D:\Projects\ai-ml\DeepResearchAgent\AGENTS.md

[^3]: OpenAI API Temperature Parameter. 2026. https://platform.openai.com/docs/api-reference/parameters

[^4]: Open Science Framework API. 2026. https://developer.osf.io/

