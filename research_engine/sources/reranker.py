"""LLM-based search result reranker (Phase 3B).

Scores search results by relevance to the query, then reorders them
so the scraper fetches the most relevant pages first.

Batch-scores title+snippet against query (0-10). Uses a single LLM call
for the entire result set to minimize latency.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from research_engine.llm.provider import LLMProvider
from research_engine.models import SearchResult

logger = logging.getLogger(__name__)


# ─── Prompt ─────────────────────────────────────────────────────────

RERANKING_PROMPT = """\
You are a search result relevance scorer. Rate each search result by how relevant
it is to the research query.

Research Query: {query}

Search Results to Score:
{results_text}

Score each result from 0 (completely irrelevant) to 10 (perfectly relevant).
Consider:
- Does the title/snippet directly address the query?
- Is it likely to be a primary source (research, official, expert)?
- Is it likely to be informative (not just a list or index page)?

Return JSON with scores in the SAME ORDER as the results:
{{
  "scores": [
    {{"index": 0, "score": 8, "reason": "directly addresses query"}},
    {{"index": 1, "score": 3, "reason": "tangentially related"}},
    ...
  ]
}}
"""


class ResultScore(BaseModel):
    index: int
    score: float = Field(ge=0.0, le=10.0)
    reason: str = ""


class RerankingOutput(BaseModel):
    scores: list[ResultScore] = Field(default_factory=list)


# ─── Reranker ────────────────────────────────────────────────────────

async def rerank_results(
    query: str,
    results: list[SearchResult],
    *,
    llm: LLMProvider,
    model: str | None = None,
    top_k: int | None = None,
    provider: str | None = None,
) -> list[SearchResult]:
    """Score and reorder search results by relevance using LLM.

    Args:
        query: The search query string.
        results: Raw search results to score.
        llm: LLM provider for relevance scoring.
        model: Optional model override.
        top_k: If set, return only the top-k results.

    Returns:
        Results reordered by relevance score (highest first).
        Falls back to original order if LLM scoring fails.
    """
    if not results:
        return results

    # Skip reranking for very small result sets — not worth an LLM call
    if len(results) <= 2:
        return results[:top_k] if top_k else results

    results_text = "\n".join(
        f"[{i}] Title: {r.title or '(no title)'}\n    Snippet: {r.snippet[:200]}"
        for i, r in enumerate(results)
    )

    prompt = RERANKING_PROMPT.format(query=query, results_text=results_text)

    try:
        output = await llm.call_structured(prompt, RerankingOutput, model=model, provider=provider)
        if isinstance(output, dict):
            output = RerankingOutput(**output)

        # Build a score map: index → score
        score_map: dict[int, float] = {}
        for item in output.scores:
            if 0 <= item.index < len(results):
                score_map[item.index] = item.score

        # Sort results by score descending; unscored results go to the end
        scored = sorted(
            enumerate(results),
            key=lambda pair: score_map.get(pair[0], -1.0),
            reverse=True,
        )
        reranked = [r for _, r in scored]

        logger.info(
            f"Reranked {len(results)} results for query: {query!r}. "
            f"Top result: {reranked[0].title!r} (score={score_map.get(0, '?')})"
        )

        return reranked[:top_k] if top_k else reranked

    except Exception as e:
        logger.warning(
            f"Reranking failed ({type(e).__name__}: {e}), "
            f"falling back to original order"
        )
        return results[:top_k] if top_k else results
