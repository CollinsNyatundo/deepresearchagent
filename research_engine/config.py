"""Configuration loader — TOML file + env vars + defaults."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    default_model: str = "nvidia/nemotron-3-super-120b-a12b:free"
    base_url: str = "https://openrouter.ai/api/v1"
    temperature: float = 0.2
    max_tokens: int = 16384
    request_timeout: int = 120  # seconds — prevents indefinite hangs on slow models
    presets: dict[str, str] = Field(default_factory=lambda: {
        "nemotron": "nvidia/nemotron-3-super-120b-a12b:free",
        "gpt_oss": "openai/gpt-oss-120b:free",
        "qwen": "qwen/qwen3-235b-a22b:free",
    })


class SearchConfig(BaseModel):
    """Search provider configuration."""

    default_provider: str = "all"  # aggregated multi-provider (DDG + Tavily + Brave)
    max_results: int = 10
    tavily_api_key: str = ""
    brave_api_key: str = ""


class ScrapingConfig(BaseModel):
    """Scrapling scraper configuration."""

    max_concurrent: int = 5
    timeout_ms: int = 30000
    max_content_chars: int = 20000
    fetcher_tier: str = "stealthy"  # stealthy | dynamic | basic


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


class AppConfig(BaseModel):
    """Top-level application configuration."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    scraping: ScrapingConfig = Field(default_factory=ScrapingConfig)
    research: ResearchConfig = Field(default_factory=ResearchConfig)
    api: APIConfig = Field(default_factory=APIConfig)


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

    if tavily_key := os.environ.get("TAVILY_API_KEY"):
        env_overrides.setdefault("search", {})["tavily_api_key"] = tavily_key

    if brave_key := os.environ.get("BRAVE_SEARCH_API_KEY"):
        env_overrides.setdefault("search", {})["brave_api_key"] = brave_key

    if model := os.environ.get("OPENROUTER_MODEL"):
        env_overrides.setdefault("llm", {})["default_model"] = model

    if provider := os.environ.get("SEARCH_PROVIDER"):
        env_overrides.setdefault("search", {})["default_provider"] = provider

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
