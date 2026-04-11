"""Candidate crossover — evolutionary answer merging strategy.

Generates multiple answer candidates with different LLM temperature settings,
then merges them into a single superior answer (inspired by DRE's crossover).
"""

from __future__ import annotations

import asyncio
import logging

from research_engine.llm.provider import LLMProvider
from research_engine.llm.prompts import CANDIDATES_CROSSOVER_TEMPLATE
from research_engine.models import ScrapedPage, SearchAnswer, SearchQuery

logger = logging.getLogger(__name__)

# Temperature configs for candidate diversity
CANDIDATE_CONFIGS = [
    {"temperature": 0.3},   # Conservative, factual
    {"temperature": 0.7},   # Balanced
    {"temperature": 1.2},   # Creative, exploratory
]


async def answer_with_crossover(
    topic: str,
    query: SearchQuery,
    scraped_pages: list[ScrapedPage],
    *,
    llm: LLMProvider,
    model: str | None = None,
    num_candidates: int = 3,
) -> SearchAnswer:
    """Generate multiple answer candidates and merge them via crossover.

    1. Generates N candidates in parallel with different temperature settings.
    2. Feeds all candidates to the LLM for crossover merging.
    3. Returns the merged, superior answer.

    Args:
        topic: The research topic.
        query: The search query that was answered.
        scraped_pages: The scraped page content.
        llm: The LLM provider.
        model: Optional model override.
        num_candidates: Number of candidate answers to generate.

    Returns:
        The merged SearchAnswer.
    """
    from research_engine.agent.searcher import synthesize_answer

    # Ensure we don't exceed available configs
    configs = CANDIDATE_CONFIGS[:num_candidates]
    if len(configs) < num_candidates:
        # Pad with default config variations
        for i in range(num_candidates - len(configs)):
            configs.append({"temperature": 0.5 + (i * 0.3)})

    # Step 1: Generate candidates in parallel
    logger.info(f"Generating {len(configs)} answer candidates for crossover")

    # Override LLM temperature for each candidate
    tasks = []
    for config in configs:
        # We'll call synthesize_answer but with different temperatures
        # For simplicity, we generate diverse prompts
        tasks.append(
            _generate_candidate(topic, query, scraped_pages, llm, model, config)
        )

    candidates = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out failures
    valid_candidates: list[SearchAnswer] = []
    for c in candidates:
        if isinstance(c, SearchAnswer):
            valid_candidates.append(c)
        elif isinstance(c, Exception):
            logger.warning(f"Candidate generation failed: {c}")

    if not valid_candidates:
        logger.warning("All candidates failed, falling back to single-shot answer")
        return await synthesize_answer(
            topic, query, scraped_pages, llm=llm, model=model
        )

    if len(valid_candidates) == 1:
        return valid_candidates[0]

    # Step 2: Crossover — merge candidates into superior answer
    logger.info(f"Merging {len(valid_candidates)} candidates via crossover")
    return await _crossover_merge(
        topic, query, valid_candidates, llm=llm, model=model
    )


async def _generate_candidate(
    topic: str,
    query: SearchQuery,
    scraped_pages: list[ScrapedPage],
    llm: LLMProvider,
    model: str | None,
    config: dict,
) -> SearchAnswer:
    """Generate a single answer candidate with specific LLM settings."""
    from research_engine.agent.searcher import _format_page_contents
    from research_engine.llm.prompts import SEARCH_ANSWER_GENERATION_TEMPLATE

    page_contents = _format_page_contents(scraped_pages)
    prompt = SEARCH_ANSWER_GENERATION_TEMPLATE.format(
        topic=topic,
        query=query.query,
        page_contents=page_contents,
    )

    result = await llm.call_structured(
        prompt,
        SearchAnswer,
        model=model,
        temperature=config.get("temperature", 0.7),
    )
    return SearchAnswer(**result)


async def _crossover_merge(
    topic: str,
    query: SearchQuery,
    candidates: list[SearchAnswer],
    *,
    llm: LLMProvider,
    model: str | None = None,
) -> SearchAnswer:
    """Merge multiple candidates into a single superior answer."""
    candidates_text = "\n\n".join(
        f"--- CANDIDATE {i + 1} ---\n{c.answer}"
        for i, c in enumerate(candidates)
    )

    prompt = CANDIDATES_CROSSOVER_TEMPLATE.format(
        topic=topic,
        query=query.query,
        candidates=candidates_text,
        num_candidates=len(candidates),
    )

    try:
        result = await llm.call_structured(prompt, SearchAnswer, model=model)
        merged = SearchAnswer(**result)

        # Collect all unique citations from candidates
        all_citations = {}
        for c in candidates:
            for cit in c.citations:
                if cit.url not in all_citations:
                    all_citations[cit.url] = cit
        # Add any citations from the merged answer
        for cit in merged.citations:
            if cit.url not in all_citations:
                all_citations[cit.url] = cit

        merged.citations = list(all_citations.values())
        logger.info(f"Crossover produced merged answer ({len(merged.answer)} chars)")
        return merged

    except Exception as e:
        logger.warning(f"Crossover merge failed: {e}, using best candidate")
        # Return the longest candidate as best effort
        return max(candidates, key=lambda c: len(c.answer))
