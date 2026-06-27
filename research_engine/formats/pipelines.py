"""Format-specific research pipelines.

Each pipeline implements a format-aware research orchestration strategy.
Pipelines are stateless and instantiated per-request.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from research_engine.models import ResearchRequest, ResearchResult

logger = logging.getLogger(__name__)


class FormatPipeline(ABC):
    """Base class for format-specific research pipelines.

    Each subclass implements the orchestration strategy for a specific
    output format (academic, business, technical, product, etc.).
    """

    format_name: str = ""
    supported_lengths: list[str] = []
    supported_audiences: list[str] = []
    required_skills: list[str] = []

    @abstractmethod
    async def run(self, request: ResearchRequest) -> ResearchResult:
        """Execute the format-specific pipeline.

        Args:
            request: The research request with format/audience/length selections.

        Returns:
            A ResearchResult with format-appropriate output.
        """
        ...

    def validate(self, request: ResearchRequest) -> None:
        """Validate that the request matches this pipeline's capabilities."""
        if request.length not in self.supported_lengths:
            raise ValueError(
                f"Length '{request.length}' not supported by {self.format_name}. "
                f"Supported: {self.supported_lengths}"
            )
        if request.audience not in self.supported_audiences:
            raise ValueError(
                f"Audience '{request.audience}' not supported by {self.format_name}. "
                f"Supported: {self.supported_audiences}"
            )


class AcademicPaperPipeline(FormatPipeline):
    """Pipeline for academic paper generation.

    Inspired by OpenDraft: 19-agent pipeline with citation verification.
    Phases: research → structure → write → cite → polish → export
    """

    format_name = "academic"
    supported_lengths = ["abstract", "short", "full", "thesis"]
    supported_audiences = ["researcher", "student", "reviewer"]
    required_skills = ["citation_verifier", "paper_structurer", "bibliography_formatter"]

    # Academic section structure per length
    _STRUCTURE_TEMPLATES: dict[str, list[str]] = {
        "abstract": ["Abstract", "Key Findings", "References"],
        "short": ["Abstract", "Introduction", "Methodology", "Results", "Discussion", "Conclusion", "References"],
        "full": ["Abstract", "Introduction", "Literature Review", "Methodology", "Results", "Discussion", "Conclusion", "References"],
        "thesis": ["Abstract", "Acknowledgements", "Introduction", "Literature Review", "Theoretical Framework", "Methodology", "Results", "Discussion", "Conclusion", "Future Work", "References", "Appendices"],
    }

    # Length guidance (words) per section
    _SECTION_WORD_COUNTS: dict[str, dict[str, int]] = {
        "abstract": {"Abstract": 500, "Key Findings": 300, "References": 200},
        "short": {"Abstract": 300, "Introduction": 800, "Methodology": 600, "Results": 800, "Discussion": 600, "Conclusion": 400, "References": 400},
        "full": {"Abstract": 500, "Introduction": 2000, "Literature Review": 3000, "Methodology": 2000, "Results": 3000, "Discussion": 2500, "Conclusion": 1000, "References": 1000},
        "thesis": {"Abstract": 500, "Acknowledgements": 300, "Introduction": 3000, "Literature Review": 5000, "Theoretical Framework": 3000, "Methodology": 3000, "Results": 5000, "Discussion": 4000, "Conclusion": 1500, "Future Work": 1000, "References": 2000, "Appendices": 2000},
    }

    async def run(self, request: ResearchRequest) -> ResearchResult:
        """Execute academic paper pipeline.

        1. Research phase (web search + scrape) via existing orchestrator
        2. Structure generation (chapters/sections per length)
        3. Draft writing (academic tone per section)
        4. Bibliography formatting (APA/MLA/Chicago/IEEE)
        """
        self.validate(request)
        logger.info(f"AcademicPaperPipeline: {request.length} paper for {request.audience}")

        from research_engine.agent.orchestrator import DeepResearchOrchestrator
        from research_engine.config import get_config

        # Step 1: Research phase using existing orchestrator
        config = get_config()
        # Adjust max_cycles based on length for academic papers
        length_cycles = {"abstract": 2, "short": 5, "full": 15, "thesis": 25}
        config.research.max_cycles = length_cycles.get(request.length, 10)

        orchestrator = DeepResearchOrchestrator(config)
        raw_result = await orchestrator.run(request)

        # Step 2: Apply academic structure
        structured_report = self._structure_report(raw_result, request)

        # Step 3: Format bibliography
        citation_style = request.options.get("citation_style", "apa") if request.options else "apa"
        formatted_report = self._format_bibliography(structured_report, raw_result.citations, citation_style)

        # Update result with academic formatting
        raw_result.report = formatted_report
        return raw_result

    def _structure_report(self, result: ResearchResult, request: ResearchRequest) -> str:
        """Apply academic structure to the research report."""
        sections = self._STRUCTURE_TEMPLATES.get(request.length, self._STRUCTURE_TEMPLATES["full"])
        word_counts = self._SECTION_WORD_COUNTS.get(request.length, self._SECTION_WORD_COUNTS["full"])

        report_parts = []
        for section in sections:
            target_words = word_counts.get(section, 1000)
            section_content = self._generate_section(section, result.report, target_words)
            report_parts.append(f"# {section}\n\n{section_content}\n")

        return "\n".join(report_parts)

    def _generate_section(self, section: str, raw_report: str, target_words: int) -> str:
        """Generate a specific academic section from the raw report."""
        # For now, use a simple extraction/placeholder approach
        # In production, this would call an LLM to rewrite the content
        # into the specific academic section with the target word count

        # Extract relevant sentences from the raw report
        sentences = raw_report.split(". ")
        section_sentences = []
        current_words = 0

        for sentence in sentences:
            words = len(sentence.split())
            if current_words + words > target_words:
                break
            section_sentences.append(sentence)
            current_words += words

        if not section_sentences:
            return f"[Section content to be generated for {section} — approximately {target_words} words]"

        return ". ".join(section_sentences) + "."

    def _format_bibliography(self, report: str, citations: list, style: str) -> str:
        """Format the bibliography section according to citation style."""
        if not citations:
            return report

        # Simple bibliography formatting
        # In production, this would use a proper citation formatter
        bib_entries = []
        for i, citation in enumerate(citations, 1):
            if style == "apa":
                entry = f"[{i}] Author. (Year). {citation.title}. Retrieved from {citation.url}"
            elif style == "mla":
                entry = f"[{i}] Author. \"{citation.title}.\" Web. {citation.url}"
            elif style == "chicago":
                entry = f"[{i}] Author, \"{citation.title},\" accessed {citation.accessed_at}, {citation.url}"
            elif style == "ieee":
                entry = f"[{i}] Author, \"{citation.title},\" Online. Available: {citation.url}"
            else:
                entry = f"[{i}] {citation.title}. {citation.url}"
            bib_entries.append(entry)

        bibliography = "\n".join(bib_entries)

        # Replace the References section
        if "# References" in report:
            parts = report.split("# References")
            return parts[0] + "# References\n\n" + bibliography + "\n"

        return report + "\n\n# References\n\n" + bibliography


class BusinessReportPipeline(FormatPipeline):
    """Pipeline for business report generation.

    Frameworks: SWOT, PESTLE, Porter's Five Forces, TAM/SAM/SOM, financial modeling.
    """

    format_name = "business"
    supported_lengths = ["executive_summary", "briefing", "deep_dive"]
    supported_audiences = ["executive", "investor", "founder", "board"]
    required_skills = ["swot_analyzer", "pestle_analyzer", "market_sizer", "competitor_profiler"]

    _STRUCTURE_TEMPLATES: dict[str, list[str]] = {
        "executive_summary": ["Executive Summary", "Key Findings", "Recommendations"],
        "briefing": ["Executive Summary", "Market Context", "SWOT Analysis", "Competitive Landscape", "Recommendations"],
        "deep_dive": ["Executive Summary", "Market Analysis", "SWOT Analysis", "PESTLE Analysis", "Competitive Landscape", "Financial Projections", "Risk Assessment", "Recommendations", "Appendices"],
    }

    _SECTION_WORD_COUNTS: dict[str, dict[str, int]] = {
        "executive_summary": {"Executive Summary": 500, "Key Findings": 300, "Recommendations": 200},
        "briefing": {"Executive Summary": 500, "Market Context": 800, "SWOT Analysis": 600, "Competitive Landscape": 600, "Recommendations": 500},
        "deep_dive": {"Executive Summary": 1000, "Market Analysis": 2000, "SWOT Analysis": 1500, "PESTLE Analysis": 1500, "Competitive Landscape": 2000, "Financial Projections": 1500, "Risk Assessment": 1000, "Recommendations": 1000, "Appendices": 1000},
    }

    async def run(self, request: ResearchRequest) -> ResearchResult:
        """Execute business report pipeline."""
        self.validate(request)
        logger.info(f"BusinessReportPipeline: {request.length} report for {request.audience}")

        from research_engine.agent.orchestrator import DeepResearchOrchestrator
        from research_engine.config import get_config

        config = get_config()
        length_cycles = {"executive_summary": 2, "briefing": 5, "deep_dive": 15}
        config.research.max_cycles = length_cycles.get(request.length, 10)

        orchestrator = DeepResearchOrchestrator(config)
        raw_result = await orchestrator.run(request)

        structured = self._structure_report(raw_result, request)
        raw_result.report = structured
        return raw_result

    def _structure_report(self, result: ResearchResult, request: ResearchRequest) -> str:
        """Apply business report structure."""
        sections = self._STRUCTURE_TEMPLATES.get(request.length, self._STRUCTURE_TEMPLATES["deep_dive"])
        word_counts = self._SECTION_WORD_COUNTS.get(request.length, self._SECTION_WORD_COUNTS["deep_dive"])
        report_parts = []
        for section in sections:
            target_words = word_counts.get(section, 1000)
            section_content = self._generate_section(section, result.report, target_words)
            report_parts.append(f"# {section}\n\n{section_content}\n")
        return "\n".join(report_parts)

    def _generate_section(self, section: str, raw_report: str, target_words: int) -> str:
        sentences = raw_report.split(". ")
        section_sentences = []
        current_words = 0
        for sentence in sentences:
            words = len(sentence.split())
            if current_words + words > target_words:
                break
            section_sentences.append(sentence)
            current_words += words
        if not section_sentences:
            return f"[Section content to be generated for {section} — approximately {target_words} words]"
        return ". ".join(section_sentences) + "."


class TechnicalSpecPipeline(FormatPipeline):
    """Pipeline for technical specification generation.

    Inspired by ArcKit: HLD/DLD, risk registers, security reviews, Wardley mapping.
    """

    format_name = "technical"
    supported_lengths = ["rfc", "architecture_doc", "design_review"]
    supported_audiences = ["cto", "ai_engineer", "dev", "architect"]
    required_skills = ["hld_generator", "risk_register", "security_review", "wardley_mapper"]

    _STRUCTURE_TEMPLATES: dict[str, list[str]] = {
        "rfc": ["Overview", "Problem Statement", "Proposed Solution", "Alternatives Considered", "Trade-offs", "Implementation Plan", "Appendices"],
        "architecture_doc": ["Overview", "Architecture Principles", "High-Level Design", "Detailed Design", "Data Model", "Risk Assessment", "Security Review", "Wardley Map", "Appendices"],
        "design_review": ["Overview", "Architecture Principles", "High-Level Design", "Detailed Design", "Risk Assessment", "Security Review", "Compliance Check", "Wardley Map", "Traceability Matrix", "Appendices"],
    }

    _SECTION_WORD_COUNTS: dict[str, dict[str, int]] = {
        "rfc": {"Overview": 500, "Problem Statement": 800, "Proposed Solution": 2000, "Alternatives Considered": 1000, "Trade-offs": 800, "Implementation Plan": 1000, "Appendices": 1000},
        "architecture_doc": {"Overview": 500, "Architecture Principles": 1000, "High-Level Design": 2000, "Detailed Design": 3000, "Data Model": 1500, "Risk Assessment": 1500, "Security Review": 1500, "Wardley Map": 1000, "Appendices": 1000},
        "design_review": {"Overview": 500, "Architecture Principles": 1000, "High-Level Design": 2000, "Detailed Design": 3000, "Risk Assessment": 1500, "Security Review": 1500, "Compliance Check": 1000, "Wardley Map": 1000, "Traceability Matrix": 1000, "Appendices": 1000},
    }

    async def run(self, request: ResearchRequest) -> ResearchResult:
        """Execute technical spec pipeline."""
        self.validate(request)
        logger.info(f"TechnicalSpecPipeline: {request.length} spec for {request.audience}")

        from research_engine.agent.orchestrator import DeepResearchOrchestrator
        from research_engine.config import get_config

        config = get_config()
        length_cycles = {"rfc": 5, "architecture_doc": 15, "design_review": 20}
        config.research.max_cycles = length_cycles.get(request.length, 10)

        orchestrator = DeepResearchOrchestrator(config)
        raw_result = await orchestrator.run(request)

        structured = self._structure_report(raw_result, request)
        raw_result.report = structured
        return raw_result

    def _structure_report(self, result: ResearchResult, request: ResearchRequest) -> str:
        """Apply technical spec structure."""
        sections = self._STRUCTURE_TEMPLATES.get(request.length, self._STRUCTURE_TEMPLATES["architecture_doc"])
        word_counts = self._SECTION_WORD_COUNTS.get(request.length, self._SECTION_WORD_COUNTS["architecture_doc"])
        report_parts = []
        for section in sections:
            target_words = word_counts.get(section, 1000)
            section_content = self._generate_section(section, result.report, target_words)
            report_parts.append(f"# {section}\n\n{section_content}\n")
        return "\n".join(report_parts)

    def _generate_section(self, section: str, raw_report: str, target_words: int) -> str:
        sentences = raw_report.split(". ")
        section_sentences = []
        current_words = 0
        for sentence in sentences:
            words = len(sentence.split())
            if current_words + words > target_words:
                break
            section_sentences.append(sentence)
            current_words += words
        if not section_sentences:
            return f"[Section content to be generated for {section} — approximately {target_words} words]"
        return ". ".join(section_sentences) + "."


class ProductResearchPipeline(FormatPipeline):
    """Pipeline for product research generation.

    Inspired by PM Skills: OST, JTBD, assumption mapping, PRDs, OKRs.
    """

    format_name = "product"
    supported_lengths = ["discovery", "strategy", "execution"]
    supported_audiences = ["pm", "founder", "growth"]
    required_skills = ["opportunity_solution_tree", "assumption_mapper", "prd_writer"]

    _STRUCTURE_TEMPLATES: dict[str, list[str]] = {
        "discovery": ["Discovery Summary", "Customer Research", "Opportunity Solution Tree", "Assumption Mapping", "Experiment Plan", "Next Steps"],
        "strategy": ["Discovery Summary", "Opportunity Solution Tree", "Assumption Mapping", "Experiment Plan", "Strategy Document", "OKRs", "Roadmap", "Next Steps"],
        "execution": ["Strategy Document", "OKRs", "PRD", "Execution Plan", "Metrics", "Risk Mitigation", "Next Steps"],
    }

    _SECTION_WORD_COUNTS: dict[str, dict[str, int]] = {
        "discovery": {"Discovery Summary": 500, "Customer Research": 1500, "Opportunity Solution Tree": 1500, "Assumption Mapping": 1000, "Experiment Plan": 1000, "Next Steps": 500},
        "strategy": {"Discovery Summary": 500, "Opportunity Solution Tree": 1500, "Assumption Mapping": 1000, "Experiment Plan": 1000, "Strategy Document": 2000, "OKRs": 1000, "Roadmap": 1000, "Next Steps": 500},
        "execution": {"Strategy Document": 1000, "OKRs": 1000, "PRD": 2000, "Execution Plan": 1500, "Metrics": 1000, "Risk Mitigation": 1000, "Next Steps": 500},
    }

    async def run(self, request: ResearchRequest) -> ResearchResult:
        """Execute product research pipeline."""
        self.validate(request)
        logger.info(f"ProductResearchPipeline: {request.length} research for {request.audience}")

        from research_engine.agent.orchestrator import DeepResearchOrchestrator
        from research_engine.config import get_config

        config = get_config()
        length_cycles = {"discovery": 5, "strategy": 10, "execution": 15}
        config.research.max_cycles = length_cycles.get(request.length, 10)

        orchestrator = DeepResearchOrchestrator(config)
        raw_result = await orchestrator.run(request)

        structured = self._structure_report(raw_result, request)
        raw_result.report = structured
        return raw_result

    def _structure_report(self, result: ResearchResult, request: ResearchRequest) -> str:
        """Apply product research structure."""
        sections = self._STRUCTURE_TEMPLATES.get(request.length, self._STRUCTURE_TEMPLATES["strategy"])
        word_counts = self._SECTION_WORD_COUNTS.get(request.length, self._SECTION_WORD_COUNTS["strategy"])
        report_parts = []
        for section in sections:
            target_words = word_counts.get(section, 1000)
            section_content = self._generate_section(section, result.report, target_words)
            report_parts.append(f"# {section}\n\n{section_content}\n")
        return "\n".join(report_parts)

    def _generate_section(self, section: str, raw_report: str, target_words: int) -> str:
        sentences = raw_report.split(". ")
        section_sentences = []
        current_words = 0
        for sentence in sentences:
            words = len(sentence.split())
            if current_words + words > target_words:
                break
            section_sentences.append(sentence)
            current_words += words
        if not section_sentences:
            return f"[Section content to be generated for {section} — approximately {target_words} words]"
        return ". ".join(section_sentences) + "."


class LiteratureReviewPipeline(FormatPipeline):
    """Pipeline for literature review generation.

    Synthesis of existing research with citation clustering and gap analysis.
    """

    format_name = "literature"
    supported_lengths = ["quick", "comprehensive", "systematic"]
    supported_audiences = ["researcher", "grad_student"]
    required_skills = ["citation_verifier", "citation_clusterer", "gap_analyzer"]

    _STRUCTURE_TEMPLATES: dict[str, list[str]] = {
        "quick": ["Abstract", "Introduction", "Key Themes", "Gaps", "Conclusion", "References"],
        "comprehensive": ["Abstract", "Introduction", "Methodology", "Thematic Analysis", "Critical Discussion", "Gaps", "Future Directions", "Conclusion", "References"],
        "systematic": ["Abstract", "Introduction", "Search Strategy", "Inclusion Criteria", "Thematic Analysis", "Critical Discussion", "Gaps", "Future Directions", "Conclusion", "References"],
    }

    _SECTION_WORD_COUNTS: dict[str, dict[str, int]] = {
        "quick": {"Abstract": 300, "Introduction": 1000, "Key Themes": 2000, "Gaps": 500, "Conclusion": 500, "References": 700},
        "comprehensive": {"Abstract": 500, "Introduction": 2000, "Methodology": 1500, "Thematic Analysis": 4000, "Critical Discussion": 2000, "Gaps": 1000, "Future Directions": 1000, "Conclusion": 1000, "References": 1500},
        "systematic": {"Abstract": 500, "Introduction": 2000, "Search Strategy": 1500, "Inclusion Criteria": 1000, "Thematic Analysis": 5000, "Critical Discussion": 3000, "Gaps": 1500, "Future Directions": 1500, "Conclusion": 1500, "References": 2000},
    }

    async def run(self, request: ResearchRequest) -> ResearchResult:
        """Execute literature review pipeline."""
        self.validate(request)
        logger.info(f"LiteratureReviewPipeline: {request.length} review for {request.audience}")

        from research_engine.agent.orchestrator import DeepResearchOrchestrator
        from research_engine.config import get_config

        config = get_config()
        length_cycles = {"quick": 5, "comprehensive": 15, "systematic": 25}
        config.research.max_cycles = length_cycles.get(request.length, 10)

        orchestrator = DeepResearchOrchestrator(config)
        raw_result = await orchestrator.run(request)

        structured = self._structure_report(raw_result, request)
        raw_result.report = structured
        return raw_result

    def _structure_report(self, result: ResearchResult, request: ResearchRequest) -> str:
        """Apply literature review structure."""
        sections = self._STRUCTURE_TEMPLATES.get(request.length, self._STRUCTURE_TEMPLATES["comprehensive"])
        word_counts = self._SECTION_WORD_COUNTS.get(request.length, self._SECTION_WORD_COUNTS["comprehensive"])
        report_parts = []
        for section in sections:
            target_words = word_counts.get(section, 1000)
            section_content = self._generate_section(section, result.report, target_words)
            report_parts.append(f"# {section}\n\n{section_content}\n")
        return "\n".join(report_parts)

    def _generate_section(self, section: str, raw_report: str, target_words: int) -> str:
        sentences = raw_report.split(". ")
        section_sentences = []
        current_words = 0
        for sentence in sentences:
            words = len(sentence.split())
            if current_words + words > target_words:
                break
            section_sentences.append(sentence)
            current_words += words
        if not section_sentences:
            return f"[Section content to be generated for {section} — approximately {target_words} words]"
        return ". ".join(section_sentences) + "."


class DataBriefPipeline(FormatPipeline):
    """Pipeline for data brief generation.

    Analysis of datasets, trends, statistical findings.
    """

    format_name = "data"
    supported_lengths = ["snapshot", "analysis", "report"]
    supported_audiences = ["analyst", "data_scientist", "pm"]
    required_skills = ["sql_generator", "cohort_analyzer", "ab_test_analyzer"]

    _STRUCTURE_TEMPLATES: dict[str, list[str]] = {
        "snapshot": ["Executive Summary", "Key Metrics", "Trends", "Recommendations"],
        "analysis": ["Executive Summary", "Data Overview", "Methodology", "Key Findings", "Visualizations", "Recommendations"],
        "report": ["Executive Summary", "Data Overview", "Methodology", "Key Findings", "Deep Dive", "Statistical Analysis", "Visualizations", "Recommendations", "Appendices"],
    }

    _SECTION_WORD_COUNTS: dict[str, dict[str, int]] = {
        "snapshot": {"Executive Summary": 300, "Key Metrics": 500, "Trends": 500, "Recommendations": 300},
        "analysis": {"Executive Summary": 500, "Data Overview": 800, "Methodology": 1000, "Key Findings": 2000, "Visualizations": 500, "Recommendations": 500},
        "report": {"Executive Summary": 1000, "Data Overview": 1500, "Methodology": 1500, "Key Findings": 3000, "Deep Dive": 2000, "Statistical Analysis": 1500, "Visualizations": 1000, "Recommendations": 1000, "Appendices": 1000},
    }

    async def run(self, request: ResearchRequest) -> ResearchResult:
        """Execute data brief pipeline."""
        self.validate(request)
        logger.info(f"DataBriefPipeline: {request.length} brief for {request.audience}")

        from research_engine.agent.orchestrator import DeepResearchOrchestrator
        from research_engine.config import get_config

        config = get_config()
        length_cycles = {"snapshot": 2, "analysis": 5, "report": 10}
        config.research.max_cycles = length_cycles.get(request.length, 5)

        orchestrator = DeepResearchOrchestrator(config)
        raw_result = await orchestrator.run(request)

        structured = self._structure_report(raw_result, request)
        raw_result.report = structured
        return raw_result

    def _structure_report(self, result: ResearchResult, request: ResearchRequest) -> str:
        """Apply data brief structure."""
        sections = self._STRUCTURE_TEMPLATES.get(request.length, self._STRUCTURE_TEMPLATES["analysis"])
        word_counts = self._SECTION_WORD_COUNTS.get(request.length, self._SECTION_WORD_COUNTS["analysis"])
        report_parts = []
        for section in sections:
            target_words = word_counts.get(section, 1000)
            section_content = self._generate_section(section, result.report, target_words)
            report_parts.append(f"# {section}\n\n{section_content}\n")
        return "\n".join(report_parts)

    def _generate_section(self, section: str, raw_report: str, target_words: int) -> str:
        sentences = raw_report.split(". ")
        section_sentences = []
        current_words = 0
        for sentence in sentences:
            words = len(sentence.split())
            if current_words + words > target_words:
                break
            section_sentences.append(sentence)
            current_words += words
        if not section_sentences:
            return f"[Section content to be generated for {section} — approximately {target_words} words]"
        return ". ".join(section_sentences) + "."
