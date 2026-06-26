"""Citation verifier — orchestrates parser + adapters for verification."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum

from research_engine.citations.adapters.crossref import AdapterResult
from research_engine.citations.cache import VerificationCache
from research_engine.citations.parser import CitationParser


class CitationStatus(str, Enum):
    """Status of a citation verification."""
    VERIFIED = "verified"      # 2+ sources confirm
    UNVERIFIED = "unverified"  # 1 source confirms
    FAILED = "failed"          # 0 sources confirm or error


@dataclass(frozen=True)
class VerificationResult:
    """Result of citation verification."""
    status: CitationStatus
    found: bool
    title: str = ""
    authors: list[str] | None = None
    year: int | None = None
    doi: str = ""
    url: str = ""
    confidence: float = 0.0
    sources: int = 0
    databases: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerificationReport:
    """Aggregate report for batch verification."""
    total: int = 0
    verified_count: int = 0
    unverified_count: int = 0
    failed_count: int = 0
    verification_rate: float = 0.0
    results: list[VerificationResult] = field(default_factory=list)

    @classmethod
    def from_results(cls, results: list[VerificationResult]) -> VerificationReport:
        verified = sum(1 for r in results if r.status == CitationStatus.VERIFIED)
        unverified = sum(1 for r in results if r.status == CitationStatus.UNVERIFIED)
        failed = sum(1 for r in results if r.status == CitationStatus.FAILED)
        total = len(results)
        rate = verified / total if total > 0 else 0.0
        return cls(
            total=total,
            verified_count=verified,
            unverified_count=unverified,
            failed_count=failed,
            verification_rate=rate,
            results=results,
        )


class CitationVerifier:
    """Orchestrates citation parsing and external verification.

    Flow:
    1. Check cache first
    2. Parse citation string into structured Citation objects
    3. Query each adapter in parallel
    4. Score results (2+ sources = verified, 1 = unverified, 0 = failed)
    5. Cache and return
    """

    def __init__(
        self,
        parser: CitationParser,
        adapters: list,
        cache: VerificationCache | None = None,
    ):
        self._parser = parser
        self._adapters = adapters
        self._cache = cache or VerificationCache()

    async def verify(self, citation_text: str) -> VerificationResult:
        """Verify a citation string against external sources."""
        if not citation_text.strip():
            return VerificationResult(
                status=CitationStatus.FAILED, found=False, confidence=0.0
            )

        citations = self._parser.parse(citation_text)
        if not citations:
            return VerificationResult(
                status=CitationStatus.FAILED, found=False, confidence=0.0
            )

        citation = citations[0]
        cache_key = citation.doi or citation.title

        # Check cache
        if cache_key and (cached := self._cache.get(cache_key)):
            return cached

        if not self._adapters:
            return VerificationResult(
                status=CitationStatus.FAILED, found=False, confidence=0.0
            )

        # Query all adapters in parallel, catch errors individually
        results = await asyncio.gather(
            *[self._safe_lookup(adapter, citation) for adapter in self._adapters],
            return_exceptions=True,
        )

        # Filter out errors and not-found results
        successful = [
            r for r in results
            if isinstance(r, AdapterResult) and r.found
        ]

        result = self._score_results(successful)

        # Cache the result
        if cache_key:
            self._cache.set(cache_key, result)

        return result

    async def verify_batch(self, citations: list[str]) -> VerificationReport:
        """Verify multiple citations and return aggregate report."""
        results = []
        for text in citations:
            result = await self.verify(text)
            results.append(result)
        return VerificationReport.from_results(results)

    def _score_results(self, successful: list[AdapterResult]) -> VerificationResult:
        """Score results based on number of confirming sources."""
        if not successful:
            return VerificationResult(
                status=CitationStatus.FAILED,
                found=False,
                confidence=0.0,
                sources=0,
            )

        # Pick best result by confidence
        best = max(successful, key=lambda r: r.confidence)
        sources = len(successful)

        # Determine status based on source count
        if sources >= 2:
            status = CitationStatus.VERIFIED
        elif sources == 1:
            status = CitationStatus.UNVERIFIED
        else:
            status = CitationStatus.FAILED

        return VerificationResult(
            status=status,
            found=True,
            title=best.title,
            authors=best.authors,
            year=best.year,
            doi=best.doi,
            url=best.url,
            confidence=best.confidence,
            sources=sources,
            databases=[],
        )

    async def _safe_lookup(self, adapter, citation) -> AdapterResult:
        """Lookup with error handling."""
        try:
            return await adapter.lookup(citation)
        except Exception:
            return AdapterResult(found=False, confidence=0.0)
