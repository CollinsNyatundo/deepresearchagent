"""Research planner — plan creation, reflection, update, and progress checking."""

from __future__ import annotations

import logging

from research_engine.llm.prompts import (
    QUERY_DECOMPOSITION_TEMPLATE,
    RESEARCH_PLAN_REFLECTION_TEMPLATE,
    RESEARCH_PLAN_UPDATE_TEMPLATE,
    RESEARCH_PLANNING_TEMPLATE,
    RESEARCH_PROGRESS_TEMPLATE,
)
from research_engine.llm.provider import LLMProvider
from research_engine.models import (
    QueryDecomposition,
    ResearchPlan,
    ResearchPlanReflection,
    ResearchProgress,
)

logger = logging.getLogger(__name__)


async def create_plan(
    topic: str,
    *,
    llm: LLMProvider,
    model: str | None = None,
    provider: str | None = None,
) -> ResearchPlan:
    """Create an initial research plan for a topic.

    Uses the LLM to generate 5-10 ordered research steps.
    """
    prompt = RESEARCH_PLANNING_TEMPLATE.format(topic=topic)

    try:
        result = await llm.call_structured(prompt, ResearchPlan, model=model, provider=provider)
        plan = ResearchPlan(**result)
        logger.info(f"Created research plan with {len(plan.steps)} steps")
        return plan
    except Exception as e:
        logger.error(f"Plan creation failed: {e}")
        # Fallback: generate a basic plan
        return ResearchPlan(steps=[
            f"Research the fundamentals of: {topic}",
            f"Find key recent developments related to: {topic}",
            f"Identify expert opinions and analysis on: {topic}",
            f"Look for data, statistics, and evidence related to: {topic}",
            f"Synthesize findings and identify implications of: {topic}",
        ])


async def decompose_query(
    topic: str,
    *,
    llm: LLMProvider,
    model: str | None = None,
    provider: str | None = None,
) -> list[str]:
    """Break a complex research query into 2-4 focused sub-queries.

    Each sub-query targets a distinct aspect of the topic, enabling
    broader search coverage when used with the aggregated provider.

    Returns:
        List of sub-query strings. Falls back to [topic] on failure.
    """
    prompt = QUERY_DECOMPOSITION_TEMPLATE.format(topic=topic)

    try:
        result = await llm.call_structured(prompt, QueryDecomposition, model=model, provider=provider)
        if isinstance(result, dict):
            decomp = QueryDecomposition(**result)
        else:
            decomp = result

        sub_queries = [q for q in decomp.sub_queries if q.strip()]
        if not sub_queries:
            return [topic]

        logger.info(f"Decomposed query into {len(sub_queries)} sub-queries")
        return sub_queries

    except Exception as e:
        logger.warning(f"Query decomposition failed: {e}. Using original topic.")
        return [topic]


async def reflect_on_plan(
    topic: str,
    plan: ResearchPlan,
    history: str,
    *,
    llm: LLMProvider,
    model: str | None = None,
    provider: str | None = None,
) -> ResearchPlanReflection:
    """Evaluate whether the current plan needs updating based on findings so far."""
    prompt = RESEARCH_PLAN_REFLECTION_TEMPLATE.format(
        topic=topic,
        plan="\n".join(f"- {s}" for s in plan.steps),
        history=history,
    )

    try:
        result = await llm.call_structured(prompt, ResearchPlanReflection, model=model, provider=provider, use_cache=True)
        reflection = ResearchPlanReflection(**result)
        logger.info(f"Plan reflection: should_update={reflection.should_update}")
        return reflection
    except Exception as e:
        logger.warning(f"Plan reflection failed: {e}")
        return ResearchPlanReflection(should_update=False, updates="")


async def update_plan(
    topic: str,
    plan: ResearchPlan,
    reflection: ResearchPlanReflection,
    history: str,
    *,
    llm: LLMProvider,
    model: str | None = None,
    provider: str | None = None,
) -> ResearchPlan:
    """Update the research plan based on a reflection."""
    prompt = RESEARCH_PLAN_UPDATE_TEMPLATE.format(
        topic=topic,
        plan="\n".join(f"- {s}" for s in plan.steps),
        reflection=reflection.updates,
        history=history,
    )

    try:
        result = await llm.call_structured(prompt, ResearchPlan, model=model, provider=provider, use_cache=True)
        updated = ResearchPlan(**result)
        logger.info(f"Updated research plan: {len(updated.steps)} steps")
        return updated
    except Exception as e:
        logger.warning(f"Plan update failed: {e}")
        return plan  # Keep the original plan


async def check_progress(
    topic: str,
    plan: ResearchPlan,
    history: str,
    *,
    llm: LLMProvider,
    model: str | None = None,
    provider: str | None = None,
) -> int:
    """Estimate research completion percentage (0-100)."""
    prompt = RESEARCH_PROGRESS_TEMPLATE.format(
        topic=topic,
        plan="\n".join(f"- {s}" for s in plan.steps),
        history=history,
    )

    try:
        result = await llm.call_structured(prompt, ResearchProgress, model=model, provider=provider, use_cache=True)
        progress = ResearchProgress(**result).progress
        logger.info(f"Research progress: {progress}%")
        return max(0, min(100, progress))
    except Exception as e:
        logger.warning(f"Progress check failed: {e}")
        return 50  # Conservative estimate
