<div align="center">

# 🔬 Deep Research Agent (DRA)


A multi-module AI-powered research platform featuring deep iterative web research, workspace-isolated personal wiki notes, and intelligent document ingestion.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=white)](https://react.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v3.4.19-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)

</div>

---

## What is this?

**Deep Research Agent (DRA)** is a multi-module AI-powered research platform featuring deep iterative web research, workspace-isolated personal wiki notes, and intelligent document ingestion. Powered by an advanced DRE (Deep Research Reflect Evolve) agentic loop, it orchestrates parallel search, tiered scraping, crossover answer synthesis, and automated knowledge graph construction. The entire platform is built with a premium glassmorphic interface, featuring interactive G6 mindmaps, D3 force-directed notes graphs, and multi-turn document chat.

---

## Key Modules

### 1. 🔍 Research Module
Autonomous deep web research engine that explores topics, validates sources, and reflects on coverage gaps.
- **DRE Orchestrator**: Runs up to 30 iterative research cycles with reflective retries to resolve gaps.
- **SSE Progress Stream**: Exposes real-time agent logic, search terms, validation parameters, and transfer metrics.
- **Interactive Mindmaps**: Renders findings into hierarchical AntV G6 mindmaps supporting node expansion.
- **Multi-Format Export**: Generates reports in Markdown, PDF (`fpdf2`), Word (`.docx`), Excel (`.xlsx`), and JSON.

### 2. 📝 Notes Module
Personal wiki-style knowledge base optimized for developer thought organization and automated state saving.
- **Wiki Linking**: Cross-reference entities and past runs with `[[Note Title]]`, `[[run:run_id]]`, and `[[doc:filename]]` syntax.
- **Notes Graph**: Dynamic, interactive D3 force-directed visualizer mapping note links and backlinks.
- **Auto-Save Engine**: 400ms debounced auto-saving combined with standard `Ctrl+S` hotkeys.
- **Visual Canvas Widgets**: Embeds canvas-rendered widgets (like Moon phase tracking) in the sidebar.

### 3. 📂 Documents Module
OpenKB-powered document ingestion engine allowing isolated workspace knowledge management.
- **OpenKB Storage**: Full workspace separation located locally in `openkb/{workspace_id}/`.
- **Hybrid Q&A**: PostgreSQL full-text search (`tsvector`) integrated with LLM multi-turn chat.
- **Skill Factory**: Automated generator to create, validate, evaluate, and rollback agentic skills from ingestion corpuses.
- **Obsidian Sync**: Generates and downloads entire ingested wiki folder structures as ZIP files.

---

## Premium UI/UX Design

The application implements a premium, dark-mode slate glassmorphism theme:
- **OLED Slate Palette**: Pure OLED black background (`#000000`), slate cards (`rgba(255,255,255,0.06)`), and liquid glass styling for borders with pseudo-element light refraction (`backdrop-filter: blur(6px)`).
- **Icon Sidebar**: Space-efficient 48px left icon sidebar with a hover drawer that exposes sidebar panels without causing page reflow.
- **Monospace CLI Mode**: Toggleable console view with developer telemetry graphs and command autocompletion.
- **Telemetry Indicators**: SSE-powered charts representing crawler queues, byte transfers, and scraper tier breakdowns.

---

## Quick Start

### Prerequisites
- **Python** $\ge$ 3.11
- **Node.js** $\ge$ 18
- **OpenRouter** API key (or Groq API key)
- **Supabase** Project (URL, publishable key, and JWT secret)

### 1. Clone & Install
```bash
# Clone the repository
git clone https://github.com/CollinsNyatundo/deepresearchagent.git
cd deepresearchagent

# Setup Backend Virtual Environment
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
# source .venv/bin/activate  # macOS / Linux

# Install backend dependencies
pip install -e .

# Install stealth browser scraping (optional)
pip install -e .[browser]
python -m playwright install chromium
python -m camoufox fetch

# Setup Environment Variables
cp .env.example .env
# Edit .env and configure keys
```

### 2. Configure Environment
Add the following keys to your `.env` file:
```ini
OPENROUTER_API_KEY=sk-or-v1-your-key-here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
```

### 3. Run the Application
```bash
# Start backend server (FastAPI)
research serve

# Start frontend dashboard (Vite + React)
cd frontend
npm install
npm run dev
```

---

## Project Structure

```
deepresearchagent/
├── docs/                      # Architecture, guides, plans; working notes in docs/notes/
├── frontend/                  # React + Tailwind CSS client dashboard
│   ├── src/                   # React source files (components, api, types)
│   └── design.md              # Design system documentation
├── openkb/                    # Workspace-isolated documents (created at runtime, git-ignored)
├── research/                  # Analytical document archives
├── research_engine/           # FastAPI backend server
│   ├── agent/                 # Core orchestrator, planner, searcher, crossover, retry
│   ├── db/                    # Supabase integration and SQL migrations
│   ├── llm/                   # OpenRouter/Groq providers and prompt templates
│   ├── sources/               # Scrapling fetcher, web search, GitHub search
│   ├── utils/                 # OpenKB and wiki link parsers
│   ├── api.py                 # FastAPI routes (20+ REST/SSE endpoints)
│   └── cli.py                 # Typer command-line interface
├── scripts/live/              # Manual end-to-end checks against real LLM providers and the DB
├── tests/                     # pytest E2E and unit test suite
├── AGENTS.md                  # Development guidelines and common design patterns
├── CLAUDE.md                  # Architecture reference and commands guide
├── STRATEGY.md                # Project roadmap and priority tracks
├── TEST_INFRA.md              # Testing guide for developers
└── pyproject.toml             # Python metadata, packaging and dependencies
```

---

## Documentation

| Resource | Description |
|----------|-------------|
| [AGENTS.md](AGENTS.md) | Coding guidelines, architecture decisions, and design patterns. |
| [CLAUDE.md](CLAUDE.md) | Dev setup, command list, build instructions, and guidelines. |
| [STRATEGY.md](STRATEGY.md) | Current product strategy, priorities, and roadmap. |
| [TEST_INFRA.md](TEST_INFRA.md) | Test framework setup, E2E verification, and mock details. |
| [pyproject.toml](pyproject.toml) | Python dependencies, packaging meta, and tool settings. |

---

## Code Intelligence & Knowledge Graph

- **GitNexus Integration**: Switch the dashboard to "Code Arch" mode to start the local `gitnexus` process, rendering interactive architectural code maps of the codebase.
- **Graphify Engine**: Builds semantic 3D knowledge graphs from your research outputs. Traversal is available via the UI's Knowledge Graph query panel or the command line:
  ```bash
  python -X utf8 -m graphify query "Reinforcement learning" --graph graphify-out/graph.json
  ```

---

## Contributing

We welcome contributions to optimize the research orchestrator and enhance note-taking functionality. Please refer to [AGENTS.md](AGENTS.md) for style conventions.

## License

MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=CollinsNyatundo/deepresearchagent&type=Date)](https://star-history.com/#CollinsNyatundo/deepresearchagent&Date)

</div>
