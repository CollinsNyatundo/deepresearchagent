import pytest
from unittest.mock import AsyncMock, patch

from research_engine.citations.adapters.openalex import OpenAlexAdapter
from research_engine.citations.parser import Citation


class TestOpenAlexAdapter:
    """Integration-style tests: verify adapter behavior through public interface.
    HTTP client is mocked at system boundary.
    """

    @pytest.mark.asyncio
    async def test_lookup_by_doi_returns_metadata(self):
        """Given a DOI, adapter returns metadata from OpenAlex response."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "status": 200,
            "json": lambda: {
                "title": "AI Progress in Healthcare",
                "authorships": [
                    {"author": {"display_name": "John Smith"}},
                    {"author": {"display_name": "Alice Lee"}},
                ],
                "publication_year": 2020,
                "doi": "https://doi.org/10.1234/example",
                "open_access": {"oa_url": "https://example.com/paper"},
            }
        }

        adapter = OpenAlexAdapter(http_client=mock_http, email="test@example.com")
        citation = Citation(doi="10.1234/example")

        result = await adapter.lookup(citation)

        assert result.found is True
        assert result.title == "AI Progress in Healthcare"
        assert result.authors == ["John Smith", "Alice Lee"]
        assert result.year == 2020
        assert result.doi == "10.1234/example"
        assert result.url == "https://example.com/paper"
        assert result.confidence > 0.9

    @pytest.mark.asyncio
    async def test_lookup_by_title_returns_metadata(self):
        """Given a title (no DOI), adapter queries OpenAlex by title."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "status": 200,
            "json": lambda: {
                "results": [
                    {
                        "title": "AI Progress in Healthcare",
                        "authorships": [
                            {"author": {"display_name": "John Smith"}}
                        ],
                        "publication_year": 2020,
                        "doi": "https://doi.org/10.1234/example",
                    }
                ]
            }
        }

        adapter = OpenAlexAdapter(http_client=mock_http, email="test@example.com")
        citation = Citation(title="AI Progress in Healthcare")

        result = await adapter.lookup(citation)

        assert result.found is True
        assert result.title == "AI Progress in Healthcare"
        assert result.year == 2020

    @pytest.mark.asyncio
    async def test_lookup_not_found_returns_not_found(self):
        """Given a DOI not in OpenAlex, adapter returns not found."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {"status": 404, "json": lambda: {}}

        adapter = OpenAlexAdapter(http_client=mock_http, email="test@example.com")
        citation = Citation(doi="10.9999/nonexistent")

        result = await adapter.lookup(citation)

        assert result.found is False
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_rate_limit_enforced(self):
        """Given rapid requests exceeding 100 req/5s, adapter throttles."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "status": 200,
            "json": lambda: {"title": ["Test"], "authorships": []},
        }

        adapter = OpenAlexAdapter(
            http_client=mock_http,
            email="test@example.com",
            rate_limit=100,  # 100 req/5s
        )

        with patch("research_engine.citations.adapters.openalex.asyncio.sleep") as mock_sleep:
            for _ in range(101):  # 101st request triggers throttle
                await adapter.lookup(Citation(doi="10.1234/test"))

        assert mock_sleep.call_count >= 1
        sleep_duration = mock_sleep.call_args[0][0]
        assert sleep_duration > 0

    @pytest.mark.asyncio
    async def test_lookup_error_returns_not_found(self):
        """Given HTTP error, adapter returns not found without crashing."""
        mock_http = AsyncMock()
        mock_http.get.side_effect = Exception("Connection timeout")

        adapter = OpenAlexAdapter(http_client=mock_http, email="test@example.com")
        citation = Citation(doi="10.1234/test")

        result = await adapter.lookup(citation)

        assert result.found is False
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_lookup_without_email(self):
        """Given no email, adapter still works without polite pool."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "status": 200,
            "json": lambda: {
                "title": "Test",
                "authorships": [],
                "publication_year": 2020,
                "doi": "https://doi.org/10.1234/test",
            }
        }

        adapter = OpenAlexAdapter(http_client=mock_http, email="")
        citation = Citation(doi="10.1234/test")

        result = await adapter.lookup(citation)

        assert result.found is True
        assert result.title == "Test"
