"""Cost optimization — exhaustive implementation with tracking and analysis.

Features:
- CacheAligner: Prompt prefix stabilization for cache hit rates
- CostTracker: Token usage and cost tracking per model
- TokenEstimator: Estimate token count from text
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


# ─── Cache Aligner ───────────────────────────────────────────────────

class CacheAligner:
    """Stabilizes prompt prefixes for better cache hit rates.

    Ensures identical system prompt prefix across calls so that
    prefix cache hits are more likely on LLM providers (e.g., OpenAI,
    Anthropic) that support prompt caching.
    """

    SEPARATOR = "\n\n[QUERY]\n"

    def prepare(self, system_prompt: str, context: str) -> str:
        """Prepare a prompt with stable prefix and separated context.

        Args:
            system_prompt: Stable system instructions (cached by LLM provider)
            context: Variable query content

        Returns:
            Combined prompt with stable prefix
        """
        return f"{system_prompt}{self.SEPARATOR}{context}"

    def extract_prefix(self, full_prompt: str) -> str:
        """Extract the stable prefix from a prepared prompt."""
        if self.SEPARATOR in full_prompt:
            return full_prompt.split(self.SEPARATOR)[0]
        return full_prompt

    def extract_context(self, full_prompt: str) -> str:
        """Extract the variable context from a prepared prompt."""
        if self.SEPARATOR in full_prompt:
            parts = full_prompt.split(self.SEPARATOR, 1)
            return parts[1] if len(parts) > 1 else ""
        return ""


# ─── Token Estimator ─────────────────────────────────────────────────

class TokenEstimator:
    """Estimates token count from text.

    Uses a rough approximation: ~4 characters per token for English text.
    More accurate estimators can be plugged in.
    """

    CHARS_PER_TOKEN = 4.0

    def estimate(self, text: str) -> int:
        """Estimate token count for given text."""
        if not text:
            return 0
        return max(1, int(len(text) / self.CHARS_PER_TOKEN))

    def estimate_chat(self, messages: list[dict]) -> int:
        """Estimate token count for a chat message list."""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += self.estimate(content)
            # Add overhead per message (role tokens, etc.)
            total += 4
        return total


# ─── Cost Tracker ────────────────────────────────────────────────────

@dataclass
class CostEntry:
    """Single cost tracking entry."""
    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float  # Cost per 1K input tokens
    output_cost: float  # Cost per 1K output tokens
    total_cost: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if self.total_cost == 0.0:
            self.total_cost = (
                (self.input_tokens / 1000) * self.input_cost +
                (self.output_tokens / 1000) * self.output_cost
            )


class CostTracker:
    """Tracks LLM usage costs across models.

    Maintains a running log of all API calls with token counts and costs.
    """

    # Cost per 1K tokens (input, output) for common models
    MODEL_COSTS: dict[str, tuple[float, float]] = {
        "gpt-4o": (5.0, 15.0),
        "gpt-4o-mini": (0.15, 0.60),
        "claude-3-5-sonnet": (3.0, 15.0),
        "claude-3-haiku": (0.25, 1.25),
        "deepseek-chat": (0.14, 0.28),
        "default": (1.0, 2.0),
    }

    def __init__(self):
        self._entries: list[CostEntry] = []
        self._estimator = TokenEstimator()

    def track(
        self,
        model: str,
        prompt: str,
        response: str,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> CostEntry:
        """Track a single LLM call.

        Args:
            model: Model identifier
            prompt: Prompt text (used for token estimation if not provided)
            response: Response text
            input_tokens: Optional actual input token count
            output_tokens: Optional actual output token count

        Returns:
            CostEntry with computed costs
        """
        if input_tokens is None:
            input_tokens = self._estimator.estimate(prompt)
        if output_tokens is None:
            output_tokens = self._estimator.estimate(response)

        input_cost, output_cost = self.MODEL_COSTS.get(model, self.MODEL_COSTS["default"])

        entry = CostEntry(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
        )
        self._entries.append(entry)
        return entry

    def total_cost(self) -> float:
        """Total cost across all tracked entries."""
        return sum(e.total_cost for e in self._entries)

    def total_tokens(self) -> dict[str, int]:
        """Total input and output tokens."""
        return {
            "input": sum(e.input_tokens for e in self._entries),
            "output": sum(e.output_tokens for e in self._entries),
        }

    def cost_by_model(self) -> dict[str, float]:
        """Cost breakdown by model."""
        breakdown = {}
        for e in self._entries:
            breakdown[e.model] = breakdown.get(e.model, 0.0) + e.total_cost
        return breakdown

    def get_summary(self) -> dict[str, Any]:
        """Get comprehensive cost summary."""
        tokens = self.total_tokens()
        return {
            "total_cost_usd": round(self.total_cost(), 4),
            "total_calls": len(self._entries),
            "total_input_tokens": tokens["input"],
            "total_output_tokens": tokens["output"],
            "cost_by_model": self.cost_by_model(),
        }

    def reset(self) -> None:
        """Clear all tracked entries."""
        self._entries.clear()
