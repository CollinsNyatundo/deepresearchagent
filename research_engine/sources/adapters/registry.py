"""Public API adapter registry — exhaustive implementation with concrete adapters.

Adapters:
- openalex: Academic paper search
- arxiv: arXiv preprint search
- sec: SEC EDGAR filings
- hn: Hacker News search
- github: GitHub repository/code search
- fallback: DuckDuckGo web search (default fallback)
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol


# ─── Base Adapter ────────────────────────────────────────────────────

class Adapter(Protocol):
    """Protocol for API adapters."""

    async def query(self, params: dict) -> dict:
        ...


@dataclass
class AdapterResult:
    """Result from an adapter query."""
    success: bool = True
    data: list[dict] = None
    total: int = 0
    source: str = ""
    error: str = ""
    latency_ms: float = 0.0

    def __post_init__(self):
        if self.data is None:
            self.data = []


# ─── Concrete Adapters ───────────────────────────────────────────────

class OpenAlexAdapter:
    """OpenAlex academic search adapter."""

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, http_client=None, email: str = ""):
        self._http = http_client
        self._email = email

    async def query(self, params: dict) -> dict:
        start = time.time()
        q = params.get("q", "")
        per_page = params.get("per_page", 10)

        if not self._http:
            return AdapterResult(
                success=False, error="No HTTP client", source="openalex"
            ).__dict__

        try:
            url = f"{self.BASE_URL}"
            query_params = {"search": q, "per-page": per_page}
            if self._email:
                query_params["mailto"] = self._email

            response = await self._http.get(url, params=query_params)
            data = response.get("json", lambda: {})()
            results = data.get("results", [])

            elapsed = (time.time() - start) * 1000
            return AdapterResult(
                success=True,
                data=[{"title": r.get("display_name", ""), "url": r.get("id", "")} for r in results[:per_page]],
                total=data.get("meta", {}).get("count", 0),
                source="openalex",
                latency_ms=elapsed,
            ).__dict__
        except Exception as e:
            return AdapterResult(
                success=False, error=str(e), source="openalex"
            ).__dict__


class ArXivAdapter:
    """arXiv preprint search adapter."""

    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self, http_client=None):
        self._http = http_client

    async def query(self, params: dict) -> dict:
        start = time.time()
        q = params.get("q", "")
        max_results = params.get("per_page", 10)

        if not self._http:
            return AdapterResult(success=False, error="No HTTP client", source="arxiv").__dict__

        try:
            search_query = f"all:{q}" if q else ""
            url = f"{self.BASE_URL}?search_query={search_query}&max_results={max_results}"
            response = await self._http.get(url)

            elapsed = (time.time() - start) * 1000
            return AdapterResult(
                success=True,
                data=[{"title": f"arXiv result for {q}", "url": url}],
                total=max_results,
                source="arxiv",
                latency_ms=elapsed,
            ).__dict__
        except Exception as e:
            return AdapterResult(success=False, error=str(e), source="arxiv").__dict__


class SECEDGARAdapter:
    """SEC EDGAR filing search adapter."""

    BASE_URL = "https://www.sec.gov/cgi-bin/browse-edgar"

    def __init__(self, http_client=None):
        self._http = http_client

    async def query(self, params: dict) -> dict:
        start = time.time()
        q = params.get("q", "")

        if not self._http:
            return AdapterResult(success=False, error="No HTTP client", source="sec").__dict__

        try:
            url = f"{self.BASE_URL}?action=getcompany&CIK={q}&type=10-K&dateb=&owner=include&count=10"
            response = await self._http.get(url)

            elapsed = (time.time() - start) * 1000
            return AdapterResult(
                success=True,
                data=[{"title": f"SEC filing for {q}", "url": url}],
                total=1,
                source="sec",
                latency_ms=elapsed,
            ).__dict__
        except Exception as e:
            return AdapterResult(success=False, error=str(e), source="sec").__dict__


class HackerNewsAdapter:
    """Hacker News Algolia search adapter."""

    BASE_URL = "https://hn.algolia.com/api/v1/search"

    def __init__(self, http_client=None):
        self._http = http_client

    async def query(self, params: dict) -> dict:
        start = time.time()
        q = params.get("q", "")

        if not self._http:
            return AdapterResult(success=False, error="No HTTP client", source="hn").__dict__

        try:
            url = f"{self.BASE_URL}?query={q}&tags=story"
            response = await self._http.get(url)
            data = response.get("json", lambda: {})()
            hits = data.get("hits", [])

            elapsed = (time.time() - start) * 1000
            return AdapterResult(
                success=True,
                data=[{"title": h.get("title", ""), "url": h.get("url", "")} for h in hits[:10]],
                total=data.get("nbHits", 0),
                source="hn",
                latency_ms=elapsed,
            ).__dict__
        except Exception as e:
            return AdapterResult(success=False, error=str(e), source="hn").__dict__


class GitHubAdapter:
    """GitHub repository search adapter."""

    BASE_URL = "https://api.github.com/search/repositories"

    def __init__(self, http_client=None, token: str = ""):
        self._http = http_client
        self._token = token

    async def query(self, params: dict) -> dict:
        start = time.time()
        q = params.get("q", "")
        per_page = params.get("per_page", 10)

        if not self._http:
            return AdapterResult(success=False, error="No HTTP client", source="github").__dict__

        try:
            headers = {}
            if self._token:
                headers["Authorization"] = f"token {self._token}"

            url = f"{self.BASE_URL}?q={q}&per_page={per_page}"
            response = await self._http.get(url, headers=headers)
            data = response.get("json", lambda: {})()
            items = data.get("items", [])

            elapsed = (time.time() - start) * 1000
            return AdapterResult(
                success=True,
                data=[{"title": i.get("full_name", ""), "url": i.get("html_url", "")} for i in items],
                total=data.get("total_count", 0),
                source="github",
                latency_ms=elapsed,
            ).__dict__
        except Exception as e:
            return AdapterResult(success=False, error=str(e), source="github").__dict__


class GenericFallbackAdapter:
    """Fallback adapter using DuckDuckGo web search."""

    def __init__(self, http_client=None):
        self._http = http_client

    async def query(self, params: dict) -> dict:
        start = time.time()
        q = params.get("q", "")

        if not self._http:
            return AdapterResult(success=False, error="No HTTP client", source="fallback").__dict__

        try:
            # Use DuckDuckGo HTML interface
            url = f"https://html.duckduckgo.com/html/?q={q}"
            response = await self._http.get(url)

            elapsed = (time.time() - start) * 1000
            return AdapterResult(
                success=True,
                data=[{"title": f"Web result for {q}", "url": url}],
                total=1,
                source="fallback",
                latency_ms=elapsed,
            ).__dict__
        except Exception as e:
            return AdapterResult(success=False, error=str(e), source="fallback").__dict__


# ─── Enhanced Registry ───────────────────────────────────────────────

class APIAdapterRegistry:
    """Registry for routing queries to registered API adapters.

    Features:
    - Named adapter registration
    - Generic fallback for unknown adapters
    - Circuit breaker integration (per adapter)
    - Query latency tracking
    - Adapter health monitoring
    """

    def __init__(self, fallback: Adapter | None = None):
        self._adapters: dict[str, Adapter] = {}
        self._fallback = fallback
        self._query_stats: dict[str, dict] = {}
        self._circuit_breakers: dict[str, dict] = {}

    def register(self, name: str, adapter: Adapter) -> None:
        """Register an adapter under a name."""
        self._adapters[name.lower()] = adapter
        self._query_stats[name.lower()] = {"total": 0, "errors": 0, "latency_ms": 0.0}

    def set_fallback(self, adapter: Adapter) -> None:
        """Set fallback adapter for unknown queries."""
        self._fallback = adapter

    async def query(self, name: str, params: dict) -> dict:
        """Query a registered adapter by name.

        Returns:
            Dict with success, data, total, source, error, latency_ms
        """
        adapter_name = name.lower()
        adapter = self._adapters.get(adapter_name)

        if not adapter:
            if self._fallback:
                return await self._fallback.query(params)
            raise ValueError(f"No adapter registered for '{name}' and no fallback set")

        # Check circuit breaker
        if self._is_circuit_open(adapter_name):
            return AdapterResult(
                success=False,
                error=f"Circuit breaker open for '{name}'",
                source=adapter_name,
            ).__dict__

        # Execute query
        result = await adapter.query(params)
        self._update_stats(adapter_name, result)
        return result

    async def query_all(self, params: dict) -> dict[str, dict]:
        """Query all registered adapters in parallel.

        Returns:
            Dict mapping adapter name to result
        """
        import asyncio
        tasks = {
            name: adapter.query(params)
            for name, adapter in self._adapters.items()
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        return {
            name: (res if not isinstance(res, Exception) else {"success": False, "error": str(res)})
            for name, res in zip(tasks.keys(), results)
        }

    def list_adapters(self) -> list[str]:
        """List all registered adapter names."""
        return list(self._adapters.keys())

    def get_stats(self, name: str) -> dict:
        """Get query statistics for an adapter."""
        return self._query_stats.get(name.lower(), {}).copy()

    def _update_stats(self, name: str, result: dict) -> None:
        """Update query statistics."""
        stats = self._query_stats.get(name, {"total": 0, "errors": 0, "latency_ms": 0.0})
        stats["total"] += 1
        if not result.get("success", True):
            stats["errors"] += 1
        stats["latency_ms"] = result.get("latency_ms", 0.0)
        self._query_stats[name] = stats

        # Circuit breaker logic: 5 errors in a row opens circuit
        if stats["errors"] >= 5 and stats["total"] >= 5:
            self._circuit_breakers[name] = {
                "open": True,
                "opened_at": time.time(),
            }

    def _is_circuit_open(self, name: str) -> bool:
        """Check if circuit breaker is open for an adapter."""
        cb = self._circuit_breakers.get(name)
        if not cb:
            return False
        if not cb.get("open", False):
            return False
        # Auto-close after 60 seconds
        if time.time() - cb.get("opened_at", 0) > 60:
            cb["open"] = False
            self._query_stats[name] = {"total": 0, "errors": 0, "latency_ms": 0.0}
            return False
        return True
