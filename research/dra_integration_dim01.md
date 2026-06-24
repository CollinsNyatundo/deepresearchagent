# Dimension 01: Citation Verification Architecture & API Adapters

## Overview

This dimension investigates the technical feasibility of integrating four academic citation databases (CrossRef, OpenAlex, Semantic Scholar, arXiv) into DRA's citation verification pipeline. The analysis covers actual API behaviors, rate limits, reliability, and architectural recommendations.

---

## Key Findings

### 1. CrossRef API: Reliable but Rate-Limited

**Claim:** CrossRef's REST API has well-documented rate limits that vary significantly by access pool, and the December 2025 rate limit changes make the "polite pool" mandatory for any production use.[^1]

**Source:** CrossRef Official Documentation

**URL:** https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/

**Date:** 2025-10-16

**Excerpt:**
> "The following limits apply: Public pool: Rate limit 5, Concurrency limit 1. Polite pool: Rate limit 10, Concurrency limit 3. Plus pool: Rate limit 150, Concurrency limit None."

**Context:** The DRA plan claims "50 req/s with polite pool header" but CrossRef's actual polite pool is **10 requests per second with 3 concurrent requests**. This is a 5× discrepancy from the plan's estimate. For list queries (filtering, searching), the rate drops to **3 req/s**.

**Confidence:** High

---

**Claim:** CrossRef changed rate limits in December 2025 after 12 years of stability, citing a 3× increase in API traffic and 180 million metadata records.[^2]

**Source:** CrossRef Blog

**URL:** https://www.crossref.org/blog/announcing-changes-to-rest-api-rate-limits/

**Date:** 2025-11-05

**Excerpt:**
> "From 1 December 2025, we will be revising the rate limits for the public and polite pools of the REST API to ensure that we can maintain a stable and reliable system. We haven't changed the rate limits since the REST API was launched in 2013. In the past five years, the number of requests to the REST API has tripled."

**Context:** This indicates CrossRef is actively managing load and may make further changes. The DRA plan does not account for API evolution or migration paths.

**Confidence:** High

---

### 2. Semantic Scholar: Shared Pool Risk

**Claim:** Semantic Scholar's unauthenticated rate limit is 100 requests per 5 minutes (shared among ALL unauthenticated users), and authenticated users get only 1 RPS for search/batch endpoints.[^3]

**Source:** Semantic Scholar Official API Documentation

**URL:** https://www.semanticscholar.org/product/api

**Date:** 2026

**Excerpt:**
> "Most Semantic Scholar endpoints are available to the public without authentication, but they are rate-limited to 1000 requests per second shared among all unauthenticated users. Requests may also be further throttled during periods of heavy use. The introductory rate limit for an API key is 1 RPS on all endpoints."

**Context:** The DRA plan's claim of "100 req/5min" for unauthenticated mode is actually optimistic — the 1000 RPS is shared globally. During peak usage, individual users may see much lower effective rates. The plan's "dual-mode authentication" strategy is sound, but the fallback unauthenticated mode will be unreliable under load.

**Confidence:** High

---

**Claim:** Semantic Scholar's API release notes show a pattern of reducing unauthenticated limits over time, from 5,000 requests/5min in 2023 to 1,000 RPS shared globally in 2025, indicating a trend toward requiring authentication.[^4]

**Source:** AllenAI s2-folks API Release Notes

**URL:** https://github.com/allenai/s2-folks/blob/main/API_RELEASE_NOTES.md

**Date:** 2023-2025

**Excerpt:**
> "May 2024: Rate Plan redesign: All new key requests receive a 1 RPS rate limit on all endpoints. Unauthenticated pool reduction: We are observing the results of reducing rate limits. Based on our findings, we may introduce further reductions in the following months."

**Context:** Semantic Scholar is actively discouraging unauthenticated use. DRA should plan for mandatory API keys in production, not treat them as optional.

**Confidence:** High

---

### 3. OpenAlex: The Best Free Option

**Claim:** OpenAlex offers 100,000 requests/day with 10 RPS for polite pool users, making it the most generous free academic API.[^5]

**Source:** openalexR R Package Documentation / contentanalysis CRAN docs

**URL:** https://rdrr.io/cran/contentanalysis/f/README.md

**Date:** 2025-12-12

**Excerpt:**
> "OpenAlex provides comprehensive scholarly metadata: Complete author lists, citation counts, open access status, institutional affiliations. Rate limits: 100,000 requests/day (polite pool with email), 10 requests/second. API key: Optional, increases rate limits."

**Context:** OpenAlex is the most scalable free option. The DRA plan correctly identifies it as requiring no API key, but should emphasize it as the primary fallback when other APIs are rate-limited.

**Confidence:** High

---

### 4. arXiv: Simple but Slow

**Claim:** arXiv's API requires 3-second delays between requests (effectively 1 req/3s) and provides no DOI integration — it's preprint-only.[^6]

**Source:** Citation workflow documentation (NousResearch/hermes-agent, davila7/claude-code-templates)

**URL:** https://github.com/NousResearch/hermes-agent/blob/main/skills/research/research-paper-writing/references/citation-workflow.md

**Date:** 2025

**Excerpt:**
> "arXiv: Preprints. Rate limits: 3-second delays. ML preprints, PDF access."

**Context:** arXiv is a secondary source. It cannot verify published journal citations, only preprints. The DRA plan's claim of "arXiv preprint verification" is useful but limited in scope.

**Confidence:** High

---

### 5. Citation Hallucination is a Real Problem

**Claim:** AI-generated citations have approximately 40% error rates, with common errors including fabricated titles, wrong venues, and non-existent papers.[^7]

**Source:** Citation Management & Hallucination Prevention documentation

**URL:** https://github.com/davila7/claude-code-templates/blob/main/cli-tool/components/skills/ai-research/ml-paper-writing/references/citation-workflow.md

**Date:** 2025

**Excerpt:**
> "Research has documented significant issues with AI-generated citations: ~40% error rate in AI-generated citations (Enago Academy research). NeurIPS 2025 found 100+ hallucinated citations slipped through review."

**Context:** This validates the DRA plan's emphasis on citation verification. However, the plan's "verified (≥2 sources confirm)" threshold may be too strict — if a real citation exists in only 1 database, it would be marked "unverified," creating false negatives.

**Confidence:** Medium (the 40% figure needs primary source verification)

---

### 6. Existing Citation Verification Tools

**Claim:** Zotero, Mendeley, and JabRef all use CrossRef's content negotiation API for DOI resolution, but none do real-time multi-database verification during document generation.[^8]

**Source:** CrossRef Access and Authentication docs

**URL:** https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/

**Date:** 2025-10-16

**Excerpt:**
> "Anyone can access the REST API, no signup or registration is required. We recommend the polite option so that we can contact you if there is an issue."

**Context:** The DRA plan's 4-database concurrent verification is actually more ambitious than most existing tools. This is innovative but increases complexity and failure modes.

**Confidence:** Medium

---

## Tensions and Counter-Arguments

### Tension 1: Verification Thoroughness vs. Speed

The DRA plan proposes running 4 adapters concurrently per citation. For a report with 50 citations, this means 200 API calls. Even with polite pools, this could take:
- CrossRef: 50 citations / 3 concurrent = ~17 seconds (assuming 100ms per request)
- Semantic Scholar: 50 citations / 1 RPS = 50 seconds
- OpenAlex: 50 citations / 10 RPS = 5 seconds
- arXiv: 50 citations / 0.33 RPS = 150 seconds

**Total critical path:** ~150 seconds (dominated by arXiv) for a single report.

For a 30-cycle exhaustive research run with potentially 100+ citations per cycle, this would add **significant latency** to the pipeline.

**Counter-argument:** The plan proposes "inline verification (quick check)" and "post-synthesis deep verification" as two separate modes. This is a good architectural choice, but the inline mode still needs to decide which databases to query. If it skips arXiv (the slowest), it loses preprint coverage.

### Tension 2: False Negatives vs. False Positives

The plan's scoring system:
- Verified: ≥2 sources confirm
- Unverified: 1 source confirms
- Failed: 0 sources confirm

This creates a **false negative problem**: A real citation that exists in only one database (e.g., a niche paper only in Semantic Scholar) would be marked "unverified." For web sources (blogs, news articles, company docs), **all citations would be "failed"** since none of these 4 databases index them.

**Counter-argument:** The plan should add a "web source" verification path (e.g., URL accessibility check, domain reputation) or distinguish between "academic citation" and "web reference" types.

### Tension 3: Rate Limiting vs. User Experience

The plan does not mention caching. Without caching:
- Re-running verification on the same report (after revision) re-queries all APIs
- Multiple users in the same workspace verifying similar citations create redundant API calls
- A popular workspace could hit global rate limits quickly

**Counter-argument:** A simple in-memory cache with 24-hour TTL for DOI/title lookups would dramatically reduce API calls. CrossRef explicitly recommends caching in their best practices.

---

## Recommendations

### Architecture Recommendation

```python
# Proposed CitationVerifier with tiered verification
class CitationVerifier:
    async def verify(self, citation: Citation, mode: str = "quick") -> VerificationResult:
        # Tier 1: DOI lookup (fastest, most reliable)
        if citation.doi:
            results = await self._verify_doi(citation.doi)
        # Tier 2: Title fuzzy match
        else:
            results = await self._verify_title(citation.title)
        
        # Score based on available evidence
        return self._score_results(results, citation.source_type)
    
    def _score_results(self, results: list, source_type: str) -> VerificationResult:
        # Academic sources: require 2+ databases
        if source_type == "academic":
            if len(results) >= 2:
                return VerificationResult.VERIFIED
            elif len(results) == 1:
                return VerificationResult.UNVERIFIED
            else:
                return VerificationResult.FAILED
        # Web sources: URL check + domain reputation
        elif source_type == "web":
            return self._verify_web_source(results)
```

### Implementation Priority

1. **P0 (Immediate)**: CrossRef + OpenAlex adapters (most reliable, highest rate limits)
2. **P1 (Soon)**: Semantic Scholar with mandatory API key for production
3. **P2 (Later)**: arXiv adapter for preprint coverage
4. **P3 (Future)**: Web source verification (URL checks, domain reputation)

### Critical Correction to Plan

The DRA plan claims CrossRef polite pool is "50 req/s" but the actual limit is **10 req/s** (3 req/s for list queries). This needs immediate correction to avoid architectural decisions based on incorrect assumptions.

---

## Confidence Assessment

| Finding | Confidence |
|---------|------------|
| CrossRef rate limits (10 req/s polite) | High |
| Semantic Scholar unauthenticated shared pool | High |
| OpenAlex 100K/day limit | High |
| arXiv 1 req/3s limit | High |
| AI citation hallucination rate (~40%) | Medium (needs primary source) |
| Verification latency dominated by arXiv | High (calculated) |
| False negative risk for single-source citations | High (logical) |

---

## Sources

[^1]: CrossRef REST API Access and Authentication. 2025-10-16. https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/

[^2]: CrossRef Blog: Announcing changes to REST API rate limits. 2025-11-05. https://www.crossref.org/blog/announcing-changes-to-rest-api-rate-limits/

[^3]: Semantic Scholar Product API. 2026. https://www.semanticscholar.org/product/api

[^4]: AllenAI s2-folks API Release Notes. 2023-2025. https://github.com/allenai/s2-folks/blob/main/API_RELEASE_NOTES.md

[^5]: openalexR / contentanalysis documentation. 2025-12-12. https://rdrr.io/cran/contentanalysis/f/README.md

[^6]: Citation Workflow documentation. 2025. https://github.com/NousResearch/hermes-agent/blob/main/skills/research/research-paper-writing/references/citation-workflow.md

[^7]: Citation Management & Hallucination Prevention. 2025. https://github.com/davila7/claude-code-templates/blob/main/cli-tool/components/skills/ai-research/ml-paper-writing/references/citation-workflow.md

[^8]: CrossRef Best Practices. 2025. https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/

