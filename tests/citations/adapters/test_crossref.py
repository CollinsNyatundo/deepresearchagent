import pytest
from unittest.mock import AsyncMock

from research_engine.citations.adapters.crossref import CrossRefAdapter
from research_engine.citations.parser import Citation


class TestCrossRefAdapter:
    """Integration-style tests: verify adapter behavior through public interface.
    HTTP client is mocked at system boundary.
    """

    @pytest.mark.asyncio
    async def test_lookup_by_doi_returns_metadata(self):
        """Given a DOI, adapter returns metadata from CrossRef response."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "status": 200,
            "json": lambda: {
                "message": {
                    "title": ["AI Progress in Healthcare"],
                    "author": [
                        {"family": "Smith", "given": "John"},
                        {"family": "Lee", "given": "Alice"},
                    ],
                    "published-print": {"date-parts": [[2020, 3, 15]]},
                    "DOI": "10.1234/example",
                    "URL": "https://doi.org/10.1234/example",
                }
            }
        }

        adapter = CrossRefAdapter(
            http_client=mock_http,
            email="test@example.com",
            rate_limit=10,
        )
        citation = Citation(doi="10.1234/example")

        result = await adapter.lookup(citation)

        assert result.found is True
        assert result.title == "AI Progress in Healthcare"
        assert result.authors == ["Smith, John", "Lee, Alice"]
        assert result.year == 2020
        assert result.confidence > 0.9

    @pytest.mark.asyncio
    async def test_lookup_by_title_returns_metadata(self):
        """Given a title (no DOI), adapter queries CrossRef by title."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "status": 200,
            "json": lambda: {
                "message": {
                    "items": [
                        {
                            "title": ["AI Progress in Healthcare"],
                            "author": [{"family": "Smith", "given": "John"}],
                            "published-print": {"date-parts": [[2020]]},
                            "DOI": "10.1234/example",
                        }
                    ]
                }
            }
        }

        adapter = CrossRefAdapter(http_client=mock_http, email="test@example.com")
        citation = Citation(title="AI Progress in Healthcare")

        result = await adapter.lookup(citation)

        assert result.found is True
        assert result.title == "AI Progress in Healthcare"
        assert result.year == 2020

    @pytest.mark.asyncio
    async def test_lookup_not_found_returns_not_found(self):
        """Given a DOI not in CrossRef, adapter returns not found."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {"status": 404, "json": lambda: {}}

        adapter = CrossRefAdapter(http_client=mock_http, email="test@example.com")
        citation = Citation(doi="10.9999/nonexistent")

        result = await adapter.lookup(citation)

        assert result.found is False
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_rate_limit_enforced(self):
        """Given multiple rapid requests exceeding limit, adapter throttles."""
        from unittest.mock import patch
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "status": 200,
            "json": lambda: {"message": {"title": ["Test"], "author": []}},
        }

        adapter = CrossRefAdapter(
            http_client=mock_http,
            email="test@example.com",
            rate_limit=5,  # 5 req/s
        )

        with patch("research_engine.citations.adapters.crossref.asyncio.sleep") as mock_sleep:
            for _ in range(6):  # 6th request triggers throttle
                await adapter.lookup(Citation(doi="10.1234/test"))

        # The 6th request should trigger a sleep to respect rate limit
        assert mock_sleep.call_count >= 1
        # Sleep should be for a positive duration (roughly 1 second minus elapsed)
        sleep_duration = mock_sleep.call_args[0][0]
        assert sleep_duration > 0

    @pytest.mark.asyncio
    async def test_lookup_includes_polite_email_in_user_agent(self):
        """Given an email, adapter includes it in User-Agent header."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {"status": 200, "json": lambda: {"message": {}}}

        adapter = CrossRefAdapter(http_client=mock_http, email="test@example.com")
        await adapter.lookup(Citation(doi="10.1234/test"))

        call_kwargs = mock_http.get.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert "User-Agent" in headers
        assert "test@example.com" in headers["User-Agent"]

    @pytest.mark.asyncio
    async def test_lookup_error_returns_not_found(self):
        """Given HTTP error, adapter returns not found without crashing."""
        mock_http = AsyncMock()
        mock_http.get.side_effect = Exception("Connection timeout")

        adapter = CrossRefAdapter(http_client=mock_http, email="test@example.com")
        citation = Citation(doi="10.1234/test")

        result = await adapter.lookup(citation)

        assert result.found is False
        assert result.confidence == 0.0
