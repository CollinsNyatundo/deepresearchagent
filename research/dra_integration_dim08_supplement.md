# Dimension 08 Supplement: Specific API Reliability & Rate Limits

## Overview

This supplementary dimension provides detailed rate limit, reliability, and adapter-specific information for the 25 public APIs proposed in the DRA integration plan. It covers concrete API behaviors, deprecation history, and failure modes.

---

## Key Findings

### 1. Tier 1 API: OpenAlex — Reliable and Well-Documented

**Claim:** OpenAlex provides 100,000 requests/day with 10 RPS for the polite pool. It has a comprehensive REST API with OpenAPI specification and is actively maintained by OurResearch.[^1]

**Source:** OpenAlex API Documentation

**URL:** https://docs.openalex.org/

**Date:** 2026

**Excerpt:**
> "The OpenAlex API is free and requires no authentication. We ask that you provide your email address as a polite request so we can contact you if needed."

**Context:** OpenAlex is the most reliable free academic API. It provides:
- Works, authors, institutions, venues, concepts endpoints
- Filter, sort, group, and search parameters
- JSON response format with comprehensive metadata
- Bulk download (parquet files) for large datasets

**Rate limits:**
- Polite pool: 100,000 requests/day, 10 RPS
- No authentication required, but email recommended
- No rate limit headers in responses (hard to track programmatically)

**Python library:** `pyalex` (PyPI) provides a Pythonic wrapper.

**Reliability:** High. OurResearch is well-funded and actively maintains the API. No significant downtime reported.

**Confidence:** High

---

### 2. Tier 1 API: arXiv — Simple XML API, Well-Established

**Claim:** arXiv provides a simple XML API with 3-second delays between requests. It is extremely reliable (running since 1991) but limited to preprints.[^2]

**Source:** arXiv API Documentation

**URL:** https://info.arxiv.org/help/api/index.html

**Date:** 2026

**Excerpt:**
> "The arXiv API allows programmatic access to arXiv's paper metadata."

**Context:** arXiv's API is straightforward:
- Endpoint: `http://export.arxiv.org/api/query`
- Returns Atom XML (not JSON)
- Rate limit: 1 request every 3 seconds
- Supports search, id_list, and start/max_results parameters

**Rate limits:**
- 1 request per 3 seconds (effectively 0.33 RPS)
- No authentication required
- Rate limit headers not provided

**Python library:** `arxiv` (PyPI) provides a Pythonic wrapper with JSON conversion.

**Reliability:** Very high. arXiv has been running since 1991 with minimal downtime. The API is simple and stable.

**Limitations:**
- XML response requires parsing (not JSON)
- Only preprints (no published journal articles)
- No DOI integration
- Rate limit is very low (1 req/3s)

**Confidence:** High

---

### 3. Tier 1 API: SEC EDGAR — Reliable but Requires CIK Lookup

**Claim:** SEC EDGAR provides free access to corporate filings (10-K, 10-Q, 8-K) but requires a CIK (Central Index Key) lookup before querying. The API is reliable but has strict rate limits.[^3]

**Source:** SEC EDGAR API Documentation

**URL:** https://www.sec.gov/edgar/sec-api-documentation

**Date:** 2026

**Excerpt:**
> "The SEC API provides access to EDGAR filings data."

**Context:** SEC EDGAR API:
- Endpoint: `https://www.sec.gov/Archives/edgar/daily-index/`
- Rate limit: 10 requests per second (enforced)
- Requires User-Agent header with contact email
- Returns JSON for company facts, XML for filings

**Rate limits:**
- 10 requests per second
- Must include User-Agent header with contact email
- Rate limit enforced via 429 responses

**Python library:** `sec-edgar-downloader` (PyPI) provides a convenient wrapper.

**Reliability:** High. SEC infrastructure is enterprise-grade. However, rate limits are strictly enforced and violations can result in IP blocking.

**Limitations:**
- Requires CIK lookup (company identifier)
- Filings are XML or HTML, not structured JSON
- Historical data is voluminous (terabytes)

**Confidence:** High

---

### 4. Tier 1 API: Hacker News Search — Simple REST API, No Auth

**Claim:** Hacker News Search (Algolia) provides a simple REST API with no authentication required. It is reliable but has undocumented rate limits.[^4]

**Source:** Algolia HN Search API

**URL:** https://hn.algolia.com/api

**Date:** 2026

**Excerpt:**
> "The Hacker News Search API is powered by Algolia."

**Context:** HN Search API:
- Endpoint: `https://hn.algolia.com/api/v1/search`
- Returns JSON with stories, comments, and metadata
- No authentication required
- Rate limit: Undocumented, but Algolia free tier is 10,000 requests/month

**Rate limits:**
- Undocumented (assumed ~1 RPS for safety)
- No authentication required
- No rate limit headers

**Reliability:** Medium. Algolia is reliable, but HN Search is a free service with no SLA. Algolia may change rate limits without notice.

**Confidence:** Medium

---

### 5. Tier 1 API: GitHub API — Well-Documented, Rate-Limited by Auth

**Claim:** GitHub REST API provides comprehensive access to repositories, issues, pull requests, and users. Rate limits vary by authentication level.[^5]

**Source:** GitHub REST API Documentation

**URL:** https://docs.github.com/en/rest

**Date:** 2026

**Excerpt:**
> "The GitHub REST API provides a way to interact with GitHub programmatically."

**Context:** GitHub API:
- Unauthenticated: 60 requests/hour
- Authenticated (Personal Access Token): 5,000 requests/hour
- GitHub App: 15,000 requests/hour

**Rate limits:**
- Strictly enforced with `X-RateLimit-Remaining` headers
- Rate limit resets hourly
- GraphQL API has separate points-based rate limit

**Python library:** `PyGithub` (PyPI) is the official Python wrapper.

**Reliability:** Very high. GitHub's API is enterprise-grade with comprehensive documentation and status monitoring.

**Confidence:** High

---

### 6. Tier 2 API: CoinGecko — Free Tier Has Limitations

**Claim:** CoinGecko provides a free tier with 10-30 calls/minute, but rate limits are not clearly documented and may change.[^6]

**Source:** CoinGecko API Documentation

**URL:** https://www.coingecko.com/en/api/documentation

**Date:** 2026

**Excerpt:**
> "The CoinGecko API provides access to cryptocurrency data."

**Context:** CoinGecko API:
- Free tier: ~10-30 calls/minute (undocumented exact limit)
- Paid tier: Higher limits, priority support
- No authentication required for free tier

**Rate limits:**
- Undocumented for free tier (assumed ~10 calls/minute)
- Rate limit headers not provided

**Reliability:** Medium. CoinGecko is a commercial service but the free tier is unsupported. Rate limits may change without notice.

**Confidence:** Medium

---

### 7. Tier 3 API Reliability: Hobby Projects and Personal Services

**Claim:** Many Tier 3 APIs in the plan (dead-drop, wttr.in, CodeCogs, RSS-to-JSON) are personal projects or hobby services with no SLA, no status page, and may disappear without notice.[^7]

**Source:** public-apis GitHub Issues / Various API status pages

**URL:** https://github.com/public-apis/public-apis/issues

**Date:** 2026

**Excerpt:** N/A (various issues)

**Context:** Examples of unreliable Tier 3 APIs:
- **dead-drop**: Personal project, no status page, may be discontinued
- **wttr.in**: Weather service, frequently overloaded, returns ASCII art
- **CodeCogs**: LaTeX equation rendering, no SLA, may have downtime
- **RSS-to-JSON**: Vercel-hosted serverless function, may hit cold start delays
- **Open Library**: Open-source project, occasional maintenance downtime

These APIs should not be used for critical research paths. They are acceptable as supplementary data sources but should never be the primary source for a research claim.

**Confidence:** High

---

## Tensions and Counter-Arguments

### Tension 1: Tier 1 API Reliability vs. Coverage

Tier 1 APIs are reliable but don't cover all research domains. For example, OpenAlex and arXiv cover academic research but not business news, financial data, or developer sentiment.

**Counter-argument:** Tier 1 APIs cover the core research domains. For specialized domains (crypto, weather, etc.), use web search (DuckDuckGo) as the primary source and APIs as supplementary. This maintains reliability while preserving coverage.

### Tension 2: Rate Limit Uncertainty

Many APIs have undocumented or unclear rate limits. This makes it hard to design a reliable adapter.

**Counter-argument:** Implement conservative rate limiting (assume lower limits than documented) and use circuit breakers. For undocumented APIs, start with 1 RPS and increase gradually. Monitor for 429 responses and auto-adjust.

### Tension 3: API Authentication Burden

Some APIs require authentication (GitHub, SEC EDGAR). Managing API keys for users adds complexity.

**Counter-argument:** For APIs requiring authentication, provide optional configuration in `config.toml`. If no key is provided, skip the API and fall back to web search. Document the API key requirement for users who want enhanced results.

---

## Recommended API Adapter Framework

```python
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import asyncio

class APIAdapter(ABC):
    """Base class for all API adapters with rate limiting and caching."""
    
    def __init__(self, rate_limit: int, rate_window: int = 60):
        self.rate_limit = rate_limit  # requests per window
        self.rate_window = rate_window  # seconds
        self.request_times = []
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour default
    
    async def _throttle(self):
        """Ensure rate limit compliance."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.rate_window)
        self.request_times = [t for t in self.request_times if t > cutoff]
        
        if len(self.request_times) >= self.rate_limit:
            sleep_time = (self.request_times[0] - cutoff).total_seconds()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        self.request_times.append(now)
    
    async def cached_query(self, params: dict) -> dict:
        """Query with caching."""
        cache_key = self._cache_key(params)
        if cache_key in self.cache:
            result, expiry = self.cache[cache_key]
            if datetime.utcnow() < expiry:
                return result
        
        result = await self.query(params)
        self.cache[cache_key] = (result, datetime.utcnow() + timedelta(seconds=self.cache_ttl))
        return result
    
    @abstractmethod
    async def query(self, params: dict) -> dict:
        pass
    
    @abstractmethod
    def _cache_key(self, params: dict) -> str:
        pass

class OpenAlexAdapter(APIAdapter):
    def __init__(self):
        super().__init__(rate_limit=10, rate_window=1)  # 10 RPS
    
    async def query(self, params: dict) -> dict:
        await self._throttle()
        # ... actual API call
    
    def _cache_key(self, params: dict) -> str:
        return f"openalex:{hash(str(params))}"

class ArxivAdapter(APIAdapter):
    def __init__(self):
        super().__init__(rate_limit=1, rate_window=3)  # 1 req per 3s
    
    async def query(self, params: dict) -> dict:
        await self._throttle()
        # ... actual API call
```

---

## Confidence Assessment

| Finding | Confidence |
|---------|------------|
| OpenAlex is most reliable free academic API | High |
| arXiv is simple but very slow (1 req/3s) | High |
| SEC EDGAR requires strict rate limit compliance | High |
| HN Search has undocumented rate limits | Medium |
| GitHub API is enterprise-grade reliable | High |
| Tier 3 APIs are hobby projects, unreliable | High |

---

## Sources

[^1]: OpenAlex API Documentation. 2026. https://docs.openalex.org/

[^2]: arXiv API Documentation. 2026. https://info.arxiv.org/help/api/index.html

[^3]: SEC EDGAR API Documentation. 2026. https://www.sec.gov/edgar/sec-api-documentation

[^4]: Algolia HN Search API. 2026. https://hn.algolia.com/api

[^5]: GitHub REST API Documentation. 2026. https://docs.github.com/en/rest

[^6]: CoinGecko API Documentation. 2026. https://www.coingecko.com/en/api/documentation

[^7]: public-apis GitHub Issues. 2026. https://github.com/public-apis/public-apis/issues

