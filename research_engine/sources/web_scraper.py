"""Scrapling-based async web scraper with tiered fetcher fallback.

Uses Scrapling (by D4Vinci) — the adaptive Python web scraping library with:
- StealthyFetcher (Camoufox) — handles Cloudflare, bot detection, anti-fingerprinting
- DynamicFetcher (Playwright) — JS rendering for SPA / dynamic content
- Fetcher (basic HTTP) — fast, lightweight fallback for static pages

All fetchers support async via async_fetch().
"""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import urlparse

from research_engine.config import ScrapingConfig
from research_engine.models import ScrapedPage

logger = logging.getLogger(__name__)


class WebScraper:
    """Async web scraper with tiered Scrapling fetcher fallback.

    Fetcher chain (automatic fallback):
      1. StealthyFetcher — Camoufox browser, anti-bot stealth
      2. DynamicFetcher — Playwright Chromium, JS rendering
      3. Fetcher — basic HTTP (httpx), fast but no JS

    Each page is fetched, content extracted as text, and truncated to
    max_content_chars to fit within LLM context windows.
    """

    def __init__(self, config: ScrapingConfig | None = None):
        self.config = config or ScrapingConfig()

    async def fetch_page(self, url: str) -> ScrapedPage:
        """Fetch a single page with automatic fetcher fallback.

        Tries StealthyFetcher first, then DynamicFetcher, then basic Fetcher.
        Returns a ScrapedPage with the extracted content or error details.
        """
        for fetcher_name, fetcher_fn in self._get_fetcher_chain():
            try:
                logger.debug(f"Trying {fetcher_name} for {url}")
                page = await fetcher_fn(url)

                if page is not None and hasattr(page, "status") and page.status == 200:
                    scraped = self._extract_content(page, url, fetcher_name)
                    logger.info(
                        f"✓ Scraped {url} via {fetcher_name} "
                        f"({scraped.content_length} chars)"
                    )
                    return scraped
                else:
                    status = getattr(page, "status", "unknown") if page else "null"
                    logger.warning(f"{fetcher_name} returned status {status} for {url}")

            except Exception as e:
                logger.warning(f"{fetcher_name} failed for {url}: {type(e).__name__}: {e}")
                continue

        logger.error(f"✗ All fetchers failed for {url}")
        return ScrapedPage(
            url=url,
            success=False,
            error="All fetchers failed (stealthy → dynamic → basic)",
        )

    async def fetch_pages(
        self,
        urls: list[str],
        max_concurrent: int | None = None,
    ) -> list[ScrapedPage]:
        """Fetch multiple pages concurrently with a semaphore limit.

        Args:
            urls: List of URLs to scrape.
            max_concurrent: Max concurrent fetches (defaults to config).

        Returns:
            List of ScrapedPage results (order matches input URLs).
        """
        concurrency = max_concurrent or self.config.max_concurrent
        semaphore = asyncio.Semaphore(concurrency)

        async def _limited_fetch(url: str) -> ScrapedPage:
            async with semaphore:
                return await self.fetch_page(url)

        tasks = [_limited_fetch(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        pages: list[ScrapedPage] = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                logger.error(f"Exception scraping {url}: {result}")
                pages.append(ScrapedPage(
                    url=url, success=False, error=str(result),
                ))
            else:
                pages.append(result)

        return pages

    def _get_fetcher_chain(self):
        """Build the tiered fetcher chain based on config.

        Returns list of (name, async_callable) tuples.
        """
        chain = []
        tier = self.config.fetcher_tier.lower()
        timeout = self.config.timeout_ms

        # Tier 1: Stealthy (Camoufox — anti-bot, fingerprint resistant)
        if tier in ("stealthy", "all"):
            async def _stealthy_fetch(url: str):
                from scrapling.fetchers import StealthyFetcher
                return await StealthyFetcher.async_fetch(
                    url, headless=True, network_idle=True, timeout=timeout
                )
            chain.append(("stealthy", _stealthy_fetch))

        # Tier 2: Dynamic (Playwright — JS rendering)
        if tier in ("stealthy", "dynamic", "all"):
            async def _dynamic_fetch(url: str):
                from scrapling.fetchers import PlayWrightFetcher
                return await PlayWrightFetcher.async_fetch(
                    url, headless=True, disable_resources=True, timeout=timeout
                )
            chain.append(("dynamic", _dynamic_fetch))

        # Tier 3: Basic (HTTP — fast, no JS)
        async def _basic_fetch(url: str):
            from scrapling.fetchers import Fetcher
            return await Fetcher.async_fetch(url)

        chain.append(("basic", _basic_fetch))

        return chain

    def _extract_content(self, page, url: str, fetcher_name: str) -> ScrapedPage:
        """Extract text content from a Scrapling page response.

        Tries to get clean text content and truncates to max_content_chars.
        """
        title = ""
        content = ""

        try:
            # Try to get page title
            title_elem = page.css("title::text")
            if title_elem:
                title = title_elem.get("").strip()
        except Exception:
            pass

        try:
            # Get text content — method varies by Scrapling version
            if hasattr(page, "get_text"):
                content = page.get_text()
            elif hasattr(page, "text"):
                content = page.text if isinstance(page.text, str) else str(page.text)
            elif hasattr(page, "body"):
                content = page.body.decode("utf-8", errors="ignore") if isinstance(page.body, bytes) else str(page.body)
            else:
                content = str(page)
        except Exception as e:
            logger.warning(f"Content extraction failed for {url}: {e}")
            content = ""

        # Clean up the content
        content = _clean_content(content)

        # Truncate to configured max
        max_chars = self.config.max_content_chars
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n[... content truncated ...]"

        return ScrapedPage(
            url=url,
            title=title or _extract_title_from_url(url),
            content=content,
            status_code=getattr(page, "status", 200),
            content_length=len(content),
            success=True,
            fetcher_used=fetcher_name,
        )


def _clean_content(text: str) -> str:
    """Clean extracted text content — remove excessive whitespace and noise."""
    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove excessive spaces
    text = re.sub(r"[ \t]{3,}", "  ", text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def _extract_title_from_url(url: str) -> str:
    """Extract a readable title from a URL as fallback."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if path:
        # Use last path segment, replace hyphens/underscores with spaces
        segment = path.split("/")[-1]
        segment = re.sub(r"[-_]", " ", segment)
        segment = re.sub(r"\.\w+$", "", segment)  # Remove file extension
        return segment.title()
    return parsed.netloc
