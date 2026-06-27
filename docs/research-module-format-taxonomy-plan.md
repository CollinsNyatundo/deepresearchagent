# Research Module Format & Audience Taxonomy — TDD Plan

> **Status:** Draft — awaiting user approval before implementation
> **Based on:** Analysis of OpenDraft, OpenPaper, ArcKit, and PM Skills
> **Method:** Test-Driven Development (vertical slices, one test → one implementation)

---

## 1. Problem Statement

The current DRA Research Module produces a single output type: a markdown research report with citations. Users cannot:
- Choose output formats (academic paper vs. business report vs. tech spec)
- Choose output lengths (brief vs. comprehensive)
- Choose target audiences (researchers vs. executives vs. engineers vs. PMs)
- Dynamically load specialized skills for their domain

**Goal:** Transform the Research Module into a multi-modal research orchestrator that surfaces format/audience/length choices, routes to the right agent pipeline, and dynamically loads specialized skills.

---

## 2. External System Analysis

### 2.1 OpenDraft / OpenPaper
- **19 specialized agents** in a pipeline: research → structure → write → cite → polish → export
- **Paper type taxonomy:** `research_paper`, `bachelor`, `master`, `phd` — each with different length/structure expectations
- **Length ranges:** 5-80 pages, 10k-20k+ words
- **Citation verification:** CrossRef, OpenAlex, Semantic Scholar, arXiv (every source verified)
- **Export:** PDF, DOCX, LaTeX with academic formatting
- **Key feature:** `paper_type` parameter drives the entire pipeline structure

### 2.2 ArcKit
- **75+ role-based commands** for enterprise architects across 13 jurisdictions
- **Plugin overlay system:** Core + jurisdiction (UK, EU, US, Canada, UAE) + sector (NHS, finance, energy)
- **Domain-specific commands:** `/arckit:requirements`, `/arckit:principles`, `/arckit:risk`, `/arckit:sobc`, `/arckit:ai-playbook`
- **Structured output:** Markdown with YAML frontmatter, traceability matrices, version control
- **Key insight:** Commands are organized by role + jurisdiction, not by generic task

### 2.3 PM Skills Marketplace
- **9 plugin domains** with 68 skills and 42 commands
- **Skill auto-discovery:** Skills load automatically when relevant to conversation
- **Command chaining:** `/discover` chains 4 skills (brainstorm → assumptions → prioritize → experiments)
- **Frameworks from thought leaders:** Cagan (INSPIRED), Torres (Continuous Discovery), Savoia (The Right It)
- **Key insight:** Skills are composable and reusable across commands

---

## 3. Proposed Architecture

### 3.1 Research Format Taxonomy

```
Research Output = Format × Length × Audience × Domain
```

| Format | Description | Length Options | Audience | Domain Skills |
|--------|-------------|----------------|----------|---------------|
| **Academic Paper** | Source-grounded research with verified citations | Abstract (500w), Short (2-5p), Full (10-20p), Thesis (50-80p) | Researchers, Students, Reviewers | Citation verification, peer review, LaTeX export |
| **Business Report** | Strategic analysis with ROI, market sizing, competitive landscape | Executive Summary (1p), Briefing (3-5p), Deep Dive (15-30p) | Executives, Investors, Founders, Board | SWOT, PESTLE, Porter's, financial modeling |
| **Technical Specification** | Architecture decisions, RFCs, design reviews | RFC (5-10p), Architecture Doc (10-20p), Design Review (20-40p) | CTOs, AI Engineers, Devs, Architects | HLD/DLD, data modeling, security review, Wardley mapping |
| **Product Research** | Discovery, strategy, execution planning | Discovery (5-10p), Strategy (10-20p), Execution Plan (10-20p) | PMs, Founders, Growth | OST, JTBD, assumption mapping, OKRs, PRDs |
| **Architecture Review** | Enterprise architecture governance | Principles (5p), HLD (10-20p), Full Review (30-50p) | CTOs, CIOs, Enterprise Architects | Risk register, requirements traceability, compliance |
| **Literature Review** | Synthesis of existing research on a topic | Quick (5-10p), Comprehensive (20-40p), Systematic (50-100p) | Researchers, Grad Students | Citation clustering, gap analysis, methodology comparison |
| **Data Brief** | Analysis of datasets, trends, statistical findings | Snapshot (1-3p), Analysis (5-10p), Report (15-30p) | Analysts, Data Scientists, PMs | Cohort analysis, A/B testing, SQL, visualization |

### 3.2 Skill Registry Architecture

```python
# research_engine/skills/registry.py

class SkillRegistry:
    """Dynamic skill registry loaded by format + audience + domain."""
    
    _skills: dict[str, Skill] = {}
    
    @classmethod
    def register(cls, name: str, skill: Skill) -> None:
        cls._skills[name] = skill
    
    @classmethod
    def resolve(cls, format: str, audience: str, domain: str | None = None) -> list[Skill]:
        """Return ordered list of skills for the given configuration."""
        ...
```

**Skill Categories:**

```
skills/
├── academic/           # From OpenDraft analysis
│   ├── citation_verifier.py    # CrossRef, OpenAlex, Semantic Scholar, arXiv
│   ├── paper_structurer.py     # Chapter/section outline per paper_type
│   ├── bibliography_formatter.py  # APA, MLA, Chicago, IEEE
│   ├── peer_review.py          # Critical review simulation
│   └── latex_exporter.py       # LaTeX/PDF generation
├── business/           # From business analysis frameworks
│   ├── swot_analyzer.py
│   ├── pestle_analyzer.py
│   ├── porters_five_forces.py
│   ├── market_sizer.py         # TAM/SAM/SOM
│   ├── financial_modeler.py    # DCF, WACC, ROI
│   └── competitor_profiler.py
├── technical/          # From ArcKit analysis
│   ├── architecture_principles.py
│   ├── hld_generator.py        # High-level design
│   ├── dld_generator.py        # Detailed-level design
│   ├── risk_register.py        # Orange Book / NIST
│   ├── data_modeler.py         # ERD, GDPR compliance
│   ├── security_review.py      # Secure by Design, NCSC
│   └── wardley_mapper.py       # Wardley Mapping
├── product/            # From PM Skills analysis
│   ├── opportunity_solution_tree.py  # Teresa Torres
│   ├── assumption_mapper.py
│   ├── experiment_designer.py
│   ├── prd_writer.py           # Cagan-style PRD
│   ├── okr_planner.py
│   ├── stakeholder_analyzer.py
│   ├── roadmap_generator.py
│   └── metrics_designer.py   # North Star + input metrics
├── data/               # Data analysis skills
│   ├── sql_generator.py
│   ├── cohort_analyzer.py
│   ├── ab_test_analyzer.py
│   └── visualization_designer.py
└── common/             # Shared across all formats
    ├── web_searcher.py         # Already exists
    ├── web_scraper.py          # Already exists
    ├── synthesizer.py          # Already exists
    └── fact_checker.py         # Already exists
```

### 3.3 Format-Aware Orchestrator Pipeline

```python
# research_engine/agent/format_pipelines.py

class FormatPipeline:
    """Base class for format-specific research pipelines."""
    
    format_name: str
    supported_lengths: list[str]
    supported_audiences: list[str]
    required_skills: list[str]
    
    async def run(self, request: ResearchRequest) -> ResearchResult:
        """Execute the format-specific pipeline."""
        ...

class AcademicPaperPipeline(FormatPipeline):
    format_name = "academic"
    supported_lengths = ["abstract", "short", "full", "thesis"]
    supported_audiences = ["researcher", "student", "reviewer"]
    required_skills = ["citation_verifier", "paper_structurer", "bibliography_formatter"]
    
    async def run(self, request):
        # 1. Research phase (existing web search + scrape)
        # 2. Citation verification (new: CrossRef/OpenAlex)
        # 3. Structure generation (chapters/sections per paper_type)
        # 4. Draft writing (academic tone per section)
        # 5. Bibliography formatting (APA/MLA/Chicago/IEEE)
        # 6. Export (PDF/DOCX/LaTeX)
        ...

class BusinessReportPipeline(FormatPipeline):
    format_name = "business"
    supported_lengths = ["executive_summary", "briefing", "deep_dive"]
    supported_audiences = ["executive", "investor", "founder", "board"]
    required_skills = ["swot_analyzer", "market_sizer", "competitor_profiler"]
    
    async def run(self, request):
        # 1. Research phase
        # 2. Market analysis (TAM/SAM/SOM, competitive landscape)
        # 3. Strategic analysis (SWOT, PESTLE, Porter's)
        # 4. Financial modeling (if applicable)
        # 5. Executive summary generation
        # 6. Export (PDF with business formatting)
        ...

class TechnicalSpecPipeline(FormatPipeline):
    format_name = "technical"
    supported_lengths = ["rfc", "architecture_doc", "design_review"]
    supported_audiences = ["cto", "ai_engineer", "dev", "architect"]
    required_skills = ["hld_generator", "risk_register", "security_review"]
    
    async def run(self, request):
        # 1. Research phase (tech docs, GitHub, papers)
        # 2. Architecture principles
        # 3. HLD/DLD generation
        # 4. Risk assessment
        # 5. Security review
        # 6. Export (Markdown with Mermaid diagrams)
        ...

class ProductResearchPipeline(FormatPipeline):
    format_name = "product"
    supported_lengths = ["discovery", "strategy", "execution"]
    supported_audiences = ["pm", "founder", "growth"]
    required_skills = ["opportunity_solution_tree", "assumption_mapper", "prd_writer"]
    
    async def run(self, request):
        # 1. Research phase (market, competitors, users)
        # 2. Opportunity Solution Tree
        # 3. Assumption mapping + prioritization
        # 4. Experiment design
        # 5. PRD/Strategy doc generation
        # 6. Export (Markdown with structured sections)
        ...
```

---

## 4. Database Schema Changes

### 4.1 New Tables

```sql
-- research_formats: Available output formats
CREATE TABLE research_formats (
    id TEXT PRIMARY KEY,  -- "academic", "business", "technical", "product"
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,  -- lucide icon name
    default_length TEXT,
    default_audience TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- research_lengths: Available lengths per format
CREATE TABLE research_lengths (
    id TEXT PRIMARY KEY,  -- "abstract", "short", "full", "thesis", etc.
    format_id TEXT REFERENCES research_formats(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    word_count_min INT,
    word_count_max INT,
    page_count_min INT,
    page_count_max INT,
    estimated_cycles INT DEFAULT 1,  -- how many research cycles needed
    created_at TIMESTAMPTZ DEFAULT now()
);

-- research_audiences: Target audiences
CREATE TABLE research_audiences (
    id TEXT PRIMARY KEY,  -- "researcher", "executive", "cto", "pm", etc.
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    personas TEXT[],  -- e.g. ["Founder", "Investor", "Board Member"]
    created_at TIMESTAMPTZ DEFAULT now()
);

-- research_skills: Available skills
CREATE TABLE research_skills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,  -- "academic", "business", "technical", "product", "data", "common"
    formats TEXT[],  -- which formats this skill applies to
    audiences TEXT[],  -- which audiences this skill applies to
    requires_config JSONB,  -- e.g. {"api_key": "CROSSREF_API_KEY"}
    is_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- research_format_skills: Many-to-many mapping
CREATE TABLE research_format_skills (
    format_id TEXT REFERENCES research_formats(id),
    skill_id TEXT REFERENCES research_skills(id),
    is_required BOOLEAN DEFAULT false,
    execution_order INT DEFAULT 0,
    PRIMARY KEY (format_id, skill_id)
);

-- research_runs format tracking (add to existing table)
ALTER TABLE research_runs
    ADD COLUMN format TEXT DEFAULT 'report',
    ADD COLUMN length TEXT DEFAULT 'full',
    ADD COLUMN audience TEXT DEFAULT 'general',
    ADD COLUMN skills_used TEXT[],
    ADD COLUMN export_format TEXT DEFAULT 'markdown';  -- markdown, pdf, docx, latex
```

---

## 5. Frontend Changes

### 5.1 New Components

```
frontend/src/components/research/
├── FormatSelector.tsx        # Cards for format selection (Academic, Business, Technical, Product)
├── LengthSelector.tsx        # Slider/cards for length selection
├── AudienceSelector.tsx      # Persona cards for audience selection
├── SkillIndicator.tsx        # Shows which skills are active for current selection
├── FormatPreview.tsx         # Preview of what the output will look like
├── AcademicPaperOptions.tsx  # Citation style, language, paper type (bachelor/master/phd)
├── BusinessReportOptions.tsx # Report type, financial modeling toggle
├── TechnicalSpecOptions.tsx  # Architecture type, diagram preferences
└── ProductResearchOptions.tsx # Framework selection (OST, JTBD, etc.)
```

### 5.2 UI Flow

```
1. User enters query
2. Format Selector appears (4 cards: Academic, Business, Technical, Product)
3. User selects format → Length Selector appears (format-specific options)
4. User selects length → Audience Selector appears (persona cards)
5. User selects audience → Skill Indicator shows active skills
6. Optional: Advanced Options (citation style, language, export format)
7. User clicks "Research" → pipeline executes with selected configuration
8. Progress shows format-specific phases (e.g., "Verifying citations..." for academic)
9. Final output is formatted according to selected format/audience
```

---

## 6. API Changes

### 6.1 Updated ResearchRequest Model

```python
class ResearchRequest(BaseModel):
    # ... existing fields ...
    
    # NEW: Format selection
    format: str = "report"  # "academic", "business", "technical", "product", "literature", "data"
    length: str = "full"    # format-specific: e.g. "abstract", "short", "full", "thesis"
    audience: str = "general"  # "researcher", "executive", "cto", "pm", "founder", "ai_engineer"
    
    # NEW: Format-specific options
    options: dict[str, Any] = Field(default_factory=dict)
    # e.g. for academic: {"citation_style": "apa", "paper_type": "research_paper", "language": "en"}
    # e.g. for business: {"include_financial_model": True, "competitor_count": 5}
    # e.g. for technical: {"architecture_type": "hld", "include_diagrams": True}
    # e.g. for product: {"framework": "ost", "include_okrs": True}
    
    # NEW: Export
    export_format: str = "markdown"  # "markdown", "pdf", "docx", "latex"
    
    # NEW: Skill override
    skills: list[str] | None = None  # Override auto-resolved skills
```

### 6.2 New Endpoints

```python
GET  /research/formats              # List available formats
GET  /research/formats/{id}/lengths  # Length options for format
GET  /research/formats/{id}/audiences  # Audience options for format
GET  /research/skills               # List all available skills
GET  /research/skills/resolve       # Resolve skills for format+audience
```

---

## 7. TDD Implementation Plan (Vertical Slices)

### Slice 1: Format Registry (Tracer Bullet)

**RED:** Test that `FormatRegistry.resolve("academic", "researcher")` returns `AcademicPaperPipeline`
**GREEN:** Implement `FormatRegistry` with basic format mapping
**Test:** `tests/research/test_format_registry.py`

### Slice 2: Academic Paper Pipeline

**RED:** Test that `AcademicPaperPipeline.run()` produces output with verified citations
**GREEN:** Implement academic pipeline with citation verification
**Test:** `tests/research/test_academic_pipeline.py`

### Slice 3: Skill Registry

**RED:** Test that `SkillRegistry.resolve("academic", "researcher")` returns citation skills
**GREEN:** Implement skill registry with lazy loading
**Test:** `tests/research/test_skill_registry.py`

### Slice 4: Business Report Pipeline

**RED:** Test that `BusinessReportPipeline.run()` produces SWOT + market analysis
**GREEN:** Implement business pipeline with business skills
**Test:** `tests/research/test_business_pipeline.py`

### Slice 5: Frontend Format Selector

**RED:** Test that `FormatSelector` renders 4 format cards
**GREEN:** Implement React component with Tailwind + liquid-glass
**Test:** `frontend/tests/FormatSelector.test.tsx`

### Slice 6: API Endpoints

**RED:** Test GET `/research/formats` returns format list
**GREEN:** Implement FastAPI routes
**Test:** `tests/api/test_research_formats.py`

### Slice 7: Database Schema

**RED:** Test that `research_runs` accepts format/length/audience columns
**GREEN:** Run migration
**Test:** `tests/db/test_research_runs_schema.py`

### Slice 8: Export Formats

**RED:** Test that academic export produces LaTeX
**GREEN:** Implement LaTeX exporter
**Test:** `tests/research/test_latex_export.py`

### Slice 9: Dynamic Skill Loading (ARC-Kit + PM Skills)

**RED:** Test that `arc_kit_principles` skill loads for CTO audience
**GREEN:** Implement dynamic skill loading from external repos
**Test:** `tests/research/test_dynamic_skills.py`

### Slice 10: Integration

**RED:** E2E test: user selects "academic" → "full" → "researcher" → gets academic paper with citations
**GREEN:** Wire everything together
**Test:** `tests/e2e/test_research_formats.py`

---

## 8. OpenRouter Key Update

Before proceeding with implementation, verify the updated OpenRouter key works:

```bash
py -c "from dotenv import load_dotenv; load_dotenv(); import os; print('Key:', os.environ.get('OPENROUTER_API_KEY','')[:20])"
```

Then run a quick test with a free OpenRouter model to confirm connectivity.

---

## 9. Decision Points for User

1. **Which formats to implement first?** I recommend: Academic → Business → Technical → Product (in that order)
2. **Which audiences to support first?** I recommend: Researcher, Executive, CTO, PM, Founder, AI Engineer
3. **Export priority?** Markdown (existing) → PDF → DOCX → LaTeX
4. **External skill loading?** Clone ARC-Kit/PM-Skills repos locally or fetch via GitHub API on demand?
5. **Citation verification?** Implement CrossRef/OpenAlex verification for academic papers?

---

## 10. Estimated Effort

| Slice | Description | Est. Time | Tests |
|-------|-------------|-----------|-------|
| 1 | Format Registry | 2h | 5 |
| 2 | Academic Pipeline | 4h | 8 |
| 3 | Skill Registry | 3h | 6 |
| 4 | Business Pipeline | 3h | 6 |
| 5 | Frontend Selector | 4h | 4 |
| 6 | API Endpoints | 2h | 5 |
| 7 | DB Schema | 1h | 3 |
| 8 | LaTeX Export | 3h | 4 |
| 9 | Dynamic Skills | 4h | 5 |
| 10 | E2E Integration | 3h | 3 |
| **Total** | | **29h** | **49** |

---

*Plan ready for review. Awaiting user approval before proceeding with Slice 1 (Tracer Bullet).*
