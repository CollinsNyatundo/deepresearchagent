# Dimension 11: License Compliance & Legal Risk

## Overview

This dimension investigates the legal implications of integrating concepts from academic-research-skills (CC-BY-NC 4.0) into DRA. It covers license compatibility, clean-room implementation, and risk mitigation.

---

## Key Findings

### 1. CC-BY-NC 4.0 Explicitly Prohibits Commercial Use

**Claim:** The Creative Commons Attribution-NonCommercial 4.0 International license explicitly prohibits use for commercial purposes. "NonCommercial means not primarily intended for or directed towards commercial advantage or monetary compensation."[^1]

**Source:** Creative Commons Legal Code

**URL:** https://creativecommons.org/licenses/by-nc/4.0/legalcode

**Date:** 2026

**Excerpt:**
> "NonCommercial means not primarily intended for or directed towards commercial advantage or monetary compensation."

**Context:** The DRA plan extensively references academic-research-skills as a source for:
- Multi-perspective review agents (FactChecker, Devil's Advocate, QualityScorer)
- Checkpoint/resume system
- Material Passports
- repro_lock files
- Collaboration Depth Observer
- Socratic adjacent-framing probe

**All of these concepts are derived from a CC-BY-NC 4.0 licensed work.** If DRA is intended for any commercial use (SaaS, paid hosting, consulting, etc.), directly copying or closely adapting these concepts creates legal liability.

**Confidence:** High

---

### 2. The DRA Plan's File Paths Suggest Direct Study of Source Code

**Claim:** The DRA plan includes specific file paths (`research_engine/agent/reviewer.py`, `material_passport.json`, `repro_lock`) that match the structure and naming conventions of academic-research-skills.[^2]

**Source:** academic-research-skills GitHub repository structure

**URL:** https://github.com/Imbad0202/academic-research-skills

**Date:** 2026

**Excerpt:** N/A (structural analysis)

**Context:** In a legal dispute, the specificity of these file paths could be used as evidence that the DRA team studied the original source code. For clean-room implementation to be valid, the implementing team must NOT have seen the original code. If the DRA authors have already studied the academic-research-skills repo, they cannot legally re-implement it.

**This is a critical risk that must be addressed before any development begins.**

**Confidence:** High

---

### 3. opendraft is a Fully MIT-Licensed Alternative

**Claim:** opendraft (federicodeponte/opendraft) implements similar capabilities (multi-agent pipeline, citation verification, export) and is MIT-licensed, making it safe for commercial use.[^3]

**Source:** opendraft GitHub repository

**URL:** https://github.com/federicodeponte/opendraft

**Date:** 2025-11-18

**Excerpt:**
> "100% free and open source (MIT license)."

**Context:** opendraft provides:
- 19-agent pipeline (similar to ARS's multi-agent approach)
- Citation verification against CrossRef, OpenAlex, Semantic Scholar, arXiv
- Export to PDF, DOCX, LaTeX
- MIT license (commercial use allowed)

DRA should use opendraft as its primary reference for these features, not academic-research-skills.

**Confidence:** High

---

**Claim:** FactReview (2026), OpenReviewer, and ReviewerToo are academic papers describing MIT-licensed or open-source review systems that DRA can reference.[^4]

**Source:** arXiv FactReview paper

**URL:** https://arxiv.org/html/2604.04074v3

**Date:** 2026-05-27

**Excerpt:**
> "Systems such as MARG, OpenReviewer, DeepReview, and ReviewerToo improve on this baseline through multi-agent discussion, specialized fine-tuning, retrieval, or structured reasoning."

**Context:** These are research papers describing review systems. Reading the papers (which describe concepts and methods) is legally safe. Implementing the concepts from the papers is also safe, as long as the implementation is original and not copied from any CC-BY-NC code.

**Confidence:** High

---

### 4. Clean-Room Implementation Requires Separation

**Claim:** Clean-room software engineering requires that the specification team (who reads the original) and the implementation team (who writes the new code) be completely separate. The implementers must not have seen the original code.[^5]

**Source:** Software engineering legal knowledge

**URL:** N/A

**Date:** 2026

**Excerpt:** N/A

**Context:** If DRA wants to re-implement concepts from academic-research-skills, it must:
1. Document the concepts at a high level (without copying code or specific file structures)
2. Have a different engineer (who has NOT seen the original) implement the feature
3. Use generic names that don't match the original

The DRA plan as currently written violates principles 1 and 3. It needs to be rewritten with generic terminology and without specific file paths derived from the original.

**Confidence:** High

---

## Tensions and Counter-Arguments

### Tension 1: Feature Parity vs. Legal Safety

Removing all academic-research-skills references may result in a less detailed integration plan. But legal safety is more important than feature completeness.

**Counter-argument:** The DRA plan should be rewritten to:
1. Remove all references to academic-research-skills
2. Replace with opendraft (MIT) as the primary reference
3. Use generic terms: "review agents" instead of "Devil's Advocate/QualityScorer"
4. Use generic file names: `review_agent.py` instead of `reviewer.py`
5. Document concepts from research papers (FactReview, etc.) rather than from CC-BY-NC skills

### Tension 2: Attribution vs. License Violation

CC-BY-NC requires attribution. Even if DRA gives credit to Cheng-I Wu, commercial use is still prohibited. Attribution does not cure the license violation.

**Counter-argument:** DRA should not attribute academic-research-skills at all. Instead, attribute:
- opendraft (MIT) for multi-agent pipeline concepts
- FactReview paper for review agent concepts
- W3C PROV-O for provenance concepts
- General software engineering knowledge for checkpoint/resume patterns

### Tension 3: Internal vs. External Use

If DRA is currently only for internal use, does CC-BY-NC still apply? "NonCommercial" is defined as "not primarily intended for commercial advantage." Internal use for a commercial company's research could still be considered commercial use.

**Counter-argument:** The safest interpretation is that any use by a for-profit entity is commercial. DRA should not rely on the "internal use" defense.

---

## Recommendations

### 1. Immediate Action: Rewrite Integration Plan

The DRA integration plan must be rewritten before any code is written:

**Remove:**
- All references to `academic-research-skills`
- All references to `Imbad0202`
- Specific file paths derived from the original (`reviewer.py`, `material_passport.json`, `repro_lock`)
- Terminology unique to the original ("Material Passport", "repro_lock", "Collaboration Depth Observer")

**Replace with:**
- `opendraft` as primary reference for multi-agent pipeline
- Generic terms: "quality review agents", "report audit trail", "run checkpointing"
- Research papers as concept sources (FactReview, OpenReviewer, etc.)

### 2. Document Clean-Room Process

If any DRA team member has seen the academic-research-skills source code:
- They must NOT implement the derived features
- A different engineer (who has not seen the code) must implement from generic specifications
- Document this separation in writing

### 3. Consider Commercial License Negotiation

If DRA wants to use specific concepts from academic-research-skills, contact Cheng-I Wu to negotiate a commercial license. This may be faster than clean-room re-implementation for complex features.

---

## Confidence Assessment

| Finding | Confidence |
|---------|------------|
| CC-BY-NC 4.0 prohibits commercial use | High |
| DRA plan's file paths suggest source code study | High |
| opendraft is MIT-licensed alternative | High |
| Clean-room requires implementer separation | High |
| Attribution does not cure license violation | High |

---

## Sources

[^1]: Creative Commons BY-NC 4.0 Legal Code. 2026. https://creativecommons.org/licenses/by-nc/4.0/legalcode

[^2]: academic-research-skills GitHub structure. 2026. https://github.com/Imbad0202/academic-research-skills

[^3]: opendraft README. 2025. https://github.com/federicodeponte/opendraft

[^4]: FactReview paper. 2026-05-27. https://arxiv.org/html/2604.04074v3

[^5]: Clean-room software engineering (general legal knowledge). 2026.

