"""SQLite-backed local cache for search queries and scraped web pages."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from research_engine.models import ScrapedPage, SearchResult

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages SQLite cache for query results and scraped pages to reduce latency and API usage."""

    def __init__(self, db_path: str | Path = "outputs/cache.db"):
        self.db_path = Path(db_path)

    async def init_db(self) -> None:
        """Asynchronously initialize the cache database tables."""

        def _init():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS query_cache (
                        normalized_query TEXT PRIMARY KEY,
                        results_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS page_cache (
                        url TEXT PRIMARY KEY,
                        content_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                """)
                conn.commit()

        await asyncio.to_thread(_init)

    def normalize_query(self, query: str) -> str:
        """Strip punctuation, lowercase, and alphabetically sort query keywords."""
        if not query:
            return ""
        # Keep alphanumeric characters and spaces
        cleaned = re.sub(r"[^\w\s]", "", query.lower())
        # Split into words, sort them, and rejoin
        words = sorted(cleaned.split())
        return " ".join(words)

    async def get_search_results(self, query: str, ttl_hours: float = 12.0) -> list[SearchResult] | None:
        """Retrieve cached search results for a query if within TTL."""
        normalized = self.normalize_query(query)
        if not normalized:
            return None

        def _get():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT results_json, created_at FROM query_cache WHERE normalized_query = ?",
                    (normalized,),
                )
                return cursor.fetchone()

        row = await asyncio.to_thread(_get)
        if not row:
            return None

        results_json, created_at_str = row
        try:
            created_at = datetime.fromisoformat(created_at_str)
            age = datetime.now(timezone.utc) - created_at
            if age.total_seconds() > ttl_hours * 3600:
                logger.info(f"Query cache expired for: {query}")
                return None

            logger.info(f"Query cache hit for: {query}")
            data = json.loads(results_json)
            return [SearchResult.model_validate(item) for item in data]
        except Exception as e:
            logger.warning(f"Error parsing cached search results: {e}")
            return None

    async def set_search_results(self, query: str, results: list[SearchResult]) -> None:
        """Cache search results for a query."""
        normalized = self.normalize_query(query)
        if not normalized:
            return

        def _set():
            data = [r.model_dump() for r in results]
            results_json = json.dumps(data)
            created_at_str = datetime.now(timezone.utc).isoformat()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO query_cache (normalized_query, results_json, created_at) "
                    "VALUES (?, ?, ?)",
                    (normalized, results_json, created_at_str),
                )
                conn.commit()

        await asyncio.to_thread(_set)

    async def get_scraped_page(self, url: str, ttl_hours: float = 24.0) -> ScrapedPage | None:
        """Retrieve cached page content for a URL if within TTL."""
        if not url:
            return None

        def _get():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT content_json, created_at FROM page_cache WHERE url = ?",
                    (url,),
                )
                return cursor.fetchone()

        row = await asyncio.to_thread(_get)
        if not row:
            return None

        content_json, created_at_str = row
        try:
            created_at = datetime.fromisoformat(created_at_str)
            age = datetime.now(timezone.utc) - created_at
            if age.total_seconds() > ttl_hours * 3600:
                logger.info(f"Page cache expired for URL: {url}")
                return None

            logger.info(f"Page cache hit for URL: {url}")
            data = json.loads(content_json)
            return ScrapedPage.model_validate(data)
        except Exception as e:
            logger.warning(f"Error parsing cached scraped page: {e}")
            return None

    async def set_scraped_page(self, page: ScrapedPage) -> None:
        """Cache scraped page contents."""
        if not page or not page.url:
            return

        def _set():
            content_json = page.model_dump_json()
            created_at_str = datetime.now(timezone.utc).isoformat()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO page_cache (url, content_json, created_at) VALUES (?, ?, ?)",
                    (page.url, content_json, created_at_str),
                )
                conn.commit()

        await asyncio.to_thread(_set)
