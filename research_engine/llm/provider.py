"""LLM Provider — async OpenRouter access via LangChain, with runtime model selection."""

from __future__ import annotations

import asyncio
import functools
import hashlib
import json
import logging
import os
import re
import sqlite3
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from research_engine.config import LLMConfig, workspace_id_var
from pathlib import Path

logger = logging.getLogger(__name__)


class LLMSQLiteCache:
    def __init__(self, db_path: str = ".llm_cache.db"):
        self.db_path = db_path
        self._initialized_paths = set()

    @property
    def current_db_path(self) -> str:
        workspace_id = workspace_id_var.get()
        if workspace_id:
            path = Path("openkb") / workspace_id / "llm_cache.db"
            path.parent.mkdir(parents=True, exist_ok=True)
            return str(path)
        return self.db_path

    def _init_db(self, path: str):
        if path in self._initialized_paths:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            conn = sqlite3.connect(path)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA busy_timeout=5000;")
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS llm_cache (
                        key_hash TEXT PRIMARY KEY,
                        prompt TEXT,
                        model TEXT,
                        provider TEXT,
                        response TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
            finally:
                conn.close()
            self._initialized_paths.add(path)
        except Exception as e:
            logger.warning(f"Failed to initialize SQLite LLM cache at {path}: {e}")

    async def get(self, prompt: str, model: str, provider: str) -> str | None:
        db_path = self.current_db_path
        
        def _get():
            self._init_db(db_path)
            conn = sqlite3.connect(db_path)
            try:
                key = f"{prompt}:{model}:{provider}"
                key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA busy_timeout=5000;")
                cursor = conn.cursor()
                cursor.execute("SELECT response FROM llm_cache WHERE key_hash = ?", (key_hash,))
                row = cursor.fetchone()
                if row:
                    return row[0]
            except Exception as e:
                logger.warning(f"Failed to query SQLite LLM cache: {e}")
            finally:
                conn.close()
            return None

        return await asyncio.to_thread(_get)

    async def set(self, prompt: str, model: str, provider: str, response: str):
        db_path = self.current_db_path

        def _set():
            self._init_db(db_path)
            conn = sqlite3.connect(db_path)
            try:
                key = f"{prompt}:{model}:{provider}"
                key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA busy_timeout=5000;")
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO llm_cache (key_hash, prompt, model, provider, response) VALUES (?, ?, ?, ?, ?)",
                    (key_hash, prompt, model, provider, response)
                )
                conn.commit()
            except Exception as e:
                logger.warning(f"Failed to set SQLite LLM cache: {e}")
            finally:
                conn.close()

        await asyncio.to_thread(_set)


def cached_llm_query(func):
    @functools.wraps(func)
    async def wrapper(self, prompt: str, *args, **kwargs):
        use_cache = kwargs.get("use_cache", False)
        if not use_cache:
            kwargs_clean = {k: v for k, v in kwargs.items() if k != "use_cache"}
            return await func(self, prompt, *args, **kwargs_clean)

        model = kwargs.get("model") or getattr(self.config, "default_model", "default")
        provider = kwargs.get("provider") or getattr(self.config, "provider", "default")
        
        cache = getattr(self, "_sqlite_cache", None)
        if cache is None:
            cache = LLMSQLiteCache(db_path=os.path.join(os.getcwd(), ".llm_cache.db"))
            self._sqlite_cache = cache
            
        cached_val = await cache.get(prompt, model, provider)
        if cached_val is not None:
            logger.info("LLM cache hit!")
            if func.__name__ == "call_structured":
                return json.loads(cached_val)
            return cached_val

        kwargs_clean = {k: v for k, v in kwargs.items() if k != "use_cache"}
        result = await func(self, prompt, *args, **kwargs_clean)
        
        if func.__name__ == "call_structured":
            await cache.set(prompt, model, provider, json.dumps(result))
        else:
            await cache.set(prompt, model, provider, str(result))
            
        return result
    return wrapper



def validate_model_id(model: str, provider: str | None = None) -> str:
    """Validate a model ID string.

    OpenRouter model IDs follow the 'provider/model' format.
    Groq model IDs are plain names (e.g. 'llama-3.3-70b-versatile').
    NVIDIA model IDs are plain names (e.g. 'nemotron-3-super-120b-a12b').

    Args:
        model: The model ID to validate.
        provider: Optional provider hint ('groq' or 'nvidia' skips the slash requirement).

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
    # For NVIDIA direct API, keep the nvidia/ prefix
    # (models are e.g. 'nvidia/nemotron-3-super-120b-a12b')
    if provider == "nvidia" and model.startswith("nvidia/"):
        return model
    # OpenRouter requires provider/model format; Groq uses plain names
    if provider not in ("groq", "nvidia") and "/" not in model:
        raise ValueError(
            f"Model ID must be in 'provider/model' format (got '{model}'). "
            "Check the exact id on OpenRouter or use --provider groq for Groq models "
            "or --provider nvidia for NVIDIA models."
        )
    return model


class LLMProvider:
    """Async LLM provider backed by OpenRouter (OpenAI-compatible API).

    Supports runtime model selection — every call can specify a different model.
    Falls back gracefully when structured output is not supported.
    Includes rate limiting for Groq free tier (20 RPM).
    """

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.groq_api_key = os.environ.get("GROQ_API_KEY", "")
        self.nvidia_api_key = os.environ.get("NVIDIA_API_KEY", "")
        # Rate limiting: track last call time per provider
        self._last_call_time: dict[str, float] = {}

    async def _rate_limit(self, provider: str) -> None:
        """Enforce rate limits between LLM calls."""
        import time
        if provider == "groq":
            now = time.monotonic()
            last = self._last_call_time.get("groq", 0)
            elapsed = now - last
            min_interval = self.config.groq_min_interval
            if elapsed < min_interval:
                delay = min_interval - elapsed
                logger.debug(f"Groq rate limit: waiting {delay:.1f}s")
                await asyncio.sleep(delay)
            self._last_call_time["groq"] = time.monotonic()
        elif provider == "nvidia":
            # NVIDIA rate limit
            now = time.monotonic()
            last = self._last_call_time.get("nvidia", 0)
            elapsed = now - last
            min_interval = self.config.nvidia_min_interval
            if elapsed < min_interval:
                delay = min_interval - elapsed
                logger.debug(f"NVIDIA rate limit: waiting {delay:.1f}s")
                await asyncio.sleep(delay)
            self._last_call_time["nvidia"] = time.monotonic()

    def _get_llm(
        self,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        provider: str | None = None,
    ) -> ChatOpenAI:
        """Create a ChatOpenAI instance pointed at OpenRouter, Groq, or NVIDIA."""
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
        elif provider == "nvidia":
            api_key = self.nvidia_api_key
            base_url = "https://integrate.api.nvidia.com/v1"
            # NVIDIA direct API uses full model names WITH the nvidia/ prefix
            # e.g. 'nvidia/nemotron-3-super-120b-a12b'
            if model and model.startswith("nvidia/"):
                pass  # Keep the prefix for NVIDIA direct API
            if not model:
                model = "nvidia/nemotron-3-super-120b-a12b"
            effective_max_tokens = max_tokens or self.config.max_tokens
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

    @cached_llm_query
    async def call(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        provider: str | None = None,
        use_cache: bool = False,
    ) -> str:
        """Unstructured async text completion with retry logic.

        Args:
            prompt: The prompt text to send.
            model: Optional model override (OpenRouter/Groq ID).
            temperature: Optional temperature override.
            provider: Optional provider override ('groq' or 'openrouter').
            use_cache: Optional parameter to toggle local query caching.

        Returns:
            The model's text response.
        """
        llm = self._get_llm(model=model, temperature=temperature, provider=provider)
        effective_provider = provider or self.config.provider

        max_retries = self.config.max_retries
        for attempt in range(max_retries):
            try:
                await self._rate_limit(effective_provider)
                response = await llm.ainvoke(prompt)
                return response.content
            except Exception as e:
                if attempt < max_retries - 1 and _is_retryable(e):
                    wait = self.config.retry_backoff_base ** (attempt + 1)
                    logger.warning(
                        f"LLM call failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait:.1f}s: {e}"
                    )
                    await asyncio.sleep(wait)
                else:
                    raise

        raise RuntimeError("LLM call failed after all retries")  # unreachable

    @cached_llm_query
    async def call_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        *,
        model: str | None = None,
        temperature: float | None = None,
        provider: str | None = None,
        use_cache: bool = False,
    ) -> dict[str, Any]:
        """Structured output with automatic fallback to JSON parsing.

        For Groq models, uses 'json_mode' (llama-3.3-70b-versatile does
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
        # Groq's llama models support json_mode but NOT json_schema.
        # Only openai/gpt-oss-* models on Groq support json_schema (strict mode).
        structured_output_method = "json_mode" if effective_provider == "groq" else "json_schema"
        try:
            await self._rate_limit(effective_provider)
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
