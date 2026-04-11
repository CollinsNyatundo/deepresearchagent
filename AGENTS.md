# AGENTS.md — Agent Guidelines for Deep Research Agent

## Critical Rules

1. **All backend I/O must be async.** Use `await` for LLM calls (`ainvoke`), Scrapling fetches (`async_fetch`), and file I/O (`aiofiles`). Never use blocking calls in the FastAPI event loop.

2. **Model IDs are runtime parameters.** The LLM model is selected per-request via the API body (`model` field) or CLI flag (`--model`). The `config.toml` provides a default, but code must never assume a specific model. Use `LLMProvider._get_llm(model=...)` pattern.

3. **Scrapling is the sole scraping layer.** Do NOT add requests, httpx direct calls, or other scraping libraries. All web content fetching goes through `sources/web_scraper.py` which uses Scrapling's tiered fallback:
   - Tier 1: `StealthyFetcher.async_fetch()` (Camoufox — handles Cloudflare, bot detection)
   - Tier 2: `DynamicFetcher.async_fetch()` (Playwright — JS rendering)
   - Tier 3: `Fetcher.async_fetch()` (basic HTTP — static pages)

4. **Never commit secrets.** API keys live in `config.toml` (git-ignored) and environment variables. The `config.example.toml` has placeholder values only.

5. **Pydantic models are the source of truth.** All data structures are defined in `research_engine/models.py`. Frontend TypeScript types in `frontend/src/types/api.ts` must mirror these exactly. When modifying a model, update both files.

6. **Mantine for all UI.** Use Mantine components (AppShell, Tabs, Button, TextInput, Paper, etc.) for the frontend. Do not use raw HTML elements where a Mantine equivalent exists.

7. **AntV G6 v5 patterns.** Use the unified `Graph` class (not the deprecated `TreeGraph`). Mindmap layout configuration uses `type: 'mindmap'`, `direction: 'H'`. Node updates use `graph.changeData()`.

## Architecture Decisions (Do Not Reverse)

- **DRE is re-implemented**, not vendored. The original repo has no package distribution and is coupled to Gemini + Tavily. Our implementation is in `research_engine/agent/`.
- **Exhaustive depth (5) is the default.** This means up to 30 research cycles. Don't lower it without user consent.
- **OpenRouter is the LLM gateway.** All models are accessed via `https://openrouter.ai/api/v1` using `langchain-openai`'s `ChatOpenAI` with custom `base_url`.
- **Structured output has a fallback.** Free models may not support JSON schema mode. Always try `with_structured_output()` first, then fall back to raw completion + Pydantic `model_validate_json()`.

## Common Patterns

### Adding a new search provider
1. Create a class implementing `SearchProvider` protocol in `sources/web_search.py`
2. Add it to the `get_search_provider()` factory
3. Add its config key to `config.example.toml` under `[search]`

### Adding a new prompt
1. Add the template string to `llm/prompts.py`
2. If it requires structured output, define the Pydantic model in `models.py`
3. Call it via `llm_provider.call_structured(prompt, schema, model=model)`

### Adding a new API endpoint
1. Add the route in `api.py`
2. Add the corresponding function in `api/client.ts` on the frontend
3. If there's a new return type, add it to both `models.py` and `types/api.ts`

## Testing

```bash
# Backend tests (async)
pytest tests/ -v --asyncio-mode=auto

# Frontend type-check + build
cd frontend && npm run build

# Quick smoke test
research "test query" --depth 1 --no-crossover
```

## Known Gotchas

- **Camoufox binary**: Must run `python -m camoufox fetch` after first install. Without it, `StealthyFetcher` will fail and fall back to `DynamicFetcher`.
- **Playwright browsers**: Must run `python -m playwright install chromium`. Without it, `DynamicFetcher` will fail and fall back to `Fetcher`.
- **OpenRouter rate limits**: Free models have rate limits. The `LLMProvider` has retry logic with exponential backoff, but exhaustive research (depth=5) may hit limits. Consider adding a small delay between cycles.
- **Mantine PostCSS**: The `postcss-preset-mantine` and `postcss-simple-vars` plugins are required. Without them, Mantine styles break silently.
- **G6 container sizing**: The G6 graph container div MUST have explicit width/height. If it's 0×0, the graph renders invisibly.
