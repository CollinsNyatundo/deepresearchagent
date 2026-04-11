"""LLM Provider — async OpenRouter access via LangChain, with runtime model selection."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Type

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from research_engine.config import LLMConfig

logger = logging.getLogger(__name__)

# Maximum retries for rate-limit / transient errors
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0  # seconds


def validate_model_id(model: str, provider: str | None = None) -> str:
    """Validate a model ID string.

    OpenRouter model IDs follow the 'provider/model' format.
    Groq model IDs are plain names (e.g. 'llama-3.3-70b-versatile').

    Args:
        model: The model ID to validate.
        provider: Optional provider hint ('groq' skips the slash requirement).

    Returns:
        The validated and stripped model ID.

    Raises:
        ValueError: If the model ID is invalid.
    """
    if not model or not isinstance(model, str):
        raise ValueError("Model ID must be a non-empty string")
    model = model.strip()
    if len(model) > 200:
        raise ValueError("Model ID must be at most 200 characters")
    # Strip 'groq/' prefix if user accidentally included it
    if model.startswith("groq/"):
        model = model[len("groq/"):]
        return model
    # OpenRouter requires provider/model format; Groq uses plain names
    if provider != "groq" and "/" not in model:
        raise ValueError(
            f"Model ID must be in 'provider/model' format (got '{model}'). "
            "Check the exact id on OpenRouter or use --provider groq for Groq models."
        )
    return model


class LLMProvider:
    """Async LLM provider backed by OpenRouter (OpenAI-compatible API).

    Supports runtime model selection — every call can specify a different model.
    Falls back gracefully when structured output is not supported.
    """

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.groq_api_key = os.environ.get("GROQ_API_KEY", "")

    def _get_llm(
        self,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        provider: str | None = None,
    ) -> ChatOpenAI:
        """Create a ChatOpenAI instance pointed at OpenRouter or Groq."""
        provider = provider or self.config.provider
        
        if provider == "groq":
            api_key = self.groq_api_key
            base_url = "https://api.groq.com/openai/v1"
            # Strip groq/ prefix if user passed it (e.g. 'groq/llama-3.3-70b-versatile')
            if model and model.startswith("groq/"):
                model = model[len("groq/"):]
            # Fallback if no model specified or it's an OpenRouter-only model
            if not model or "/" in model:
                model = "llama-3.3-70b-versatile"
            # Groq free tier TPM = 12,000 (input + max_output_tokens counted together).
            # Use groq_max_tokens (default 4096) to stay within limits.
            effective_max_tokens = max_tokens or self.config.groq_max_tokens
        else:
            api_key = self.openrouter_api_key
            base_url = self.config.base_url
            model = model or self.config.default_model
            effective_max_tokens = max_tokens or self.config.max_tokens

        if not api_key:
            logger.warning(f"API Key for provider '{provider}' not set. LLM calls will fail.")

        return ChatOpenAI(
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=temperature if temperature is not None else self.config.temperature,
            max_tokens=effective_max_tokens,
            timeout=self.config.request_timeout,
        )

    async def call(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        provider: str | None = None,
    ) -> str:
        """Unstructured async text completion with retry logic.

        Args:
            prompt: The prompt text to send.
            model: Optional model override (OpenRouter/Groq ID).
            temperature: Optional temperature override.
            provider: Optional provider override ('groq' or 'openrouter').

        Returns:
            The model's text response.
        """
        llm = self._get_llm(model=model, temperature=temperature, provider=provider)

        for attempt in range(MAX_RETRIES):
            try:
                response = await llm.ainvoke(prompt)
                return response.content
            except Exception as e:
                if attempt < MAX_RETRIES - 1 and _is_retryable(e):
                    wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                    logger.warning(
                        f"LLM call failed (attempt {attempt + 1}/{MAX_RETRIES}), "
                        f"retrying in {wait:.1f}s: {e}"
                    )
                    await asyncio.sleep(wait)
                else:
                    raise

        raise RuntimeError("LLM call failed after all retries")  # unreachable

    async def call_structured(
        self,
        prompt: str,
        schema: Type[BaseModel],
        *,
        model: str | None = None,
        temperature: float | None = None,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Structured output with automatic fallback to JSON parsing.

        For Groq models, uses 'json_object' mode (llama-3.3-70b-versatile does
        not support 'json_schema'). For OpenRouter, tries 'json_schema' first.
        Falls back to raw completion + Pydantic validation for both.

        Args:
            prompt: The prompt text.
            schema: A Pydantic model class defining the expected output shape.
            model: Optional model override.
            temperature: Optional temperature override.
            provider: Optional provider override ('groq' or 'openrouter').

        Returns:
            A dict matching the schema.
        """
        effective_provider = provider or self.config.provider
        llm = self._get_llm(model=model, temperature=temperature, provider=provider)

        # Strategy 1: Native structured output
        # Groq's llama models support json_object but NOT json_schema.
        # Only openai/gpt-oss-* models on Groq support json_schema (strict mode).
        structured_output_method = "json_object" if effective_provider == "groq" else "json_schema"
        try:
            structured_llm = llm.with_structured_output(
                schema=schema, method=structured_output_method
            )
            result = await structured_llm.ainvoke(prompt)
            if isinstance(result, BaseModel):
                return result.model_dump()
            if isinstance(result, dict):
                return schema.model_validate(result).model_dump()
            return result
        except Exception as e:
            logger.info(
                f"Structured output not supported for this model, "
                f"falling back to JSON parsing: {e}"
            )

        # Strategy 2: Raw completion + JSON extraction
        json_prompt = (
            prompt
            + "\n\n---\n"
            + "IMPORTANT: Respond with ONLY valid JSON matching this schema. "
            + "No markdown, no explanation, just the JSON object.\n"
            + f"Schema: {json.dumps(schema.model_json_schema(), indent=2)}"
        )

        raw = await self.call(json_prompt, model=model, temperature=temperature, provider=provider)
        cleaned = _extract_json(raw)

        try:
            return schema.model_validate_json(cleaned).model_dump()
        except Exception:
            # Last resort: try to parse as dict and validate
            parsed = json.loads(cleaned)
            return schema.model_validate(parsed).model_dump()


def _is_retryable(error: Exception) -> bool:
    """Check if an error is transient and worth retrying."""
    error_str = str(error).lower()
    retryable_patterns = [
        "rate limit",
        "429",
        "503",
        "502",
        "500",
        "timeout",
        "connection",
        "temporarily",
    ]
    return any(pattern in error_str for pattern in retryable_patterns)


def _extract_json(text: str) -> str:
    """Extract a JSON object or array from text that may contain markdown fences."""
    # Try to extract from ```json ... ``` blocks
    match = re.search(r"```(?:json)?\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try to find raw JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0).strip()

    # Return as-is and let the caller handle parsing errors
    return text.strip()
