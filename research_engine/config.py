"""Configuration loader — TOML file + env vars + defaults."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: str = "openrouter"
    default_model: str = "nvidia/nemotron-3-super-120b-a12b:free"
    base_url: str = "https://openrouter.ai/api/v1"
    temperature: float = 0.2
    max_tokens: int = 16384
    # Groq free tier: TPM limit = 12,000 (counts input + max_output_tokens).
    # Keeping max_tokens at 16384 would make even tiny prompts exceed the limit.
    # 4096 leaves ~7900 tokens of headroom for input context on the free tier.
    groq_max_tokens: int = 4096
    request_timeout: int = 120  # seconds — prevents indefinite hangs on slow models
    presets: dict[str, str] = Field(default_factory=lambda: {
        "nemotron": "nvidia/nemotron-3-super-120b-a12b:free",
        "gpt_oss": "openai/gpt-oss-120b:free",
        "qwen": "qwen/qwen3-235b-a22b:free",
    })
    # Groq model presets — plain model IDs (no provider prefix)
    groq_presets: dict[str, str] = Field(default_factory=lambda: {
        # ── LLaMA 3.x generation ───────────────────────────────────────────────
        "llama3_70b": "llama-3.3-70b-versatile",          # Best all-rounder, 128K ctx
        "llama3_70b_specdec": "llama-3.3-70b-specdec",    # Speculative decoding, 2-4x faster
        "llama3_8b": "llama-3.1-8b-instant",              # Fastest, 128K ctx
        "llama3_1b": "llama-3.2-1b-preview",             # Ultra-fast triage / routing
        "llama3_3b": "llama-3.2-3b-preview",             # Small but capable
        "llama3_11b_vision": "llama-3.2-11b-vision-preview",  # Vision + text, 128K ctx
        "llama3_90b_vision": "llama-3.2-90b-vision-preview",  # Large vision model
        # ── LLaMA 4 generation (Groq preview) ──────────────────────────────────
        "llama4_scout": "meta-llama/llama-4-scout-17b-16e-instruct",      # 512K context!
        "llama4_maverick": "meta-llama/llama-4-maverick-17b-128e-instruct",  # 128K, powerful
        # ── Reasoning / CoT models ─────────────────────────────────────────────
        "deepseek_r1": "deepseek-r1-distill-llama-70b",   # DeepSeek R1 distilled
        "qwen_qwq": "qwen-qwq-32b",                       # Alibaba QwQ, strong reasoning
        # ── Multilingual & specialized ─────────────────────────────────────────
        "gemma2_9b": "gemma2-9b-it",                      # Google Gemma 2
        "mistral_saba": "mistral-saba-24b",               # Mistral, Arabic & multilingual
        "mixtral_8x7b": "mixtral-8x7b-32768",             # Mixtral MoE, long context
        # ── Compound / agentic ─────────────────────────────────────────────────
        "compound_beta": "compound-beta",                 # Full Groq compound AI (tools)
        "compound_mini": "compound-beta-mini",            # Smaller compound (fast tools)
        # ── Safety / guard models ──────────────────────────────────────────────
        "llama_guard": "llama-guard-3-8b",                # Content moderation
    })


class SearchConfig(BaseModel):
    """Search provider configuration."""

    default_provider: str = "all"  # aggregated multi-provider (DDG + Tavily + Brave)
    max_results: int = 10
    tavily_api_key: str = ""
    brave_api_key: str = ""
    exa_api_key: str = ""
    firecrawl_api_key: str = ""
    parallel_api_key: str = ""


class ScrapingConfig(BaseModel):
    """Scrapling scraper configuration."""

    max_concurrent: int = 5
    timeout_ms: int = 30000
    max_content_chars: int = 20000
    # Fetcher tier controls which scrapling tiers are enabled:
    #   "async"    — curl_cffi only (fast, no JS, for static sites)
    #   "dynamic"  — async + Playwright Chromium JS rendering
    #   "stealthy" — async + Playwright + patchright + Camoufox Firefox (maximum bypass)
    #   "all"      — all tiers in order (recommended: auto-fallback from fast → stealthy)
    fetcher_tier: str = "all"
    firecrawl_api_key: str = ""
    parallel_api_key: str = ""


class ResearchConfig(BaseModel):
    """Research loop configuration."""

    default_depth: int = 5  # Exhaustive mode
    max_cycles: int = 30
    progress_threshold: int = 90
    max_pages_per_query: int = 5
    enable_crossover: bool = True
    crossover_candidates: int = 3
    progress_check_interval: int = 5


class APIConfig(BaseModel):
    """FastAPI server configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


class GithubConfig(BaseModel):
    """GitHub MCP configuration."""

    personal_access_token: str = ""
    default_repo: str = "CollinsNyatundo/Ulti-IDE"


class GraphifyConfig(BaseModel):
    """Graphify knowledge graph integration configuration."""

    # Master switch — set to False to disable all Graphify integration
    enabled: bool = True
    # Extraction mode: 'fast' (AST only) | 'deep' (AST + LLM-inferred edges)
    mode: str = "deep"
    # Where graphify builds its output relative to the run dir
    output_subdir: str = "graphify-out"
    # Strategy B: start MCP server after building the graph
    mcp_enabled: bool = True
    mcp_port: int = 8765
    # Strategy C: max ArXiv/PDF URLs to enrich per run (0 = unlimited)
    max_paper_enrichments: int = 5


class AppConfig(BaseModel):
    """Top-level application configuration."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    scraping: ScrapingConfig = Field(default_factory=ScrapingConfig)
    research: ResearchConfig = Field(default_factory=ResearchConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    github: GithubConfig = Field(default_factory=GithubConfig)
    graphify: GraphifyConfig = Field(default_factory=GraphifyConfig)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load configuration from TOML file, overlaid with environment variables.

    Priority: env vars > TOML file > defaults.
    """
    data: dict[str, Any] = {}

    # 1. Load TOML file if it exists
    if path is None:
        path = Path("config.toml")
    else:
        path = Path(path)

    if path.exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)

    # 2. Overlay environment variables
    env_overrides: dict[str, Any] = {}

    if api_key := os.environ.get("OPENROUTER_API_KEY"):
        # Stored in env, not in config — provider reads it directly
        pass

    if groq_key := os.environ.get("GROQ_API_KEY"):
        # Stored in env, not in config — provider reads it directly
        pass

    if tavily_key := os.environ.get("TAVILY_API_KEY"):
        env_overrides.setdefault("search", {})["tavily_api_key"] = tavily_key

    if brave_key := os.environ.get("BRAVE_SEARCH_API_KEY"):
        env_overrides.setdefault("search", {})["brave_api_key"] = brave_key

    if exa_key := os.environ.get("EXA_API_KEY"):
        env_overrides.setdefault("search", {})["exa_api_key"] = exa_key

    if firecrawl_key := os.environ.get("FIRECRAWL_API_KEY"):
        env_overrides.setdefault("search", {})["firecrawl_api_key"] = firecrawl_key
        env_overrides.setdefault("scraping", {})["firecrawl_api_key"] = firecrawl_key

    if parallel_key := os.environ.get("PARALLEL_API_KEY"):
        env_overrides.setdefault("search", {})["parallel_api_key"] = parallel_key
        env_overrides.setdefault("scraping", {})["parallel_api_key"] = parallel_key

    if model := os.environ.get("OPENROUTER_MODEL"):
        env_overrides.setdefault("llm", {})["default_model"] = model

    if llm_provider := os.environ.get("LLM_PROVIDER"):
        env_overrides.setdefault("llm", {})["provider"] = llm_provider

    if provider := os.environ.get("SEARCH_PROVIDER"):
        env_overrides.setdefault("search", {})["default_provider"] = provider

    if github_token := os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN"):
        env_overrides.setdefault("github", {})["personal_access_token"] = github_token

    # Graphify env overrides
    if graphify_enabled := os.environ.get("GRAPHIFY_ENABLED"):
        env_overrides.setdefault("graphify", {})["enabled"] = graphify_enabled.lower() in ("1", "true", "yes")
    if graphify_mode := os.environ.get("GRAPHIFY_MODE"):
        env_overrides.setdefault("graphify", {})["mode"] = graphify_mode
    if graphify_mcp := os.environ.get("GRAPHIFY_MCP_ENABLED"):
        env_overrides.setdefault("graphify", {})["mcp_enabled"] = graphify_mcp.lower() in ("1", "true", "yes")

    merged = _deep_merge(data, env_overrides)

    return AppConfig(**merged)


# Module-level singleton (lazy)
_config: AppConfig | None = None


def get_config(path: str | Path | None = None) -> AppConfig:
    """Get or create the singleton config."""
    global _config
    if _config is None:
        _config = load_config(path)
    return _config
