"""Async in-memory research context manager.

Stores the running Q&A history and full research trace for the current run.
Thread-safe via asyncio.Lock.
"""

from __future__ import annotations

import asyncio

from research_engine.models import ResearchStep


class ResearchContext:
    """In-memory research state for a single run.

    Tracks:
    - Q&A pairs (query → answer) as a formatted text log
    - Full typed trace (list of ResearchStep objects)
    """

    def __init__(self, max_history_steps: int | None = 5):
        self._history: list[tuple[str, str]] = []  # (query, answer)
        self._trace: list[ResearchStep] = []
        self._lock = asyncio.Lock()
        self.max_history_steps = max_history_steps

    async def add_qa(self, query: str, answer: str) -> None:
        """Append a query-answer pair to the history, enforcing rolling memory limit."""
        async with self._lock:
            self._history.append((query, answer))
            if self.max_history_steps is not None and len(self._history) > self.max_history_steps:
                self._history.pop(0)

    async def add_step(self, step: ResearchStep) -> None:
        """Append a full research step to the trace."""
        async with self._lock:
            self._trace.append(step)

    def get_history_text(self) -> str:
        """Get formatted text of all Q&A pairs for prompt injection."""
        if not self._history:
            return "No research has been done yet."

        parts = []
        for i, (q, a) in enumerate(self._history, 1):
            parts.append(f"--- Research Step {i} ---")
            parts.append(f"Query: {q}")
            parts.append(f"Findings: {a}")
            parts.append("")
        return "\n".join(parts)

    def get_trace(self) -> list[ResearchStep]:
        """Get the full typed research trace."""
        return list(self._trace)

    def get_all_citations(self) -> list:
        """Collect all unique citations from all steps."""
        from research_engine.models import Citation

        seen_urls: set[str] = set()
        citations: list[Citation] = []
        for step in self._trace:
            for cit in step.answer.citations:
                if cit.url not in seen_urls:
                    seen_urls.add(cit.url)
                    citations.append(cit)
        return citations

    @property
    def step_count(self) -> int:
        """Number of completed research steps."""
        return len(self._history)

    def clear(self) -> None:
        """Reset all state."""
        self._history.clear()
        self._trace.clear()
