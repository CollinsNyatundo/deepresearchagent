"""Scrapling-based async web scraper with 4-tier fetcher fallback.

Uses Scrapling v0.4.5 (D4Vinci) — the adaptive Python web scraping library.

Correct Scrapling v0.4.5 API:
  from scrapling.fetchers import AsyncFetcher, DynamicFetcher, StealthyFetcher, Fetcher

  # Tier 1 — AsyncFetcher: natively async curl_cffi HTTP (NO browser, no JS)
    page = await AsyncFetcher().get(url, follow_redirects=True)   # await directly!

  # Tier 2 — DynamicFetcher: sync Playwright Chromium JS rendering (wrapper in to_thread)
    page = await asyncio.to_thread(DynamicFetcher(headless=True).get, url)

  # Tier 3 — StealthyFetcher (patchright): stealth Chromium anti-bot (sync, to_thread)
    page = await asyncio.to_thread(StealthyFetcher(headless=True).get, url)

  # Tier 4 — StealthyFetcher (camoufox): Camoufox Firefox, best bypass (sync, to_thread)
    page = await asyncio.to_thread(StealthyFetcher(headless=True, camoufox=True).get, url)

  # Content extraction (all tiers):
    text = page.get_all_text()       # strips HTML tags, returns clean str
    title_el = page.find("title")    # None-safe element lookup
    status = page.status             # int HTTP status code

IMPORTANT — What NOT to do:
  - DO NOT wrap AsyncFetcher.get() in asyncio.to_thread() — it's already a coroutine
  - DO NOT use PlayWrightFetcher — it doesn't exist in v0.4.5
  - DO NOT use page.text or page.content — they don't exist on the Response object
  - DO NOT use page.css("title::text") — parsel-style selectors not supported

Fetcher chain order (fastest → most bypass capability):
  1. AsyncFetcher     — curl_cffi, <1s, no JS, works for ~60% of sites
  2. DynamicFetcher   — Playwright Chromium, JS rendering, handles SPAs
  3. StealthyFetcher  — patchright stealth Chromium, handles bot-detection
  4. StealthyFetcher  — Camoufox Firefox, maximum anti-detection (required)
"""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import urlparse
from typing import Any
from html.parser import HTMLParser

import httpx

from research_engine.config import ScrapingConfig
from research_engine.models import ScrapedPage

logger = logging.getLogger(__name__)


class MockResponse:
    """Mock response object mimicking Scrapling's Response interface for API fetchers."""

    def __init__(self, status: int, text: str, title: str = ""):
        self.status = status
        self.text_content = text
        self.title_content = title

    def get_all_text(self) -> str:
        return self.text_content

    def find(self, tag: str) -> Any:
        if tag == "title":
            class MockElement:
                text = self.title_content
            return MockElement()
        return None


VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr"
}


class BoilerplateStripper(HTMLParser):
    """HTML parser that strips boilerplate tags (nav, footer, ads) and custom class selectors."""

    def __init__(self, boilerplate_classes_regex=None):
        super().__init__()
        self.strip_tags = {
            "nav", "footer", "header", "aside", "script", "style", "form", "noscript", "iframe"
        }
        self.boilerplate_regex = boilerplate_classes_regex or re.compile(
            r"menu|sidebar|cookie|social|share|banner|ads", re.IGNORECASE
        )
        self.strip_stack = []
        self.cleaned_text_chunks: list[str] = []

    def _is_boilerplate(self, tag: str, attrs: list[tuple[str, str | None]]) -> bool:
        if tag in ("body", "html", "main", "article"):
            return False
        for attr, val in attrs:
            if attr in ("class", "id") and val:
                val_lower = val.lower()
                # Skip layout wraps/containers to avoid stripping main content
                if any(k in val_lower for k in ("wrap", "layout", "container", "content", "inner", "main", "body", "page")):
                    continue
                if self.boilerplate_regex.search(val):
                    return True
        return False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not self.strip_stack:
            should_strip = False
            if tag in self.strip_tags:
                should_strip = True
            elif self._is_boilerplate(tag, attrs):
                should_strip = True

            if should_strip:
                if tag not in VOID_ELEMENTS:
                    self.strip_stack.append(tag)
                return

        if self.strip_stack:
            if tag not in VOID_ELEMENTS:
                self.strip_stack.append(tag)
            return

        if tag in ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br", "tr"):
            self.cleaned_text_chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self.strip_stack:
            if tag not in VOID_ELEMENTS:
                if tag in self.strip_stack:
                    while self.strip_stack:
                        popped = self.strip_stack.pop()
                        if popped == tag:
                            break
            return

        if tag in ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"):
            self.cleaned_text_chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.strip_stack:
            self.cleaned_text_chunks.append(data)

    def get_cleaned_text(self) -> str:
        text = "".join(self.cleaned_text_chunks)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()


def smart_crusher_compress(content: str, query: str) -> str:
    """Query-guided sentence/paragraph level token compressor.

    Computes semantic overlap of query words with each paragraph.
    Keeps headings and paragraphs with overlap >= 0.2.
    """
    if not content or not query:
        return content

    # Normalize query terms
    query_words = set(re.findall(r"\w+", query.lower()))
    if not query_words:
        return content

    paragraphs = content.split("\n\n")
    kept_paragraphs = []

    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue

        # Tokenize paragraph words
        para_words = set(re.findall(r"\w+", para_clean.lower()))
        if not para_words:
            continue

        # Compute Jaccard overlap or simple intersection ratio
        overlap = len(query_words.intersection(para_words)) / len(query_words)

        # Keep if overlap ratio is >= 0.2, or if it's a heading
        if overlap >= 0.2 or para_clean.startswith("#"):
            kept_paragraphs.append(para_clean)

    compressed = "\n\n".join(kept_paragraphs)
    orig_len = len(content)
    comp_len = len(compressed)
    ratio = (1.0 - comp_len / orig_len) * 100 if orig_len > 0 else 0.0
    logger.info(f"SmartCrusher compressed content from {orig_len} to {comp_len} chars ({ratio:.1f}% reduction)")
    return compressed


def _check_fetcher_availability() -> dict[str, bool]:
    """Probe which Scrapling fetchers are importable on this machine."""
    available: dict[str, bool] = {}

    # Tier 1: AsyncFetcher (curl_cffi — always available with scrapling)
    try:
        from scrapling.fetchers import AsyncFetcher  # noqa: F401
        available["async"] = True
    except Exception:
        available["async"] = False

    # Tier 2: DynamicFetcher (Playwright — needs msgspec + playwright browser)
    try:
        from scrapling.fetchers import DynamicFetcher  # noqa: F401
        available["dynamic"] = True
    except Exception:
        available["dynamic"] = False

    # Tier 3: StealthyFetcher via patchright (needs patchright installed)
    try:
        from scrapling.fetchers import StealthyFetcher  # noqa: F401
        available["stealthy_patchright"] = True
    except Exception:
        available["stealthy_patchright"] = False

    # Tier 4: StealthyFetcher + camoufox=True (needs camoufox binary fetched)
    try:
        import camoufox  # noqa: F401
        available["stealthy_camoufox"] = available.get("stealthy_patchright", False)
    except Exception:
        available["stealthy_camoufox"] = False

    logger.info(f"Scrapling fetcher availability: {available}")
    return available


# Module-level availability cache — computed once at import time
_FETCHER_AVAILABILITY: dict[str, bool] | None = None


def get_fetcher_availability() -> dict[str, bool]:
    """Return cached fetcher availability, probing once per process lifetime."""
    global _FETCHER_AVAILABILITY
    if _FETCHER_AVAILABILITY is None:
        _FETCHER_AVAILABILITY = _check_fetcher_availability()
    return _FETCHER_AVAILABILITY


def reset_fetcher_cache() -> dict[str, bool]:
    """Force re-probe of fetcher availability and return fresh result.

    Call this after installing new packages (e.g. curl_cffi, playwright)
    without restarting the server.
    """
    global _FETCHER_AVAILABILITY
    _FETCHER_AVAILABILITY = None
    result = get_fetcher_availability()
    logger.info(f"Fetcher cache refreshed: {result}")
    return result


class WebScraper:
    """Async web scraper with 4-tier Scrapling fetcher fallback.

    Tier chain (automatic fallback, fastest → most stealthy):
      1. AsyncFetcher     — curl_cffi native async, handles most static/semi-dynamic sites
      2. DynamicFetcher   — Playwright Chromium, full JS rendering (SPAs, React, Vue)
      3. StealthyFetcher  — patchright stealth Chromium, anti-bot bypass
      4. StealthyFetcher  — Camoufox Firefox, maximum fingerprint spoofing (required)

    Each tier is tried in order. If one fails (import error, connection error,
    non-200 status), we fall back to the next tier automatically.

    All sync fetchers (Dynamic, Stealthy) are wrapped in asyncio.to_thread()
    so the FastAPI event loop is never blocked. AsyncFetcher is awaited directly.
    """

    def __init__(
        self,
        config: ScrapingConfig | None = None,
        cache_manager = None,
        circuit_breaker = None,
    ):
        self.config = config or ScrapingConfig()
        self.cache_manager = cache_manager
        self.circuit_breaker = circuit_breaker

    async def fetch_page(
        self,
        url: str,
        query: str | None = None,
        upgrade_context: bool = False,
        on_progress = None,
    ) -> ScrapedPage:
        """Fetch a single page with automatic 4-tier fetcher fallback.

        Returns a ScrapedPage with extracted content or error details.
        """
        # Check domain-scoped circuit breaker
        if self.circuit_breaker:
            if not self.circuit_breaker.check_circuit(url):
                logger.warning(f"Circuit Breaker tripped for {url}. Fail-fast skip.")
                if on_progress:
                    await on_progress(url, "SKIPPED_CIRCUIT", {"reason": "Circuit breaker is open"})
                return ScrapedPage(
                    url=url,
                    success=False,
                    error="Circuit breaker is open for this domain",
                )

        # Check local page cache (skip if upgrade_context)
        if self.cache_manager and not upgrade_context:
            cached = await self.cache_manager.get_scraped_page(url)
            if cached:
                if on_progress:
                    await on_progress(url, "CACHE_HIT", {"content_length": cached.content_length})
                return cached

        # Rewrite arXiv PDF URLs to abstract pages for high-reliability scraping
        if "arxiv.org/pdf/" in url:
            rewritten_url = url.replace("arxiv.org/pdf/", "arxiv.org/abs/")
            if rewritten_url.endswith(".pdf"):
                rewritten_url = rewritten_url[:-4]
            logger.info(f"Rewriting arXiv PDF URL {url} -> abstract page {rewritten_url}")
            url = rewritten_url

        availability = get_fetcher_availability()
        chain = self._build_fetcher_chain(availability, upgrade_context=upgrade_context)

        # Skip heavy browser fetchers for other PDFs to avoid slow browser failures
        is_pdf = url.lower().split("?")[0].endswith(".pdf")
        if is_pdf:
            chain = [item for item in chain if item[0] in ("async_fetcher", "basic_fetcher", "firecrawl_scrape", "parallel_extract")]
            logger.debug(f"Restricting fetchers to non-browser tiers for PDF URL: {url}")

        if not chain:
            logger.error("No Scrapling fetchers available! Check installation.")
            return ScrapedPage(
                url=url,
                success=False,
                error="No Scrapling fetchers available",
            )

        last_error = ""
        fallback_attempts: list[str] = []
        original_status: int | None = None

        for fetcher_name, fetcher_fn in chain:
            try:
                logger.debug(f"[{fetcher_name}] Trying {url}")
                if on_progress:
                    await on_progress(url, "TRYING_TIER", {"fetcher": fetcher_name})
                page = await fetcher_fn(url)

                status = getattr(page, "status", None)
                if original_status is None:
                    original_status = status

                fallback_attempts.append(f"{fetcher_name}: status {status}")

                if page is not None and status == 200:
                    scraped = self._extract_content(page, url, fetcher_name, query=query, upgrade_context=upgrade_context)
                    if scraped.content_length >= 50:
                        logger.info(
                            f"✓ [{fetcher_name}] Scraped {url} "
                            f"({scraped.content_length:,} chars)"
                        )
                        scraped.original_status = original_status
                        scraped.fallback_attempts = fallback_attempts

                        # Register success on circuit breaker and save to cache
                        if self.circuit_breaker:
                            self.circuit_breaker.register_success(url)
                        if self.cache_manager and not upgrade_context:
                            await self.cache_manager.set_scraped_page(scraped)

                        if on_progress:
                            await on_progress(url, "COMPLETE", {
                                "fetcher": fetcher_name,
                                "content_length": scraped.content_length
                            })
                        return scraped
                    else:
                        logger.warning(
                            f"[{fetcher_name}] Got 200 but empty/near-empty content "
                            f"({scraped.content_length} chars) for {url}, trying next tier"
                        )
                        last_error = f"Empty content ({scraped.content_length} chars)"
                else:
                    logger.warning(
                        f"[{fetcher_name}] Status {status} for {url}, trying next tier"
                    )
                    last_error = f"HTTP {status}"

            except ImportError as e:
                logger.warning(f"[{fetcher_name}] Not available: {e}")
                last_error = f"ImportError: {e}"
                fallback_attempts.append(f"{fetcher_name}: ImportError")
                continue
            except Exception as e:
                logger.warning(f"[{fetcher_name}] Failed for {url}: {type(e).__name__}: {e}")
                last_error = f"{type(e).__name__}: {e}"
                fallback_attempts.append(f"{fetcher_name}: {type(e).__name__}: {e}")
                continue

        logger.error(f"✗ All fetchers failed for {url}. Last error: {last_error}")

        # Register failure in circuit breaker
        if self.circuit_breaker:
            self.circuit_breaker.register_failure(url)

        if on_progress:
            await on_progress(url, "FAILED", {"error": last_error})
        return ScrapedPage(
            url=url,
            success=False,
            error=f"All fetchers failed. Last: {last_error}",
            original_status=original_status,
            fallback_attempts=fallback_attempts,
        )

    async def fetch_pages(
        self,
        urls: list[str],
        max_concurrent: int | None = None,
        query: str | None = None,
        upgrade_context: bool = False,
        on_progress = None,
    ) -> list[ScrapedPage]:
        """Fetch multiple pages concurrently with a semaphore limit."""
        concurrency = max_concurrent or self.config.max_concurrent
        semaphore = asyncio.Semaphore(concurrency)

        async def _limited_fetch(url: str) -> ScrapedPage:
            async with semaphore:
                if on_progress:
                    await on_progress(url, "START", {})
                return await self.fetch_page(
                    url, query=query, upgrade_context=upgrade_context, on_progress=on_progress
                )

        tasks = [_limited_fetch(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        pages: list[ScrapedPage] = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                logger.error(f"Exception scraping {url}: {result}")
                pages.append(ScrapedPage(url=url, success=False, error=str(result)))
            else:
                pages.append(result)

        return pages

    def _build_fetcher_chain(
        self, availability: dict[str, bool], upgrade_context: bool = False
    ) -> list[tuple[str, object]]:
        """Build the ordered fetcher chain based on tier config and availability.

        Returns list of (name, async_callable) tuples in priority order.
        """
        chain: list[tuple[str, object]] = []
        tier = self.config.fetcher_tier.lower()
        timeout_s = self.config.timeout_ms / 1000

        # ── Tier 0a: Parallel AI Extract (if API key available) ─────────────────
        if self.config.parallel_api_key:
            async def _parallel_fetch(url: str, _timeout: float = timeout_s):
                headers = {
                    "Authorization": f"Bearer {self.config.parallel_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {"url": url}
                async with httpx.AsyncClient(timeout=_timeout) as client:
                    resp = await client.post(
                        "https://api.parallel.ai/v1/extract",
                        json=payload,
                        headers=headers
                    )
                    resp.raise_for_status()
                    data = resp.json()
                content = data.get("text", "") or data.get("content", "") or data.get("extracted_content", "")
                title = data.get("title", "")
                return MockResponse(status=200, text=content, title=title)

            chain.append(("parallel_extract", _parallel_fetch))

        # ── Tier 0b: Firecrawl Scrape (if API key available) ────────────────────
        if self.config.firecrawl_api_key:
            async def _firecrawl_fetch(url: str, _timeout: float = timeout_s):
                headers = {
                    "Authorization": f"Bearer {self.config.firecrawl_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "url": url,
                    "formats": ["markdown"],
                    "onlyMainContent": not upgrade_context
                }
                async with httpx.AsyncClient(timeout=_timeout) as client:
                    resp = await client.post(
                        "https://api.firecrawl.dev/v1/scrape",
                        json=payload,
                        headers=headers
                    )
                    resp.raise_for_status()
                    data = resp.json()
                content = data.get("data", {}).get("markdown", "")
                title = data.get("data", {}).get("metadata", {}).get("title", "")
                return MockResponse(status=200, text=content, title=title)

            chain.append(("firecrawl_scrape", _firecrawl_fetch))

        # ── Tier 1: AsyncFetcher (curl_cffi, natively async) ─────────────────
        # Always included unless tier is explicitly "stealthy_only"
        if availability.get("async") and tier != "stealthy_only":
            async def _async_fetch(url: str, _timeout: float = timeout_s):
                from scrapling.fetchers import AsyncFetcher
                # AsyncFetcher.get() is a coroutine — await directly, NOT to_thread
                fetcher = AsyncFetcher()
                return await fetcher.get(url, follow_redirects=True, timeout=_timeout)

            chain.append(("async_fetcher", _async_fetch))

        # ── Tier 2: DynamicFetcher (Playwright Chromium, JS rendering) ───────
        # Included when tier is "dynamic", "stealthy", or "all"
        if availability.get("dynamic") and tier in ("dynamic", "stealthy", "all"):
            async def _dynamic_fetch(url: str, _timeout: float = timeout_s):
                from scrapling.fetchers import DynamicFetcher
                # DynamicFetcher.async_fetch is natively async
                return await DynamicFetcher.async_fetch(
                    url, headless=True, disable_resources=True, timeout=int(_timeout * 1000)
                )

            chain.append(("dynamic_fetcher", _dynamic_fetch))

        # ── Tier 3: StealthyFetcher via patchright (stealth Chromium) ────────
        if availability.get("stealthy_patchright") and tier in ("stealthy", "all"):
            async def _stealthy_patchright_fetch(url: str, _timeout: float = timeout_s):
                from scrapling.fetchers import StealthyFetcher
                # StealthyFetcher.async_fetch is natively async
                return await StealthyFetcher.async_fetch(
                    url, headless=True, timeout=int(_timeout * 1000)
                )

            chain.append(("stealthy_patchright", _stealthy_patchright_fetch))

        # ── Tier 4: StealthyFetcher + Camoufox Firefox (required, max stealth) ───
        if availability.get("stealthy_camoufox") and tier in ("stealthy", "all"):
            async def _stealthy_camoufox_fetch(url: str, _timeout: float = timeout_s):
                from scrapling.fetchers import StealthyFetcher
                # StealthyFetcher.async_fetch with camoufox=True is natively async
                return await StealthyFetcher.async_fetch(
                    url, headless=True, camoufox=True, timeout=int(_timeout * 1000)
                )

            chain.append(("stealthy_camoufox", _stealthy_camoufox_fetch))

        # ── Emergency fallback: sync Fetcher (always available) ───────────────
        # Only used if somehow async_fetcher wasn't added
        if not chain:
            async def _basic_fetch(url: str, _timeout: float = timeout_s):
                from scrapling.fetchers import Fetcher
                fetcher = Fetcher()
                return await asyncio.to_thread(
                    fetcher.get, url, follow_redirects=True, timeout=_timeout
                )

            chain.append(("basic_fetcher", _basic_fetch))
            logger.warning("Using emergency basic Fetcher — no higher tiers available!")

        return chain

    def _extract_content(self, page, url: str, fetcher_name: str, query: str | None = None, upgrade_context: bool = False) -> ScrapedPage:
        """Extract text content from a Scrapling v0.4.5 Response object.

        Includes DOM-based boilerplate removal using BoilerplateStripper before extraction.
        """
        title = ""
        content = ""

        # ── Extract title ──────────────────────────────────────────────────
        try:
            title_el = page.find("title")
            if title_el is not None:
                title = (title_el.text or "").strip()
        except Exception:
            pass

        # ── Extract body HTML & Run Boilerplate Stripping ──────────────────
        html_str = ""
        try:
            html_str = str(getattr(page, "html_content", ""))
            if not html_str:
                raw_body = getattr(page, "body", b"")
                if isinstance(raw_body, bytes):
                    html_str = raw_body.decode("utf-8", errors="ignore")
                elif isinstance(raw_body, str):
                    html_str = raw_body
        except Exception:
            pass

        if html_str and not upgrade_context:
            try:
                parser = BoilerplateStripper()
                parser.feed(html_str)
                content = parser.get_cleaned_text()
            except Exception as e:
                logger.warning(f"Boilerplate stripping failed for {url}: {e}, falling back to get_all_text")
                content = ""

        # ── Fallback: Extract standard body text ───────────────────────────
        if not content:
            try:
                raw_text = page.get_all_text()
                if isinstance(raw_text, str):
                    content = raw_text
                elif raw_text is not None:
                    content = str(raw_text)
            except AttributeError:
                # Fallback: decode raw bytes body
                try:
                    raw = getattr(page, "body", b"")
                    if isinstance(raw, bytes):
                        content = raw.decode("utf-8", errors="ignore")
                    elif isinstance(raw, str):
                        content = raw
                except Exception:
                    content = ""
            except Exception as e:
                logger.warning(f"Content extraction failed for {url}: {e}")
                content = ""

        # ── Clean and truncate ─────────────────────────────────────────────
        content = _clean_content(content)
        if query and not upgrade_context:
            content = smart_crusher_compress(content, query)
        max_chars = self.config.max_content_chars if not upgrade_context else self.config.max_content_chars * 5
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


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _clean_content(text: str) -> str:
    """Clean extracted text — remove excessive whitespace and noise."""
    if not text:
        return ""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{3,}", "  ", text)
    text = text.strip()
    return text


def _extract_title_from_url(url: str) -> str:
    """Extract a readable title from a URL as fallback."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if path:
        segment = path.split("/")[-1]
        segment = re.sub(r"[-_]", " ", segment)
        segment = re.sub(r"\.\w+$", "", segment)
        return segment.title()
    return parsed.netloc
