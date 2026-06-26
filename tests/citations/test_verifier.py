import pytest
from unittest.mock import AsyncMock

from research_engine.citations.verifier import (
    CitationVerifier,
    VerificationResult,
    CitationStatus,
    VerificationReport,
)
from research_engine.citations.parser import CitationParser
from research_engine.citations.adapters.crossref import AdapterResult
from research_engine.citations.cache import VerificationCache


class TestCitationVerifier:
    """Integration-style tests for the citation verifier orchestrator."""

    @pytest.fixture
    def mock_crossref(self):
        mock = AsyncMock()
        mock.lookup.return_value = AdapterResult(
            found=True,
            title="AI Progress in Healthcare",
            authors=["Smith, John", "Lee, Alice"],
            year=2020,
            doi="10.1234/example",
            url="https://doi.org/10.1234/example",
            confidence=0.95,
        )
        return mock

    @pytest.fixture
    def mock_openalex(self):
        mock = AsyncMock()
        mock.lookup.return_value = AdapterResult(
            found=True,
            title="AI Progress in Healthcare",
            authors=["John Smith", "Alice Lee"],
            year=2020,
            doi="10.1234/example",
            url="https://example.com/paper",
            confidence=0.85,
        )
        return mock

    @pytest.fixture
    def verifier(self, mock_crossref, mock_openalex):
        return CitationVerifier(
            parser=CitationParser(),
            adapters=[mock_crossref, mock_openalex],
            cache=VerificationCache(),
        )

    @pytest.mark.asyncio
    async def test_verify_doi_citation_returns_verified(self, verifier, mock_crossref):
        """Given a citation with DOI found in both sources, returns verified."""
        citation_text = "See https://doi.org/10.1234/example for details."

        result = await verifier.verify(citation_text)

        assert result.status == CitationStatus.VERIFIED
        assert result.found is True
        assert result.title == "AI Progress in Healthcare"
        assert result.year == 2020
        assert result.confidence > 0.9
        assert result.sources >= 2
        mock_crossref.lookup.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_verify_one_source_returns_unverified(self):
        """Given a citation found in only one source, returns unverified."""
        crossref_mock = AsyncMock()
        crossref_mock.lookup.return_value = AdapterResult(
            found=True, title="Paper A", confidence=0.95, authors=[], year=None, doi="", url=""
        )
        openalex_mock = AsyncMock()
        openalex_mock.lookup.return_value = AdapterResult(
            found=False, confidence=0.0, authors=[], year=None, doi="", url=""
        )

        verifier = CitationVerifier(
            parser=CitationParser(),
            adapters=[crossref_mock, openalex_mock],
            cache=VerificationCache(),
        )

        result = await verifier.verify("See https://doi.org/10.1234/test")

        assert result.status == CitationStatus.UNVERIFIED
        assert result.found is True
        assert result.sources == 1

    @pytest.mark.asyncio
    async def test_verify_no_sources_returns_failed(self):
        """Given a citation not found anywhere, returns failed."""
        crossref_mock = AsyncMock()
        crossref_mock.lookup.return_value = AdapterResult(
            found=False, confidence=0.0, authors=[], year=None, doi="", url=""
        )
        openalex_mock = AsyncMock()
        openalex_mock.lookup.return_value = AdapterResult(
            found=False, confidence=0.0, authors=[], year=None, doi="", url=""
        )

        verifier = CitationVerifier(
            parser=CitationParser(),
            adapters=[crossref_mock, openalex_mock],
            cache=VerificationCache(),
        )

        result = await verifier.verify("See https://doi.org/10.1234/test")

        assert result.status == CitationStatus.FAILED
        assert result.found is False
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_verify_uses_cache_on_second_call(self, mock_crossref, mock_openalex):
        """Given a cached result, adapter is not called again."""
        cache = VerificationCache()
        verifier = CitationVerifier(
            parser=CitationParser(),
            adapters=[mock_crossref, mock_openalex],
            cache=cache,
        )

        # First call — hits adapters
        result1 = await verifier.verify("See https://doi.org/10.1234/example")
        assert result1.status == CitationStatus.VERIFIED
        assert mock_crossref.lookup.call_count == 1

        # Second call — should hit cache
        result2 = await verifier.verify("See https://doi.org/10.1234/example")
        assert result2.status == CitationStatus.VERIFIED
        # Adapter should not be called again
        assert mock_crossref.lookup.call_count == 1

    @pytest.mark.asyncio
    async def test_verify_empty_string_returns_failed(self, verifier):
        """Given empty citation string, verifier returns failed."""
        result = await verifier.verify("")

        assert result.status == CitationStatus.FAILED
        assert result.found is False

    @pytest.mark.asyncio
    async def test_verify_batch_returns_report(self):
        """Given multiple citations, returns aggregate verification report."""
        crossref_mock = AsyncMock()
        crossref_mock.lookup.side_effect = [
            AdapterResult(found=True, title="Paper A", confidence=0.95, authors=[], year=2020, doi="", url=""),
            AdapterResult(found=False, confidence=0.0, authors=[], year=None, doi="", url=""),
        ]
        openalex_mock = AsyncMock()
        openalex_mock.lookup.side_effect = [
            AdapterResult(found=True, title="Paper A", confidence=0.85, authors=[], year=2020, doi="", url=""),
            AdapterResult(found=False, confidence=0.0, authors=[], year=None, doi="", url=""),
        ]

        verifier = CitationVerifier(
            parser=CitationParser(),
            adapters=[crossref_mock, openalex_mock],
            cache=VerificationCache(),
        )

        citations = [
            "See https://doi.org/10.1234/example",
            "See https://doi.org/10.9999/nonexistent",
        ]

        report = await verifier.verify_batch(citations)

        assert report.total == 2
        assert len(report.results) == 2
        assert report.verification_rate == 0.5  # 1 verified out of 2
        assert report.verified_count == 1
        assert report.failed_count == 1

    def test_verification_report_from_results(self):
        """Given results, report computes correct counts."""
        results = [
            VerificationResult(status=CitationStatus.VERIFIED, found=True, confidence=0.95),
            VerificationResult(status=CitationStatus.UNVERIFIED, found=True, confidence=0.6),
            VerificationResult(status=CitationStatus.FAILED, found=False, confidence=0.0),
        ]

        report = VerificationReport.from_results(results)

        assert report.total == 3
        assert report.verified_count == 1
        assert report.unverified_count == 1
        assert report.failed_count == 1
        assert report.verification_rate == pytest.approx(1 / 3)
