# DRA Enhancement: Multi-Repo Capability Integration

> **Goal**: Integrate high-value capabilities from 5 researched repositories into DRA across 4 phases, transforming it from a web research tool into a comprehensive academic-grade research platform with citation verification, quality scoring, token optimization, and sandboxed experimentation.

## Source Repositories Analysis

| Repo | Key Extraction | System Benefits | Phase |
|------|---------------|-----------------|-------|
| [opendraft](https://github.com/federicodeponte/opendraft) | Citation verification pipeline (CrossRef/OpenAlex/Semantic Scholar/arXiv), draft versioning, Word/LaTeX export | Eliminates hallucinated references, tracks incremental draft revisions, and exports high-quality documents. | P0, P1, P2 |
| [academic-research-skills](https://github.com/Imbad0202/academic-research-skills) | Multi-perspective review agents (Devil's Advocate/QualityScorer), checkpoint/resume, Material Passports, repro_lock | Implements self-correcting logic checks, handles network interrupts resiliently, and maps every claim back to its exact source. | P0, P1, P2 |
| [AI-Researcher](https://github.com/HKUDS/AI-Researcher) | Hierarchical LaTeX composing (IHDS), Docker sandboxed execution, Scientist-Bench grading, matplotlib visualization | Automates section-by-section paper writing, compiles code/figures in real-time, and scores paper quality objectively. | P1, P3 |
| [headroom](https://github.com/chopratejas/headroom) | Token compression (Rust+Python hybrid), CacheAligner, SmartCrusher, CCR retrieval | Reduces OpenRouter LLM costs by up to 95% for long contexts and maximizes prompt caching hits. | P2 |
| [public-apis](https://github.com/public-apis/public-apis) | Curated non-auth developer, financial, security, and news APIs (HN Search, CoinGecko, SEC, etc.) | Provides zero-auth direct data layers to support diverse tech and startup factual research queries. | P2 |

---

## Phase 0 — Citation Verification + Review Agents

> **Impact**: Eliminates hallucinated citations, adds multi-perspective quality review  
> **Effort**: Medium (~2-3 weeks)

### Citation Verification Module

#### [NEW] [__init__.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/citations/__init__.py)
- Package init exporting `CitationVerifier`, `VerificationResult`, adapter classes

#### [NEW] [models.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/citations/models.py)
- `Citation` — parsed citation with title, authors, year, DOI, URL
- `VerificationResult` — status enum (verified/unverified/failed), source DB, confidence, metadata
- `VerificationReport` — aggregated results: verification_rate, source_diversity_score, flagged_citations

#### [NEW] [parser.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/citations/parser.py)
- Extract citations from synthesized markdown reports using regex + LLM fallback
- Handle inline citations `[Author, Year]`, numbered `[1]`, and footnote styles
- Return structured `list[Citation]`

#### [NEW] [adapters/crossref.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/citations/adapters/crossref.py)
- Async CrossRef API adapter (`https://api.crossref.org/works`)
- DOI resolution, title-based fuzzy search, metadata extraction
- Rate limiting (50 req/s with polite pool header)

#### [NEW] [adapters/openalex.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/citations/adapters/openalex.py)
- Async OpenAlex API adapter (`https://api.openalex.org/works`)
- Open scholarly metadata search, author disambiguation
- Free tier, no API key required (but polite pool email recommended)

#### [NEW] [adapters/semantic_scholar.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/citations/adapters/semantic_scholar.py)
- Async Semantic Scholar API adapter (`https://api.semanticscholar.org/graph/v1`)
- Paper search by title/DOI, citation graph traversal
- Dual-mode authentication: defaults to unauthenticated mode with rate limiting (100 req/5min) and graceful degradation for dev/local environments; supports optional `SEMANTIC_SCHOLAR_API_KEY` for production mode

#### [NEW] [adapters/arxiv.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/citations/adapters/arxiv.py)
- Async arXiv API adapter (`http://export.arxiv.org/api/query`)
- Preprint verification, arxiv ID resolution, category metadata
- Rate limit: 1 req/3s

#### [NEW] [verifier.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/citations/verifier.py)
- `CitationVerifier` orchestrator: runs all 4 adapters concurrently per citation
- Inline verification (quick check during synthesis — DOI/title match only)
- Post-synthesis deep verification (full metadata cross-reference)
- Scoring: verified ✅ (≥2 sources confirm), unverified ⚠️ (1 source), failed ❌ (0 sources)
- Returns `VerificationReport` with per-citation status + aggregate metrics

---

### Multi-Perspective Review Agents

#### [NEW] [research_engine/agent/reviewer.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/agent/reviewer.py)
- `ReviewAgent` base class with `review(report, context) -> ReviewFeedback`
- 3 specialized reviewers:
  - **FactChecker**: Cross-references claims against scraped sources
  - **DevilsAdvocate**: Challenges conclusions, identifies logical gaps, tests counter-arguments
  - **QualityScorer**: Rates report on completeness, coherence, citation density, source diversity
- Each reviewer uses a dedicated prompt from `llm/prompts.py`
- Results aggregated into `QualityReport` model

#### [MODIFY] [orchestrator.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/agent/orchestrator.py)
- Insert new `review` phase between `synthesize` and `mindmap`:
  - `synthesize → citation_verify → review → mindmap`
- Emit SSE events: `citation_verification_start`, `citation_verification_complete`, `review_start`, `review_complete`
- Pass `QualityReport` to final report metadata

#### [MODIFY] [models.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/models.py)
- Add `QualityReport` model (confidence_score, citation_verification_rate, reviewer_feedback, improvement_suggestions)
- Add `CitationStatus` enum to `Citation` model
- Add `quality_report` field to `ResearchRun` response

#### [MODIFY] [prompts.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/llm/prompts.py)
- Add prompts: `FACT_CHECK_PROMPT`, `DEVILS_ADVOCATE_PROMPT`, `QUALITY_SCORE_PROMPT`
- Add `CITATION_EXTRACTION_PROMPT` for LLM-based citation parsing fallback

#### [MODIFY] [api.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/api.py)
- Add `POST /research/{run_id}/review` — on-demand re-review endpoint
- Modify stream response to include citation verification + review events
- Add quality report to run response

---

### Frontend — Citation & Quality UI

#### [NEW] [CitationBadge.tsx](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/components/views/CitationBadge.tsx)
- Inline badge component: ✅ verified / ⚠️ unverified / ❌ failed
- Tooltip showing which databases confirmed the citation
- Click to expand full citation metadata

#### [NEW] [QualityTab.tsx](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/components/views/QualityTab.tsx)
- New tab in ReportView: "Research Quality"
- Shows: citation verification rate (%), source diversity score, confidence level
- Review agent feedback cards (FactChecker, Devil's Advocate, Quality Scorer)
- Improvement suggestions list

#### [MODIFY] [ReportView.tsx](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/components/views/ReportView.tsx)
- Add "Quality" tab alongside Citations, Export, Mindmap
- Render `CitationBadge` inline within markdown report

#### [MODIFY] [ResearchProgress.tsx](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/components/views/ResearchProgress.tsx)
- Add progress phases for citation verification and review

#### [MODIFY] [api.ts](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/types/api.ts)
- Add `QualityReport`, `CitationStatus`, `VerificationResult` types

#### [MODIFY] [client.ts](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/api/client.ts)
- Add `reviewRun(runId)` API function
- Update SSE event handling for new phases

---

## Phase 1 — Checkpoint/Resume + Versioning + Quality Scoring

> **Impact**: Resilience for long runs, iterative report improvement  
> **Effort**: Medium (~2 weeks)

### Checkpoint/Resume System

#### [NEW] [research_engine/agent/checkpoint.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/agent/checkpoint.py)
- `CheckpointManager` class: saves research state at each phase boundary
- State includes: current phase, accumulated sources, partial report, search results, plan
- Supabase `research_checkpoints` table: `run_id`, `phase`, `state_json`, `created_at`
- `save_checkpoint(run_id, phase, state)` — async, wrapped in `asyncio.to_thread()`
- `load_checkpoint(run_id)` — returns latest checkpoint state
- `resume_from_checkpoint(run_id)` — re-enters orchestrator at saved phase

#### [MODIFY] [orchestrator.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/agent/orchestrator.py)
- Call `checkpoint_manager.save_checkpoint()` after each phase completes
- Add `resume` parameter to `run_research()` — if True, load checkpoint and skip completed phases
- Handle interrupted runs gracefully (catch exceptions, save partial state)

#### [MODIFY] [api.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/api.py)
- Add `POST /research/{run_id}/resume` endpoint
- Add `GET /research/{run_id}/checkpoints` — list available checkpoints

### Draft Versioning

#### [NEW] [research_engine/agent/versioning.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/agent/versioning.py)
- `VersionManager`: tracks report revisions (v1, v2, v3...)
- Auto-detect existing drafts, preserve citations during revisions
- Diff computation between versions (for frontend display)
- Supabase `report_versions` table: `run_id`, `version`, `content`, `diff_from_prev`, `created_at`

#### [MODIFY] [api.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/api.py)
- Add `POST /research/{run_id}/revise` — trigger report revision with optional user instructions
- Add `GET /research/{run_id}/versions` — list all versions with diffs

### Quality Benchmarking (from AI-Researcher)

#### [NEW] [research_engine/agent/benchmark.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/agent/benchmark.py)
- Quality scoring framework inspired by Scientist-Bench
- Dimensions: completeness, factual accuracy, citation density, source diversity, coherence, depth
- Scoring via LLM-as-judge with structured rubric output
- Historical tracking per workspace for quality trends

### Frontend

#### [NEW] [VersionHistory.tsx](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/components/views/VersionHistory.tsx)
- Version selector dropdown in ReportView
- Diff viewer showing changes between versions
- "Revise" button triggering revision with optional instructions

#### [MODIFY] [ReportView.tsx](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/components/views/ReportView.tsx)
- Add version selector header
- Add "Resume" button for interrupted runs (shown when checkpoint exists)

---

## Phase 2 — Token Compression + Academic APIs + Export Formats

> **Impact**: Cost reduction, broader source coverage, professional export  
> **Effort**: High (~3-4 weeks)

### Token Compression (from headroom — Rust+Python hybrid)

#### [NEW] [research_engine/compression/](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/compression/)
- **`router.py`** — `ContentRouter`: auto-detect content type → route to specialized compressor
- **`smart_crusher.py`** — JSON compression: flatten nested objects, dedup keys, collapse arrays
- **`code_compressor.py`** — AST-aware code compression (preserves semantics, strips noise)
- **`text_compressor.py`** — Natural language compression: remove redundancy, preserve meaning
- **`cache_aligner.py`** — Stabilize prompt prefixes for KV cache hit maximization
- **`ccr.py`** — Content-Compressed Retrieval: reversible compression with on-demand full retrieval
- **`rust_core/`** — Rust extension module (via PyO3/maturin) for performance-critical compression

#### [NEW] [scripts/setup_headroom.py](file:///d:/Projects/ai-ml/DeepResearchAgent/scripts/setup_headroom.py)
- Setup script that automates the headroom installation: checks for Rust toolchain (`rustup`), installs it if missing, builds the headroom Rust packages, and packages the binary extensions for performance-critical context compression.

> [!IMPORTANT]  
> Rust dependency: Requires Rust toolchain. The system will autoinstall full Rust packages and pre-built binaries necessary for performance-critical context compression.

#### [MODIFY] [provider.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/llm/provider.py)
- Integrate `ContentRouter` before all LLM calls
- Auto-compress context, decompress responses
- Log token savings metrics per call

### Additional Academic Search Providers

#### [NEW] [research_engine/sources/academic_search.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/sources/academic_search.py)
- `AcademicSearchProvider` implementing `SearchProvider` protocol
- Adapters for: arXiv, PubMed, CORE, Unpaywall, BASE
- Unified result format compatible with existing `SearchResult` model
- Auto-selection based on query domain (biomedical → PubMed, CS → arXiv, general → OpenAlex)

#### [MODIFY] [web_search.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/sources/web_search.py)
- Register `AcademicSearchProvider` in `get_search_provider()` factory
- Add `academic` mode to `ResearchRequest.mode` enum

### PRISMA Compliance Systematic Reviews

#### [NEW] [research_engine/agent/prisma.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/agent/prisma.py)
- `PrismaWorkflowManager`: orchestrator that enforces PRISMA systematic review standards
- Tracks identification, screening, eligibility, and inclusion stages of paper search/extraction
- Exports systematic review mapping data as Excel/CSV table and visual SVG PRISMA flow diagram

#### [MODIFY] [orchestrator.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/agent/orchestrator.py)
- Add systematic review/PRISMA option to research request queries
- Record screening inclusion/exclusion metrics at each iteration for flow representation

### Export Formats

#### [MODIFY] [exporter.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/output/exporter.py)
- Add `export_docx()` — Word export via `python-docx` with academic formatting
- Add `export_latex()` — LaTeX export with BibTeX bibliography
- Add `export_bibtex()` — standalone BibTeX file from verified citations
- Add `export_ris()` — RIS format for reference managers (Zotero, Mendeley, EndNote)
- Add `export_obsidian_vault()` — full Obsidian vault with wikilinks, backlinks, and metadata

#### [MODIFY] [api.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/api.py)
- Extend export endpoint to support new formats
- Add format parameter: `json`, `markdown`, `pdf`, `docx`, `latex`, `bibtex`, `ris`, `obsidian`

### Frontend

#### [MODIFY] [ExportPanel.tsx](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/components/views/ExportPanel.tsx)
- Add new export format buttons: Word, LaTeX, BibTeX, RIS, Obsidian Vault
- Show format descriptions and use-case hints

---

## Phase 3 — Docker Sandbox + Cross-Agent Memory

> **Impact**: Experimental validation, multi-session memory  
> **Effort**: High (~3-4 weeks)

### Docker Sandboxed Execution ("Research Lab")

#### [NEW] [research_engine/sandbox/](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/sandbox/)
- **`executor.py`** — `SandboxExecutor`: manages Docker containers for code execution
  - Create isolated containers per experiment
  - Resource limits (CPU, memory, network, timeout)
  - Capture stdout/stderr, exit codes, generated files
  - Auto-cleanup after execution
- **`builder.py`** — `ImageBuilder`: constructs Docker images with required dependencies
  - Base images for Python, R, Julia
  - Auto-detect requirements from generated code
  - Caching layer for frequently-used environments
- **`models.py`** — `ExperimentRequest`, `ExperimentResult`, `SandboxConfig`
- **`security.py`** — Network isolation, filesystem restrictions, privilege dropping

#### [MODIFY] [api.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/api.py)
- Add `POST /research/{run_id}/experiment` — execute code in sandbox
- Add `GET /research/{run_id}/experiments` — list experiment results
- Add `GET /research/{run_id}/experiments/{exp_id}/output` — fetch experiment artifacts

### Cross-Agent Memory (from headroom)

#### [NEW] [research_engine/memory/](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/memory/)
- **`shared_context.py`** — Cross-run shared context with deduplication
  - Compress and store key findings across research runs within a workspace
  - Auto-surface relevant prior findings when starting new research
  - Uses CCR (from compression module) for storage efficiency
- **`session.py`** — `SessionMemory`: per-session working memory
  - Track what's been searched, scraped, and synthesized
  - Prevent redundant work across cycles within a run
- **`learn.py`** — Mine failed/low-quality runs to generate correction patterns (inspired by `headroom learn`)

### Frontend

#### [NEW] [ExperimentPanel.tsx](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/components/views/ExperimentPanel.tsx)
- Code editor with run button
- Output terminal display
- Experiment history sidebar

#### [NEW] [ResearchMemory.tsx](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/components/views/ResearchMemory.tsx)
- Display cross-run memory items
- Allow users to pin/unpin findings
- Show relevance connections between runs

---

## Database Migrations

### Supabase Tables

```sql
-- P0: Citation verification
CREATE TABLE citation_verifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID REFERENCES research_runs(id),
  workspace_id UUID NOT NULL,
  citation_text TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('verified', 'unverified', 'failed')),
  sources JSONB DEFAULT '[]',  -- [{db: "crossref", confidence: 0.95, metadata: {...}}]
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- P0: Quality reports
CREATE TABLE quality_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID REFERENCES research_runs(id),
  workspace_id UUID NOT NULL,
  confidence_score FLOAT,
  citation_verification_rate FLOAT,
  source_diversity_score FLOAT,
  reviewer_feedback JSONB DEFAULT '[]',
  improvement_suggestions JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- P1: Checkpoints
CREATE TABLE research_checkpoints (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID REFERENCES research_runs(id),
  workspace_id UUID NOT NULL,
  phase TEXT NOT NULL,
  state_json JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- P1: Report versions
CREATE TABLE report_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID REFERENCES research_runs(id),
  workspace_id UUID NOT NULL,
  version INT NOT NULL,
  content TEXT NOT NULL,
  diff_from_prev TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(run_id, version)
);

-- P3: Experiments
CREATE TABLE sandbox_experiments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID REFERENCES research_runs(id),
  workspace_id UUID NOT NULL,
  code TEXT NOT NULL,
  language TEXT DEFAULT 'python',
  status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'timeout')),
  stdout TEXT,
  stderr TEXT,
  exit_code INT,
  artifacts JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- P3: Cross-run memory
CREATE TABLE research_memory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL,
  run_id UUID REFERENCES research_runs(id),
  finding TEXT NOT NULL,
  compressed_context TEXT,
  relevance_tags JSONB DEFAULT '[]',
  pinned BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Verification Plan

### Automated Tests

```bash
# P0: Citation verification
pytest tests/unit/test_citation_parser.py
pytest tests/unit/test_citation_adapters.py  # Mock API responses
pytest tests/unit/test_citation_verifier.py
pytest tests/unit/test_review_agents.py
pytest tests/integration/test_citation_pipeline.py  # Live API calls (rate-limited)

# P1: Checkpoint/resume
pytest tests/unit/test_checkpoint_manager.py
pytest tests/unit/test_version_manager.py
pytest tests/integration/test_checkpoint_resume.py

# P2: Compression
pytest tests/unit/test_content_router.py
pytest tests/unit/test_smart_crusher.py
pytest tests/unit/test_cache_aligner.py
pytest tests/unit/test_academic_search.py
pytest tests/unit/test_export_formats.py

# P3: Sandbox
pytest tests/unit/test_sandbox_executor.py
pytest tests/integration/test_docker_sandbox.py  # Requires Docker

# Frontend (all phases)
cd frontend && npm run build  # TypeScript type parity check
```

### Manual Verification
- Run a full research query and verify citation badges appear in report
- Trigger on-demand review and check Quality tab
- Interrupt a research run, then resume from checkpoint
- Export to Word/LaTeX/BibTeX and verify formatting
- Run a code experiment in sandbox (P3)

---

## Dependencies to Add

### Python (requirements.txt / pyproject.toml)

| Package | Phase | Purpose |
|---------|-------|---------|
| `aiohttp` | P0 | Async HTTP for citation API calls |
| `python-docx` | P2 | Word document export |
| `pylatex` | P2 | LaTeX document generation |
| `maturin` | P2 | Build Rust extension for compression |
| `docker` | P3 | Docker SDK for sandbox execution |

### Rust (P2)
- Rust toolchain (rustup) for compression module
- PyO3 + maturin for Python bindings

### Frontend (package.json)
- No new dependencies expected — all UI built with existing Tailwind + Radix + Lucide stack

---

## Resolved Design Decisions

> [!NOTE]
> **Semantic Scholar API Key**: Both unauthenticated and authenticated modes will be supported. In production, a key can be provided via `config.toml`. For local development, the system will default to unauthenticated mode with graceful rate limiting and degradation.

> [!NOTE]
> **Rust Toolchain & Binaries**: Full headroom token compression is a hard requirement. The setup scripts will autoinstall/package the necessary Rust compiler/binaries/extensions to guarantee the maximum 60-95% compression ratio.

> [!NOTE]
> **PRISMA Compliance**: PRISMA systematic review support will be tracked and implemented as a separate P2 enhancement.

---

## Deeper Repo Extraction Findings

To guarantee DRA provides a publishable-grade academic research platform, we are augmenting the implementation plan with specific architectural patterns and concrete mechanisms extracted from the deep dive.

### 1. Hierarchical LaTeX & Document Synthesis (from AI-Researcher)

Instead of generating flat Markdown or compiling drafts in single prompts, we will integrate AI-Researcher's **Iterative Checkpointed Hierarchical Document Synthesis (IHDS)**. This is the mechanism that enabled AI-Researcher's output to match the quality standards of spotlight platforms (NeurIPS 2025).

#### The Composition Pipeline
The synthesis engine will run a specialized `SectionComposer` subclass for each paper section:
```python
# Conceptual design of SectionComposer integration
class SectionComposer(ABC):
    def __init__(self, run_id: str, section_name: str, config: Dict):
        self.run_id = run_id
        self.section_name = section_name
        self.config = config

    @abstractmethod
    async def compose(self, sources: List[Dict], outline: Dict) -> str:
        pass
```

1. **Section-Specific Composers**:
   - `IntroductionComposer`: Focuses on logical progression: *Research Background -> Research Motivation (gaps & challenges) -> Proposed Methodology -> Key Contributions*.
   - `RelatedWorkComposer`: Follows a strict structure. First details existing work, then highlights our relative contribution (where related work discussion length must be $\ge 2\times$ our contribution details). Every subsection must cite $4$ to $10$ papers.
   - `ExperimentsComposer`: Automatically parses project code files and experiment runs (`run_*.py` files and logs). It extracts performance numbers and structures them into standard LaTeX subsubsections: *Datasets, Evaluation Metrics, Baselines, and Main Performance Comparison*. It uses matplotlib/seaborn script generation within the sandbox to output figures, placing them in LaTeX `\begin{figure}` blocks.
   - `ConclusionComposer` & `AbstractComposer`: Focuses on high-level impact, limitations, and future work.

2. **The Iterative Composition Flow**:
   - **Step 1: Outline Refinement**: The composer drafts a LaTeX outline with comments (%) specifying the key claims, required metrics, and bibliography keys.
   - **Step 2: Subsection Detailization**: The composer detailizes each subsection by feeding in small, focused chunks of source context (e.g., specific PDF texts, code modules, or experiment logs) sequentially. This bypasses context window dilution and ensures maximum density of facts and numbers.
   - **Step 3: LaTeX Formatting & Citation Post-Processing**:
     - Automatically strips LLM code blocks (````latex...````) from outputs.
     - Parses inline reference keys and extracts BibTeX entries (`@article{...}`) written by the LLM inside `.tex` files, separating them into a central `references.bib` file.

---

### 2. Provenance Tracking & Reproducibility (from academic-research-skills)

To ensure the trustworthiness of generated papers and research runs, we will implement **Material Passports** and **repro_lock** files.

#### Material Passports
Every generated draft or report will be accompanied by a `material_passport.json` artifact mapping the exact provenance of every load-bearing claim.
* **Claims Registry**: Stores a list of key claims made in the synthesized paper.
* **Evidence Mapping**: Maps each claim to the exact source (e.g., PDF filename, section number, website URL) and quotes the raw text snippet that supports the claim.
* **Hallucination Auditing**: If a claim lacks a valid mapped snippet or fails citation verification, it is flagged, and the `FactChecker` agent triggers a revision loop.

#### Artifact Reproducibility Lockfile (repro_lock)
A lockfile metadata block stored in Supabase under `research_checkpoints` to record:
* The exact model IDs and parameters used at each step.
* The content hashes of input files and prompts.
* The state hash of the retrieved search results.
While not providing absolute deterministic reproducibility due to LLM stochasticity, this provides an auditable paper trail of how a specific scientific manuscript was constructed.

---

### 3. Factual, Developer & Academic APIs as Sources of Truth (from public-apis)

To support **Nightglass**'s core target audience (developers, indie hackers, AI engineers, and high-agency founders), we are expanding the system's direct sources of truth beyond academic databases. These zero-authentication APIs enable deep factual lookups across development repositories, financial datasets, public company filings, and real-time developer trends:

| API Group / Namespace | Focus | Use Case | System Benefit (Why We Added It) | Auth |
|---|---|---|---|---|
| **OpenAlex** (`https://api.openalex.org`) | Academic Citation Graph | Mapping co-citation networks, author networks, and tracking research papers. | Builds visual co-citation maps and knowledge graphs to help developers trace the academic lineage of libraries and machine learning models. | None |
| **arXiv** (`http://export.arxiv.org/api`) | Preprints & Papers | Searching preprints for Computer Science, Math, Physics, and AI research. | Instantly extracts full preprint texts, allowing AI engineers to search and retrieve bleeding-edge papers on deep learning and algorithms. | None |
| **Hacker News Search** (`https://hn.algolia.com/api`) | Developer Discussions | Querying history of HN stories, comments, and tech show-cases for developer sentiment/feedback. | Analyzes developer sentiment, community feedback, product launch receptions, and technology debates for product/market validation. | None |
| **SEC EDGAR** (`https://www.sec.gov/edgar/...`) | Corporate Financial Filings | Extracting corporate financial reports (10-K, 10-Q) and SEC filings for startup & business research. | Ingests audited corporate financial filings, balance sheets, and competitive risk profiles to provide founders with reliable business intelligence. | None |
| **CoinGecko** (`https://api.coingecko.com/api/v3`) | Cryptocurrency & Tokens | Tracking real-time crypto prices, market caps, exchanges, and coin metadata. | Enriches Web3 research by feeding real-time cryptocurrency token metrics, coin listings, and historical market data directly to research runs. | None |
| **npm Registry** (`https://registry.npmjs.org`) | JavaScript Ecosystem | Retrieving Node package metadata, versions, and dependencies for developer queries. | Automates dependency audits, package version checks, repository health evaluations, and download trends for developer-focused research. | None |
| **Econdb** (`https://www.econdb.com/api`) | Global Macroeconomics | Accessing GDP, inflation, interest rates, and employment indices for 90+ countries. | Supplies official macroeconomic indicators, allowing high-agency founders to validate market conditions and size business models globally. | None |
| **Mozilla HTTP Observatory** (`https://httpobs.mozilla.org/api/v1`) | Website Security | Programmatically checking HTTP headers, cookies, and TLS configurations of target domains. | Programmatically scans security headers, cookie configurations, and TLS parameters to automate web app and site security reviews. | None |
| **National Vulnerability Database (NVD)** (`https://services.nvd.nist.gov/...`) | Cybersecurity Vulnerabilities | Checking CVE entries, vulnerability details, and severities for dev ops & security reviews. | Serves as a direct reference lookup for CVE numbers, severities, and remediation details during systems/software audits. | None |
| **Bluesky (AT Protocol)** (`https://public.api.bsky.app/xrpc/...`) | Decentralized Social | Querying public posts, profiles, and feeds to track dev/AI ecosystem announcements. | Crawls real-time developer announcements, tech updates, and decentralized social discussion threads to bypass closed APIs. | None |
| **Open Collective** (`https://opencollective.com/api/...`) | Open-Source Finances | Looking up backing, budget, and expenses for popular open-source repos. | Audits project financial transparency, backing stats, and development run rates to verify open-source dependency health. | None |
| **Nominatim (OpenStreetMap)** (`https://nominatim.openstreetmap.org`) | Geocoding & Addresses | Resolving coordinates and reverse geocoding addresses globally. | Ground search queries geographically by resolving street addresses and map coordinates without expensive Google Maps API costs. | None |
| **REST Countries** (`https://restcountries.com`) | Geographic Data | Querying border details, languages, and country profiles. | Standardizes country demographic metadata, currency mappings, and profiles for localization and market analysis. | None |
| **dead-drop** (`https://api.dead-drop.xyz`) | ZK Encryption | Accessing zero-knowledge ephemeral sharing parameters. | Integrates zero-knowledge ephemeral encryption parameters to support privacy reviews and secure sharing mechanism research. | None |
| **Open Library** (`https://openlibrary.org/api`) | Published Books | Validating book references, publishers, and published ISBN metadata. | Resolves and formats non-academic book details, publishers, and ISBN references to ensure comprehensive citation outputs. | None |
| **Kroki** (`https://kroki.io`) | Diagram Rendering | Rendering Mermaid, Graphviz, or PlantUML diagrams from text into SVG/PNG. | Converts plain text layout definitions (Mermaid, PlantUML) into high-fidelity SVG/PNG diagrams for reports and graphs. | None |
| **QuickChart** (`https://quickchart.io`) | Dynamic Chart Generation | Generating charts/graph images (Chart.js syntax) to embed directly in research reports. | Renders data tables and research metrics into visual Chart.js chart images directly within PDF/Word document exports. | None |
| **CodeCogs** (`https://latex.codecogs.com`) | LaTeX Equation Renderer | Generating high-fidelity equation images for frontend markdown equation previews. | Converts complex mathematical equations and deep learning formulas into high-resolution SVG previews for frontend display. | None |
| **RSS-to-JSON** (`https://rss-to-json-serverless-api.vercel.app`) | Feed Parsing | Converting arbitrary RSS feeds (tech blogs, release notes) to structured JSON. | Connects news sites, tech releases, and product changelogs to the research engine by parsing RSS feeds on-the-fly. | None |
| **datos.gob.es** / **data.gov.uk** / **data.gov** | Public Demographic Data | Official country-specific statistical figures (economic performance, public metrics). | Ingests official census datasets, population figures, and national economic records for country-level research. | None |
| **Open Science Framework** (`https://api.osf.io`) | Pre-registrations & studies | Checking registered study protocols, methodologies, and raw datasets. | Validates pre-registered study hypotheses, testing methodologies, and clinical design protocols to ensure research integrity. | None |
| **USAspending** (`https://api.usaspending.gov`) | Government Spending | Extracting factual US federal funding data, contracts, and grant histories. | Tracks federal funding flows, government contracts, and research grants for public policy and competitive market audits. | None |
| **wttr.in** (`https://wttr.in`) | Terminal Weather | Terminal-friendly weather and climate fact verification. | Obtains quick weather summaries and climate history figures for geographic fact-checking during research runs. | None |
