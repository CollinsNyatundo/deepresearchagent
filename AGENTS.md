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

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **DeepResearchAgent** (456 symbols, 1392 relationships, 37 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/DeepResearchAgent/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/DeepResearchAgent/context` | Codebase overview, check index freshness |
| `gitnexus://repo/DeepResearchAgent/clusters` | All functional areas |
| `gitnexus://repo/DeepResearchAgent/processes` | All execution flows |
| `gitnexus://repo/DeepResearchAgent/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## Keeping the Index Fresh

After committing code changes, the GitNexus index becomes stale. Re-run analyze to update it:

```bash
npx gitnexus analyze
```

If the index previously included embeddings, preserve them by adding `--embeddings`:

```bash
npx gitnexus analyze --embeddings
```

To check whether embeddings exist, inspect `.gitnexus/meta.json` — the `stats.embeddings` field shows the count (0 means no embeddings). **Running analyze without `--embeddings` will delete any previously generated embeddings.**

> Claude Code users: A PostToolUse hook handles this automatically after `git commit` and `git merge`.

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
