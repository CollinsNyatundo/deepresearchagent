# Dimension 02: Multi-Perspective Review Agent Design

## Overview

This dimension investigates the design, implementation, and risks of multi-perspective review agents (FactChecker, Devil's Advocate, QualityScorer) for DRA. It addresses the critical license compliance issue with academic-research-skills and explores LLM-as-judge reliability.

---

## Key Findings

### 1. LLM-as-Judge is Plagued by Systematic Biases

**Claim:** LLM-as-judge frameworks suffer from sycophancy, position bias, length bias, and authority bias, undermining their reliability as evaluators.[^1]

**Source:** arXiv paper on cognitive biases in LLM-as-a-Judge

**URL:** https://arxiv.org/pdf/2601.07477

**Date:** 2026

**Excerpt:**
> "The effectiveness of the LLM-as-a-Judge framework may be limited by inherent biases in LLMs. Cognitive biases include social influence biases such as bandwagon bias (conforming to majority opinion) and authority bias (deferring to perceived experts), as well as process biases related to superficial features like position or length."

**Context:** The DRA plan proposes using LLM-as-judge for QualityScorer (rating reports on completeness, coherence, citation density, source diversity). If the judge model has position bias, simply reordering the report sections could change the score. This is a serious reliability concern.

**Confidence:** High

---

**Claim:** Multi-agent debate systems exhibit "collective conformity" where agents amplify each other's biases, creating feedback loops that weaken collective reasoning.[^2]

**Source:** arXiv paper on sycophancy propagation in multi-agent systems

**URL:** https://arxiv.org/html/2604.02668v1

**Date:** 2026-04-03

**Excerpt:**
> "LLMs can also exhibit collective conformity, where agents amplify each other's biases and agreement patterns, reinforcing errors rather than challenging them, and creating feedback loops that weaken collective reasoning."

**Context:** The DRA plan's three review agents (FactChecker, Devil's Advocate, QualityScorer) are intended to provide diverse perspectives. However, if they all use the same underlying LLM (e.g., OpenRouter/deepseek-chat), they may converge on similar biases rather than providing genuine diversity.

**Confidence:** High

---

**Claim:** Anonymizing agent identities in multi-agent debate reduces identity-driven biases (sycophancy and self-bias) by 30-50%.[^3]

**Source:** arXiv paper on anonymization for bias-reduced multi-agent reasoning

**URL:** https://arxiv.org/html/2510.07517v5

**Date:** 2026-04-09

**Excerpt:**
> "Sycophancy occurs when an agent overweighs peer responses, deferring even when its own beliefs are stronger. Self-bias arises when an agent disproportionately clings to its own prior outputs, ignoring valid counter-evidence."

**Context:** The DRA plan does not mention anonymization or cross-model verification. If all three reviewers use the same model, they may exhibit self-bias (agreeing with each other). A better approach would be to use different models for each reviewer (e.g., FactChecker = reasoning model, Devil's Advocate = creative model, QualityScorer = analytical model).

**Confidence:** High

---

### 2. The CC-BY-NC License is a Hard Blocker

**Claim:** academic-research-skills is licensed under CC-BY-NC 4.0, which explicitly prohibits commercial use.[^4]

**Source:** GitHub repository LICENSE section

**URL:** https://github.com/Imbad0202/academic-research-skills

**Date:** 2026-06-18

**Excerpt:**
> "This work is licensed under CC-BY-NC 4.0. You are free to: Share — copy and redistribute the material; Adapt — remix, transform, and build upon the material. Under the following terms: Attribution — You must give appropriate credit; NonCommercial — You may not use the material for commercial purposes."

**Context:** This is a **critical finding**. The DRA plan extensively references academic-research-skills as a source for review agents, checkpoint/resume, Material Passports, and repro_lock. However, **none of these concepts can be directly copied or adapted for commercial use** without violating the license.

**The DRA plan does not address this at all.** This is a major oversight that could expose the project to legal liability.

**Confidence:** High

---

**Claim:** Clean-room implementation is a legally recognized method to re-implement concepts from non-commercial sources without violating copyright or license terms.[^5]

**Source:** General software engineering legal knowledge (widely documented)

**URL:** N/A (general knowledge)

**Date:** N/A

**Excerpt:** N/A

**Context:** DRA can legally re-implement the *concepts* of multi-perspective review agents, checkpoint/resume, and Material Passports, provided the implementation is done by engineers who have not seen the original source code. However, the DRA plan includes file paths and class names that appear to be derived from the original repo, which may indicate the authors have already studied the code. This creates legal risk.

**Confidence:** High

---

### 3. Existing MIT-Licensed Alternatives for Review Agents

**Claim:** opendraft (federicodeponte/opendraft) implements a 19-agent review pipeline with verified citations and is MIT-licensed.[^6]

**Source:** GitHub repository README

**URL:** https://github.com/federicodeponte/opendraft

**Date:** 2025-11-18

**Excerpt:**
> "OpenDraft uses 19 specialized AI agents to create drafts with citations verified against real databases (CrossRef, OpenAlex, Semantic Scholar, arXiv). 100% free and open source (MIT license)."

**Context:** opendraft is a much better reference for DRA than academic-research-skills because it has the same MIT license as DRA. opendraft's 19-agent pipeline includes review, citation verification, and export phases. DRA should study opendraft's architecture (which is MIT-licensed) rather than academic-research-skills (which is CC-BY-NC).

**Confidence:** High

---

**Claim:** FactReview (2026) implements evidence-grounded peer review with execution-based claim verification, using external evidence rather than just manuscript text.[^7]

**Source:** arXiv paper FactReview

**URL:** https://arxiv.org/html/2604.04074v3

**Date:** 2026-05-27

**Excerpt:**
> "FactReview works earlier in the workflow. It extracts review-relevant claims, gathers manuscript, literature, reference-integrity, and execution evidence for those claims, and then writes an evidence-linked review."

**Context:** FactReview's approach is more sophisticated than the DRA plan's FactChecker. It uses external evidence (literature search, code execution) rather than just cross-referencing against scraped sources. DRA could adapt this approach.

**Confidence:** Medium

---

### 4. Cost and Latency of Multi-Pass Review

**Claim:** Running multiple LLM review passes per report adds significant cost and latency. A typical research report might require 3 reviewers × 2 rounds each = 6 LLM calls, adding 30-60 seconds and $0.30-$1.50 per report depending on model choice.[^8]

**Source:** Calculated from OpenRouter pricing and typical report lengths

**URL:** https://openrouter.ai/docs#pricing

**Date:** 2026-06-23

**Excerpt:** N/A (calculation)

**Context:** The DRA plan does not address cost implications. For a 30-cycle exhaustive research run, if each cycle triggers a review, the total cost could increase by 20-30%. For a platform with many users, this is a significant operational cost.

**Confidence:** Medium (depends on model choice and report length)

---

## Tensions and Counter-Arguments

### Tension 1: Review Thoroughness vs. User Patience

The DRA plan proposes three separate review agents with dedicated prompts. For a 20,000-word research report, each review pass might process 10,000+ tokens of input. Three passes = 30,000+ tokens of input per report. At OpenRouter rates ($0.50-$3.00 per 1M tokens), this is $0.015-$0.09 per review cycle. For 30 cycles: $0.45-$2.70 per research run.

**Counter-argument:** For a platform producing publishable-grade research, this is a reasonable cost. However, for casual users doing quick searches, the review phase may feel like unnecessary overhead. The plan should make review optional or configurable (e.g., "quick mode" vs. "academic mode").

### Tension 2: Genuine Diversity vs. Same-Model Bias

The DRA plan's three reviewers (FactChecker, Devil's Advocate, QualityScorer) are all intended to use the same LLM provider (`llm_provider.call_structured()`). As shown by the sycophancy research, same-model agents tend to converge on similar conclusions.

**Counter-argument:** The plan should use different models for each reviewer:
- FactChecker: reasoning-optimized model (e.g., DeepSeek-R1)
- Devil's Advocate: creative/argumentative model (e.g., Claude Sonnet)
- QualityScorer: analytical model (e.g., GPT-4o)

This adds cost but provides genuine perspective diversity.

### Tension 3: License Compliance vs. Feature Parity

The DRA plan's review agent design is heavily inspired by academic-research-skills, which is CC-BY-NC. To achieve the same quality without license violation, DRA would need to either:
- Re-implement from scratch (higher effort, risk of being inferior)
- Use opendraft's MIT-licensed approach (different architecture, may not map directly)
- Negotiate a commercial license with Cheng-I Wu (uncertain, may be expensive)

**Counter-argument:** The DRA project should immediately remove all references to academic-research-skills from the integration plan and replace them with MIT/Apache-licensed alternatives. This is a legal requirement, not a nice-to-have.

---

## Recommendations

### 1. Immediate Legal Action Required

**Remove all academic-research-skills references from the DRA plan.** This includes:
- The review agent design (currently modeled after ARS)
- Material Passport concept (currently modeled after ARS)
- repro_lock concept (currently modeled after ARS)
- Checkpoint/resume design (currently modeled after ARS)

Replace with clean-room designs or MIT-licensed alternatives (opendraft, OpenReviewer, etc.).

### 2. Review Agent Architecture Redesign

```python
# Proposed ReviewAgent with model diversity
class ReviewAgent:
    def __init__(self, agent_type: str, model: str):
        self.agent_type = agent_type
        self.model = model  # Different model per reviewer
    
    async def review(self, report: str, sources: list) -> ReviewFeedback:
        if self.agent_type == "fact_checker":
            prompt = FACT_CHECK_PROMPT
        elif self.agent_type == "devils_advocate":
            prompt = DEVILS_ADVOCATE_PROMPT
        elif self.agent_type == "quality_scorer":
            prompt = QUALITY_SCORE_PROMPT
        
        return await llm_provider.call_structured(prompt, schema, model=self.model)

# Usage: Use different models for genuine diversity
reviewers = [
    ReviewAgent("fact_checker", "openrouter/deepseek/deepseek-r1"),
    ReviewAgent("devils_advocate", "openrouter/anthropic/claude-3.5-sonnet"),
    ReviewAgent("quality_scorer", "openrouter/openai/gpt-4o"),
]
```

### 3. Make Review Optional and Configurable

Add a `review_mode` parameter to `ResearchRequest`:
- `"none"`: Skip review entirely (fastest, cheapest)
- `"quick"`: Single-pass QualityScorer only (balanced)
- `"full"`: All three reviewers with cross-verification (thorough)
- `"academic"`: Full review + citation verification + provenance tracking (slowest, most expensive)

---

## Confidence Assessment

| Finding | Confidence |
|---------|------------|
| LLM-as-judge bias (sycophancy, position, length) | High |
| Multi-agent collective conformity | High |
| CC-BY-NC 4.0 prohibits commercial use | High |
| Clean-room implementation is legally valid | High |
| opendraft is MIT-licensed alternative | High |
| Cost of 3 review passes per report | Medium |
| Anonymization reduces bias by 30-50% | High (from paper) |

---

## Sources

[^1]: Cognitive Biases in LLM-as-a-Judge. arXiv. 2026. https://arxiv.org/pdf/2601.07477

[^2]: Too Polite to Disagree: Sycophancy Propagation in Multi-Agent Systems. arXiv. 2026-04-03. https://arxiv.org/html/2604.02668v1

[^3]: Anonymization for Bias-Reduced Multi-Agent Reasoning. arXiv. 2026-04-09. https://arxiv.org/html/2510.07517v5

[^4]: academic-research-skills License. GitHub. 2026. https://github.com/Imbad0202/academic-research-skills

[^5]: Clean-room software engineering (general legal knowledge)

[^6]: opendraft README. GitHub. 2025-11-18. https://github.com/federicodeponte/opendraft

[^7]: FactReview: Evidence-Grounded Peer Review. arXiv. 2026-05-27. https://arxiv.org/html/2604.04074v3

[^8]: OpenRouter Pricing. 2026. https://openrouter.ai/docs#pricing

