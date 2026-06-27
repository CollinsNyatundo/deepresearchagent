"""Research skills system.

Provides composable, domain-specific skills that transform ResearchResults.
Skills are organized by category (academic, business, technical, product, data, common)
and resolved by format + audience.

Usage:
    from research_engine.skills import SkillRegistry
    registry = SkillRegistry()
    skills = registry.resolve(format="academic", audience="researcher")
    for skill in skills:
        result = skill.execute(result, citation_style="apa")
"""

from research_engine.skills.registry import (
    BaseSkill,
    SkillRegistry,
    Skill,
    # Common skills
    WebSearcherSkill,
    WebScraperSkill,
    SynthesizerSkill,
    FactCheckerSkill,
    # Academic skills
    CitationVerifierSkill,
    PaperStructurerSkill,
    BibliographyFormatterSkill,
    PeerReviewSkill,
    LaTeXExporterSkill,
    # Business skills
    SWOTAnalyzerSkill,
    PESTLEAnalyzerSkill,
    MarketSizerSkill,
    CompetitorProfilerSkill,
    FinancialModelerSkill,
    # Technical skills
    HLDGeneratorSkill,
    DLDGeneratorSkill,
    RiskRegisterSkill,
    SecurityReviewSkill,
    WardleyMapperSkill,
    DataModelerSkill,
    # Product skills
    OpportunitySolutionTreeSkill,
    AssumptionMapperSkill,
    ExperimentDesignerSkill,
    PRDWriterSkill,
    OKRPlannerSkill,
    StakeholderAnalyzerSkill,
    RoadmapGeneratorSkill,
    MetricsDesignerSkill,
    # Data skills
    SQLGeneratorSkill,
    CohortAnalyzerSkill,
    ABTestAnalyzerSkill,
    VisualizationDesignerSkill,
)

__all__ = [
    "BaseSkill",
    "SkillRegistry",
    "Skill",
    "WebSearcherSkill",
    "WebScraperSkill",
    "SynthesizerSkill",
    "FactCheckerSkill",
    "CitationVerifierSkill",
    "PaperStructurerSkill",
    "BibliographyFormatterSkill",
    "PeerReviewSkill",
    "LaTeXExporterSkill",
    "SWOTAnalyzerSkill",
    "PESTLEAnalyzerSkill",
    "MarketSizerSkill",
    "CompetitorProfilerSkill",
    "FinancialModelerSkill",
    "HLDGeneratorSkill",
    "DLDGeneratorSkill",
    "RiskRegisterSkill",
    "SecurityReviewSkill",
    "WardleyMapperSkill",
    "DataModelerSkill",
    "OpportunitySolutionTreeSkill",
    "AssumptionMapperSkill",
    "ExperimentDesignerSkill",
    "PRDWriterSkill",
    "OKRPlannerSkill",
    "StakeholderAnalyzerSkill",
    "RoadmapGeneratorSkill",
    "MetricsDesignerSkill",
    "SQLGeneratorSkill",
    "CohortAnalyzerSkill",
    "ABTestAnalyzerSkill",
    "VisualizationDesignerSkill",
]