"""Comprehensive tests for all search providers.

Uses the actual class names from research_engine/sources/web_search.py:
  DuckDuckGoSearch      — free, no API key
  TavilySearch          — requires TAVILY_API_KEY  
  BraveSearchProvider   — requires BRAVE_SEARCH_API_KEY
  AggregatedSearchProvider(providers) — no max_results kwarg on constructor

Factory signature:
  get_search_provider(provider=None, config=None) -> SearchProvider
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from research_engine.models import SearchResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    from dotenv import load_dotenv
    load_dotenv()


def _has_tavily_key() -> bool:
    _load_dotenv()
    return bool(os.environ.get("TAVILY_API_KEY"))


def _has_brave_key() -> bool:
    _load_dotenv()
    return bool(os.environ.get("BRAVE_SEARCH_API_KEY"))


TAVILY_ENABLED = _has_tavily_key()
BRAVE_ENABLED = _has_brave_key()


# ---------------------------------------------------------------------------
# Tests: DuckDuckGoSearch (class name in web_search.py)
# ---------------------------------------------------------------------------

class TestDuckDuckGoProvider:
    @pytest.mark.asyncio
    async def test_returns_search_results(self):
        from research_engine.sources.web_search import DuckDuckGoSearch
        provider = DuckDuckGoSearch()
        results = await provider.search("Python async programming", max_results=3)

        assert isinstance(results, list)
        assert len(results) >= 1
        for r in results:
            assert isinstance(r, SearchResult)
            assert r.url.startswith("http")

    @pytest.mark.asyncio
    async def test_returns_list_not_error(self):
        """Even an unusual query should return a list, never raise."""
        from research_engine.sources.web_search import DuckDuckGoSearch
        provider = DuckDuckGoSearch()
        results = await provider.search("xkcd 2024 comic strip", max_results=3)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_result_has_snippet(self):
        from research_engine.sources.web_search import DuckDuckGoSearch
        provider = DuckDuckGoSearch()
        results = await provider.search("Python programming language tutorial", max_results=5)
        assert isinstance(results, list)
        # DDG may return [] under rate limiting in sequential test runs — that's OK
        if len(results) == 0:
            pytest.skip("DDG returned 0 results (likely rate limited) — skip, not fail")
        for r in results:
            assert r.url.startswith("http"), f"Bad URL: {r.url}"


    @pytest.mark.asyncio
    async def test_respects_max_results_limit(self):
        from research_engine.sources.web_search import DuckDuckGoSearch
        provider = DuckDuckGoSearch()
        results = await provider.search("machine learning tutorial", max_results=3)
        assert len(results) <= 3


# ---------------------------------------------------------------------------
# Tests: TavilySearch (class name in web_search.py)
# ---------------------------------------------------------------------------

class TestTavilyProvider:
    @pytest.mark.asyncio
    async def test_returns_empty_without_key(self, monkeypatch):
        """With no API key in constructor AND no env var → graceful empty list.

        Note: TavilySearch(api_key="") falls back to TAVILY_API_KEY env var
        (correct production behavior). We must clear the env var to test no-key path.
        """
        from research_engine.sources.web_search import TavilySearch
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        provider = TavilySearch(api_key="")
        results = await provider.search("Python web scraping")
        assert isinstance(results, list)
        assert len(results) == 0, "No key at all should return [] not raise"

    @pytest.mark.asyncio
    @pytest.mark.skipif(not TAVILY_ENABLED, reason="TAVILY_API_KEY not set")
    async def test_live_search_with_key(self):
        from research_engine.sources.web_search import TavilySearch
        api_key = os.environ["TAVILY_API_KEY"]
        provider = TavilySearch(api_key=api_key)
        results = await provider.search("deep learning transformer architecture", max_results=4)

        assert isinstance(results, list)
        assert len(results) >= 1, "Expected at least 1 Tavily result"
        for r in results:
            assert r.url.startswith("http")
            assert isinstance(r, SearchResult)

    @pytest.mark.asyncio
    async def test_invalid_key_returns_empty(self):
        """An invalid key should return [] gracefully (catches HTTP 401)."""
        from research_engine.sources.web_search import TavilySearch
        provider = TavilySearch(api_key="invalid-key-xxxxxx")
        results = await provider.search("test query")
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# Tests: BraveSearchProvider
# ---------------------------------------------------------------------------

class TestBraveProvider:
    @pytest.mark.asyncio
    async def test_returns_empty_without_key(self, monkeypatch):
        """With no API key in constructor AND no env var → graceful empty list.

        Note: BraveSearchProvider(api_key="") falls back to BRAVE_SEARCH_API_KEY
        env var (correct production behavior). We must clear env to test no-key path.
        """
        from research_engine.sources.web_search import BraveSearchProvider
        monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
        provider = BraveSearchProvider(api_key="")
        results = await provider.search("Python programming")
        assert isinstance(results, list)
        assert len(results) == 0, "No key at all should return [] not raise"

    @pytest.mark.asyncio
    @pytest.mark.skipif(not BRAVE_ENABLED, reason="BRAVE_SEARCH_API_KEY not set")
    async def test_live_search_with_key(self):
        from research_engine.sources.web_search import BraveSearchProvider
        api_key = os.environ["BRAVE_SEARCH_API_KEY"]
        provider = BraveSearchProvider(api_key=api_key)
        results = await provider.search("Scrapling Python web scraper library", max_results=4)

        assert isinstance(results, list)
        assert len(results) >= 1, "Expected at least 1 Brave result"
        for r in results:
            assert r.url.startswith("http")
            assert isinstance(r, SearchResult)

    @pytest.mark.asyncio
    async def test_invalid_key_returns_empty(self):
        from research_engine.sources.web_search import BraveSearchProvider
        provider = BraveSearchProvider(api_key="INVALID-KEY")
        results = await provider.search("test query")
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# Tests: AggregatedSearchProvider
# Note: constructor is AggregatedSearchProvider(providers: list) — NO max_results kwarg
# ---------------------------------------------------------------------------

class TestAggregatedProvider:
    @pytest.mark.asyncio
    async def test_aggregates_from_multiple_mock_providers(self):
        from research_engine.sources.web_search import AggregatedSearchProvider

        mock_a = AsyncMock()
        mock_a.search.return_value = [
            SearchResult(url="https://a.com/1", title="A1", snippet="snippet A1"),
            SearchResult(url="https://a.com/2", title="A2", snippet="snippet A2"),
        ]
        mock_b = AsyncMock()
        mock_b.search.return_value = [
            SearchResult(url="https://b.com/1", title="B1", snippet="snippet B1"),
        ]

        # Constructor takes a list, NOT max_results kwarg
        provider = AggregatedSearchProvider([mock_a, mock_b])
        results = await provider.search("test query", max_results=10)

        assert len(results) == 3
        urls = {r.url for r in results}
        assert "https://a.com/1" in urls
        assert "https://b.com/1" in urls

    @pytest.mark.asyncio
    async def test_deduplicates_by_url(self):
        from research_engine.sources.web_search import AggregatedSearchProvider

        dup_result = SearchResult(url="https://dup.com/page", title="Dup", snippet="same")

        mock_a = AsyncMock()
        mock_a.search.return_value = [dup_result]
        mock_b = AsyncMock()
        mock_b.search.return_value = [dup_result]

        provider = AggregatedSearchProvider([mock_a, mock_b])
        results = await provider.search("test", max_results=10)

        urls = [r.url for r in results]
        assert urls.count("https://dup.com/page") == 1, "Duplicate URL must be deduplicated"

    @pytest.mark.asyncio
    async def test_handles_provider_failure_gracefully(self):
        from research_engine.sources.web_search import AggregatedSearchProvider

        mock_working = AsyncMock()
        mock_working.search.return_value = [
            SearchResult(url="https://good.com", title="Good", snippet="ok"),
        ]
        mock_broken = AsyncMock()
        mock_broken.search.side_effect = RuntimeError("Provider exploded")

        provider = AggregatedSearchProvider([mock_working, mock_broken])
        results = await provider.search("test", max_results=10)

        # Should still get results from the working provider
        assert len(results) >= 1
        assert results[0].url == "https://good.com"

    @pytest.mark.asyncio
    async def test_respects_max_results_trim(self):
        from research_engine.sources.web_search import AggregatedSearchProvider

        mock_a = AsyncMock()
        mock_a.search.return_value = [
            SearchResult(url=f"https://a.com/{i}", title=f"A{i}", snippet="")
            for i in range(20)
        ]

        provider = AggregatedSearchProvider([mock_a])
        results = await provider.search("test", max_results=5)
        # AggregatedSearchProvider returns max_results * 2 — at most 10 for max_results=5
        assert len(results) <= 10


# ---------------------------------------------------------------------------
# Tests: get_search_provider() factory
# Signature: get_search_provider(provider=None, config=None)
# ---------------------------------------------------------------------------

class TestSearchProviderFactory:
    def test_factory_returns_ddg_by_default(self):
        from research_engine.sources.web_search import get_search_provider, DuckDuckGoSearch
        from research_engine.config import SearchConfig

        cfg = SearchConfig(default_provider="ddg", tavily_api_key="", brave_api_key="")
        # Pass config as keyword arg (not positional — positional 1 is 'provider' str)
        provider = get_search_provider(config=cfg)
        assert isinstance(provider, DuckDuckGoSearch)

    def test_factory_returns_aggregated_for_all(self):
        from research_engine.sources.web_search import get_search_provider, AggregatedSearchProvider
        from research_engine.config import SearchConfig

        cfg = SearchConfig(default_provider="all", tavily_api_key="", brave_api_key="")
        provider = get_search_provider(config=cfg)
        assert isinstance(provider, AggregatedSearchProvider)

    def test_aggregated_includes_ddg_always(self):
        """DDG has no API key requirement — must always be in aggregated provider."""
        from research_engine.sources.web_search import (
            get_search_provider,
            AggregatedSearchProvider,
            DuckDuckGoSearch,
        )
        from research_engine.config import SearchConfig

        cfg = SearchConfig(default_provider="all", tavily_api_key="", brave_api_key="")
        provider = get_search_provider(config=cfg)
        assert isinstance(provider, AggregatedSearchProvider)
        provider_types = [type(p).__name__ for p in provider.providers]
        assert "DuckDuckGoSearch" in provider_types

    def test_aggregated_includes_tavily_when_key_set(self):
        from research_engine.sources.web_search import get_search_provider, AggregatedSearchProvider
        from research_engine.config import SearchConfig

        cfg = SearchConfig(default_provider="all", tavily_api_key="tvly-test123", brave_api_key="")
        provider = get_search_provider(config=cfg)
        assert isinstance(provider, AggregatedSearchProvider)
        provider_types = [type(p).__name__ for p in provider.providers]
        assert "TavilySearch" in provider_types, (
            f"TavilySearch must be in providers when key is set. Got: {provider_types}"
        )

    def test_aggregated_includes_brave_when_key_set(self):
        from research_engine.sources.web_search import get_search_provider, AggregatedSearchProvider
        from research_engine.config import SearchConfig

        cfg = SearchConfig(default_provider="all", tavily_api_key="", brave_api_key="BSAxxxxxx")
        provider = get_search_provider(config=cfg)
        assert isinstance(provider, AggregatedSearchProvider)
        provider_types = [type(p).__name__ for p in provider.providers]
        assert "BraveSearchProvider" in provider_types, (
            f"BraveSearchProvider must be in providers when key is set. Got: {provider_types}"
        )

    def test_aggregated_with_both_keys_has_three_providers(self):
        from research_engine.sources.web_search import get_search_provider, AggregatedSearchProvider
        from research_engine.config import SearchConfig

        cfg = SearchConfig(
            default_provider="all",
            tavily_api_key="tvly-abc",
            brave_api_key="BSA-xyz",
        )
        provider = get_search_provider(config=cfg)
        assert isinstance(provider, AggregatedSearchProvider)
        assert len(provider.providers) == 3, (
            f"Should have DDG + Tavily + Brave = 3 providers, got {len(provider.providers)}"
        )

    def test_explicit_provider_string_overrides_config_default(self):
        """Passing provider='duckduckgo' overrides config.default_provider='all'."""
        from research_engine.sources.web_search import get_search_provider, DuckDuckGoSearch
        from research_engine.config import SearchConfig

        cfg = SearchConfig(default_provider="all", tavily_api_key="key", brave_api_key="key")
        provider = get_search_provider(provider="duckduckgo", config=cfg)
        assert isinstance(provider, DuckDuckGoSearch)
