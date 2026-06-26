"""Quality review module — exhaustive implementation for research reports.

Architecture:
    QualityReviewer (public interface)
    ├── ScoringRubric (scoring criteria & validation)
    ├── PromptBuilder (prompt template construction)
    ├── QualityStorage (database persistence)
    └── QualityReport (result data model)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol


# ─── Scoring Rubric ──────────────────────────────────────────────────

@dataclass(frozen=True)
class Dimension:
    """A scoring dimension with criteria and weight."""
    name: str
    description: str
    weight: float = 1.0
    criteria: list[str] = field(default_factory=list)


class ScoringRubric:
    """Comprehensive rubric for research report quality assessment.

    Five dimensions, each scored 0-1, weighted equally by default.
    """

    DIMENSIONS: list[Dimension] = [
        Dimension(
            name="confidence_score",
            description="How confident is the report in its claims?",
            weight=1.0,
            criteria=[
                "Claims are supported by evidence",
                "Hedging language is appropriate (not overconfident)",
                "Uncertainties are acknowledged",
                "No unsupported assertions",
            ],
        ),
        Dimension(
            name="citation_verification_rate",
            description="What percentage of citations are verifiable?",
            weight=1.0,
            criteria=[
                "Citations include DOIs or URLs",
                "Author names and years are correct",
                "Sources are accessible (not paywalled/broken)",
                "Citation format is consistent",
            ],
        ),
        Dimension(
            name="source_diversity_score",
            description="How diverse are the sources?",
            weight=1.0,
            criteria=[
                "Multiple source types (academic, industry, government)",
                "Geographic diversity",
                "Temporal diversity (not all recent)",
                "Perspective diversity (not echo chamber)",
            ],
        ),
        Dimension(
            name="completeness_score",
            description="Does the report cover the topic comprehensively?",
            weight=1.0,
            criteria=[
                "Key subtopics are addressed",
                "Counter-arguments are presented",
                "Gaps in knowledge are acknowledged",
                "Sufficient depth for the scope",
            ],
        ),
        Dimension(
            name="coherence_score",
            description="Is the report well-structured and coherent?",
            weight=1.0,
            criteria=[
                "Clear logical flow between sections",
                "Transitions are smooth",
                "Introduction sets up conclusion",
                "Sections are appropriately sized",
            ],
        ),
    ]

    @classmethod
    def validate_scores(cls, scores: dict[str, float]) -> list[str]:
        """Validate scores against rubric. Returns list of errors."""
        errors = []
        dim_names = {d.name for d in cls.DIMENSIONS}
        for name in dim_names:
            if name not in scores:
                errors.append(f"Missing score for dimension: {name}")
            elif not 0.0 <= scores[name] <= 1.0:
                errors.append(f"Score for {name} out of range [0,1]: {scores[name]}")
        for name in scores:
            if name not in dim_names and name not in {"improvement_suggestions", "overall_score"}:
                errors.append(f"Unknown dimension: {name}")
        return errors

    @classmethod
    def weighted_overall(cls, scores: dict[str, float]) -> float:
        """Compute weighted overall score from dimension scores."""
        total_weight = sum(d.weight for d in cls.DIMENSIONS)
        weighted_sum = sum(
            scores.get(d.name, 0.0) * d.weight
            for d in cls.DIMENSIONS
        )
        return weighted_sum / total_weight if total_weight > 0 else 0.0

    @classmethod
    def format_rubric(cls) -> str:
        """Format rubric as markdown for prompt injection."""
        lines = ["## Scoring Rubric", ""]
        for dim in cls.DIMENSIONS:
            lines.append(f"### {dim.name} (weight: {dim.weight})")
            lines.append(f"{dim.description}")
            lines.append("")
            for criterion in dim.criteria:
                lines.append(f"- {criterion}")
            lines.append("")
        return "\n".join(lines)


# ─── Prompt Builder ────────────────────────────────────────────────

class PromptBuilder:
    """Builds quality assessment prompts with rubric injection."""

    TEMPLATE = """You are an expert research quality reviewer. Evaluate the following research report against the rubric below.

## Report to Evaluate

{report}

## Sources Used

{sources}

{rubric}

## Instructions

Score each dimension on a scale of 0.0 to 1.0 (1.0 = excellent).
Provide 3-5 specific, actionable improvement suggestions.

Respond with a JSON object matching this schema:
{{
    "confidence_score": float,
    "citation_verification_rate": float,
    "source_diversity_score": float,
    "completeness_score": float,
    "coherence_score": float,
    "improvement_suggestions": [string],
    "overall_score": float
}}
"""

    MAX_REPORT_LEN = 8000
    MAX_SOURCES = 30

    def __init__(self, rubric: ScoringRubric | None = None):
        self._rubric = rubric or ScoringRubric()

    def build(self, report: str, sources: list[dict]) -> str:
        """Build a quality assessment prompt."""
        truncated_report = report[:self.MAX_REPORT_LEN]
        if len(report) > self.MAX_REPORT_LEN:
            truncated_report += f"\n\n[...truncated from {len(report)} chars]"

        formatted_sources = self._format_sources(sources[:self.MAX_SOURCES])
        rubric_text = self._rubric.format_rubric()

        return self.TEMPLATE.format(
            report=truncated_report,
            sources=formatted_sources,
            rubric=rubric_text,
        )

    def _format_sources(self, sources: list[dict]) -> str:
        if not sources:
            return "*No sources provided*"
        lines = []
        for i, s in enumerate(sources, 1):
            title = s.get("title", "Untitled")
            url = s.get("url", "No URL")
            lines.append(f"{i}. {title} — {url}")
        return "\n".join(lines)


# ─── Quality Report ────────────────────────────────────────────────

@dataclass(frozen=True)
class QualityReport:
    """Quality assessment of a research report."""
    confidence_score: float = 0.0
    citation_verification_rate: float = 0.0
    source_diversity_score: float = 0.0
    completeness_score: float = 0.0
    coherence_score: float = 0.0
    improvement_suggestions: list[str] = field(default_factory=list)
    overall_score: float = 0.0
    run_id: str = ""
    created_at: str = ""

    def __post_init__(self):
        # Ensure suggestions is a list (frozen dataclass workaround)
        if not isinstance(self.improvement_suggestions, list):
            object.__setattr__(self, 'improvement_suggestions', list(self.improvement_suggestions) if self.improvement_suggestions else [])

    @property
    def is_high_quality(self) -> bool:
        """True if overall score >= 0.8."""
        return self.overall_score >= 0.8

    @property
    def is_acceptable(self) -> bool:
        """True if overall score >= 0.6."""
        return self.overall_score >= 0.6

    @property
    def dimension_scores(self) -> dict[str, float]:
        """Return all dimension scores as a dict."""
        return {
            "confidence_score": self.confidence_score,
            "citation_verification_rate": self.citation_verification_rate,
            "source_diversity_score": self.source_diversity_score,
            "completeness_score": self.completeness_score,
            "coherence_score": self.coherence_score,
        }

    @classmethod
    def from_raw_scores(
        cls,
        scores: dict[str, float],
        suggestions: list[str] | None = None,
        run_id: str = "",
    ) -> "QualityReport":
        """Create a QualityReport from raw scores, computing overall."""
        errors = ScoringRubric.validate_scores(scores)
        if errors:
            raise ValueError(f"Invalid scores: {errors}")

        overall = ScoringRubric.weighted_overall(scores)
        return cls(
            confidence_score=scores.get("confidence_score", 0.0),
            citation_verification_rate=scores.get("citation_verification_rate", 0.0),
            source_diversity_score=scores.get("source_diversity_score", 0.0),
            completeness_score=scores.get("completeness_score", 0.0),
            coherence_score=scores.get("coherence_score", 0.0),
            improvement_suggestions=suggestions or [],
            overall_score=overall,
            run_id=run_id,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for API response."""
        return {
            "confidence_score": self.confidence_score,
            "citation_verification_rate": self.citation_verification_rate,
            "source_diversity_score": self.source_diversity_score,
            "completeness_score": self.completeness_score,
            "coherence_score": self.coherence_score,
            "improvement_suggestions": self.improvement_suggestions,
            "overall_score": self.overall_score,
            "run_id": self.run_id,
            "is_high_quality": self.is_high_quality,
            "is_acceptable": self.is_acceptable,
        }


# ─── Quality Storage (Protocol) ────────────────────────────────────

class QualityStorage(Protocol):
    """Protocol for persisting quality reports."""

    async def save(self, report: QualityReport) -> dict:
        ...

    async def load(self, run_id: str) -> QualityReport | None:
        ...


class InMemoryQualityStorage:
    """In-memory storage for quality reports (testing)."""

    def __init__(self):
        self._store: dict[str, QualityReport] = {}

    async def save(self, report: QualityReport) -> dict:
        self._store[report.run_id] = report
        return {"run_id": report.run_id, "saved": True}

    async def load(self, run_id: str) -> QualityReport | None:
        return self._store.get(run_id)


# ─── Quality Reviewer ──────────────────────────────────────────────

class QualityReviewer:
    """Reviews research report quality using LLM assessment.

    Full implementation with:
    - ScoringRubric for structured evaluation
    - PromptBuilder for consistent prompts
    - QualityStorage for persistence
    - Citation verification integration
    - Source diversity analysis
    """

    def __init__(
        self,
        llm_provider,
        model: str = "default",
        rubric: ScoringRubric | None = None,
        prompt_builder: PromptBuilder | None = None,
        storage: QualityStorage | None = None,
    ):
        self._llm = llm_provider
        self._model = model
        self._rubric = rubric or ScoringRubric()
        self._prompt_builder = prompt_builder or PromptBuilder(self._rubric)
        self._storage = storage or InMemoryQualityStorage()

    async def review(
        self,
        report: str,
        sources: list[dict],
        run_id: str = "",
    ) -> QualityReport:
        """Review a research report and return quality assessment.

        Args:
            report: Markdown research report text
            sources: List of source dicts with 'title', 'url' keys
            run_id: Optional run ID for persistence

        Returns:
            QualityReport with scores and suggestions
        """
        # Check cache first
        if run_id:
            cached = await self._storage.load(run_id)
            if cached:
                return cached

        # Build prompt and call LLM
        prompt = self._prompt_builder.build(report, sources)
        raw_result = await self._llm.call_structured(
            prompt=prompt,
            schema=QualityReport,
            model=self._model,
        )

        # Convert to QualityReport with validation
        if isinstance(raw_result, QualityReport):
            result = raw_result
        else:
            # Handle dict-like results from LLM
            scores = {
                "confidence_score": getattr(raw_result, "confidence_score", 0.0),
                "citation_verification_rate": getattr(raw_result, "citation_verification_rate", 0.0),
                "source_diversity_score": getattr(raw_result, "source_diversity_score", 0.0),
                "completeness_score": getattr(raw_result, "completeness_score", 0.0),
                "coherence_score": getattr(raw_result, "coherence_score", 0.0),
            }
            suggestions = getattr(raw_result, "improvement_suggestions", [])
            result = QualityReport.from_raw_scores(scores, suggestions, run_id=run_id)

        # Override with computed overall score and set run_id
        overall = self._rubric.weighted_overall(result.dimension_scores)
        # Create new instance with correct run_id and overall (frozen dataclass)
        result = QualityReport(
            confidence_score=result.confidence_score,
            citation_verification_rate=result.citation_verification_rate,
            source_diversity_score=result.source_diversity_score,
            completeness_score=result.completeness_score,
            coherence_score=result.coherence_score,
            improvement_suggestions=result.improvement_suggestions,
            overall_score=overall,
            run_id=run_id,
        )

        # Persist
        if run_id:
            await self._storage.save(result)

        return result

    async def analyze_source_diversity(self, sources: list[dict]) -> dict[str, Any]:
        """Analyze source diversity metrics.

        Returns:
            Dict with domain_count, tld_distribution, temporal_range
        """
        from urllib.parse import urlparse

        domains = {}
        tlds = {}
        years = []

        for s in sources:
            url = s.get("url", "")
            if url:
                parsed = urlparse(url)
                domain = parsed.netloc
                domains[domain] = domains.get(domain, 0) + 1
                # Extract TLD
                parts = domain.split('.')
                if len(parts) > 1:
                    tld = parts[-1]
                    tlds[tld] = tlds.get(tld, 0) + 1

            year = s.get("year")
            if year:
                years.append(int(year))

        return {
            "domain_count": len(domains),
            "top_domains": sorted(domains.items(), key=lambda x: x[1], reverse=True)[:5],
            "tld_distribution": tlds,
            "temporal_range": {"min": min(years) if years else None, "max": max(years) if years else None},
            "source_count": len(sources),
        }

    def _extract_citations(self, report: str) -> list[str]:
        """Extract citation patterns from report text."""
        # DOI pattern
        doi_pattern = re.compile(r'10\.\d{4,}/[^\s]+')
        dois = doi_pattern.findall(report)

        # Inline citation pattern [Author, Year]
        inline_pattern = re.compile(r'\[([A-Z][a-zA-Z\s]+,\s*\d{4})\]')
        inline = inline_pattern.findall(report)

        return {"dois": dois, "inline_citations": inline}
