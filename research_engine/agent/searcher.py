"""Search agent — query generation, web search + Scrapling scraping, answer synthesis."""

from __future__ import annotations

import asyncio
import collections
import logging
import math
import re
from datetime import UTC, datetime
from urllib.parse import urlparse

from research_engine.llm.prompts import (
    SEARCH_ANSWER_GENERATION_TEMPLATE,
    SEARCH_QUERY_GENERATION_TEMPLATE,
    BATCH_SEARCH_QUERY_GENERATION_TEMPLATE,
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
    SearchQueryBatch,
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


async def generate_query_batch(
    topic: str,
    plan: ResearchPlan,
    history: str,
    *,
    llm: LLMProvider,
    model: str | None = None,
    provider: str | None = None,
) -> list[SearchQuery]:
    """Generate a batch of 2-3 optimal search queries to be executed in parallel."""
    prompt = BATCH_SEARCH_QUERY_GENERATION_TEMPLATE.format(
        topic=topic,
        plan="\n".join(f"- {s}" for s in plan.steps),
        history=history,
    )

    try:
        result = await llm.call_structured(prompt, SearchQueryBatch, model=model, provider=provider)
        batch = SearchQueryBatch(**result)
        logger.info(f"Generated batch queries: {[q.query for q in batch.queries]}")
        if not batch.queries:
            raise ValueError("Empty queries list in generated batch")
        return batch.queries
    except Exception as e:
        logger.warning(f"Batch query generation failed: {e}. Falling back to single query.")
        # Fallback to single query wrapped in a list
        single_query = await generate_query(topic, plan, history, llm=llm, model=model, provider=provider)
        return [single_query]



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
        res = await llm.call_structured(prompt, RelevanceEvaluation, model=model, provider=provider, use_cache=True)
        eval_res = RelevanceEvaluation(**res)
        return result, eval_res.score, eval_res.rationale
    except Exception as e:
        logger.warning(f"Relevance evaluation failed for {result.url}: {e}. Defaulting to 1.0.")
        return result, 1.0, f"Evaluation fallback due to error: {e}"


async def _evaluate_relevance_batch(
    results: list[SearchResult],
    sub_query: str,
    llm: LLMProvider,
    model: str | None = None,
    provider: str | None = None,
) -> list[tuple[SearchResult, float, str]]:
    """Batch relevance check for multiple SearchResults in a single LLM call."""
    from research_engine.llm.prompts import BATCH_RELEVANCE_EVALUATION_TEMPLATE
    from research_engine.models import BatchRelevanceEvaluation

    # 1. Filter out empty or too short snippets (AutoPass)
    results_to_eval: list[tuple[int, SearchResult]] = []
    autopassed: dict[int, tuple[float, str]] = {}

    for idx, r in enumerate(results):
        if not r.snippet or len(r.snippet.strip()) < 20:
            autopassed[idx] = (0.8, "AutoPass: Snippet is empty or too short to evaluate. Passing to scraper.")
        else:
            results_to_eval.append((idx, r))

    if not results_to_eval:
        # All were autopassed!
        eval_results = []
        for idx, r in enumerate(results):
            score, rationale = autopassed[idx]
            eval_results.append((r, score, rationale))
        return eval_results

    # 2. Build the snippets text list
    snippets_list = "\n".join(
        f"[{i}] Title: {r.title or '(no title)'}\n    Snippet: {r.snippet}"
        for i, r in results_to_eval
    )

    prompt = BATCH_RELEVANCE_EVALUATION_TEMPLATE.format(
        sub_query=sub_query,
        snippets_list=snippets_list,
    )

    try:
        res = await llm.call_structured(prompt, BatchRelevanceEvaluation, model=model, provider=provider, use_cache=True)
        eval_output = BatchRelevanceEvaluation(**res)
        
        # Map evaluations back by index
        scores_by_idx: dict[int, tuple[float, str]] = {}
        for item in eval_output.evaluations:
            scores_by_idx[item.index] = (item.score, item.rationale)

        # Merge results
        eval_results = []
        for idx, r in enumerate(results):
            if idx in autopassed:
                score, rationale = autopassed[idx]
                eval_results.append((r, score, rationale))
            elif idx in scores_by_idx:
                score, rationale = scores_by_idx[idx]
                eval_results.append((r, score, rationale))
            else:
                # LLM missed or returned invalid index, default to 1.0 (pass)
                logger.warning(f"Batch eval missed index {idx} for {r.url}. Defaulting to 1.0.")
                eval_results.append((r, 1.0, "AutoPass: Index missing in batch evaluation response."))
        return eval_results

    except Exception as e:
        logger.warning(f"Batch relevance evaluation failed: {e}. Falling back to pointwise evaluation.")
        # Fall back to pointwise evaluation in parallel
        tasks = [
            _evaluate_relevance(r, sub_query, llm, model=model, provider=provider)
            for r in results
        ]
        return await asyncio.gather(*tasks)
def _tfidf_score(query: str, snippet: str) -> float:
    """Compute a lightweight TF-IDF cosine similarity score between query and snippet."""
    if not snippet or len(snippet.strip()) < 20:
        return 0.0
    
    # Tokenize and lowercase
    def tokenize(text: str) -> list[str]:
        return [w for w in re.findall(r"\w+", text.lower()) if len(w) > 1]

    q_tokens = tokenize(query)
    s_tokens = tokenize(snippet)
    
    if not q_tokens or not s_tokens:
        return 0.0

    # TF for query and snippet
    q_tf = collections.Counter(q_tokens)
    s_tf = collections.Counter(s_tokens)

    # Cosine similarity
    all_words = set(q_tf.keys()).union(set(s_tf.keys()))
    dot_product = sum(q_tf.get(w, 0) * s_tf.get(w, 0) for w in all_words)
    q_magnitude = math.sqrt(sum(v ** 2 for v in q_tf.values()))
    s_magnitude = math.sqrt(sum(v ** 2 for v in s_tf.values()))
    
    if q_magnitude == 0 or s_magnitude == 0:
        return 0.0
        
    return dot_product / (q_magnitude * s_magnitude)


def pre_filter_search_results(
    query: str,
    results: list[SearchResult],
    min_score: float = 0.05
) -> tuple[list[SearchResult], list[SearchResult]]:
    """Pre-filter search results using lightweight length and word overlap checks.
    
    Returns a tuple of (keep_results, filter_out_results).
    """
    keep = []
    filtered_out = []
    
    for r in results:
        snippet = r.snippet or ""
        # 1. Junk length check
        if len(snippet.strip()) < 20:
            r.relevance_score = 0.0
            r.eval_rationale = "Pre-filtered: Snippet too short (<20 characters)."
            filtered_out.append(r)
            continue
            
        # 2. Cosine similarity word overlap check
        score = _tfidf_score(query, snippet)
        if score < min_score:
            r.relevance_score = 0.0
            r.eval_rationale = f"Pre-filtered: Cosine word overlap score ({score:.3f}) below threshold ({min_score})."
            filtered_out.append(r)
        else:
            keep.append(r)
            
    return keep, filtered_out


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

    # Step 2: Relevance filter (AutoEval)
    if llm and search_results:
        keep_results, pre_filtered = pre_filter_search_results(query.query, search_results)
        logger.info(f"Snippet pre-filtering: kept {len(keep_results)}/{len(search_results)} results, pre-filtered {len(pre_filtered)}")
        
        if keep_results:
            logger.info(f"Running relevance AutoEval on {len(keep_results)} search results...")
            eval_results = await _evaluate_relevance_batch(
                keep_results, query.query, llm, model=model, provider=provider
            )

            # Attach scores to SearchResult models
            for r, score, rationale in eval_results:
                r.relevance_score = score
                r.eval_rationale = rationale

            passed_results = [r for r, score, _ in eval_results if score >= 0.7]
        else:
            passed_results = []
            
        logger.info(f"Relevance AutoEval: {len(passed_results)}/{len(keep_results)} passed threshold (>=0.7)")
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

