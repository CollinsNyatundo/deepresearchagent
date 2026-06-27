"""Research output format system.

Provides format-specific pipelines, skill registries, and export tools
for generating research in different formats, lengths, and for different audiences.
"""

from research_engine.formats.pipelines import (
    AcademicPaperPipeline,
    BusinessReportPipeline,
    DataBriefPipeline,
    FormatPipeline,
    LiteratureReviewPipeline,
    ProductResearchPipeline,
    TechnicalSpecPipeline,
)
from research_engine.formats.registry import FormatRegistry

__all__ = [
    "FormatRegistry",
    "FormatPipeline",
    "AcademicPaperPipeline",
    "BusinessReportPipeline",
    "TechnicalSpecPipeline",
    "ProductResearchPipeline",
    "LiteratureReviewPipeline",
    "DataBriefPipeline",
]