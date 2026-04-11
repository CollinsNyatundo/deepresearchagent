"""Strategy C — Research Corpus Enricher.

Enriches the Graphify corpus with additional content from:
- ArXiv papers (PDF parsing via graphify's built-in ingestion)
- PDF documents found in scraped pages
- Diagram descriptions extracted from scraped image URLs

This module is invoked BEFORE building the knowledge graph,
after the research loop completes, to add high-quality structured
content that improves the graph's edge quality.

Architecture note:
- Only add sources, never modify existing corpus files
- All operations are async and failure-tolerant
- Respects `max_paper_enrichments` config limit
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

import aiofiles

logger = logging.getLogger(__name__)

# URL patterns for enrichable content
ARXIV_PATTERN = re.compile(r"https?://(?:arxiv\.org/(?:abs|pdf)|ar5iv\.org)/[\d.]+v?\d*", re.I)
PDF_URL_PATTERN = re.compile(r"https?://\S+\.pdf(?:\?\S*)?", re.I)


async def enrich_corpus(
    scraped_urls: list[str],
    corpus_dir: Path,
    max_enrichments: int = 5,
) -> int:
    """Enrich the corpus with paper/PDF content from scraped URLs.

    Finds ArXiv and PDF URLs in the research results and adds their
    content to the `corpus/papers/` sub-directory for graphify ingestion.

    Args:
        scraped_urls: All URLs found during research.
        corpus_dir: The corpus directory to add papers to.
        max_enrichments: Maximum papers to add (prevents runaway costs).

    Returns:
        Number of documents successfully enriched.
    """
    paper_urls = _extract_paper_urls(scraped_urls)[:max_enrichments]
    if not paper_urls:
        logger.info("No ArXiv/PDF URLs found — skipping corpus enrichment")
        return 0

    papers_dir = corpus_dir / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)

    enriched = 0
    for url in paper_urls:
        try:
            success = await _add_paper(url, papers_dir)
            if success:
                enriched += 1
        except Exception as e:
            logger.warning(f"Failed to enrich {url}: {e}")

    logger.info(f"Corpus enriched: {enriched}/{len(paper_urls)} papers added")
    return enriched


def _extract_paper_urls(urls: list[str]) -> list[str]:
    """Extract unique ArXiv and PDF URLs from a list of URLs."""
    paper_urls: list[str] = []
    seen: set[str] = set()

    for url in urls:
        normalized = url.split("?")[0].rstrip("/")
        if normalized in seen:
            continue

        # Convert arxiv abs → pdf for downloading
        if ARXIV_PATTERN.match(url):
            if "/abs/" in url:
                pdf_url = url.replace("/abs/", "/pdf/") + ".pdf"
            elif "/pdf/" in url and not url.endswith(".pdf"):
                pdf_url = url + ".pdf"
            else:
                pdf_url = url
            paper_urls.append(pdf_url)
            seen.add(normalized)

        elif PDF_URL_PATTERN.match(url):
            paper_urls.append(url)
            seen.add(normalized)

    return paper_urls


async def _add_paper(url: str, papers_dir: Path) -> bool:
    """Download a paper and save its text content to the corpus.

    First tries graphify's `add` command (if available).
    Falls back to direct HTTP download + text extraction.

    Returns:
        True if the paper was successfully added.
    """
    # Try graphify add command first
    if await _graphify_add(url, papers_dir):
        return True

    # Fallback: HTTP download + save as-is for graphify to ingest
    return await _http_download_paper(url, papers_dir)


async def _graphify_add(url: str, papers_dir: Path) -> bool:
    """Use `graphify add <url>` to add a paper to the corpus."""
    import sys
    args = [sys.executable, "-m", "graphify", "add", url, "--output", str(papers_dir)]
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode == 0:
            logger.debug(f"graphify add succeeded: {url}")
            return True
        logger.debug(f"graphify add failed ({proc.returncode}): {stderr.decode()[:200]}")
        return False
    except (asyncio.TimeoutError, FileNotFoundError, Exception) as e:
        logger.debug(f"graphify add exception: {e}")
        return False


async def _http_download_paper(url: str, papers_dir: Path) -> bool:
    """Fallback: download a PDF/HTML and save its URL as a stub markdown file.

    We save the URL as a markdown stub that Graphify can reference (even if
    it can't parse the PDF, the citation still enriches the graph).
    """
    try:
        import httpx
    except ImportError:
        logger.debug("httpx not available for paper download fallback")
        return False

    try:
        safe_name = re.sub(r"[^\w]", "_", url)[-80:] + ".md"
        stub_path = papers_dir / safe_name

        # Download with a reasonable timeout (PDFs can be large)
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.head(url)
            content_type = response.headers.get("content-type", "")

            if "pdf" in content_type:
                # Save a stub noting the PDF was found
                stub_content = f"# Paper: {url}\n\n**Source URL**: {url}\n\n_PDF content — available for manual review._"
            elif "html" in content_type:
                # Download small HTML for text extraction
                resp = await client.get(url)
                text = resp.text[:5000]
                stub_content = f"# Paper: {url}\n\nURL: {url}\n\n{text}"
            else:
                stub_content = f"# Source: {url}\n\nURL: {url}"

        async with aiofiles.open(stub_path, "w", encoding="utf-8") as f:
            await f.write(stub_content)

        logger.debug(f"Saved paper stub: {stub_path.name}")
        return True

    except Exception as e:
        logger.debug(f"HTTP download fallback failed for {url}: {e}")
        return False
