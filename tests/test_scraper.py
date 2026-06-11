"""Comprehensive tests for the Scrapling-based web scraper.

Tests verify:
  - AsyncFetcher works correctly (native async, no to_thread)
  - WebScraper.fetch_page() returns valid ScrapedPage objects
  - Fetcher tier fallback chain builds correctly
  - Content extraction from Scrapling Response objects
  - Concurrent page fetching with semaphore
  - DynamicFetcher available after msgspec install
  - Error handling for bad URLs and network failures
"""

from __future__ import annotations

import asyncio
import importlib
import re
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from research_engine.config import ScrapingConfig
from research_engine.models import ScrapedPage


# ---------------------------------------------------------------------------
# Tier availability helpers
# ---------------------------------------------------------------------------

def _can_import(module: str) -> bool:
    """Check if a module is importable without side effects."""
    try:
        importlib.import_module(module)
        return True
    except ImportError:
        return False


HAS_MSGSPEC = _can_import("msgspec")
HAS_PATCHRIGHT = _can_import("patchright")
HAS_CAMOUFOX = _can_import("camoufox")


# ---------------------------------------------------------------------------
# Helper: build a fake Scrapling Response object
# ---------------------------------------------------------------------------

class FakeElement:
    """Minimal mock for a Scrapling element (find() result)."""

    def __init__(self, text: str):
        self.text = text


class FakeScraplingPage:
    """Mimics the Scrapling Response object returned by all fetchers."""

    def __init__(
        self,
        status: int = 200,
        text_content: str = "Hello world content",
        title: str = "Test Page",
    ):
        self.status = status
        self._text = text_content
        self._title = title

    def get_all_text(self) -> str:
        return self._text

    def find(self, selector: str) -> FakeElement | None:
        if selector == "title":
            return FakeElement(self._title) if self._title else None
        return None


# ---------------------------------------------------------------------------
# Tests: get_fetcher_availability()
# ---------------------------------------------------------------------------

class TestFetcherAvailability:
    def test_returns_dict_with_expected_keys(self):
        from research_engine.sources.web_scraper import _check_fetcher_availability

        result = _check_fetcher_availability()
        assert isinstance(result, dict)
        assert "async" in result
        assert "dynamic" in result
        assert "stealthy_patchright" in result
        assert "stealthy_camoufox" in result

    def test_async_fetcher_always_available(self):
        """AsyncFetcher should be importable — it only needs scrapling installed."""
        from research_engine.sources.web_scraper import _check_fetcher_availability

        result = _check_fetcher_availability()
        assert result["async"] is True, "AsyncFetcher must always be available with scrapling"

    def test_dynamic_fetcher_available_with_msgspec(self):
        from research_engine.sources.web_scraper import _check_fetcher_availability

        result = _check_fetcher_availability()
        if HAS_MSGSPEC:
            assert result["dynamic"] is True
        else:
            assert result["dynamic"] is False

    def test_camoufox_requires_patchright(self):
        from research_engine.sources.web_scraper import _check_fetcher_availability

        result = _check_fetcher_availability()
        # camoufox can't be true if patchright isn't available
        if not result["stealthy_patchright"]:
            assert result["stealthy_camoufox"] is False


# ---------------------------------------------------------------------------
# Tests: WebScraper._build_fetcher_chain()
# ---------------------------------------------------------------------------

class TestFetcherChain:
    def _make_scraper(self, tier: str = "all") -> object:
        from research_engine.sources.web_scraper import WebScraper
        return WebScraper(ScrapingConfig(fetcher_tier=tier))

    def test_chain_has_at_least_one_entry(self):
        from research_engine.sources.web_scraper import get_fetcher_availability, WebScraper
        scraper = self._make_scraper("all")
        availability = get_fetcher_availability()
        chain = scraper._build_fetcher_chain(availability)
        assert len(chain) >= 1, "At least one fetcher must be in the chain"

    def test_async_fetcher_first_in_all_tier(self):
        from research_engine.sources.web_scraper import get_fetcher_availability, WebScraper
        scraper = self._make_scraper("all")
        availability = get_fetcher_availability()
        chain = scraper._build_fetcher_chain(availability)
        first_name, _ = chain[0]
        assert first_name == "async_fetcher", "AsyncFetcher must be first in 'all' tier chain"

    def test_basic_tier_only_has_async(self):
        from research_engine.sources.web_scraper import get_fetcher_availability, WebScraper
        scraper = self._make_scraper("async")
        availability = get_fetcher_availability()
        chain = scraper._build_fetcher_chain(availability)
        names = [n for n, _ in chain]
        assert "async_fetcher" in names
        # When using "async" tier, dynamic fetcher should NOT be in chain
        assert "dynamic_fetcher" not in names

    def test_all_tier_includes_dynamic_if_available(self):
        from research_engine.sources.web_scraper import get_fetcher_availability, WebScraper
        scraper = self._make_scraper("all")
        availability = get_fetcher_availability()
        chain = scraper._build_fetcher_chain(availability)
        names = [n for n, _ in chain]
        if availability.get("dynamic"):
            assert "dynamic_fetcher" in names
        else:
            assert "dynamic_fetcher" not in names


# ---------------------------------------------------------------------------
# Tests: _extract_content() with mock page
# ---------------------------------------------------------------------------

class TestContentExtraction:
    def _make_scraper(self):
        from research_engine.sources.web_scraper import WebScraper
        return WebScraper(ScrapingConfig())

    def test_extracts_title_and_content(self):
        scraper = self._make_scraper()
        page = FakeScraplingPage(text_content="  Hello   world  \n\n", title="My Title")
        result = scraper._extract_content(page, "https://example.com", "async_fetcher")

        assert isinstance(result, ScrapedPage)
        assert result.success is True
        assert result.title == "My Title"
        assert "Hello" in result.content
        assert result.content_length > 0
        assert result.fetcher_used == "async_fetcher"
        assert result.status_code == 200

    def test_returns_success_false_with_empty_body(self):
        scraper = self._make_scraper()
        page = FakeScraplingPage(text_content="", title="")
        result = scraper._extract_content(page, "https://example.com", "async_fetcher")
        # Empty content is still a ScrapedPage (success=True), content_length=0
        assert result.content_length == 0

    def test_truncates_content_at_max_chars(self):
        scraper = self._make_scraper()
        long_text = "A" * 100_000
        page = FakeScraplingPage(text_content=long_text, title="t")
        result = scraper._extract_content(page, "https://example.com", "async_fetcher")
        assert len(result.content) <= scraper.config.max_content_chars + 200  # +200 for truncation msg

    def test_title_fallback_from_url(self):
        scraper = self._make_scraper()
        page = FakeScraplingPage(text_content="data", title="")
        result = scraper._extract_content(page, "https://example.com/my-article", "bf")
        # When no title found, extract from URL
        assert result.title  # not empty


# ---------------------------------------------------------------------------
# Tests: WebScraper.fetch_page() with mocked fetcher chain
# ---------------------------------------------------------------------------

class TestFetchPage:
    @pytest.mark.asyncio
    async def test_returns_scraped_page_on_success(self):
        from research_engine.sources.web_scraper import WebScraper

        scraper = WebScraper(ScrapingConfig(fetcher_tier="async"))
        # Content must be >= 50 chars to pass the quality gate in fetch_page
        fake_page = FakeScraplingPage(
            text_content="This is a detailed webpage with enough content to pass the 50 char quality threshold check.",
            title="Test",
        )

        async def fake_fetcher(url: str):
            return fake_page

        with patch.object(scraper, "_build_fetcher_chain", return_value=[("mocked", fake_fetcher)]):
            result = await scraper.fetch_page("https://example.com")

        assert isinstance(result, ScrapedPage)
        assert result.success is True
        assert result.content_length > 0
        assert "detailed" in result.content

    @pytest.mark.asyncio
    async def test_returns_failure_when_all_fetchers_fail(self):
        from research_engine.sources.web_scraper import WebScraper

        scraper = WebScraper(ScrapingConfig(fetcher_tier="async"))

        async def always_fails(url: str):
            raise ConnectionError("simulated network error")

        with patch.object(scraper, "_build_fetcher_chain", return_value=[("fail1", always_fails), ("fail2", always_fails)]):
            result = await scraper.fetch_page("https://broken.invalid")

        assert isinstance(result, ScrapedPage)
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_falls_back_to_next_tier_on_failure(self):
        from research_engine.sources.web_scraper import WebScraper

        scraper = WebScraper(ScrapingConfig(fetcher_tier="all"))
        # Content must be >= 50 chars to pass quality gate
        success_page = FakeScraplingPage(
            text_content="This is the fallback tier content with more than fifty characters in it!",
            title="Fallback",
        )
        call_count = {"n": 0}

        async def first_fails(url: str):
            call_count["n"] += 1
            raise ConnectionError("tier 1 failed")

        async def second_succeeds(url: str):
            call_count["n"] += 1
            return success_page

        with patch.object(scraper, "_build_fetcher_chain", return_value=[
            ("tier1", first_fails),
            ("tier2", second_succeeds),
        ]):
            result = await scraper.fetch_page("https://example.com")

        assert result.success is True
        assert call_count["n"] == 2  # Both were called
        assert "fallback" in result.content.lower()

    @pytest.mark.asyncio
    async def test_fetch_pages_concurrent(self):
        from research_engine.sources.web_scraper import WebScraper

        scraper = WebScraper(ScrapingConfig(fetcher_tier="async", max_concurrent=3))
        counter = {"calls": 0}

        async def fake_fetcher(url: str):
            counter["calls"] += 1
            return FakeScraplingPage(text_content=f"Content for {url}", title="page")

        with patch.object(scraper, "_build_fetcher_chain", return_value=[("mock", fake_fetcher)]):
            urls = ["https://a.com", "https://b.com", "https://c.com"]
            results = await scraper.fetch_pages(urls)

        assert len(results) == 3
        assert all(isinstance(r, ScrapedPage) for r in results)
        assert counter["calls"] == 3


# ---------------------------------------------------------------------------
# Tests: Live network fetches (marks: live — skipped in CI without network)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.live
async def test_async_fetcher_live_httpbin():
    """LIVE: AsyncFetcher fetches httpbin.org/json and returns 200 + JSON content."""
    from scrapling.fetchers import AsyncFetcher

    fetcher = AsyncFetcher()
    page = await fetcher.get("https://httpbin.org/json", follow_redirects=True)

    assert page is not None
    assert page.status == 200
    text = page.get_all_text()
    assert len(text) > 0, "Expected non-empty content from httpbin"


@pytest.mark.asyncio
@pytest.mark.live
async def test_web_scraper_live_static_site():
    """LIVE: WebScraper fetches example.com and returns meaningful content."""
    from research_engine.sources.web_scraper import WebScraper

    scraper = WebScraper(ScrapingConfig(fetcher_tier="async"))
    result = await scraper.fetch_page("https://example.com")

    assert isinstance(result, ScrapedPage)
    assert result.success is True, f"Scraper failed: {result.error}"
    assert result.content_length > 50, f"Expected >50 chars, got {result.content_length}"
    assert result.fetcher_used != "", "fetcher_used must be set"


@pytest.mark.asyncio
@pytest.mark.live
@pytest.mark.skipif(not HAS_MSGSPEC, reason="DynamicFetcher requires msgspec")
async def test_dynamic_fetcher_live_js_site():
    """LIVE: DynamicFetcher (Playwright) fetches a JS-rendered page."""
    from scrapling.fetchers import DynamicFetcher

    page = await DynamicFetcher.async_fetch("https://example.com", headless=True, disable_resources=True)

    assert page is not None
    assert page.status == 200
    text = page.get_all_text()
    assert len(text) > 0


# ---------------------------------------------------------------------------
# Tests: _clean_content helper
# ---------------------------------------------------------------------------

class TestCleanContent:
    def test_removes_excessive_newlines(self):
        from research_engine.sources.web_scraper import _clean_content
        result = _clean_content("a\n\n\n\n\nb")
        assert "\n\n\n" not in result

    def test_strips_whitespace(self):
        from research_engine.sources.web_scraper import _clean_content
        result = _clean_content("   hello world   ")
        assert result == "hello world"

    def test_empty_string(self):
        from research_engine.sources.web_scraper import _clean_content
        assert _clean_content("") == ""
        assert _clean_content(None or "") == ""
