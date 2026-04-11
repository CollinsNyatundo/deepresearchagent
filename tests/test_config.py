"""Tests for config loading."""

from research_engine.config import AppConfig, load_config, LLMConfig, SearchConfig


def test_default_config():
    """Default config should have sensible values."""
    config = AppConfig()
    assert config.llm.default_model == "nvidia/nemotron-3-super-120b-a12b:free"
    assert config.research.default_depth == 5
    assert config.research.max_cycles == 30
    assert config.scraping.max_content_chars == 20000
    assert config.search.default_provider == "duckduckgo"


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
