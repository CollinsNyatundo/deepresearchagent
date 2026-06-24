# Search Results: Repository Landscape Scan

## 1. academic-research-skills (Imbad0202/academic-research-skills)

**License:** CC-BY-NC 4.0 (Non-commercial — critical for integration!)
**Stars:** 33,395+ | **Language:** Python | **Primary Author:** Cheng-I Wu (吳政宜)

**Core Architecture:**
- A Claude Code skill suite for human-in-the-loop academic research workflows
- Four main skills: `deep-research`, `academic-paper`, `academic-paper-reviewer`, `academic-pipeline` (orchestrator)
- Multi-agent pipeline: Stage 1 (RESEARCH) → Stage 2 (WRITE) → Stage 3 (REVIEW) → Stage 4 (REVISION) → Stage 5 (FINALIZE) → Stage 6 (PROCESS SUMMARY)

**Key Capabilities (from search results):**
- **6 modes** for deep-research including Socratic dialogue mode
- **Academic Paper Reviewer** with 7 agents (EIC + R1/R2/R3 + Devil's Advocate + integrity verification + post-review Socratic coaching)
- **Collaboration Depth Observer** (v3.5.0): 4-dimension rubric scoring user-AI collaboration quality
- **Material Passport-compatible output**: verification status, explicit audit trail
- **Experiment-agent** companion: runs code experiments, manages human studies, interprets statistics, verifies reproducibility
- **Cross-model verification** (`ARS_CROSS_MODEL`): runs dual-model verification for critical outputs
- **Anti-sycophancy discipline**: scores require specific dialogue-turn citations
- **Adjacent-framing probe** (STORM-borrowed): surfaces adjacent research framings as pure questions
- **Reproducibility guarantees**: two-stage review, mandatory integrity verification

**Integration Concerns:**
- CC-BY-NC 4.0 license is NON-COMMERCIAL — this is a major blocker for any commercial DRA deployment
- Designed as Claude Code skills, not a standalone API service
- Requires Claude Code specifically (not generic LLM gateway)
- Heavy dependency on Anthropic ecosystem

---

## 2. opendraft (federicodeponte/opendraft)

**License:** MIT (Fully commercial-friendly)
**Tech Stack:** Python 3.10+, multi-agent orchestration, WeasyPrint (PDF), python-docx (Word)
**Models:** Google Gemini 3, Anthropic Claude 4.5/Opus 4.5, OpenAI GPT-5.5/GPT-5
**Hosted Version:** OpenPaper.dev (3 free papers/day)

**Core Architecture:**
- **19 specialized AI agents** working in a pipeline:
  - RESEARCH PHASE → STRUCTURE PHASE → WRITING PHASE → CITATION PHASE → POLISH PHASE → EXPORT PHASE
- Citation verification against: CrossRef, OpenAlex, Semantic Scholar, arXiv
- Supports: Research papers (5-15 pages), Literature reviews (20-40 pages), Thesis drafts (30-80 pages), PhD dissertations (100+ pages)
- **57+ languages** supported
- Export: PDF (LaTeX-quality), Microsoft Word (.docx), LaTeX source
- **TL;DR mode**: 5-bullet summary of any academic paper from PDF
- **Audio Digest**: 60-second audio summary via ElevenLabs TTS

**Key Technical Details:**
- Each citation verified against 4 databases before inclusion
- If a paper doesn't exist in any DB, it's excluded from bibliography
- Cost per thesis draft: ~$0.35-$3 depending on model
- Uses WeasyPrint for PDF generation (not LaTeX compilation directly)
- Project structure: `engine/draft_generator.py` (main pipeline), `engine/config.py`, `engine/prompts/`, `engine/utils/`

**Integration Strengths:**
- MIT license = no commercial restrictions
- Already uses CrossRef/OpenAlex/Semantic Scholar/arXiv — exactly the same DBs DRA plans to use
- Multi-agent architecture aligns well with DRA's existing agent structure
- Export pipeline (PDF, DOCX, LaTeX) is directly reusable

---

## 3. AI-Researcher (HKUDS/AI-Researcher)

**Status:** Spotlight paper at NeurIPS 2025 (!)
**License:** Not explicitly stated in search results (assumed academic/research)
**Tech Stack:** Python 3.11, uv, Docker, Playwright, Gradio web GUI
**Models:** Configurable via LiteLLM (OpenRouter compatible)

**Core Architecture:**
- **Full end-to-end scientific research automation**: Literature Review → Idea Generation → Algorithm Design → Implementation → Validation → Refinement → Result Analysis → Manuscript Creation
- **Docker-based sandboxed execution**: `tjbtech1/airesearcher:v1` base image, GPU support configurable
- **Two task levels:**
  - Level 1: Detailed idea description → survey + experiments
  - Level 2: Reference papers only → AI generates idea + implements
- **Web GUI**: Gradio-based interface at port 7860
- **Benchmark suite**: Evaluation framework for research automation capabilities
- **Categories**: diffusion/flow, GNN, reasoning, recommendation, VQ (vector quantization)

**Key Technical Details:**
- Uses Docker containers with resource limits (CPU, GPU, memory, network, timeout)
- Requires `playwright install` for web operations
- Supports multiple LLM providers via LiteLLM (Claude, OpenAI, DeepSeek, etc.)
- Container name: `paper_eval`, workplace: `workplace_paper`
- Environment: `.env` template with OpenRouter API key, GitHub AI token, GPU config
- **IHDS (Iterative Hierarchical Document Synthesis)** for LaTeX generation

**Integration Concerns:**
- Heavy Docker dependency — may not fit DRA's lightweight BackgroundTasks architecture
- GPU-dependent for experiments — adds infrastructure complexity
- Academic/research focus — may need significant adaptation for general web research
- LiteLLM integration could conflict with DRA's existing OpenRouter + langchain-openai pattern

---

## 4. headroom (chopratejas/headroom)

**License:** Apache 2.0 (Fully commercial-friendly)
**Stars:** Trending on GitHub (active community)
**Tech Stack:** Python 3.10+, TypeScript, Rust (for performance), HuggingFace models
**PyPI:** `pip install headroom-ai[all]` | **npm:** `npm install headroom-ai`

**Core Architecture:**
- **Multi-mode deployment:**
  - **Library mode**: `compress(messages)` in Python/TypeScript, inline in any app
  - **Proxy mode**: `headroom proxy --port 8787`, zero code changes, OpenAI-compatible
  - **Agent wrap**: `headroom wrap claude|codex|cursor|aider|copilot` one-command integration
  - **MCP server**: `headroom_compress`, `headroom_retrieve`, `headroom_stats` for any MCP client
- **Compression algorithms (6 total):**
  - SmartCrusher: JSON compression (flatten nested, dedup keys, collapse arrays)
  - CodeCompressor: AST-aware code compression (Python, JS, Go, Rust, Java, C++)
  - Kompress: Trained HuggingFace model for prose text compression
  - ML Router: For image compression
  - CacheAligner: Stabilizes prompt prefixes for KV cache hit maximization
  - CCR (Content-Compressed Retrieval): Reversible compression with on-demand retrieval

**Key Features:**
- **60-95% token reduction** with same answers (benchmarked)
- **Cross-agent memory**: Shared store across Claude, Codex, Gemini, auto-dedup
- **`headroom learn`**: Mines failed sessions, writes corrections to `CLAUDE.md`/`AGENTS.md`
- **Output token reduction**: Trims what model writes back (not just input): drops ceremony, restated code, skips deep thinking on routine steps
- **Reversible compression**: Originals cached with TTL, model can retrieve on demand
- **Benchmarks**: F1 0.919 on HTML extraction, 94.9% compression, 98.2% recall

**Integration Concerns:**
- **The DRA plan says "Rust+Python hybrid"** but headroom's actual implementation is primarily Python/TypeScript with optional Rust components — the plan may overstate Rust requirements
- **Not actually a Rust-first project** — PyPI package is pure Python with optional extras
- The plan's `setup_headroom.py` script may be unnecessary — headroom installs via `pip install headroom-ai[all]`
- The plan's `rust_core/` directory might be over-engineering

---

## 5. public-apis (public-apis/public-apis)

**License:** Not specified (typically MIT for awesome lists)
**Stars:** 400,000+ (one of the most popular GitHub repos)
**Maintained by:** APILayer team + community contributors
**Companion API:** `https://api.publicapis.org` (REST, no auth, CORS-enabled)

**Scope:**
- 1,400+ free APIs across 50+ categories
- Categories: Animals, Finance, Weather, Geocoding, Government, Health, Machine Learning, Sports, and 40+ more
- APIs marked with auth requirements: None, API Key, OAuth, etc.

**Key APIs identified in DRA plan for integration:**
- **OpenAlex** (`https://api.openalex.org`): Academic citation graph, no auth
- **arXiv** (`http://export.arxiv.org/api`): Preprints, no auth
- **Hacker News Search** (`https://hn.algolia.com/api`): Developer discussions, no auth
- **SEC EDGAR** (`https://www.sec.gov/edgar/`): Corporate filings, no auth
- **CoinGecko** (`https://api.coingecko.com/api/v3`): Crypto prices, no auth
- **npm Registry** (`https://registry.npmjs.org`): JS package metadata, no auth
- **Econdb** (`https://www.econdb.com/api`): Macroeconomics, no auth
- **Mozilla HTTP Observatory** (`https://httpobs.mozilla.org/api/v1`): Website security, no auth
- **NVD** (`https://services.nvd.nist.gov/`): CVE vulnerabilities, no auth
- **Bluesky (AT Protocol)** (`https://public.api.bsky.app/xrpc/`): Decentralized social, no auth
- **Open Collective** (`https://opencollective.com/api/`): Open-source finances, no auth
- **Nominatim** (`https://nominatim.openstreetmap.org`): Geocoding, no auth
- **REST Countries** (`https://restcountries.com`): Geographic data, no auth
- **Open Library** (`https://openlibrary.org/api`): Book metadata, no auth
- **Kroki** (`https://kroki.io`): Diagram rendering, no auth
- **QuickChart** (`https://quickchart.io`): Chart generation, no auth
- **CodeCogs** (`https://latex.codecogs.com`): LaTeX equation rendering, no auth
- **RSS-to-JSON** (`https://rss-to-json-serverless-api.vercel.app`): Feed parsing, no auth
- **Open Science Framework** (`https://api.osf.io`): Pre-registrations, no auth
- **USAspending** (`https://api.usaspending.gov`): Government spending, no auth
- **wttr.in** (`https://wttr.in`): Weather, no auth

**Integration Value:**
- Provides direct data sources for tech/startup/financial research
- Zero-auth APIs reduce friction for DRA users
- Not a code library to integrate — rather a catalog of APIs to build adapters for

