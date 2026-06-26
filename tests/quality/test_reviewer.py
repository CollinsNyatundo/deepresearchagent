"""Exhaustive tests for quality review module."""
import pytest
from unittest.mock import AsyncMock

from research_engine.quality.reviewer import (
    Dimension,
    ScoringRubric,
    PromptBuilder,
    QualityReport,
    QualityReviewer,
    InMemoryQualityStorage,
    QualityStorage,
)


class TestScoringRubric:
    """Tests for scoring rubric validation and computation."""

    def test_rubric_has_five_dimensions(self):
        """Given rubric, it has exactly 5 dimensions."""
        assert len(ScoringRubric.DIMENSIONS) == 5

    def test_rubric_dimensions_have_weights(self):
        """Given dimensions, all have positive weights."""
        for dim in ScoringRubric.DIMENSIONS:
            assert dim.weight > 0, f"{dim.name} has no weight"

    def test_rubric_dimensions_have_criteria(self):
        """Given dimensions, all have criteria lists."""
        for dim in ScoringRubric.DIMENSIONS:
            assert len(dim.criteria) >= 3, f"{dim.name} has insufficient criteria"

    def test_validate_scores_all_valid(self):
        """Given valid scores, validation returns no errors."""
        scores = {d.name: 0.8 for d in ScoringRubric.DIMENSIONS}
        errors = ScoringRubric.validate_scores(scores)
        assert errors == []

    def test_validate_scores_missing_dimension(self):
        """Given missing dimension, validation returns error."""
        scores = {d.name: 0.8 for d in ScoringRubric.DIMENSIONS[:4]}
        errors = ScoringRubric.validate_scores(scores)
        assert any("Missing" in e for e in errors)

    def test_validate_scores_out_of_range(self):
        """Given out-of-range score, validation returns error."""
        scores = {d.name: 0.8 for d in ScoringRubric.DIMENSIONS}
        scores["confidence_score"] = 1.5
        errors = ScoringRubric.validate_scores(scores)
        assert any("out of range" in e for e in errors)

    def test_validate_scores_unknown_dimension(self):
        """Given unknown dimension, validation returns error."""
        scores = {d.name: 0.8 for d in ScoringRubric.DIMENSIONS}
        scores["unknown_dim"] = 0.5
        errors = ScoringRubric.validate_scores(scores)
        assert any("Unknown" in e for e in errors)

    def test_weighted_overall_computes_average(self):
        """Given equal weights, overall is average of scores."""
        scores = {d.name: 0.8 for d in ScoringRubric.DIMENSIONS}
        overall = ScoringRubric.weighted_overall(scores)
        assert overall == pytest.approx(0.8, 0.01)

    def test_weighted_overall_with_uneven_weights(self):
        """Given uneven weights, overall is weighted average."""
        scores = {d.name: 0.0 for d in ScoringRubric.DIMENSIONS}
        scores["confidence_score"] = 1.0
        # All weights are 1.0, so overall = 1.0 / 5 = 0.2
        overall = ScoringRubric.weighted_overall(scores)
        assert overall == pytest.approx(0.2, 0.01)

    def test_format_rubric_includes_all_dimensions(self):
        """Given rubric format, all dimensions are present."""
        text = ScoringRubric.format_rubric()
        for dim in ScoringRubric.DIMENSIONS:
            assert dim.name in text
            assert dim.description in text


class TestPromptBuilder:
    """Tests for prompt builder."""

    def test_build_includes_report(self):
        """Given report, prompt includes it."""
        builder = PromptBuilder()
        prompt = builder.build("This is a test report.", [])
        assert "This is a test report." in prompt

    def test_build_includes_sources(self):
        """Given sources, prompt includes them."""
        builder = PromptBuilder()
        sources = [{"title": "Source A", "url": "https://a.com"}]
        prompt = builder.build("Report", sources)
        assert "Source A" in prompt
        assert "https://a.com" in prompt

    def test_build_includes_rubric(self):
        """Given rubric, prompt includes scoring criteria."""
        builder = PromptBuilder()
        prompt = builder.build("Report", [])
        assert "Scoring Rubric" in prompt
        assert "confidence_score" in prompt

    def test_build_truncates_long_report(self):
        """Given long report, prompt truncates it."""
        builder = PromptBuilder()
        long_report = "x" * 10000
        prompt = builder.build(long_report, [])
        assert "truncated" in prompt

    def test_build_limits_sources(self):
        """Given many sources, prompt limits to MAX_SOURCES."""
        builder = PromptBuilder()
        sources = [{"title": f"Source {i}", "url": f"https://{i}.com"} for i in range(50)]
        prompt = builder.build("Report", sources)
        # Should not contain all 50
        assert prompt.count("https://") <= 35  # Some tolerance

    def test_build_no_sources_shows_placeholder(self):
        """Given no sources, prompt shows placeholder."""
        builder = PromptBuilder()
        prompt = builder.build("Report", [])
        assert "No sources provided" in prompt


class TestQualityReport:
    """Tests for quality report data model."""

    def test_is_high_quality_true(self):
        """Given score >= 0.8, is_high_quality is True."""
        report = QualityReport(overall_score=0.85)
        assert report.is_high_quality is True

    def test_is_high_quality_false(self):
        """Given score < 0.8, is_high_quality is False."""
        report = QualityReport(overall_score=0.75)
        assert report.is_high_quality is False

    def test_is_acceptable_true(self):
        """Given score >= 0.6, is_acceptable is True."""
        report = QualityReport(overall_score=0.65)
        assert report.is_acceptable is True

    def test_is_acceptable_false(self):
        """Given score < 0.6, is_acceptable is False."""
        report = QualityReport(overall_score=0.55)
        assert report.is_acceptable is False

    def test_dimension_scores_returns_all(self):
        """Given report, dimension_scores returns all 5 dimensions."""
        report = QualityReport(
            confidence_score=0.8,
            citation_verification_rate=0.7,
            source_diversity_score=0.6,
            completeness_score=0.9,
            coherence_score=0.5,
        )
        scores = report.dimension_scores
        assert len(scores) == 5
        assert scores["confidence_score"] == 0.8
        assert scores["coherence_score"] == 0.5

    def test_from_raw_scores_valid(self):
        """Given valid scores, creates QualityReport."""
        scores = {d.name: 0.8 for d in ScoringRubric.DIMENSIONS}
        report = QualityReport.from_raw_scores(scores, suggestions=["Add more"])
        assert report.confidence_score == 0.8
        assert report.overall_score == pytest.approx(0.8, 0.01)
        assert report.improvement_suggestions == ["Add more"]

    def test_from_raw_scores_invalid_raises(self):
        """Given invalid scores, raises ValueError."""
        scores = {d.name: 0.8 for d in ScoringRubric.DIMENSIONS}
        scores["confidence_score"] = 1.5
        with pytest.raises(ValueError, match="Invalid scores"):
            QualityReport.from_raw_scores(scores)

    def test_to_dict_serializes_all_fields(self):
        """Given report, to_dict includes all fields."""
        report = QualityReport(
            confidence_score=0.8,
            overall_score=0.8,
            improvement_suggestions=["Add more"],
            run_id="run-123",
        )
        data = report.to_dict()
        assert data["confidence_score"] == 0.8
        assert data["overall_score"] == 0.8
        assert data["improvement_suggestions"] == ["Add more"]
        assert data["is_high_quality"] is True
        assert data["is_acceptable"] is True


class TestInMemoryQualityStorage:
    """Tests for in-memory storage."""

    @pytest.mark.asyncio
    async def test_save_and_load_roundtrip(self):
        """Given saved report, load returns it."""
        storage = InMemoryQualityStorage()
        report = QualityReport(run_id="run-123", overall_score=0.9)
        await storage.save(report)
        loaded = await storage.load("run-123")
        assert loaded is not None
        assert loaded.run_id == "run-123"
        assert loaded.overall_score == 0.9

    @pytest.mark.asyncio
    async def test_load_missing_returns_none(self):
        """Given missing run_id, load returns None."""
        storage = InMemoryQualityStorage()
        result = await storage.load("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_overwrites_existing(self):
        """Given save with same run_id, overwrites existing."""
        storage = InMemoryQualityStorage()
        await storage.save(QualityReport(run_id="run-123", overall_score=0.5))
        await storage.save(QualityReport(run_id="run-123", overall_score=0.9))
        loaded = await storage.load("run-123")
        assert loaded.overall_score == 0.9


class TestQualityReviewer:
    """Tests for quality reviewer with full integration."""

    @pytest.fixture
    def mock_llm(self):
        mock = AsyncMock()
        mock.call_structured.return_value = QualityReport(
            confidence_score=0.85,
            citation_verification_rate=0.9,
            source_diversity_score=0.75,
            completeness_score=0.8,
            coherence_score=0.9,
            improvement_suggestions=["Add more primary sources"],
            overall_score=0.84,
        )
        return mock

    @pytest.mark.asyncio
    async def test_review_returns_quality_report(self, mock_llm):
        """Given report, reviewer returns quality assessment."""
        reviewer = QualityReviewer(llm_provider=mock_llm)
        result = await reviewer.review("Test report", [])
        assert result.confidence_score == 0.85
        assert result.overall_score > 0.7

    @pytest.mark.asyncio
    async def test_review_uses_cache_on_second_call(self, mock_llm):
        """Given cached report, second call skips LLM."""
        storage = InMemoryQualityStorage()
        reviewer = QualityReviewer(llm_provider=mock_llm, storage=storage)
        result1 = await reviewer.review("Test report", [], run_id="run-123")
        assert mock_llm.call_structured.call_count == 1
        result2 = await reviewer.review("Test report", [], run_id="run-123")
        assert mock_llm.call_structured.call_count == 1  # Not called again
        assert result1.overall_score == result2.overall_score

    @pytest.mark.asyncio
    async def test_review_persists_to_storage(self, mock_llm):
        """Given run_id, review persists to storage."""
        storage = InMemoryQualityStorage()
        reviewer = QualityReviewer(llm_provider=mock_llm, storage=storage)
        await reviewer.review("Test report", [], run_id="run-123")
        loaded = await storage.load("run-123")
        assert loaded is not None
        assert loaded.run_id == "run-123"

    @pytest.mark.asyncio
    async def test_review_computes_overall_from_dimensions(self, mock_llm):
        """Given dimension scores, overall is computed from rubric."""
        # Override LLM to return zero overall, should be recomputed
        mock_llm.call_structured.return_value = QualityReport(
            confidence_score=1.0,
            citation_verification_rate=1.0,
            source_diversity_score=1.0,
            completeness_score=1.0,
            coherence_score=1.0,
            overall_score=0.0,  # Should be overridden
        )
        reviewer = QualityReviewer(llm_provider=mock_llm)
        result = await reviewer.review("Test", [])
        assert result.overall_score == pytest.approx(1.0, 0.01)

    @pytest.mark.asyncio
    async def test_analyze_source_diversity(self, mock_llm):
        """Given sources, analyze_source_diversity returns metrics."""
        reviewer = QualityReviewer(llm_provider=mock_llm)
        sources = [
            {"url": "https://arxiv.org/abs/123", "title": "Paper 1", "year": 2020},
            {"url": "https://nature.com/article/456", "title": "Paper 2", "year": 2021},
            {"url": "https://github.com/repo", "title": "Code"},
        ]
        result = await reviewer.analyze_source_diversity(sources)
        assert result["domain_count"] == 3
        assert result["source_count"] == 3
        assert result["temporal_range"]["min"] == 2020
        assert result["temporal_range"]["max"] == 2021

    def test_extract_citations_finds_dois(self, mock_llm):
        """Given report with DOIs, extract_citations finds them."""
        reviewer = QualityReviewer(llm_provider=mock_llm)
        report = "See doi:10.1234/example and 10.5678/other for details."
        result = reviewer._extract_citations(report)
        assert "10.1234/example" in result["dois"]

    def test_extract_citations_finds_inline(self, mock_llm):
        """Given report with inline citations, extract_citations finds them."""
        reviewer = QualityReviewer(llm_provider=mock_llm)
        report = "As shown by [Smith, 2020] and [Jones, 2021]."
        result = reviewer._extract_citations(report)
        assert any("Smith, 2020" in c for c in result["inline_citations"])

    @pytest.mark.asyncio
    async def test_review_with_empty_report(self, mock_llm):
        """Given empty report, still returns valid QualityReport."""
        reviewer = QualityReviewer(llm_provider=mock_llm)
        result = await reviewer.review("", [])
        assert result is not None
        assert hasattr(result, 'overall_score')

    @pytest.mark.asyncio
    async def test_review_with_no_sources(self, mock_llm):
        """Given no sources, still returns valid QualityReport."""
        reviewer = QualityReviewer(llm_provider=mock_llm)
        result = await reviewer.review("Report", [])
        assert result is not None

    @pytest.mark.asyncio
    async def test_review_prompt_includes_rubric(self, mock_llm):
        """Given review call, prompt includes rubric text."""
        reviewer = QualityReviewer(llm_provider=mock_llm)
        await reviewer.review("Test", [])
        call_kwargs = mock_llm.call_structured.call_args[1]
        prompt = call_kwargs.get('prompt', '')
        assert "Scoring Rubric" in prompt
        assert "confidence_score" in prompt
