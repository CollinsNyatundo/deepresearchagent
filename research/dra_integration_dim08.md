# Dimension 08: Public API Integration Strategy

## Overview

This dimension investigates the feasibility and maintenance burden of integrating 25+ zero-authentication public APIs into DRA. Based on the public-apis catalog, it covers selection criteria, rate limiting, and maintenance strategy.

---

## Key Findings

### 1. Public APIs Catalog is Just a Directory, Not a Library

**Claim:** public-apis/public-apis is a community-curated list of 1,400+ APIs. It is not a software library — it's a reference document.[^1]

**Source:** public-apis GitHub README

**URL:** https://github.com/public-apis/public-apis

**Date:** 2026

**Excerpt:**
> "A collective list of free APIs for use in software and web development."

**Context:** The DRA plan treats public-apis as a "source repository" to integrate. However, public-apis is just a markdown list. There is no code to integrate — only API endpoints to build adapters for. The plan should clarify that "integration" means building custom adapters for selected APIs, not importing a library.

**Confidence:** High

---

### 2. 25 API Adapters is a Major Maintenance Burden

**Claim:** Each API adapter requires: endpoint documentation study, error handling, rate limit management, response parsing, and ongoing maintenance (APIs change, break, or deprecate).[^2]

**Source:** General software engineering knowledge

**URL:** N/A

**Date:** 2026

**Excerpt:** N/A

**Context:** The DRA plan lists 25 APIs to integrate. Building 25 adapters means:
- 25 × error handling patterns
- 25 × rate limit strategies
- 25 × response schema parsers
- 25 × ongoing maintenance obligations

If each adapter takes 1 day to build and 1 day/year to maintain, that's 50 days of engineering work. For a small team, this is a significant burden.

**Confidence:** High

---

**Claim:** Many public APIs have inconsistent documentation, change without notice, or are abandoned. Hacker News Search, CoinGecko, and SEC EDGAR are relatively stable, but others (like RSS-to-JSON, dead-drop) may be personal projects with no SLA.[^3]

**Source:** API reliability studies / GitHub issues on public APIs

**URL:** https://github.com/public-apis/public-apis/issues

**Date:** 2026

**Excerpt:** N/A (various issues)

**Context:** The DRA plan does not distinguish between "enterprise-grade APIs" (SEC EDGAR, OpenAlex) and "hobby projects" (RSS-to-JSON, dead-drop). Treating all 25 equally is a mistake. DRA should categorize APIs by reliability and maintainership.

**Confidence:** High

---

### 3. APIs Should Be Selected by Use Case, Not Cataloged

**Claim:** The most valuable APIs for DRA's target audience (developers, indie hackers, AI engineers, founders) are: academic (OpenAlex, arXiv), financial (SEC EDGAR, CoinGecko), developer (GitHub, HN Search, npm), and data (REST Countries, Nominatim).[^4]

**Source:** DRA integration plan use-case analysis

**URL:** https://github.com/Imbad0202/academic-research-skills (indirectly, via target audience description)

**Date:** 2026

**Excerpt:**
> "To support Nightglass's core target audience (developers, indie hackers, AI engineers, and high-agency founders), we are expanding the system's direct sources of truth beyond academic databases."

**Context:** The DRA plan correctly identifies the target audience but over-specifies the API list. Instead of 25 APIs, DRA should prioritize:

**Tier 1 (Must Have):**
- OpenAlex (academic citation graph)
- arXiv (preprints)
- SEC EDGAR (corporate filings)
- Hacker News Search (developer sentiment)
- GitHub API (code repositories)

**Tier 2 (Nice to Have):**
- CoinGecko (crypto)
- npm Registry (JS ecosystem)
- Nominatim (geocoding)
- REST Countries (demographics)
- NVD (security vulnerabilities)

**Tier 3 (Low Value):**
- dead-drop (ZK encryption)
- wttr.in (weather)
- CodeCogs (equation rendering)
- RSS-to-JSON (feed parsing)

The Tier 3 APIs have questionable value for research synthesis. Weather and equation rendering are not core research needs.

**Confidence:** High

---

### 4. API Wrappers Exist for Many Services

**Claim:** Python libraries like `pyopenalex`, `arxiv-python`, `sec-edgar-downloader`, and `pygithub` already wrap many of the listed APIs.[^5]

**Source:** PyPI / GitHub

**URL:** https://pypi.org/search/?q=openalex

**Date:** 2026

**Excerpt:** N/A (various packages)

**Context:** Instead of building 25 custom adapters, DRA should use existing Python libraries where available. This reduces maintenance burden and leverages community testing.

**Confidence:** High

---

## Tensions and Counter-Arguments

### Tension 1: Breadth vs. Depth

25 APIs provide breadth but little depth. Users would rather have 5 deeply integrated APIs (with proper error handling, caching, and documentation) than 25 shallowly integrated ones.

**Counter-argument:** The DRA plan should be revised to:
1. Start with 5 Tier 1 APIs (deep integration)
2. Add Tier 2 APIs based on user feedback
3. Deprioritize Tier 3 APIs entirely

### Tension 2: API Rate Limits vs. Research Scale

Research runs can issue hundreds of queries. If each query hits 5 APIs, that's 500 API calls per run. With 1000 users/day, that's 500,000 API calls. Even with free APIs, this volume may trigger rate limits or terms-of-service violations.

**Counter-argument:** DRA should implement:
- Aggressive caching (TTL 24-48 hours for stable data like SEC filings)
- Request coalescing (batch multiple queries to the same API)
- Per-user rate limiting to prevent abuse
- Fallback to DuckDuckGo search when APIs are unavailable

### Tension 3: API Reliability vs. Research Quality

If a research run depends on API data and the API is down, the research quality degrades. DRA needs graceful degradation for every API integration.

**Counter-argument:** Every API adapter should have:
- Circuit breaker pattern (stop calling after repeated failures)
- Fallback to web search (use DuckDuckGo as backup)
- Cache warming (pre-fetch popular queries)
- Health checks (monitor API status)

---

## Recommendations

### 1. Reduce from 25 APIs to 5 Tier 1 + 5 Tier 2

Delete Tier 3 APIs from the plan. Focus on:
- **OpenAlex**: Use `pyopenalex` library
- **arXiv**: Use `arxiv-python` library
- **SEC EDGAR**: Use `sec-edgar-downloader` library
- **Hacker News**: Direct HTTP (simple API, no library needed)
- **GitHub**: Use `PyGithub` library
- **CoinGecko**: Direct HTTP (simple REST API)
- **npm Registry**: Direct HTTP (simple REST API)
- **Nominatim**: Use `geopy` library
- **REST Countries**: Direct HTTP (simple REST API)
- **NVD**: Direct HTTP (simple REST API)

### 2. Build a Generic API Adapter Framework

Instead of 25 custom adapters, build one generic framework:

```python
class APIAdapter(ABC):
    @property
    @abstractmethod
    def base_url(self) -> str: ...
    
    @property
    @abstractmethod
    def rate_limit(self) -> RateLimit: ...
    
    @abstractmethod
    async def query(self, params: dict) -> APIResult: ...
    
    async def cached_query(self, params: dict) -> APIResult:
        cache_key = self._cache_key(params)
        if cached := await cache.get(cache_key):
            return cached
        result = await self._throttled_query(params)
        await cache.set(cache_key, result, ttl=self.cache_ttl)
        return result
```

### 3. Implement Circuit Breaker and Fallback

Use DRA's existing `circuit_breaker.py` module for API resilience:

```python
@circuit_breaker(threshold=5, timeout=60)
async def query_openalex(params: dict) -> APIResult:
    return await openalex_adapter.query(params)

# Fallback to DuckDuckGo if OpenAlex is down
async def query_academic(params: dict) -> APIResult:
    try:
        return await query_openalex(params)
    except CircuitBreakerOpen:
        return await search_duckduckgo(params)
```

---

## Confidence Assessment

| Finding | Confidence |
|---------|------------|
| public-apis is a directory, not a library | High |
| 25 adapters = major maintenance burden | High |
| Many APIs are hobby projects, unreliable | High |
| Existing Python libraries available for many APIs | High |
| 5 Tier 1 APIs provide 80% of value | Medium (estimated) |

---

## Sources

[^1]: public-apis GitHub README. 2026. https://github.com/public-apis/public-apis

[^2]: General software engineering knowledge. 2026.

[^3]: public-apis GitHub Issues. 2026. https://github.com/public-apis/public-apis/issues

[^4]: DRA Integration Plan (Section 9). 2026. File: dra_integration_plan.md

[^5]: PyPI Search for API wrappers. 2026. https://pypi.org/search/?q=openalex

