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

from research_engine.config import ScrapingConfig
from research_engine.models import ScrapedPage

logger = logging.getLogger(__name__)


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

    def __init__(self, config: ScrapingConfig | None = None):
        self.config = config or ScrapingConfig()

    async def fetch_page(self, url: str) -> ScrapedPage:
        """Fetch a single page with automatic 4-tier fetcher fallback.

        Returns a ScrapedPage with extracted content or error details.
        """
        availability = get_fetcher_availability()
        chain = self._build_fetcher_chain(availability)

        if not chain:
            logger.error("No Scrapling fetchers available! Check installation.")
            return ScrapedPage(
                url=url,
                success=False,
                error="No Scrapling fetchers available",
            )

        last_error = ""
        for fetcher_name, fetcher_fn in chain:
            try:
                logger.debug(f"[{fetcher_name}] Trying {url}")
                page = await fetcher_fn(url)

                status = getattr(page, "status", None)
                if page is not None and status == 200:
                    scraped = self._extract_content(page, url, fetcher_name)
                    if scraped.content_length >= 50:
                        logger.info(
                            f"✓ [{fetcher_name}] Scraped {url} "
                            f"({scraped.content_length:,} chars)"
                        )
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
                continue
            except Exception as e:
                logger.warning(f"[{fetcher_name}] Failed for {url}: {type(e).__name__}: {e}")
                last_error = f"{type(e).__name__}: {e}"
                continue

        logger.error(f"✗ All fetchers failed for {url}. Last error: {last_error}")
        return ScrapedPage(
            url=url,
            success=False,
            error=f"All fetchers failed. Last: {last_error}",
        )

    async def fetch_pages(
        self,
        urls: list[str],
        max_concurrent: int | None = None,
    ) -> list[ScrapedPage]:
        """Fetch multiple pages concurrently with a semaphore limit."""
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
                pages.append(ScrapedPage(url=url, success=False, error=str(result)))
            else:
                pages.append(result)

        return pages

    def _build_fetcher_chain(
        self, availability: dict[str, bool]
    ) -> list[tuple[str, object]]:
        """Build the ordered fetcher chain based on tier config and availability.

        Returns list of (name, async_callable) tuples in priority order.
        """
        chain: list[tuple[str, object]] = []
        tier = self.config.fetcher_tier.lower()
        timeout_s = self.config.timeout_ms / 1000

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
                # DynamicFetcher.get() is sync — wrap in to_thread
                fetcher = DynamicFetcher(headless=True, disable_resources=True)
                return await asyncio.to_thread(
                    fetcher.get, url, follow_redirects=True, timeout=_timeout
                )

            chain.append(("dynamic_fetcher", _dynamic_fetch))

        # ── Tier 3: StealthyFetcher via patchright (stealth Chromium) ────────
        if availability.get("stealthy_patchright") and tier in ("stealthy", "all"):
            async def _stealthy_patchright_fetch(url: str, _timeout: float = timeout_s):
                from scrapling.fetchers import StealthyFetcher
                # StealthyFetcher.get() is sync — wrap in to_thread
                fetcher = StealthyFetcher(headless=True)
                return await asyncio.to_thread(
                    fetcher.get, url, follow_redirects=True, timeout=_timeout
                )

            chain.append(("stealthy_patchright", _stealthy_patchright_fetch))

        # ── Tier 4: StealthyFetcher + Camoufox Firefox (required, max stealth) ───
        if availability.get("stealthy_camoufox") and tier in ("stealthy", "all"):
            async def _stealthy_camoufox_fetch(url: str, _timeout: float = timeout_s):
                from scrapling.fetchers import StealthyFetcher
                # StealthyFetcher with camoufox=True uses Camoufox Firefox binary
                fetcher = StealthyFetcher(headless=True, camoufox=True)
                return await asyncio.to_thread(
                    fetcher.get, url, follow_redirects=True, timeout=_timeout
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

    def _extract_content(self, page, url: str, fetcher_name: str) -> ScrapedPage:
        """Extract text content from a Scrapling v0.4.5 Response object.

        Scrapling v0.4.5 API (verified):
          page.get_all_text()     → clean text, strips HTML tags (str)
          page.find("title")      → first matching element or None
          title_el.text           → element's text content (str)
          page.status             → HTTP status code (int)
          page.body               → raw bytes (fallback)

        Does NOT work in v0.4.5:
          page.text, page.content → don't exist on Response objects
          page.css("title::text") → parsel-style not supported
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

        # ── Extract body text ──────────────────────────────────────────────
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
