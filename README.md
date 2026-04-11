# Deep Research Agent

A general-purpose deep research engine with mindmap visualization. Powered by DRE, Scrapling, OpenRouter, Mantine, and AntV G6.

## Quick Start

```bash
# Set up virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate # Mac/Linux

# Install dependencies (use --default-timeout=1000 for slow networks)
pip install -e .
pip install -e .[browser]  # Optional: adds playwright & camoufox for stealth scraping

# Install browser binaries (only if [browser] extra was installed)
python -m playwright install chromium
python -m camoufox fetch

# Configure
cp config.example.toml config.toml
# Edit config.toml with your API keys

# Run a research query
research run "Your research topic" --depth 5

# Start the API server
research serve

# Start the frontend
cd frontend && npm install && npm run dev
```

## Architecture

See [CLAUDE.md](CLAUDE.md) and [AGENTS.md](AGENTS.md) for detailed documentation.
