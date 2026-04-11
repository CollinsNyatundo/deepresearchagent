"""Tests for the LLM provider module."""

import pytest
from research_engine.llm.provider import validate_model_id, _extract_json


def test_validate_model_id_valid():
    """Valid model IDs should pass validation."""
    assert validate_model_id("nvidia/nemotron-3-super-120b-a12b:free") == "nvidia/nemotron-3-super-120b-a12b:free"
    assert validate_model_id("openai/gpt-oss-120b:free") == "openai/gpt-oss-120b:free"
    assert validate_model_id("  qwen/qwen3-235b-a22b:free  ") == "qwen/qwen3-235b-a22b:free"
    # Groq plain model names are valid when provider=groq
    assert validate_model_id("llama-3.3-70b-versatile", provider="groq") == "llama-3.3-70b-versatile"
    # groq/ prefix is automatically stripped
    assert validate_model_id("groq/llama-3.3-70b-versatile") == "llama-3.3-70b-versatile"


def test_validate_model_id_invalid():
    """Invalid model IDs should raise ValueError."""
    with pytest.raises(ValueError, match="non-empty"):
        validate_model_id("")

    with pytest.raises(ValueError, match="provider/model"):
        validate_model_id("no-slash-here")  # OpenRouter requires slash

    with pytest.raises(ValueError, match="200 characters"):
        validate_model_id("a/" + "b" * 200)


def test_extract_json_from_markdown():
    """Should extract JSON from markdown code fences."""
    text = '```json\n{"key": "value"}\n```'
    assert _extract_json(text) == '{"key": "value"}'


def test_extract_json_raw():
    """Should extract raw JSON object."""
    text = 'Some text {"key": "value"} more text'
    assert _extract_json(text) == '{"key": "value"}'
