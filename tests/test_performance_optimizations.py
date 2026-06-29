import pytest
import shutil
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from research_engine.config import workspace_id_var, LLMConfig
from research_engine.llm.provider import LLMSQLiteCache
from research_engine.sources.cache import CacheManager
from research_engine.models import SearchResult, ScrapedPage, ResearchPlan
from research_engine.agent.searcher import _tfidf_score, pre_filter_search_results, generate_query_batch


@pytest.fixture(autouse=True)
def cleanup_workspace_dirs():
    """Ensure any test workspace directories are cleaned up."""
    yield
    # Cleanup openkb/test-ws1 and test-ws2 if they exist
    for ws in ["test-ws1", "test-ws2"]:
        p = Path("openkb") / ws
        if p.exists():
            shutil.rmtree(p)


@pytest.mark.asyncio
async def test_workspace_cache_isolation(tmp_path):
    # Base path
    default_db = tmp_path / "global_cache.db"
    
    # Initialize CacheManager
    cache = CacheManager(db_path=default_db)
    
    # 1. Verify path without workspace_id
    workspace_id_var.set(None)
    assert cache.current_db_path == default_db
    
    # 2. Verify path with workspace_id
    workspace_id_var.set("test-ws1")
    expected_path = Path("openkb") / "test-ws1" / "cache.db"
    assert cache.current_db_path == expected_path
    
    # Initialize DB for test-ws1
    await cache.init_db()
    assert expected_path.exists()
    
    # Set search results in test-ws1
    query = "performance optimization"
    results = [SearchResult(url="https://example.com/opt", title="Opt", snippet="Snippet Opt")]
    await cache.set_search_results(query, results)
    
    # Get in test-ws1 (should be found)
    cached_ws1 = await cache.get_search_results(query)
    assert cached_ws1 is not None
    assert cached_ws1[0].url == "https://example.com/opt"
    
    # Switch to test-ws2
    workspace_id_var.set("test-ws2")
    # Get in test-ws2 (should NOT be found - isolation check!)
    cached_ws2 = await cache.get_search_results(query)
    assert cached_ws2 is None
    
    # Clean contextvar
    workspace_id_var.set(None)


def test_tfidf_snippet_scoring():
    # 1. Short snippet (<20 characters) should score 0.0
    assert _tfidf_score("query term", "too short") == 0.0
    
    # 2. Score check for matches
    score_match = _tfidf_score("python async performance", "This article talks about python async performance optimizations in SQLite databases.")
    assert score_match > 0.1
    
    # 3. Score check for no overlap
    score_no_match = _tfidf_score("python async", "A recipe for chocolate chip cookies with butter and milk.")
    assert score_no_match == 0.0
    
    # 4. Pre-filtering integration
    results = [
        SearchResult(url="url1", snippet="too short"),
        SearchResult(url="url2", snippet="This is a text about python async performance optimizations."),
        SearchResult(url="url3", snippet="A recipe for chocolate chip cookies with butter and milk."),
    ]
    
    keep, filtered = pre_filter_search_results("python async", results, min_score=0.05)
    assert len(keep) == 1
    assert keep[0].url == "url2"
    assert len(filtered) == 2
    assert filtered[0].url == "url1"
    assert filtered[1].url == "url3"


@pytest.mark.asyncio
async def test_batch_query_generation():
    llm_mock = AsyncMock()
    # Mock call_structured to return a SearchQueryBatch
    llm_mock.call_structured.return_value = {
        "queries": [
            {"query": "query one", "rationale": "first angle"},
            {"query": "query two", "rationale": "second angle"}
        ]
    }
    
    plan = ResearchPlan(steps=["step 1"])
    queries = await generate_query_batch("topic", plan, "history", llm=llm_mock)
    
    assert len(queries) == 2
    assert queries[0].query == "query one"
    assert queries[1].query == "query two"
    llm_mock.call_structured.assert_called_once()
