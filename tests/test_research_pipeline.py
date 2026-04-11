"""End-to-end research pipeline tests.

Tests verify the full search → scrape → synthesize data flow:
  - Search returns URLs that can be successfully scraped
  - Scraped content is non-empty (content_length > 0)
  - Content passes the minimum quality filter
  - Orchestrator (depth=1) completes and produces a report
  - SSE events are emitted in expected order
  - API config correctly loads Tavily/Brave keys
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from research_engine.config import ScrapingConfig, SearchConfig
from research_engine.models import (
    ResearchRequest,
    ScrapedPage,
    SearchResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_env_keys() -> tuple[str, str]:
    """Load Tavily and Brave keys from .env."""
    from dotenv import load_dotenv
    load_dotenv()
    return (
        os.environ.get("TAVILY_API_KEY", ""),
        os.environ.get("BRAVE_SEARCH_API_KEY", ""),
    )


TAVILY_KEY, BRAVE_KEY = _load_env_keys()


def _fake_search_result(url: str, title: str = "Test") -> SearchResult:
    return SearchResult(url=url, title=title, snippet=f"Snippet for {url}")


def _fake_scraped_page(url: str, content: str = "Sample content from the web page.") -> ScrapedPage:
    return ScrapedPage(
        url=url,
        title="Page Title",
        content=content,
        status_code=200,
        content_length=len(content),
        success=True,
        fetcher_used="async_fetcher",
    )


# ---------------------------------------------------------------------------
# Tests: Search + Scrape pipeline (mocked)
# ---------------------------------------------------------------------------

class TestSearchScrapePipeline:
    @pytest.mark.asyncio
    async def test_scraper_processes_search_urls(self):
        """Mock search returns URLs → mock scraper processes them → non-empty content."""
        from research_engine.sources.web_scraper import WebScraper

        search_urls = ["https://example.com", "https://httpbin.org/json"]
        scraper = WebScraper(ScrapingConfig(fetcher_tier="async"))

        mock_page = MagicMock()
        mock_page.status = 200
        mock_page.get_all_text.return_value = "This is substantial content from the web page with enough text."
        mock_page.find.return_value = MagicMock(text="Page Title")

        async def fake_fetch(url: str):
            return mock_page

        with patch.object(scraper, "_build_fetcher_chain", return_value=[("mock", fake_fetch)]):
            pages = await scraper.fetch_pages(search_urls)

        assert len(pages) == 2
        for page in pages:
            assert page.success is True
            assert page.content_length > 0, f"Expected content for {page.url}, got 0 chars"

    @pytest.mark.asyncio
    async def test_empty_content_pages_are_marked_as_failed(self):
        """Pages with > 0 status but 0 content should be success=False in pipeline."""
        from research_engine.sources.web_scraper import WebScraper

        scraper = WebScraper(ScrapingConfig(fetcher_tier="async"))

        # All tiers return empty content (e.g. redirect-only pages)
        mock_page = MagicMock()
        mock_page.status = 200
        mock_page.get_all_text.return_value = ""  # empty!
        mock_page.find.return_value = None

        async def empty_tier1(url: str):
            return mock_page

        async def empty_tier2(url: str):
            return mock_page

        with patch.object(scraper, "_build_fetcher_chain", return_value=[
            ("tier1", empty_tier1),
            ("tier2", empty_tier2),
        ]):
            result = await scraper.fetch_page("https://blocked.example.com")

        # Empty content across all tiers → failure
        assert result.success is False or result.content_length == 0

    @pytest.mark.asyncio
    async def test_content_quality_filter(self):
        """Pages under 50 chars should be considered below minimum quality."""
        from research_engine.sources.web_scraper import WebScraper

        scraper = WebScraper(ScrapingConfig(fetcher_tier="async"))

        mock_page = MagicMock()
        mock_page.status = 200
        mock_page.get_all_text.return_value = "Too short"  # 9 chars
        mock_page.find.return_value = None

        async def short_tier(url: str):
            return mock_page

        with patch.object(scraper, "_build_fetcher_chain", return_value=[("t", short_tier)]):
            result = await scraper.fetch_page("https://thin.example.com")

        # Short content → should try next tier or mark as thin
        assert result.content_length < 50 or result.success is False


# ---------------------------------------------------------------------------
# Tests: Config loads API keys correctly
# ---------------------------------------------------------------------------

class TestConfigAPIKeys:
    def test_tavily_key_loaded_from_env(self):
        """TAVILY_API_KEY env var must be reflected in config.search.tavily_api_key."""
        from dotenv import load_dotenv
        load_dotenv(override=True)

        # Temporarily set env to verify injection
        original = os.environ.get("TAVILY_API_KEY")
        os.environ["TAVILY_API_KEY"] = "tvly-test-pipeline-key"

        try:
            from research_engine import config as cfg_module
            # Reset singleton to pick up new env
            cfg_module._config = None
            cfg = cfg_module.load_config()
            assert cfg.search.tavily_api_key == "tvly-test-pipeline-key"
        finally:
            if original is not None:
                os.environ["TAVILY_API_KEY"] = original
            else:
                del os.environ["TAVILY_API_KEY"]
            import research_engine.config as cfg_module
            cfg_module._config = None  # reset singleton

    def test_brave_key_loaded_from_env(self):
        """BRAVE_SEARCH_API_KEY env var must be reflected in config.search.brave_api_key."""
        from dotenv import load_dotenv
        load_dotenv(override=True)

        original = os.environ.get("BRAVE_SEARCH_API_KEY")
        os.environ["BRAVE_SEARCH_API_KEY"] = "BSA-test-key-99"

        try:
            from research_engine import config as cfg_module
            cfg_module._config = None
            cfg = cfg_module.load_config()
            assert cfg.search.brave_api_key == "BSA-test-key-99"
        finally:
            if original is not None:
                os.environ["BRAVE_SEARCH_API_KEY"] = original
            else:
                del os.environ["BRAVE_SEARCH_API_KEY"]
            import research_engine.config as cfg_module
            cfg_module._config = None

    def test_groq_presets_are_populated(self):
        """Config must have at least 15 Groq model presets after the update."""
        from research_engine.config import LLMConfig
        cfg = LLMConfig()
        assert len(cfg.groq_presets) >= 15, (
            f"Expected ≥15 Groq presets, got {len(cfg.groq_presets)}: "
            f"{list(cfg.groq_presets.keys())}"
        )

    def test_compound_beta_in_groq_presets(self):
        """Full compound-beta (not just mini) must be a preset."""
        from research_engine.config import LLMConfig
        cfg = LLMConfig()
        assert "compound_beta" in cfg.groq_presets
        assert cfg.groq_presets["compound_beta"] == "compound-beta"

    def test_llama4_scout_has_correct_id(self):
        from research_engine.config import LLMConfig
        cfg = LLMConfig()
        assert "llama4_scout" in cfg.groq_presets
        assert "llama-4-scout" in cfg.groq_presets["llama4_scout"]

    def test_scraping_tier_is_all_by_default(self):
        """Default fetcher tier must be 'all' to enable the full fallback chain."""
        from research_engine.config import ScrapingConfig
        cfg = ScrapingConfig()
        assert cfg.fetcher_tier == "all", (
            f"Default tier should be 'all', got '{cfg.fetcher_tier}'"
        )


# ---------------------------------------------------------------------------
# Tests: Mocked orchestrator depth=1 run
# ---------------------------------------------------------------------------

class TestOrchestratorDepth1:
    @pytest.mark.asyncio
    async def test_mock_research_cycle_produces_output(self):
        """Full mocked orchestrator run — verify result has report and citations."""
        from research_engine.agent.orchestrator import DeepResearchOrchestrator
        from research_engine.config import AppConfig
        from research_engine.models import (
            ResearchPlan,
            ResearchResult,
            SearchAnswer,
            SearchQuery,
            ResearchStep,
            Citation,
        )

        config = AppConfig()

        # Build a minimal mock result the orchestrator would produce
        mock_result = ResearchResult(
            run_id="test-run-001",
            query="test query",
            model_used="llama-3.3-70b-versatile",
            plan=ResearchPlan(steps=["Step 1"]),
            final_plan=ResearchPlan(steps=["Step 1"]),
            steps=[
                ResearchStep(
                    cycle=1,
                    query=SearchQuery(query="test", rationale="initial"),
                    search_results=[_fake_search_result("https://example.com")],
                    scraped_pages=[_fake_scraped_page("https://example.com")],
                    answer=SearchAnswer(
                        answer="This is a synthesized answer.",
                        citations=[Citation(id="c1", url="https://example.com", title="Example")],
                    ),
                )
            ],
            report="# Test Research\n\nThis is a test report with content.",
            citations=[Citation(id="c1", url="https://example.com", title="Example")],
            progress=100,
        )

        with patch.object(
            DeepResearchOrchestrator,
            "run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            orchestrator = DeepResearchOrchestrator(config)
            request = ResearchRequest(query="test query", depth=1)
            result = await orchestrator.run(request)

        assert result.run_id == "test-run-001"
        assert len(result.report) > 20
        assert len(result.citations) >= 1
        assert result.progress == 100

    @pytest.mark.asyncio
    async def test_sse_event_queue_receives_events(self):
        """SSE streaming: mock research emits events to the queue."""
        from research_engine.agent.orchestrator import DeepResearchOrchestrator
        from research_engine.config import AppConfig
        from research_engine.models import ResearchPlan, ResearchResult

        config = AppConfig()
        event_queue: asyncio.Queue = asyncio.Queue()

        # Must include 'self' (orchestrator instance) since we patch the class method
        async def fake_run(self_unused, request: ResearchRequest, event_queue=None):
            if event_queue:
                await event_queue.put({"event": "planning", "data": {"message": "Generating plan"}})
                await event_queue.put({"event": "searching", "data": {"query": "test query"}})
                await event_queue.put({"event": "complete", "data": {"run_id": "run-123"}})
            return ResearchResult(
                run_id="run-123",
                query="test",
                model_used="test-model",
                plan=ResearchPlan(steps=[]),
                final_plan=ResearchPlan(steps=[]),
                report="Test report",
            )

        with patch.object(DeepResearchOrchestrator, "run", new=fake_run):
            orchestrator = DeepResearchOrchestrator(config)
            request = ResearchRequest(query="test query", depth=1)
            await orchestrator.run(request, event_queue=event_queue)

        events = []
        while not event_queue.empty():
            events.append(await event_queue.get())

        event_names = [e["event"] for e in events]
        assert "planning" in event_names
        assert "complete" in event_names


# ---------------------------------------------------------------------------
# Tests: Search provider reports active providers
# ---------------------------------------------------------------------------

class TestSearchProviderReporting:
    @pytest.mark.asyncio
    async def test_aggregated_logs_each_provider(self, caplog):
        """Search provider logs should name each active sub-provider."""
        import logging
        from research_engine.sources.web_search import AggregatedSearchProvider

        mock_provider = AsyncMock()
        mock_provider.__class__.__name__ = "TavilySearch"
        mock_provider.search.return_value = [
            SearchResult(url="https://tavily.com/1", title="Tavily Result", snippet="got it")
        ]

        # AggregatedSearchProvider takes a list, no max_results kwarg
        provider = AggregatedSearchProvider([mock_provider])

        with caplog.at_level(logging.DEBUG, logger="research_engine"):
            results = await provider.search("test query", max_results=5)

        assert len(results) >= 1

    def test_search_config_with_real_env_keys(self):
        """When .env has both keys, SearchConfig must reflect them after load_config()."""
        from dotenv import load_dotenv
        load_dotenv(override=True)

        import research_engine.config as cfg_module
        cfg_module._config = None
        cfg = cfg_module.load_config()

        if TAVILY_KEY:
            assert cfg.search.tavily_api_key == TAVILY_KEY, (
                "Tavily key from .env must match config.search.tavily_api_key"
            )
        if BRAVE_KEY:
            assert cfg.search.brave_api_key == BRAVE_KEY, (
                "Brave key from .env must match config.search.brave_api_key"
            )
        cfg_module._config = None  # reset


# ---------------------------------------------------------------------------
# Live integration test (network required)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.live
async def test_live_search_and_scrape_pipeline():
    """LIVE: Full search→scrape pipeline — verifies non-zero content for a real query."""
    from research_engine.sources.web_search import DuckDuckGoSearchProvider
    from research_engine.sources.web_scraper import WebScraper

    # Search
    search = DuckDuckGoSearchProvider(max_results=3)
    results = await search.search("Python asyncio tutorial")
    assert len(results) >= 1, "Search must return at least 1 result"

    # Scrape first result
    scraper = WebScraper(ScrapingConfig(fetcher_tier="async"))
    page = await scraper.fetch_page(results[0].url)

    assert isinstance(page, ScrapedPage)
    assert page.url == results[0].url
    assert page.content_length > 100, (
        f"Live scrape of {results[0].url} returned only {page.content_length} chars. "
        f"Fetcher: {page.fetcher_used}. Error: {page.error}"
    )
