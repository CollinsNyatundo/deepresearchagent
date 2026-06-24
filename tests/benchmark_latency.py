import asyncio
import json
import sys
import time
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

# Import actual application components
from research_engine.agent.orchestrator import DeepResearchOrchestrator
from research_engine.config import AppConfig
from research_engine.models import (
    ResearchRequest,
    ResearchPlan,
    ResearchPlanReflection,
    ResearchProgress,
    ConfidenceScore,
    QueryDecomposition,
    QueryIntent,
    SearchQuery,
    SearchAnswer,
    RelevanceEvaluation,
    SearchResult,
    ScrapedPage
)

# Global counters for diagnostics
LLM_CALLS = 0
BROWSER_LAUNCHES = 0

class MockResponse:
    def __init__(self, status=200, text="# Mocked page content that has sufficient length for verification. It contains key terms related to deep research latency and scraper speed to avoid compression.", title="Mocked Title"):
        self.status = status
        self.text_content = text
        self.title_content = title
        self.html_content = f"<html><head><title>{title}</title></head><body><p>{text}</p></body></html>"

    def get_all_text(self) -> str:
        return self.text_content

    def find(self, tag: str) -> MagicMock | None:
        if tag == "title":
            element = MagicMock()
            element.text = self.title_content
            return element
        return None

async def run_benchmark():
    global LLM_CALLS, BROWSER_LAUNCHES
    LLM_CALLS = 0
    BROWSER_LAUNCHES = 0

    # 1. Setup Mock LLM calls with simulated delay matching instance method signatures
    async def mock_call(self_mock, prompt, *, model=None, provider=None, **kwargs):
        global LLM_CALLS
        LLM_CALLS += 1
        await asyncio.sleep(0.1)  # Simulate 100ms LLM processing time
        return "Simulated raw text LLM report completion."

    async def mock_call_structured(self_mock, prompt, schema, *, model=None, provider=None, **kwargs):
        global LLM_CALLS
        LLM_CALLS += 1
        await asyncio.sleep(0.15)  # Simulate 150ms structured output LLM latency

        if schema == ResearchPlan:
            return {"steps": ["Step 1: Ingest background data", "Step 2: Investigate codebase"]}
        elif schema == QueryDecomposition:
            return {"sub_queries": ["deep research latency components", "how to optimize scraper speed"]}
        elif schema == ResearchPlanReflection:
            return {"should_update": False, "updates": ""}
        elif schema == ResearchProgress:
            # First progress check returns 50, second returns 100 to make it terminate
            p = 100 if LLM_CALLS > 6 else 50
            return {"progress": p}
        elif schema == SearchQuery:
            return {"query": "simulated search query", "rationale": "benchmark reason"}
        elif schema == RelevanceEvaluation:
            return {"score": 9.0, "rationale": "Perfect match"}
        elif schema == SearchAnswer:
            return {"answer": "Simulated synthesized cycle answer.", "citations": []}
        elif schema == ConfidenceScore:
            return {"score": 0.95, "reasoning": "Sufficient findings", "needs_more_research": False}
        elif schema == QueryIntent:
            return {"category": "web", "rationale": "General search", "target_domains": [], "avoid_domains": []}
        
        return {}

    # 2. Setup Mock Search results
    async def mock_search(self_mock, query, max_results=10, **kwargs):
        await asyncio.sleep(0.1)  # Simulate 100ms search latency
        return [
            SearchResult(url="https://example.com/1", title="Result 1", snippet="Snippet 1"),
            SearchResult(url="https://example.com/2", title="Result 2", snippet="Snippet 2"),
            SearchResult(url="https://example.com/3", title="Result 3", snippet="Snippet 3"),
        ]

    # 3. Setup Mock Scrapling fetchers with launch cost simulation using *args, **kwargs
    async def mock_async_fetch(*args, **kwargs):
        await asyncio.sleep(0.05)  # Fast async HTTP call
        return MockResponse()

    async def mock_dynamic_fetch(*args, **kwargs):
        global BROWSER_LAUNCHES
        BROWSER_LAUNCHES += 1
        await asyncio.sleep(1.0)  # Heavy browser launch + fetch
        return MockResponse()

    async def mock_stealth_fetch(*args, **kwargs):
        global BROWSER_LAUNCHES
        BROWSER_LAUNCHES += 1
        # Detect if camoufox was requested
        camoufox = kwargs.get("camoufox", False)
        delay = 1.5 if camoufox else 1.2
        await asyncio.sleep(delay)  # Stealth browser launch cost
        return MockResponse()

    # We mock fetcher availability so all tiers are seen as available
    def mock_fetcher_availability():
        return {
            "async": True,
            "dynamic": True,
            "stealthy_patchright": True,
            "stealthy_camoufox": True
        }

    # Patch everything for the measurement run
    t0 = time.time()

    with patch("research_engine.sources.web_scraper.get_fetcher_availability", mock_fetcher_availability), \
         patch("research_engine.sources.web_scraper._check_fetcher_availability", mock_fetcher_availability), \
         patch("scrapling.fetchers.AsyncFetcher.get", mock_async_fetch), \
         patch("scrapling.fetchers.DynamicFetcher.async_fetch", mock_dynamic_fetch), \
         patch("scrapling.fetchers.StealthyFetcher.async_fetch", mock_stealth_fetch), \
         patch("research_engine.sources.web_search.DuckDuckGoSearch.search", mock_search), \
         patch("research_engine.sources.web_search.TavilySearch.search", mock_search), \
         patch("research_engine.sources.web_search.BraveSearchProvider.search", mock_search), \
         patch("research_engine.llm.provider.LLMProvider.call", mock_call), \
         patch("research_engine.llm.provider.LLMProvider.call_structured", mock_call_structured):

        config = AppConfig()
        # Force scraper to run through browser tiers for benchmark visibility
        config.scraping.fetcher_tier = "all"
        # Force max concurrent pages to 3
        config.scraping.max_concurrent = 3

        orchestrator = DeepResearchOrchestrator(config)
        request = ResearchRequest(
            query="optimize latency of deep research agent",
            depth=1,
            max_pages=2,
            enable_crossover=True  # Ensure crossover is on to test crossover LLM calls
        )

        try:
            result = await orchestrator.run(request)
            report_len = len(result.report)
        except Exception as e:
            print(f"Orchestrator execution crashed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            report_len = 0

    t1 = time.time()
    total_seconds = t1 - t0

    # 4. Run simple config test to assert tests_passed gate
    test_proc = subprocess.run(
        [".venv/Scripts/pytest", "tests/test_config.py", "-q"],
        capture_output=True,
        text=True
    )
    tests_passed = 1 if test_proc.returncode == 0 else 0

    metrics = {
        "total_seconds": float(total_seconds),
        "tests_passed": int(tests_passed),
        "report_length_chars": int(report_len),
        "llm_calls": int(LLM_CALLS),
        "browser_launches": int(BROWSER_LAUNCHES)
    }

    # Print the JSON output to stdout as required by ce-optimize
    print(json.dumps(metrics))

if __name__ == "__main__":
    asyncio.run(run_benchmark())
