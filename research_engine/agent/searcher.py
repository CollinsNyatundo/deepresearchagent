"""Search agent — query generation, web search + Scrapling scraping, answer synthesis."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

from research_engine.llm.prompts import (
    SEARCH_ANSWER_GENERATION_TEMPLATE,
    SEARCH_QUERY_GENERATION_TEMPLATE,
)
from research_engine.llm.provider import LLMProvider
from research_engine.models import (
    Citation,
    QueryIntent,
    RelevanceEvaluation,
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
    provider: str | None = None,
) -> SearchQuery:
    """Generate the next optimal search query based on topic, plan, and history."""
    prompt = SEARCH_QUERY_GENERATION_TEMPLATE.format(
        topic=topic,
        plan="\n".join(f"- {s}" for s in plan.steps),
        history=history,
    )

    try:
        result = await llm.call_structured(prompt, SearchQuery, model=model, provider=provider)
        query = SearchQuery(**result)
        logger.info(f"Generated query: {query.query}")
        return query
    except Exception as e:
        logger.warning(f"Query generation failed: {e}")
        # Fallback: use the topic directly
        return SearchQuery(query=topic, rationale="Fallback: using topic as query")


async def _evaluate_relevance(
    result: SearchResult,
    sub_query: str,
    llm: LLMProvider,
    model: str | None = None,
    provider: str | None = None,
) -> tuple[SearchResult, float, str]:
    """Pointwise relevance check for a single SearchResult snippet."""
    from research_engine.llm.prompts import POINTWISE_RELEVANCE_EVALUATION_TEMPLATE

    # AutoPass if snippet is empty or too short
    if not result.snippet or len(result.snippet.strip()) < 20:
        return result, 0.8, "AutoPass: Snippet is empty or too short to evaluate. Passing to scraper."

    prompt = POINTWISE_RELEVANCE_EVALUATION_TEMPLATE.format(
        sub_query=sub_query,
        snippet=result.snippet,
    )
    try:
        res = await llm.call_structured(prompt, RelevanceEvaluation, model=model, provider=provider)
        eval_res = RelevanceEvaluation(**res)
        return result, eval_res.score, eval_res.rationale
    except Exception as e:
        logger.warning(f"Relevance evaluation failed for {result.url}: {e}. Defaulting to 1.0.")
        return result, 1.0, f"Evaluation fallback due to error: {e}"


async def search_and_scrape(
    query: SearchQuery,
    *,
    search_provider: SearchProvider,
    scraper: WebScraper,
    max_pages: int = 5,
    intent: QueryIntent | None = None,
    llm: LLMProvider | None = None,
    model: str | None = None,
    provider: str | None = None,
    upgrade_context: bool = False,
    on_progress = None,
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
        intent: Optional query intent classification for domain filtering.
        llm: Optional LLM provider for pointwise AutoEval relevance checking.
        model: Optional model override.
        provider: Optional LLM provider override.
        upgrade_context: Optional flag to request denser search parameters and disable SmartCrusher.

    Returns:
        Tuple of (search_results, scraped_pages).
    """
    # Step 1: Search for URLs
    search_results = await search_provider.search(query.query, max_results=max_pages * 2, upgrade_context=upgrade_context)
    logger.info(f"Search returned {len(search_results)} results for: {query.query}")

    if not search_results:
        return [], []

    # Apply intent-based domain filtering & prioritization
    if intent:
        filtered_results = []
        for r in search_results:
            domain = urlparse(r.url).netloc.lower()
            if any(avoid.lower() in domain for avoid in intent.avoid_domains if avoid):
                logger.info(f"AutoEval Filter: Skipping avoided domain URL: {r.url}")
                continue
            filtered_results.append(r)

        prioritized_results = []
        other_results = []
        for r in filtered_results:
            domain = urlparse(r.url).netloc.lower()
            if any(target.lower() in domain for target in intent.target_domains if target):
                logger.info(f"AutoEval Filter: Prioritizing target domain URL: {r.url}")
                prioritized_results.append(r)
            else:
                other_results.append(r)
        search_results = prioritized_results + other_results

    # Step 2: Pointwise relevance filter (AutoEval)
    if llm and search_results:
        logger.info(f"Running pointwise relevance AutoEval on {len(search_results)} search results...")
        tasks = [
            _evaluate_relevance(r, query.query, llm, model=model, provider=provider)
            for r in search_results
        ]
        eval_results = await asyncio.gather(*tasks)

        # Attach scores to SearchResult models
        for r, score, rationale in eval_results:
            r.relevance_score = score
            r.eval_rationale = rationale

        passed_results = [r for r, score, _ in eval_results if score >= 0.7]
        logger.info(f"Relevance AutoEval: {len(passed_results)}/{len(search_results)} passed threshold (>=0.7)")
    else:
        passed_results = search_results

    if not passed_results:
        logger.warning("All search results filtered out by relevance AutoEval! Falling back to all search results.")
        passed_results = search_results

    # Step 3: Take top URLs and scrape full content via Scrapling
    top_urls = [r.url for r in passed_results[:max_pages] if r.url]
    top_urls = _deduplicate_urls(top_urls)

    logger.info(f"Scraping {len(top_urls)} pages with Scrapling...")
    scraped_pages = await scraper.fetch_pages(top_urls, query=query.query, upgrade_context=upgrade_context, on_progress=on_progress)

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
    provider: str | None = None,
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
        result = await llm.call_structured(prompt, SearchAnswer, model=model, provider=provider)
        answer = SearchAnswer(**result)

        # Ensure citations have proper metadata
        for cit in answer.citations:
            if not cit.domain and cit.url:
                cit.domain = urlparse(cit.url).netloc
            if not cit.accessed_at:
                cit.accessed_at = datetime.now(UTC)

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

