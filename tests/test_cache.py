"""Tests for the local cache module."""

import pytest
import tempfile
import asyncio
from pathlib import Path
from research_engine.sources.cache import CacheManager
from research_engine.models import SearchResult, ScrapedPage

@pytest.fixture
def temp_db_path(tmp_path):
    return tmp_path / "test_cache.db"

@pytest.mark.asyncio
async def test_cache_initialization(temp_db_path):
    cache = CacheManager(db_path=temp_db_path)
    await cache.init_db()
    assert temp_db_path.exists()

def test_query_normalization():
    cache = CacheManager()
    assert cache.normalize_query("What is LLM?") == "is llm what"
    assert cache.normalize_query("hello, world!") == "hello world"
    assert cache.normalize_query("  A   b   C  ") == "a b c"
    assert cache.normalize_query("") == ""

@pytest.mark.asyncio
async def test_set_get_search_results(temp_db_path):
    cache = CacheManager(db_path=temp_db_path)
    await cache.init_db()

    query = "test query"
    results = [
        SearchResult(url="https://example.com/1", title="Title 1", snippet="Snippet 1"),
        SearchResult(url="https://example.com/2", title="Title 2", snippet="Snippet 2"),
    ]

    # Initially empty
    assert await cache.get_search_results(query) is None

    # Set cache
    await cache.set_search_results(query, results)

    # Get cache
    cached = await cache.get_search_results(query)
    assert cached is not None
    assert len(cached) == 2
    assert cached[0].url == "https://example.com/1"
    assert cached[0].title == "Title 1"
    assert cached[1].snippet == "Snippet 2"

    # Normalize variation check
    cached_var = await cache.get_search_results("Test Query!!!")
    assert cached_var is not None
    assert len(cached_var) == 2

    # Expired check
    expired = await cache.get_search_results(query, ttl_hours=0.0)
    assert expired is None

@pytest.mark.asyncio
async def test_set_get_scraped_page(temp_db_path):
    cache = CacheManager(db_path=temp_db_path)
    await cache.init_db()

    url = "https://example.com/page"
    page = ScrapedPage(
        url=url,
        title="My Page",
        content="Hello world content",
        status_code=200,
        content_length=19,
        success=True,
    )

    # Initially empty
    assert await cache.get_scraped_page(url) is None

    # Set cache
    await cache.set_scraped_page(page)

    # Get cache
    cached = await cache.get_scraped_page(url)
    assert cached is not None
    assert cached.url == url
    assert cached.title == "My Page"
    assert cached.content == "Hello world content"
    assert cached.content_length == 19
    assert cached.success is True

    # Expired check
    expired = await cache.get_scraped_page(url, ttl_hours=0.0)
    assert expired is None
