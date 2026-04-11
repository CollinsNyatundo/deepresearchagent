"""Tests for config loading."""

import os

import pytest

from research_engine.config import AppConfig, LLMConfig, SearchConfig, load_config


def test_default_config():
    """Default config should have sensible values."""
    config = AppConfig()
    assert config.llm.default_model == "nvidia/nemotron-3-super-120b-a12b:free"
    assert config.research.default_depth == 5
    assert config.research.max_cycles == 30
    assert config.scraping.max_content_chars == 20000
    assert config.search.default_provider == "all"  # aggregated multi-provider


def test_llm_config_presets():
    """LLM config should have model presets."""
    config = LLMConfig()
    assert "nemotron" in config.presets
    assert "gpt_oss" in config.presets
    assert config.base_url == "https://openrouter.ai/api/v1"


def test_exhaustive_depth():
    """Default depth should be 5 (exhaustive)."""
    config = AppConfig()
    assert config.research.default_depth == 5
    max_cycles = config.research.default_depth * 6
    assert max_cycles == 30


def test_default_provider_is_openrouter():
    """LLMConfig should default to openrouter provider."""
    config = LLMConfig()
    assert config.provider == "openrouter"


def test_llm_provider_env_override(monkeypatch):
    """LLM_PROVIDER env var should set config.llm.provider."""
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    config = load_config()
    assert config.llm.provider == "groq"


def test_groq_api_key_env(monkeypatch):
    """GROQ_API_KEY should be readable from env (not stored in config, used by provider)."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_key_123")
    # The key is read at LLMProvider init time, not stored in AppConfig
    # Confirm load_config doesn't crash when it's set
    config = load_config()
    assert config is not None


def test_search_provider_env_override(monkeypatch):
    """SEARCH_PROVIDER env var should override default search provider."""
    monkeypatch.setenv("SEARCH_PROVIDER", "brave")
    config = load_config()
    assert config.search.default_provider == "brave"
