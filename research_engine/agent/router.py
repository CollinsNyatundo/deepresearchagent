"""Agentic Search Router for mapping query intent to search providers and executing fallback cascades."""

from __future__ import annotations

import logging

from research_engine.config import SearchConfig
from research_engine.models import QueryIntent, QueryIntentCategory, SearchResult
from research_engine.sources.web_search import get_search_provider

logger = logging.getLogger(__name__)


class AgenticSearchRouter:
    """Agentic search router mapping intent to search providers with failover cascades."""

    @staticmethod
    def classify_search_intent(intent: QueryIntent | None) -> str:
        """Classifies search intent category into a routing key.

        Returns:
            One of: 'fact_check', 'semantic_concept', 'bulk_extract', 'deep_scrape'
        """
        if not intent:
            return "fact_check"

        match intent.category:
            case QueryIntentCategory.ACADEMIC:
                return "semantic_concept"
            case QueryIntentCategory.NEWS:
                return "fact_check"
            case QueryIntentCategory.TECHNICAL:
                return "bulk_extract"
            case QueryIntentCategory.GENERAL:
                return "fact_check"
            case _:
                return "fact_check"

    @staticmethod
    async def route_search(
        query: str,
        routing_key: str,
        search_config: SearchConfig,
        max_results: int = 10,
        **kwargs,
    ) -> list[SearchResult]:
        """Routes search to the best provider based on intent, with failover cascade.

        Cascade order: Primary routed provider -> Exa -> Tavily -> Brave -> DuckDuckGo
        """
        # Determine the primary provider based on the routing key
        primary = "all"
        if routing_key == "fact_check":
            primary = "tavily"
        elif routing_key == "semantic_concept":
            primary = "exa"
        elif routing_key == "bulk_extract":
            primary = "parallel"
        elif routing_key == "deep_scrape":
            primary = "exa"

        # Build cascade list starting with primary, then falling back: Exa -> Tavily -> Brave -> DuckDuckGo
        cascade = [primary]
        standard_cascade = ["exa", "tavily", "brave", "duckduckgo"]
        for p in standard_cascade:
            if p not in cascade:
                cascade.append(p)

        # Try each provider in the cascade in order
        for provider_name in cascade:
            try:
                # Skip if API key is not configured for Tavily, Exa, Brave, Parallel
                if provider_name == "tavily" and not search_config.tavily_api_key:
                    logger.debug("Skipping Tavily in cascade: key not configured")
                    continue
                if provider_name == "exa" and not search_config.exa_api_key:
                    logger.debug("Skipping Exa in cascade: key not configured")
                    continue
                if provider_name == "brave" and not search_config.brave_api_key:
                    logger.debug("Skipping Brave in cascade: key not configured")
                    continue
                if provider_name == "parallel" and not search_config.parallel_api_key:
                    logger.debug("Skipping Parallel AI in cascade: key not configured")
                    continue

                logger.info(f"Trying search provider: {provider_name} for query: {query}")
                provider = get_search_provider(provider_name, search_config)
                results = await provider.search(query, max_results=max_results, **kwargs)
                if results:
                    # Mark source provider on all results
                    for r in results:
                        if not r.provider:
                            r.provider = provider_name
                    logger.info(f"✓ Search provider {provider_name} succeeded with {len(results)} results")
                    return results
                else:
                    logger.warning(f"Search provider {provider_name} returned 0 results, falling back...")
            except Exception as e:
                logger.error(f"Search provider {provider_name} failed: {e}. Falling back...")
                continue

        # Final emergency fallback: Aggregated Search or DuckDuckGo
        logger.warning("All cascade search providers failed or skipped. Trying aggregated search fallback.")
        try:
            fallback_provider = get_search_provider("all", search_config)
            results = await fallback_provider.search(query, max_results=max_results, **kwargs)
            for r in results:
                if not r.provider:
                    r.provider = "aggregated"
            return results
        except Exception as e:
            logger.error(f"Aggregated search fallback also failed: {e}")
            return []


class RoutedSearchProvider:
    """A search provider wrapper that agentically routes search requests based on query intent."""

    def __init__(self, routing_key: str, search_config: SearchConfig):
        self.routing_key = routing_key
        self.search_config = search_config

    async def search(self, query: str, max_results: int = 10, **kwargs) -> list[SearchResult]:
        return await AgenticSearchRouter.route_search(
            query=query,
            routing_key=self.routing_key,
            search_config=self.search_config,
            max_results=max_results,
            **kwargs
        )

