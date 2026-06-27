"""Format Registry: maps format + audience + length → pipeline.

Central dispatcher for research output formats. Each format has its own
pipeline with specialized skills, prompts, and export strategies.
"""

from __future__ import annotations

import logging
from typing import Type

from research_engine.formats.pipelines import (
    AcademicPaperPipeline,
    BusinessReportPipeline,
    DataBriefPipeline,
    FormatPipeline,
    LiteratureReviewPipeline,
    ProductResearchPipeline,
    TechnicalSpecPipeline,
)

logger = logging.getLogger(__name__)


class FormatRegistry:
    """Registry of research output formats and their pipelines.

    Usage:
        registry = FormatRegistry()
        pipeline = registry.resolve(format="academic", audience="researcher", length="full")
        result = await pipeline.run(request)
    """

    # Format ID → Pipeline class mapping
    _FORMATS: dict[str, Type[FormatPipeline]] = {
        "academic": AcademicPaperPipeline,
        "business": BusinessReportPipeline,
        "technical": TechnicalSpecPipeline,
        "product": ProductResearchPipeline,
        "literature": LiteratureReviewPipeline,
        "data": DataBriefPipeline,
    }

    # Format metadata for UI/API consumption
    _FORMAT_METADATA: dict[str, dict] = {
        "academic": {
            "name": "Academic Paper",
            "description": "Source-grounded research with verified citations. Export to PDF, DOCX, or LaTeX.",
            "icon": "graduation-cap",
            "lengths": ["abstract", "short", "full", "thesis"],
            "audiences": ["researcher", "student", "reviewer"],
            "word_counts": {"abstract": (500, 500), "short": (2000, 5000), "full": (10000, 20000), "thesis": (50000, 80000)},
        },
        "business": {
            "name": "Business Report",
            "description": "Strategic analysis with market sizing, competitive landscape, and financial modeling.",
            "icon": "briefcase",
            "lengths": ["executive_summary", "briefing", "deep_dive"],
            "audiences": ["executive", "investor", "founder", "board"],
            "word_counts": {"executive_summary": (500, 1000), "briefing": (2000, 5000), "deep_dive": (15000, 30000)},
        },
        "technical": {
            "name": "Technical Specification",
            "description": "Architecture decisions, RFCs, HLD/DLD, security reviews, and design documents.",
            "icon": "cpu",
            "lengths": ["rfc", "architecture_doc", "design_review"],
            "audiences": ["cto", "ai_engineer", "dev", "architect"],
            "word_counts": {"rfc": (5000, 10000), "architecture_doc": (10000, 20000), "design_review": (20000, 40000)},
        },
        "product": {
            "name": "Product Research",
            "description": "Discovery, strategy, and execution planning with OST, JTBD, and assumption mapping.",
            "icon": "lightbulb",
            "lengths": ["discovery", "strategy", "execution"],
            "audiences": ["pm", "founder", "growth"],
            "word_counts": {"discovery": (5000, 10000), "strategy": (10000, 20000), "execution": (10000, 20000)},
        },
        "literature": {
            "name": "Literature Review",
            "description": "Synthesis of existing research with citation clustering and gap analysis.",
            "icon": "book-open",
            "lengths": ["quick", "comprehensive", "systematic"],
            "audiences": ["researcher", "grad_student"],
            "word_counts": {"quick": (5000, 10000), "comprehensive": (20000, 40000), "systematic": (50000, 100000)},
        },
        "data": {
            "name": "Data Brief",
            "description": "Analysis of datasets, trends, and statistical findings with visualizations.",
            "icon": "bar-chart-3",
            "lengths": ["snapshot", "analysis", "report"],
            "audiences": ["analyst", "data_scientist", "pm"],
            "word_counts": {"snapshot": (1000, 3000), "analysis": (5000, 10000), "report": (15000, 30000)},
        },
    }

    def resolve(self, format: str, audience: str, length: str) -> FormatPipeline:
        """Resolve format + audience + length to a pipeline instance.

        Args:
            format: Output format ID (e.g. "academic", "business", "technical").
            audience: Target audience ID (e.g. "researcher", "executive", "cto").
            length: Output length ID (e.g. "full", "briefing", "architecture_doc").

        Returns:
            An instantiated FormatPipeline ready to run.

        Raises:
            ValueError: If format is unknown or length/audience not supported.
        """
        if format not in self._FORMATS:
            raise ValueError(f"Unknown format: '{format}'. Available: {list(self._FORMATS.keys())}")

        pipeline_class = self._FORMATS[format]
        pipeline = pipeline_class()

        # Validate length and audience are supported
        if length not in pipeline.supported_lengths:
            raise ValueError(
                f"Length '{length}' not supported for format '{format}'. "
                f"Supported: {pipeline.supported_lengths}"
            )
        if audience not in pipeline.supported_audiences:
            raise ValueError(
                f"Audience '{audience}' not supported for format '{format}'. "
                f"Supported: {pipeline.supported_audiences}"
            )

        logger.debug(f"Resolved: {format} + {audience} + {length} → {pipeline_class.__name__}")
        return pipeline

    def list_formats(self) -> list[str]:
        """Return all registered format IDs."""
        return list(self._FORMATS.keys())

    def format_info(self, format_id: str) -> dict:
        """Return metadata for a format (name, description, lengths, audiences, word counts).

        Args:
            format_id: Format ID string.

        Returns:
            Dict with format metadata for UI/API consumption.

        Raises:
            ValueError: If format_id is unknown.
        """
        if format_id not in self._FORMAT_METADATA:
            raise ValueError(f"Unknown format: '{format_id}'")
        return self._FORMAT_METADATA[format_id]

    def get_word_count_range(self, format_id: str, length_id: str) -> tuple[int, int]:
        """Return (min, max) word count for a format + length combination.

        Args:
            format_id: Format ID.
            length_id: Length ID.

        Returns:
            Tuple of (min_words, max_words).
        """
        meta = self.format_info(format_id)
        return meta["word_counts"].get(length_id, (5000, 10000))
