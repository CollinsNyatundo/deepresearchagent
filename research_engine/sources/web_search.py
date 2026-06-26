"""Multi-provider async web search — DuckDuckGo + Tavily + Brave with aggregation.

Providers run concurrently via AggregatedSearchProvider, results are deduplicated
by URL and merged. DDG is rate-limit-hardened with reflective retry.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Protocol, runtime_checkable

from research_engine.config import SearchConfig
from research_engine.models import SearchResult

logger = logging.getLogger(__name__)


@runtime_checkable
class SearchProvider(Protocol):
    """Interface for async web search providers."""

    async def search(self, query: str, max_results: int = 10, **kwargs) -> list[SearchResult]: ...


# ─── DuckDuckGo (free, no API key, rate-limit hardened) ──────────────

class DuckDuckGoSearch:
    """Free web search via duckduckgo-search library.

    Uses sync DDGS wrapped in asyncio.to_thread() for reliability.
    Handles RatelimitException with retry + backoff.
    """

    _last_search_time: float = 0.0

    async def search(self, query: str, max_results: int = 10, **kwargs) -> list[SearchResult]:
        """Search DuckDuckGo with rate-limit hardening."""
        # ddgs v9+ renamed DuckDuckGoSearchException -> DDGSException.
        # duckduckgo_search package has been uninstalled — ddgs is the sole provider.
        from ddgs.exceptions import DDGSException, RatelimitException, TimeoutException

        # Throttle: at least 1s between consecutive DDG searches
        now = asyncio.get_event_loop().time()
        elapsed = now - DuckDuckGoSearch._last_search_time
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)

        try:
            results = await asyncio.to_thread(
                self._sync_search, query, max_results
            )
            DuckDuckGoSearch._last_search_time = asyncio.get_event_loop().time()
            return results

        except RatelimitException:
            logger.warning("DDG rate limited, waiting 3s and retrying once...")
            await asyncio.sleep(3)
            try:
                results = await asyncio.to_thread(
                    self._sync_search, query, max_results
                )
                DuckDuckGoSearch._last_search_time = asyncio.get_event_loop().time()
                return results
            except Exception as retry_err:
                logger.error(f"DDG retry also failed: {retry_err}")
                return []

        except TimeoutException as e:
            logger.error(f"DDG search timed out: {e}")
            return []

        except DDGSException as e:
            logger.error(f"DDG search error: {e}")
            return []

        except Exception as e:
            logger.error(f"DDG search unexpected error: {type(e).__name__}: {e}")
            return []

    def _sync_search(self, query: str, max_results: int) -> list[SearchResult]:
        """Synchronous DDG search — runs in thread pool via asyncio.to_thread()."""
        from ddgs import DDGS  # ddgs v9 — duckduckgo_search package uninstalled

        ddgs_client = DDGS(timeout=20)
        raw = ddgs_client.text(query, max_results=max_results, backend="auto")
        results = [
            SearchResult(
                url=r.get("href", ""),
                title=r.get("title", ""),
                snippet=r.get("body", ""),
            )
            for r in (raw or [])
            if r.get("href")
        ]
        logger.info(f"DDG returned {len(results)} results for: {query}")
        return results


# ─── Tavily (higher quality, requires API key) ──────────────────────

class TavilySearch:
    """Tavily search API — better quality results, requires TAVILY_API_KEY."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY", "")

    async def search(self, query: str, max_results: int = 10, **kwargs) -> list[SearchResult]:
        """Search via Tavily API."""
        if not self.api_key:
            logger.debug("TAVILY_API_KEY not set, skipping Tavily search")
            return []

        upgrade_context = kwargs.get("upgrade_context", False)
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results if not upgrade_context else max(max_results, 8),
            "search_depth": "advanced",
        }
        if upgrade_context:
            payload["include_raw_content"] = True

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            results = [
                SearchResult(
                    url=r.get("url", ""),
                    title=r.get("title", ""),
                    snippet=r.get("content", "")[:500],
                    score=r.get("score", 0.0),
                )
                for r in data.get("results", [])
                if r.get("url")
            ]
            logger.info(f"Tavily returned {len(results)} results for: {query}")
            return results
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []


# ─── Brave Search (good balance, requires API key) ──────────────────

class BraveSearchProvider:
    """Brave Search API — solid results, requires BRAVE_SEARCH_API_KEY."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("BRAVE_SEARCH_API_KEY", "")

    async def search(self, query: str, max_results: int = 10, **kwargs) -> list[SearchResult]:
        """Search via Brave Search API."""
        if not self.api_key:
            logger.debug("BRAVE_SEARCH_API_KEY not set, skipping Brave search")
            return []

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query, "count": max_results},
                    headers={
                        "X-Subscription-Token": self.api_key,
                        "Accept": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            results = [
                SearchResult(
                    url=r.get("url", ""),
                    title=r.get("title", ""),
                    snippet=r.get("description", "")[:500],
                )
                for r in data.get("web", {}).get("results", [])
                if r.get("url")
            ]
            logger.info(f"Brave returned {len(results)} results for: {query}")
            return results
        except Exception as e:
            logger.error(f"Brave search failed: {e}")
            return []


# ─── Exa Search (neural / semantic, requires EXA_API_KEY) ───────────

class ExaSearch:
    """Exa search API — neural/semantic search, requires EXA_API_KEY."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("EXA_API_KEY", "")

    async def search(self, query: str, max_results: int = 10, **kwargs) -> list[SearchResult]:
        """Search via Exa API."""
        if not self.api_key:
            logger.debug("EXA_API_KEY not set, skipping Exa search")
            return []

        upgrade_context = kwargs.get("upgrade_context", False)
        try:
            import httpx

            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "x-api-key": self.api_key,
            }
            payload = {
                "query": query,
                "use_autoprompt": True,
                "num_results": max_results,
            }
            if not upgrade_context:
                payload["highlights"] = {"num_sentences": 3}

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.exa.ai/search",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

            results = []
            for r in data.get("results", []):
                highlights_list = r.get("highlights", [])
                if highlights_list and isinstance(highlights_list, list):
                    snippet = " ".join(highlights_list)
                else:
                    snippet = r.get("text", "") or r.get("snippet", "")

                results.append(
                    SearchResult(
                        url=r.get("url", ""),
                        title=r.get("title", ""),
                        snippet=snippet[:500],
                        score=r.get("score", 0.0),
                    )
                )
            logger.info(f"Exa returned {len(results)} results for: {query}")
            return results
        except Exception as e:
            logger.error(f"Exa search failed: {e}")
            return []


# ─── Parallel AI Search (token-dense, requires PARALLEL_API_KEY) ───

class ParallelAISearch:
    """Parallel AI search API — token-dense search, requires PARALLEL_API_KEY."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("PARALLEL_API_KEY", "")

    async def search(self, query: str, max_results: int = 10, **kwargs) -> list[SearchResult]:
        """Search via Parallel AI API."""
        if not self.api_key:
            logger.debug("PARALLEL_API_KEY not set, skipping Parallel AI search")
            return []

        try:
            import httpx

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "query": query,
                "limit": max_results,
            }

            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    "https://api.parallel.ai/v1/search",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

            results = []
            for r in data.get("results", []):
                results.append(
                    SearchResult(
                        url=r.get("url", ""),
                        title=r.get("title", ""),
                        snippet=(r.get("excerpt", "") or r.get("snippet", ""))[:500],
                        score=r.get("score", 0.0),
                    )
                )
            logger.info(f"Parallel AI returned {len(results)} results for: {query}")
            return results
        except Exception as e:
            logger.error(f"Parallel AI search failed: {e}")
            return []


# ─── Aggregated Multi-Provider Search ────────────────────────────────

class AggregatedSearchProvider:
    """Runs multiple search providers concurrently, merges + deduplicates.

    This is the default provider ("all") — it fires DDG, Tavily, and Brave
    simultaneously, deduplicates by normalized URL, and returns a merged result set.
    If any provider fails, the others continue. At least one must return results.
    """

    def __init__(self, providers: list[SearchProvider]):
        self.providers = providers

    async def search(self, query: str, max_results: int = 10, **kwargs) -> list[SearchResult]:
        """Run all providers concurrently, merge and deduplicate results."""
        if not self.providers:
            logger.error("AggregatedSearchProvider has no providers!")
            return []

        tasks = [p.search(query, max_results, **kwargs) for p in self.providers]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        merged: list[SearchResult] = []
        seen_urls: set[str] = set()
        providers_succeeded = 0

        for i, result_set in enumerate(all_results):
            if isinstance(result_set, Exception):
                provider_name = type(self.providers[i]).__name__
                logger.warning(f"Search provider {provider_name} failed: {result_set}")
                continue

            providers_succeeded += 1
            for r in result_set:
                if not r.url:
                    continue
                normalized = r.url.rstrip("/").lower().split("?")[0]
                if normalized not in seen_urls:
                    seen_urls.add(normalized)
                    merged.append(r)

        logger.info(
            f"Aggregated search: {providers_succeeded}/{len(self.providers)} providers "
            f"returned {len(merged)} unique results for: {query}"
        )
        # Return generous results — the scraper will pick the best ones
        return merged[: max_results * 2]


# ─── Factory ─────────────────────────────────────────────────────────

def get_search_provider(
    provider: str | None = None,
    config: SearchConfig | None = None,
) -> SearchProvider:
    """Create a search provider instance by name.

    Args:
        provider: Provider name ('duckduckgo', 'tavily', 'brave', 'all').
                  Defaults to config.default_provider or 'all'.
        config: Search configuration with API keys.

    Returns:
        A SearchProvider implementation.
    """
    if config is None:
        config = SearchConfig()
    name = (provider or config.default_provider).lower().strip()

    match name:
        case "duckduckgo" | "ddg":
            return DuckDuckGoSearch()
        case "tavily":
            return TavilySearch(api_key=config.tavily_api_key)
        case "brave":
            return BraveSearchProvider(api_key=config.brave_api_key)
        case "exa":
            return ExaSearch(api_key=config.exa_api_key)
        case "parallel" | "parallel_ai":
            return ParallelAISearch(api_key=config.parallel_api_key)
        case "all" | "multi" | "aggregated":
            # Build list of all available providers
            providers: list[SearchProvider] = [DuckDuckGoSearch()]

            if config.tavily_api_key:
                providers.append(TavilySearch(api_key=config.tavily_api_key))
                logger.info("Tavily search enabled")
            else:
                logger.debug("Tavily API key not configured, skipping")

            if config.brave_api_key:
                providers.append(BraveSearchProvider(api_key=config.brave_api_key))
                logger.info("Brave search enabled")
            else:
                logger.debug("Brave API key not configured, skipping")

            if config.exa_api_key:
                providers.append(ExaSearch(api_key=config.exa_api_key))
                logger.info("Exa search enabled")
            else:
                logger.debug("Exa API key not configured, skipping")

            if config.parallel_api_key:
                providers.append(ParallelAISearch(api_key=config.parallel_api_key))
                logger.info("Parallel AI search enabled")
            else:
                logger.debug("Parallel AI API key not configured, skipping")

            logger.info(f"Aggregated search with {len(providers)} provider(s)")
            return AggregatedSearchProvider(providers)
        case _:
            logger.warning(f"Unknown search provider '{name}', defaulting to aggregated")
            return AggregatedSearchProvider([DuckDuckGoSearch()])
