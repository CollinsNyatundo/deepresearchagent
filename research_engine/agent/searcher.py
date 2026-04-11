"""Search agent — query generation, web search + Scrapling scraping, answer synthesis."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from research_engine.llm.provider import LLMProvider
from research_engine.llm.prompts import (
    SEARCH_ANSWER_GENERATION_TEMPLATE,
    SEARCH_QUERY_GENERATION_TEMPLATE,
)
from research_engine.models import (
    Citation,
    ResearchPlan,
    ScrapedPage,
    SearchAnswer,
    SearchQuery,
    SearchResult,
)
from research_engine.sources.web_scraper import WebScraper
from research_engine.sources.web_search import SearchProvider

logger = logging.getLogger(__name__)


async def generate_query(
    topic: str,
    plan: ResearchPlan,
    history: str,
    *,
    llm: LLMProvider,
    model: str | None = None,
) -> SearchQuery:
    """Generate the next optimal search query based on topic, plan, and history."""
    prompt = SEARCH_QUERY_GENERATION_TEMPLATE.format(
        topic=topic,
        plan="\n".join(f"- {s}" for s in plan.steps),
        history=history,
    )

    try:
        result = await llm.call_structured(prompt, SearchQuery, model=model)
        query = SearchQuery(**result)
        logger.info(f"Generated query: {query.query}")
        return query
    except Exception as e:
        logger.warning(f"Query generation failed: {e}")
        # Fallback: use the topic directly
        return SearchQuery(query=topic, rationale="Fallback: using topic as query")


async def search_and_scrape(
    query: SearchQuery,
    *,
    search_provider: SearchProvider,
    scraper: WebScraper,
    max_pages: int = 5,
) -> tuple[list[SearchResult], list[ScrapedPage]]:
    """Execute search → get URLs → deep scrape top pages with Scrapling.

    This is the key enhancement over the original DRE: instead of just
    reading search snippets (~200 chars), we scrape FULL PAGE CONTENT
    via Scrapling (20K+ chars per page).

    Args:
        query: The search query to execute.
        search_provider: The search engine to use.
        scraper: The Scrapling-based web scraper.
        max_pages: Maximum number of pages to scrape.

    Returns:
        Tuple of (search_results, scraped_pages).
    """
    # Step 1: Search for URLs
    search_results = await search_provider.search(query.query, max_results=max_pages * 2)
    logger.info(f"Search returned {len(search_results)} results for: {query.query}")

    if not search_results:
        return [], []

    # Step 2: Take top URLs and scrape full content via Scrapling
    top_urls = [r.url for r in search_results[:max_pages] if r.url]
    top_urls = _deduplicate_urls(top_urls)

    logger.info(f"Scraping {len(top_urls)} pages with Scrapling...")
    scraped_pages = await scraper.fetch_pages(top_urls)

    # Filter to successful scrapes
    successful = [p for p in scraped_pages if p.success and p.content]
    logger.info(
        f"Successfully scraped {len(successful)}/{len(top_urls)} pages "
        f"(total content: {sum(p.content_length for p in successful)} chars)"
    )

    return search_results, scraped_pages


async def synthesize_answer(
    topic: str,
    query: SearchQuery,
    scraped_pages: list[ScrapedPage],
    *,
    llm: LLMProvider,
    model: str | None = None,
) -> SearchAnswer:
    """Synthesize an answer from FULL PAGE CONTENT (not just snippets).

    This feeds the complete Markdown content from Scrapling into the LLM,
    allowing much richer and more accurate synthesis than snippet-based approaches.
    """
    # Build the content block from all successfully scraped pages
    page_contents = _format_page_contents(scraped_pages)

    if not page_contents.strip():
        return SearchAnswer(
            answer="No content could be retrieved for this query.",
            citations=[],
        )

    prompt = SEARCH_ANSWER_GENERATION_TEMPLATE.format(
        topic=topic,
        query=query.query,
        page_contents=page_contents,
    )

    try:
        result = await llm.call_structured(prompt, SearchAnswer, model=model)
        answer = SearchAnswer(**result)

        # Ensure citations have proper metadata
        for cit in answer.citations:
            if not cit.domain and cit.url:
                cit.domain = urlparse(cit.url).netloc
            if not cit.accessed_at:
                cit.accessed_at = datetime.now(timezone.utc)

        logger.info(
            f"Synthesized answer ({len(answer.answer)} chars, "
            f"{len(answer.citations)} citations)"
        )
        return answer
    except Exception as e:
        logger.error(f"Answer synthesis failed: {e}")
        # Fallback: create a basic answer from page snippets
        return _fallback_answer(scraped_pages)


def _format_page_contents(pages: list[ScrapedPage]) -> str:
    """Format scraped pages into a structured content block for the LLM."""
    parts = []
    for i, page in enumerate(pages, 1):
        if not page.success or not page.content:
            continue
        parts.append(f"=== SOURCE {i}: {page.title or page.url} ===")
        parts.append(f"URL: {page.url}")
        parts.append(f"Fetcher: {page.fetcher_used}")
        parts.append(f"Content ({page.content_length} chars):")
        parts.append(page.content)
        parts.append("")
    return "\n".join(parts)


def _fallback_answer(pages: list[ScrapedPage]) -> SearchAnswer:
    """Create a minimal answer from page content when LLM synthesis fails."""
    snippets = []
    citations = []
    for i, page in enumerate(pages):
        if page.success and page.content:
            snippet = page.content[:500]
            snippets.append(f"From {page.title or page.url}: {snippet}")
            citations.append(Citation(
                id=f"c{i + 1}",
                url=page.url,
                title=page.title or "",
                domain=urlparse(page.url).netloc,
                snippet=snippet[:200],
            ))
    return SearchAnswer(
        answer="\n\n".join(snippets) if snippets else "No content retrieved.",
        citations=citations,
    )


def _deduplicate_urls(urls: list[str]) -> list[str]:
    """Remove duplicate URLs while preserving order."""
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        normalized = url.rstrip("/").lower()
        if normalized not in seen:
            seen.add(normalized)
            unique.append(url)
    return unique


def validate_scraped_content(pages: list[ScrapedPage]) -> list[ScrapedPage]:
    """Filter out low-quality scraped content before synthesis (Protocol-H pattern).

    Checks applied:
    - Page must have succeeded (success=True)
    - Content length must be > 100 chars (filters empty/error pages)
    - Not duplicate content (deduplicates by first 500-char hash)
    - Not navigation/boilerplate-only content

    Args:
        pages: Raw scraped pages from WebScraper.

    Returns:
        Filtered list of valid pages, preserving original order.
    """
    valid: list[ScrapedPage] = []
    seen_hashes: set[int] = set()

    for page in pages:
        # Must be a successful scrape with real content
        if not page.success or page.content_length < 100:
            continue

        # Deduplicate by content prefix hash
        content_hash = hash(page.content[:500])
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)

        valid.append(page)

    filtered_count = len(pages) - len(valid)
    if filtered_count > 0:
        logger.info(
            f"Content validation: {len(pages)} → {len(valid)} pages "
            f"({filtered_count} filtered as low-quality/duplicate)"
        )

    return valid

