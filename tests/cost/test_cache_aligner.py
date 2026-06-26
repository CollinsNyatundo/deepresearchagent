"""Exhaustive tests for cost optimization module."""
import pytest

from research_engine.cost.cache_aligner import (
    CacheAligner,
    TokenEstimator,
    CostTracker,
    CostEntry,
)


class TestCacheAligner:
    """Tests for cache aligner."""

    def test_prepare_stabilizes_prefix(self):
        """Given system prompt, prefix is identical across calls."""
        aligner = CacheAligner()
        prompt1 = aligner.prepare("You are a research assistant.", context="data1")
        prompt2 = aligner.prepare("You are a research assistant.", context="data2")
        assert aligner.extract_prefix(prompt1) == aligner.extract_prefix(prompt2)

    def test_prepare_preserves_unique_context(self):
        """Given different contexts, unique content is preserved."""
        aligner = CacheAligner()
        prompt1 = aligner.prepare("System prompt", context="Query: AI in healthcare")
        prompt2 = aligner.prepare("System prompt", context="Query: Blockchain supply chain")
        assert "AI in healthcare" in prompt1
        assert "Blockchain supply chain" in prompt2

    def test_extract_prefix(self):
        """Given full prompt, extract_prefix returns system part."""
        aligner = CacheAligner()
        full = aligner.prepare("System: Do research.", context="Topic: AI")
        prefix = aligner.extract_prefix(full)
        assert prefix == "System: Do research."
        assert "Topic: AI" not in prefix

    def test_extract_context(self):
        """Given full prompt, extract_context returns context part."""
        aligner = CacheAligner()
        full = aligner.prepare("System prompt", context="Query data")
        context = aligner.extract_context(full)
        assert context == "Query data"

    def test_no_separator_returns_full_as_prefix(self):
        """Given no separator, returns full as prefix."""
        aligner = CacheAligner()
        prefix = aligner.extract_prefix("No separator here")
        assert prefix == "No separator here"

    def test_separator_constant(self):
        """Given separator, is consistent."""
        aligner = CacheAligner()
        assert aligner.SEPARATOR == "\n\n[QUERY]\n"


class TestTokenEstimator:
    """Tests for token estimator."""

    def test_estimate_empty_string(self):
        """Given empty string, returns 0."""
        estimator = TokenEstimator()
        assert estimator.estimate("") == 0

    def test_estimate_short_text(self):
        """Given short text, returns at least 1."""
        estimator = TokenEstimator()
        assert estimator.estimate("Hello") >= 1

    def test_estimate_long_text(self):
        """Given long text, returns proportional estimate."""
        estimator = TokenEstimator()
        text = "x" * 4000
        estimate = estimator.estimate(text)
        assert estimate >= 1000  # 4000 / 4 = 1000

    def test_estimate_chat(self):
        """Given chat messages, estimates total tokens."""
        estimator = TokenEstimator()
        messages = [
            {"content": "Hello"},
            {"content": "World"},
            {"content": "Test message"},
        ]
        total = estimator.estimate_chat(messages)
        assert total > 0
        assert total >= 12  # 3 messages * 4 overhead = 12 minimum

    def test_estimate_chat_empty(self):
        """Given empty chat, returns 0."""
        estimator = TokenEstimator()
        assert estimator.estimate_chat([]) == 0

    def test_estimate_with_custom_ratio(self):
        """Given custom ratio, uses it."""
        estimator = TokenEstimator()
        estimator.CHARS_PER_TOKEN = 2.0
        assert estimator.estimate("xxxx") == 2


class TestCostEntry:
    """Tests for cost entry data model."""

    def test_computes_total_cost(self):
        """Given tokens and rates, computes total cost."""
        entry = CostEntry(
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            input_cost=5.0,
            output_cost=15.0,
        )
        expected = (1000 / 1000) * 5.0 + (500 / 1000) * 15.0
        assert entry.total_cost == expected

    def test_default_timestamp(self):
        """Given no timestamp, uses current time."""
        import time
        entry = CostEntry(model="test", input_tokens=0, output_tokens=0, input_cost=0, output_cost=0)
        assert entry.timestamp > 0
        assert entry.timestamp <= time.time()


class TestCostTracker:
    """Tests for cost tracker."""

    def test_track_single_call(self):
        """Given single call, tracks cost."""
        tracker = CostTracker()
        entry = tracker.track("gpt-4o", prompt="Hello", response="Hi")
        assert entry.total_cost > 0
        assert entry.model == "gpt-4o"

    def test_total_cost_accumulates(self):
        """Given multiple calls, total cost accumulates."""
        tracker = CostTracker()
        tracker.track("gpt-4o", prompt="Hello", response="Hi")
        tracker.track("gpt-4o", prompt="World", response="Test")
        total = tracker.total_cost()
        assert total > 0

    def test_total_tokens(self):
        """Given tracked calls, returns total tokens."""
        tracker = CostTracker()
        tracker.track("gpt-4o", prompt="Hello world", response="Test response")
        tokens = tracker.total_tokens()
        assert tokens["input"] > 0
        assert tokens["output"] > 0

    def test_cost_by_model(self):
        """Given multiple models, breaks down by model."""
        tracker = CostTracker()
        tracker.track("gpt-4o", prompt="A", response="B")
        tracker.track("claude-3-haiku", prompt="C", response="D")
        breakdown = tracker.cost_by_model()
        assert "gpt-4o" in breakdown
        assert "claude-3-haiku" in breakdown

    def test_get_summary(self):
        """Given tracked calls, returns comprehensive summary."""
        tracker = CostTracker()
        tracker.track("gpt-4o", prompt="Hello", response="Hi")
        summary = tracker.get_summary()
        assert "total_cost_usd" in summary
        assert "total_calls" in summary
        assert summary["total_calls"] == 1
        assert "total_input_tokens" in summary
        assert "total_output_tokens" in summary
        assert "cost_by_model" in summary

    def test_reset_clears_entries(self):
        """Given reset, clears all entries."""
        tracker = CostTracker()
        tracker.track("gpt-4o", prompt="A", response="B")
        tracker.reset()
        assert tracker.total_cost() == 0.0
        assert tracker.total_tokens()["input"] == 0

    def test_unknown_model_uses_default_cost(self):
        """Given unknown model, uses default cost."""
        tracker = CostTracker()
        entry = tracker.track("unknown-model", prompt="Hello", response="Hi")
        assert entry.total_cost > 0

    def test_explicit_token_counts(self):
        """Given explicit token counts, uses them."""
        tracker = CostTracker()
        entry = tracker.track(
            "gpt-4o",
            prompt="Hello",
            response="Hi",
            input_tokens=100,
            output_tokens=50,
        )
        assert entry.input_tokens == 100
        assert entry.output_tokens == 50

    def test_deepseek_cost(self):
        """Given deepseek model, uses correct pricing."""
        tracker = CostTracker()
        entry = tracker.track(
            "deepseek-chat",
            prompt="Hello world",
            response="Test",
            input_tokens=1000,
            output_tokens=500,
        )
        expected = (1000 / 1000) * 0.14 + (500 / 1000) * 0.28
        assert entry.total_cost == expected
