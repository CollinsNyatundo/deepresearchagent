#!/usr/bin/env python3
"""Skill Registry: maps format + audience → ordered list of skills.

Skills are composable transformations that can be applied to a ResearchResult.
Each skill has an execute() method that takes a ResearchResult and returns a
modified ResearchResult.

Inspired by PM Skills Marketplace: skills are composable and reusable.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from research_engine.models import ResearchResult

logger = logging.getLogger(__name__)


class BaseSkill(ABC):
    """Base class for all research skills.

    Each skill transforms a ResearchResult in some way (e.g. adding structure,
    verifying citations, formatting bibliographies, etc.).
    """

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        category: str,
        formats: list[str],
        audiences: list[str],
        requires_config: dict[str, str] | None = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.category = category  # "academic", "business", "technical", "product", "data", "common"
        self.formats = formats
        self.audiences = audiences
        self.requires_config = requires_config or {}

    @abstractmethod
    def execute(self, result: ResearchResult, **kwargs: Any) -> ResearchResult:
        """Execute the skill on a ResearchResult.

        Args:
            result: The research result to transform.
            **kwargs: Additional context (e.g. citation_style, format options).

        Returns:
            The transformed ResearchResult.
        """
        ...

    def __repr__(self) -> str:
        return f"<Skill {self.id} ({self.category})>"


# ─── Common Skills ─────────────────────────────────────────────────────

class WebSearcherSkill(BaseSkill):
    """Skill: search the web for information."""

    def __init__(self):
        super().__init__(
            id="web_searcher",
            name="Web Searcher",
            description="Search the web using DuckDuckGo, Exa, or other providers",
            category="common",
            formats=["academic", "business", "technical", "product", "literature", "data"],
            audiences=["researcher", "executive", "cto", "pm", "founder", "ai_engineer", "dev", "architect", "analyst"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        # Web search is already done by the orchestrator; this skill is a no-op
        return result


class WebScraperSkill(BaseSkill):
    """Skill: scrape web pages for content."""

    def __init__(self):
        super().__init__(
            id="web_scraper",
            name="Web Scraper",
            description="Scrape web pages using Scrapling with tiered fallback",
            category="common",
            formats=["academic", "business", "technical", "product", "literature", "data"],
            audiences=["researcher", "executive", "cto", "pm", "founder", "ai_engineer", "dev", "architect", "analyst"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        # Scraping is already done by the orchestrator; this skill is a no-op
        return result


class SynthesizerSkill(BaseSkill):
    """Skill: synthesize research findings into coherent narratives."""

    def __init__(self):
        super().__init__(
            id="synthesizer",
            name="Synthesizer",
            description="Synthesize research findings into coherent narratives",
            category="common",
            formats=["academic", "business", "technical", "product", "literature", "data"],
            audiences=["researcher", "executive", "cto", "pm", "founder", "ai_engineer", "dev", "architect", "analyst"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        # Synthesis is already done by the orchestrator; this skill is a no-op
        return result


class FactCheckerSkill(BaseSkill):
    """Skill: verify factual claims against sources."""

    def __init__(self):
        super().__init__(
            id="fact_checker",
            name="Fact Checker",
            description="Verify factual claims against sources",
            category="common",
            formats=["academic", "business", "technical", "product", "literature", "data"],
            audiences=["researcher", "executive", "cto", "pm", "founder", "ai_engineer", "dev", "architect", "analyst"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        # Placeholder: will be implemented with actual fact-checking logic
        logger.info("FactChecker: verifying claims (placeholder)")
        return result


# ─── Academic Skills ───────────────────────────────────────────────────

class CitationVerifierSkill(BaseSkill):
    """Skill: verify citations against CrossRef, OpenAlex, Semantic Scholar, arXiv."""

    def __init__(self):
        super().__init__(
            id="citation_verifier",
            name="Citation Verifier",
            description="Verify citations against CrossRef, OpenAlex, Semantic Scholar, arXiv",
            category="academic",
            formats=["academic", "literature"],
            audiences=["researcher", "student", "reviewer"],
            requires_config={"crossref_api_key": "CROSSREF_API_KEY"},
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        # Placeholder: will verify citations against academic databases
        logger.info("CitationVerifier: verifying citations (placeholder)")
        return result


class PaperStructurerSkill(BaseSkill):
    """Skill: generate academic paper structure with chapters and sections."""

    def __init__(self):
        super().__init__(
            id="paper_structurer",
            name="Paper Structurer",
            description="Generate academic paper structure with chapters and sections",
            category="academic",
            formats=["academic", "literature"],
            audiences=["researcher", "student", "reviewer"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        # Apply academic structure based on length
        length = kwargs.get("length", "full")
        from research_engine.formats.pipelines import AcademicPaperPipeline
        pipeline = AcademicPaperPipeline()
        result.report = pipeline._structure_report(result, type('obj', (object,), {
            'length': length, 'options': kwargs.get('options', {})
        })())
        return result


class BibliographyFormatterSkill(BaseSkill):
    """Skill: format bibliographies in APA, MLA, Chicago, IEEE."""

    def __init__(self):
        super().__init__(
            id="bibliography_formatter",
            name="Bibliography Formatter",
            description="Format bibliographies in APA, MLA, Chicago, IEEE",
            category="academic",
            formats=["academic", "literature"],
            audiences=["researcher", "student", "reviewer"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        citation_style = kwargs.get("citation_style", "apa")
        from research_engine.formats.pipelines import AcademicPaperPipeline
        pipeline = AcademicPaperPipeline()
        result.report = pipeline._format_bibliography(
            result.report, result.citations, citation_style
        )
        return result


class PeerReviewSkill(BaseSkill):
    """Skill: simulate peer review with critical feedback."""

    def __init__(self):
        super().__init__(
            id="peer_review",
            name="Peer Review",
            description="Simulate peer review with critical feedback",
            category="academic",
            formats=["academic", "literature"],
            audiences=["researcher", "reviewer"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("PeerReview: generating review feedback (placeholder)")
        return result


class LaTeXExporterSkill(BaseSkill):
    """Skill: export to LaTeX format."""

    def __init__(self):
        super().__init__(
            id="latex_exporter",
            name="LaTeX Exporter",
            description="Export research to LaTeX format",
            category="academic",
            formats=["academic", "literature"],
            audiences=["researcher", "student", "reviewer"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("LaTeXExporter: exporting to LaTeX (placeholder)")
        return result


# ─── Business Skills ───────────────────────────────────────────────────

class SWOTAnalyzerSkill(BaseSkill):
    """Skill: generate SWOT analysis with actionable recommendations."""

    def __init__(self):
        super().__init__(
            id="swot_analyzer",
            name="SWOT Analyzer",
            description="Generate SWOT analysis with actionable recommendations",
            category="business",
            formats=["business"],
            audiences=["executive", "investor", "founder", "board"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("SWOTAnalyzer: generating SWOT analysis (placeholder)")
        return result


class PESTLEAnalyzerSkill(BaseSkill):
    """Skill: analyze macro environment across PESTLE factors."""

    def __init__(self):
        super().__init__(
            id="pestle_analyzer",
            name="PESTLE Analyzer",
            description="Analyze macro environment across Political, Economic, Social, Technological, Legal, Environmental factors",
            category="business",
            formats=["business"],
            audiences=["executive", "investor", "founder", "board"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("PESTLEAnalyzer: generating PESTLE analysis (placeholder)")
        return result


class MarketSizerSkill(BaseSkill):
    """Skill: calculate TAM, SAM, SOM with top-down and bottom-up approaches."""

    def __init__(self):
        super().__init__(
            id="market_sizer",
            name="Market Sizer",
            description="Calculate TAM, SAM, SOM with top-down and bottom-up approaches",
            category="business",
            formats=["business"],
            audiences=["executive", "investor", "founder", "board"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("MarketSizer: calculating market size (placeholder)")
        return result


class CompetitorProfilerSkill(BaseSkill):
    """Skill: analyze competitor strengths, weaknesses, and differentiation."""

    def __init__(self):
        super().__init__(
            id="competitor_profiler",
            name="Competitor Profiler",
            description="Analyze competitor strengths, weaknesses, and differentiation opportunities",
            category="business",
            formats=["business"],
            audiences=["executive", "investor", "founder", "board"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("CompetitorProfiler: analyzing competitors (placeholder)")
        return result


class FinancialModelerSkill(BaseSkill):
    """Skill: financial modeling with DCF, WACC, ROI calculations."""

    def __init__(self):
        super().__init__(
            id="financial_modeler",
            name="Financial Modeler",
            description="Financial modeling with DCF, WACC, ROI calculations",
            category="business",
            formats=["business"],
            audiences=["executive", "investor", "founder", "board"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("FinancialModeler: building financial model (placeholder)")
        return result


# ─── Technical Skills ──────────────────────────────────────────────────

class HLDGeneratorSkill(BaseSkill):
    """Skill: generate high-level design documents with architecture diagrams."""

    def __init__(self):
        super().__init__(
            id="hld_generator",
            name="HLD Generator",
            description="Generate high-level design documents with architecture diagrams",
            category="technical",
            formats=["technical"],
            audiences=["cto", "ai_engineer", "dev", "architect"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("HLDGenerator: generating HLD (placeholder)")
        return result


class DLDGeneratorSkill(BaseSkill):
    """Skill: generate detailed-level design documents."""

    def __init__(self):
        super().__init__(
            id="dld_generator",
            name="DLD Generator",
            description="Generate detailed-level design documents",
            category="technical",
            formats=["technical"],
            audiences=["cto", "ai_engineer", "dev", "architect"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("DLDGenerator: generating DLD (placeholder)")
        return result


class RiskRegisterSkill(BaseSkill):
    """Skill: create comprehensive risk registers following HM Treasury Orange Book."""

    def __init__(self):
        super().__init__(
            id="risk_register",
            name="Risk Register",
            description="Create comprehensive risk registers following HM Treasury Orange Book",
            category="technical",
            formats=["technical"],
            audiences=["cto", "ai_engineer", "dev", "architect"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("RiskRegister: creating risk register (placeholder)")
        return result


class SecurityReviewSkill(BaseSkill):
    """Skill: conduct security reviews aligned with NCSC CAF and Cyber Essentials."""

    def __init__(self):
        super().__init__(
            id="security_review",
            name="Security Review",
            description="Conduct security reviews aligned with NCSC CAF and Cyber Essentials",
            category="technical",
            formats=["technical"],
            audiences=["cto", "ai_engineer", "dev", "architect"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("SecurityReview: conducting security review (placeholder)")
        return result


class WardleyMapperSkill(BaseSkill):
    """Skill: generate Wardley Maps for strategic planning."""

    def __init__(self):
        super().__init__(
            id="wardley_mapper",
            name="Wardley Mapper",
            description="Generate Wardley Maps for strategic planning",
            category="technical",
            formats=["technical"],
            audiences=["cto", "ai_engineer", "dev", "architect"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("WardleyMapper: generating Wardley map (placeholder)")
        return result


class DataModelerSkill(BaseSkill):
    """Skill: generate data models with ERD and GDPR compliance."""

    def __init__(self):
        super().__init__(
            id="data_modeler",
            name="Data Modeler",
            description="Generate data models with ERD and GDPR compliance",
            category="technical",
            formats=["technical"],
            audiences=["cto", "ai_engineer", "dev", "architect"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("DataModeler: generating data model (placeholder)")
        return result


# ─── Product Skills ────────────────────────────────────────────────────

class OpportunitySolutionTreeSkill(BaseSkill):
    """Skill: build Opportunity Solution Trees (Teresa Torres)."""

    def __init__(self):
        super().__init__(
            id="opportunity_solution_tree",
            name="Opportunity Solution Tree",
            description="Build Opportunity Solution Trees (Teresa Torres)",
            category="product",
            formats=["product"],
            audiences=["pm", "founder", "growth"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("OpportunitySolutionTree: building OST (placeholder)")
        return result


class AssumptionMapperSkill(BaseSkill):
    """Skill: identify and prioritize risky assumptions across Value, Usability, Viability, Feasibility."""

    def __init__(self):
        super().__init__(
            id="assumption_mapper",
            name="Assumption Mapper",
            description="Identify and prioritize risky assumptions across Value, Usability, Viability, Feasibility",
            category="product",
            formats=["product"],
            audiences=["pm", "founder", "growth"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("AssumptionMapper: mapping assumptions (placeholder)")
        return result


class ExperimentDesignerSkill(BaseSkill):
    """Skill: design experiments to validate assumptions."""

    def __init__(self):
        super().__init__(
            id="experiment_designer",
            name="Experiment Designer",
            description="Design experiments to validate assumptions",
            category="product",
            formats=["product"],
            audiences=["pm", "founder", "growth"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("ExperimentDesigner: designing experiments (placeholder)")
        return result


class PRDWriterSkill(BaseSkill):
    """Skill: write comprehensive product requirement documents (Cagan-style)."""

    def __init__(self):
        super().__init__(
            id="prd_writer",
            name="PRD Writer",
            description="Write comprehensive product requirement documents (Cagan-style)",
            category="product",
            formats=["product"],
            audiences=["pm", "founder", "growth"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("PRDWriter: writing PRD (placeholder)")
        return result


class OKRPlannerSkill(BaseSkill):
    """Skill: plan OKRs with measurable key results."""

    def __init__(self):
        super().__init__(
            id="okr_planner",
            name="OKR Planner",
            description="Plan OKRs with measurable key results",
            category="product",
            formats=["product"],
            audiences=["pm", "founder", "growth"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("OKRPlanner: planning OKRs (placeholder)")
        return result


class StakeholderAnalyzerSkill(BaseSkill):
    """Skill: analyze stakeholder influence and interest."""

    def __init__(self):
        super().__init__(
            id="stakeholder_analyzer",
            name="Stakeholder Analyzer",
            description="Analyze stakeholder influence and interest",
            category="product",
            formats=["product"],
            audiences=["pm", "founder", "growth"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("StakeholderAnalyzer: analyzing stakeholders (placeholder)")
        return result


class RoadmapGeneratorSkill(BaseSkill):
    """Skill: generate product roadmaps with milestones."""

    def __init__(self):
        super().__init__(
            id="roadmap_generator",
            name="Roadmap Generator",
            description="Generate product roadmaps with milestones",
            category="product",
            formats=["product"],
            audiences=["pm", "founder", "growth"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("RoadmapGenerator: generating roadmap (placeholder)")
        return result


class MetricsDesignerSkill(BaseSkill):
    """Skill: design North Star and input metrics."""

    def __init__(self):
        super().__init__(
            id="metrics_designer",
            name="Metrics Designer",
            description="Design North Star and input metrics",
            category="product",
            formats=["product"],
            audiences=["pm", "founder", "growth"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("MetricsDesigner: designing metrics (placeholder)")
        return result


# ─── Data Skills ─────────────────────────────────────────────────────────

class SQLGeneratorSkill(BaseSkill):
    """Skill: generate SQL queries for data analysis."""

    def __init__(self):
        super().__init__(
            id="sql_generator",
            name="SQL Generator",
            description="Generate SQL queries for data analysis",
            category="data",
            formats=["data"],
            audiences=["analyst", "data_scientist", "pm"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("SQLGenerator: generating SQL (placeholder)")
        return result


class CohortAnalyzerSkill(BaseSkill):
    """Skill: perform cohort analysis."""

    def __init__(self):
        super().__init__(
            id="cohort_analyzer",
            name="Cohort Analyzer",
            description="Perform cohort analysis",
            category="data",
            formats=["data"],
            audiences=["analyst", "data_scientist", "pm"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("CohortAnalyzer: performing cohort analysis (placeholder)")
        return result


class ABTestAnalyzerSkill(BaseSkill):
    """Skill: analyze A/B test results."""

    def __init__(self):
        super().__init__(
            id="ab_test_analyzer",
            name="A/B Test Analyzer",
            description="Analyze A/B test results with statistical significance",
            category="data",
            formats=["data"],
            audiences=["analyst", "data_scientist", "pm"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("ABTestAnalyzer: analyzing A/B test (placeholder)")
        return result


class VisualizationDesignerSkill(BaseSkill):
    """Skill: design data visualizations."""

    def __init__(self):
        super().__init__(
            id="visualization_designer",
            name="Visualization Designer",
            description="Design data visualizations and charts",
            category="data",
            formats=["data"],
            audiences=["analyst", "data_scientist", "pm"],
        )

    def execute(self, result: ResearchResult, **kwargs) -> ResearchResult:
        logger.info("VisualizationDesigner: designing visualizations (placeholder)")
        return result


# ─── Skill Registry ────────────────────────────────────────────────────

class SkillRegistry:
    """Registry of research skills with format + audience resolution.

    Usage:
        registry = SkillRegistry()
        skills = registry.resolve(format="academic", audience="researcher")
        for skill in skills:
            result = skill.execute(result, citation_style="apa")
    """

    # All built-in skills
    _ALL_SKILLS: list[BaseSkill] = [
        # Common
        WebSearcherSkill(),
        WebScraperSkill(),
        SynthesizerSkill(),
        FactCheckerSkill(),
        # Academic
        CitationVerifierSkill(),
        PaperStructurerSkill(),
        BibliographyFormatterSkill(),
        PeerReviewSkill(),
        LaTeXExporterSkill(),
        # Business
        SWOTAnalyzerSkill(),
        PESTLEAnalyzerSkill(),
        MarketSizerSkill(),
        CompetitorProfilerSkill(),
        FinancialModelerSkill(),
        # Technical
        HLDGeneratorSkill(),
        DLDGeneratorSkill(),
        RiskRegisterSkill(),
        SecurityReviewSkill(),
        WardleyMapperSkill(),
        DataModelerSkill(),
        # Product
        OpportunitySolutionTreeSkill(),
        AssumptionMapperSkill(),
        ExperimentDesignerSkill(),
        PRDWriterSkill(),
        OKRPlannerSkill(),
        StakeholderAnalyzerSkill(),
        RoadmapGeneratorSkill(),
        MetricsDesignerSkill(),
        # Data
        SQLGeneratorSkill(),
        CohortAnalyzerSkill(),
        ABTestAnalyzerSkill(),
        VisualizationDesignerSkill(),
    ]

    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}
        for skill in self._ALL_SKILLS:
            self._skills[skill.id] = skill

    def register(self, skill: BaseSkill) -> None:
        """Register a new skill."""
        self._skills[skill.id] = skill
        logger.info(f"Registered skill: {skill.id}")

    def resolve(self, format: str, audience: str) -> list[BaseSkill]:
        """Resolve format + audience to an ordered list of skills.

        Returns common skills first, then format-specific skills,
        then audience-specific skills.

        Args:
            format: Output format ID.
            audience: Target audience ID.

        Returns:
            Ordered list of skills for execution.
        """
        # Common skills (always included)
        common = [s for s in self._skills.values() if s.category == "common"]

        # Format-specific skills
        format_specific = [
            s for s in self._skills.values()
            if s.category != "common" and format in s.formats
        ]

        # Audience-specific skills (subset of format-specific)
        audience_specific = [
            s for s in format_specific
            if audience in s.audiences
        ]

        # Order: common first, then audience-specific
        # Within each group, order by category priority
        category_order = {"common": 0, "academic": 1, "business": 2, "technical": 3, "product": 4, "data": 5}
        result = common + audience_specific
        result.sort(key=lambda s: category_order.get(s.category, 99))

        if not result:
            logger.warning(f"No skills found for {format}/{audience}, returning common skills only")
            return common

        logger.debug(f"Resolved {len(result)} skills for {format}/{audience}")
        return result

    def list_skills(self) -> list[BaseSkill]:
        """Return all registered skills."""
        return list(self._skills.values())

    def get_skill(self, skill_id: str) -> BaseSkill | None:
        """Get a skill by ID."""
        return self._skills.get(skill_id)

    def list_skills_by_category(self, category: str) -> list[BaseSkill]:
        """Return all skills in a category."""
        return [s for s in self._skills.values() if s.category == category]

    def list_skills_by_format(self, format: str) -> list[BaseSkill]:
        """Return all skills applicable to a format."""
        return [s for s in self._skills.values() if format in s.formats]


# Alias for convenience
Skill = BaseSkill
