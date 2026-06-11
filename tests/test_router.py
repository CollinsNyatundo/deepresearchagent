"""Tests for the AgenticSearchRouter and RoutedSearchProvider cascade policies."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from research_engine.config import SearchConfig
from research_engine.models import QueryIntent, QueryIntentCategory, SearchResult
from research_engine.agent.router import AgenticSearchRouter, RoutedSearchProvider


class TestAgenticSearchRouter:
    def test_classify_intent(self):
        # Academic -> semantic_concept
        intent_academic = QueryIntent(category=QueryIntentCategory.ACADEMIC, rationale="academic testing")
        assert AgenticSearchRouter.classify_search_intent(intent_academic) == "semantic_concept"

        # News -> fact_check
        intent_news = QueryIntent(category=QueryIntentCategory.NEWS, rationale="news testing")
        assert AgenticSearchRouter.classify_search_intent(intent_news) == "fact_check"

        # Technical -> bulk_extract
        intent_tech = QueryIntent(category=QueryIntentCategory.TECHNICAL, rationale="technical testing")
        assert AgenticSearchRouter.classify_search_intent(intent_tech) == "bulk_extract"

        # General -> fact_check
        intent_general = QueryIntent(category=QueryIntentCategory.GENERAL, rationale="general testing")
        assert AgenticSearchRouter.classify_search_intent(intent_general) == "fact_check"

        # None -> fact_check
        assert AgenticSearchRouter.classify_search_intent(None) == "fact_check"

    @pytest.mark.asyncio
    @patch("research_engine.agent.router.get_search_provider")
    async def test_route_search_success_primary(self, mock_get_provider):
        # Mock a successful search result
        mock_provider = AsyncMock()
        mock_provider.search.return_value = [
            SearchResult(url="https://primary.com", title="Primary Result", snippet="Yay")
        ]
        mock_get_provider.return_value = mock_provider

        config = SearchConfig(
            tavily_api_key="tav-key",
            exa_api_key="exa-key",
            brave_api_key="brave-key",
            parallel_api_key="parallel-key",
        )

        # Route search for academic/semantic_concept (primary: exa)
        results = await AgenticSearchRouter.route_search(
            query="test query",
            routing_key="semantic_concept",
            search_config=config,
            max_results=5,
        )

        assert len(results) == 1
        assert results[0].url == "https://primary.com"
        assert results[0].provider == "exa"
        mock_get_provider.assert_called_with("exa", config)
        mock_provider.search.assert_called_once_with("test query", max_results=5)

    @pytest.mark.asyncio
    @patch("research_engine.agent.router.get_search_provider")
    async def test_route_search_failover_cascade(self, mock_get_provider):
        # We want to test failover cascade: primary (exa) fails/returns empty, then tavily succeeds.
        mock_exa = AsyncMock()
        mock_exa.search.side_effect = Exception("Exa API timeout")

        mock_tavily = AsyncMock()
        mock_tavily.search.return_value = [
            SearchResult(url="https://tavily.com", title="Tavily Result", snippet="Tavily content")
        ]

        def get_mock_provider(name, config):
            if name == "exa":
                return mock_exa
            elif name == "tavily":
                return mock_tavily
            raise ValueError(f"Unexpected provider request: {name}")

        mock_get_provider.side_effect = get_mock_provider

        config = SearchConfig(
            tavily_api_key="tav-key",
            exa_api_key="exa-key",
            brave_api_key="brave-key",
            parallel_api_key="parallel-key",
        )

        results = await AgenticSearchRouter.route_search(
            query="test cascade query",
            routing_key="semantic_concept",
            search_config=config,
            max_results=5,
        )

        assert len(results) == 1
        assert results[0].url == "https://tavily.com"
        assert results[0].provider == "tavily"
        mock_exa.search.assert_called_once()
        mock_tavily.search.assert_called_once()

    @pytest.mark.asyncio
    @patch("research_engine.agent.router.get_search_provider")
    async def test_routed_search_provider_wrapper(self, mock_get_provider):
        mock_provider = AsyncMock()
        mock_provider.search.return_value = [
            SearchResult(url="https://wrap.com", title="Wrapped Result", snippet="Wrap")
        ]
        mock_get_provider.return_value = mock_provider

        config = SearchConfig(
            tavily_api_key="tav-key",
            exa_api_key="exa-key",
            brave_api_key="brave-key",
            parallel_api_key="parallel-key",
        )

        routed_provider = RoutedSearchProvider(routing_key="fact_check", search_config=config)
        results = await routed_provider.search("wrapped query", max_results=3, upgrade_context=True)

        assert len(results) == 1
        assert results[0].url == "https://wrap.com"
        assert results[0].provider == "tavily"
        mock_get_provider.assert_called_with("tavily", config)
        mock_provider.search.assert_called_once_with("wrapped query", max_results=3, upgrade_context=True)
