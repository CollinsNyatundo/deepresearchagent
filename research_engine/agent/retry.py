"""Standalone reflective retry module (Protocol-H pattern).

Provides a reusable `reflective_retry()` function that can be called from
any agent module (orchestrator, searcher, etc.) without coupling.

When a research step fails, instead of silently skipping:
1. Analyze the error type + context using LLM
2. Suggest a correction (e.g., rephrased query, different approach)
3. Return correction for caller to apply
4. If analysis itself fails, return a safe skip decision

This is implemented as a standalone module (not a class method) so it can
be imported and tested independently.
"""

from __future__ import annotations

import logging
from typing import Any

from research_engine.llm.provider import LLMProvider
from research_engine.llm.prompts import REFLECTIVE_RETRY_TEMPLATE
from research_engine.models import RetryCorrection

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


async def reflective_retry(
    error: Exception,
    context: dict[str, Any],
    *,
    llm: LLMProvider,
    model: str | None = None,
    retry_count: int = 0,
) -> RetryCorrection:
    """Analyze a research step failure and suggest a correction.

    Args:
        error: The exception that was raised.
        context: Dict with keys:
            - step_type: "search" | "scrape" | "synthesis"
            - current_query: The query string that failed
            - cycle: Current research cycle number
        llm: LLM provider for generating corrections.
        model: Optional model override.
        retry_count: How many times we've retried (prevents infinite loops).

    Returns:
        RetryCorrection with corrected_query, strategy, reasoning, or should_skip=True.
    """
    if retry_count >= MAX_RETRIES:
        logger.warning(
            f"Max retries ({MAX_RETRIES}) exceeded for "
            f"step_type={context.get('step_type', 'unknown')}, "
            f"cycle={context.get('cycle', '?')}"
        )
        return RetryCorrection(
            should_skip=True,
            reasoning=f"Max retries ({MAX_RETRIES}) exceeded",
        )

    error_type = type(error).__name__
    error_message = str(error)[:500]  # Truncate very long error messages
    step_type = context.get("step_type", "unknown")
    current_query = context.get("current_query", "")
    cycle = context.get("cycle", 0)

    logger.info(
        f"Reflective retry: analyzing {error_type} for "
        f"step_type={step_type}, cycle={cycle}"
    )

    prompt = REFLECTIVE_RETRY_TEMPLATE.format(
        error_type=error_type,
        error_message=error_message,
        step_type=step_type,
        current_query=current_query,
        cycle=cycle,
    )

    try:
        result = await llm.call_structured(prompt, RetryCorrection, model=model)
        if isinstance(result, dict):
            correction = RetryCorrection(**result)
        else:
            correction = result

        logger.info(
            f"Reflective retry correction: "
            f"corrected_query={correction.corrected_query!r}, "
            f"should_skip={correction.should_skip}, "
            f"reasoning={correction.reasoning[:100]!r}"
        )
        return correction

    except Exception as analysis_err:
        logger.warning(
            f"Reflective retry analysis failed: {analysis_err}. "
            f"Defaulting to skip."
        )
        return RetryCorrection(
            should_skip=True,
            reasoning=f"Retry analysis failed: {type(analysis_err).__name__}",
        )
