"""Exhaustive tests for API adapter registry with concrete adapters."""
import pytest
from unittest.mock import AsyncMock

from research_engine.sources.adapters.registry import (
    APIAdapterRegistry,
    OpenAlexAdapter,
    ArXivAdapter,
    SECEDGARAdapter,
    HackerNewsAdapter,
    GitHubAdapter,
    GenericFallbackAdapter,
    AdapterResult,
)


class TestOpenAlexAdapter:
    """Tests for OpenAlex adapter."""

    @pytest.mark.asyncio
    async def test_query_returns_results(self):
        """Given query, returns academic results."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "json": lambda: {
                "results": [
                    {"display_name": "Paper 1", "id": "https://openalex.org/W1"},
                    {"display_name": "Paper 2", "id": "https://openalex.org/W2"},
                ],
                "meta": {"count": 2},
            }
        }

        adapter = OpenAlexAdapter(http_client=mock_http, email="test@example.com")
        result = await adapter.query({"q": "AI", "per_page": 10})

        assert result["success"] is True
        assert result["source"] == "openalex"
        assert len(result["data"]) == 2
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_query_no_http_returns_error(self):
        """Given no HTTP client, returns error."""
        adapter = OpenAlexAdapter(http_client=None)
        result = await adapter.query({"q": "AI"})
        assert result["success"] is False
        assert "No HTTP client" in result["error"]

    @pytest.mark.asyncio
    async def test_query_includes_email(self):
        """Given email, includes polite pool header."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {"json": lambda: {"results": [], "meta": {"count": 0}}}
        adapter = OpenAlexAdapter(http_client=mock_http, email="test@example.com")
        await adapter.query({"q": "AI"})
        call_kwargs = mock_http.get.call_args[1]
        assert "mailto" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_query_error_handling(self):
        """Given HTTP error, returns error result."""
        mock_http = AsyncMock()
        mock_http.get.side_effect = Exception("Connection timeout")
        adapter = OpenAlexAdapter(http_client=mock_http)
        result = await adapter.query({"q": "AI"})
        assert result["success"] is False
        assert "Connection timeout" in result["error"]


class TestArXivAdapter:
    """Tests for arXiv adapter."""

    @pytest.mark.asyncio
    async def test_query_returns_results(self):
        """Given query, returns arXiv results."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {"text": "<feed><entry><title>Test</title></entry></feed>"}
        adapter = ArXivAdapter(http_client=mock_http)
        result = await adapter.query({"q": "AI", "per_page": 5})
        assert result["success"] is True
        assert result["source"] == "arxiv"

    @pytest.mark.asyncio
    async def test_query_no_http_returns_error(self):
        """Given no HTTP client, returns error."""
        adapter = ArXivAdapter(http_client=None)
        result = await adapter.query({"q": "AI"})
        assert result["success"] is False


class TestSECEDGARAdapter:
    """Tests for SEC EDGAR adapter."""

    @pytest.mark.asyncio
    async def test_query_returns_filings(self):
        """Given CIK, returns filing results."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {"text": "<html>Filing results</html>"}
        adapter = SECEDGARAdapter(http_client=mock_http)
        result = await adapter.query({"q": "0001326801"})  # Apple CIK
        assert result["success"] is True
        assert result["source"] == "sec"
        assert "0001326801" in result["data"][0]["title"]

    @pytest.mark.asyncio
    async def test_query_no_http_returns_error(self):
        """Given no HTTP client, returns error."""
        adapter = SECEDGARAdapter(http_client=None)
        result = await adapter.query({"q": "0001326801"})
        assert result["success"] is False


class TestHackerNewsAdapter:
    """Tests for Hacker News adapter."""

    @pytest.mark.asyncio
    async def test_query_returns_stories(self):
        """Given query, returns HN stories."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "json": lambda: {
                "hits": [
                    {"title": "Story 1", "url": "https://example.com/1"},
                    {"title": "Story 2", "url": "https://example.com/2"},
                ],
                "nbHits": 2,
            }
        }
        adapter = HackerNewsAdapter(http_client=mock_http)
        result = await adapter.query({"q": "AI"})
        assert result["success"] is True
        assert result["source"] == "hn"
        assert len(result["data"]) == 2
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_query_no_http_returns_error(self):
        """Given no HTTP client, returns error."""
        adapter = HackerNewsAdapter(http_client=None)
        result = await adapter.query({"q": "AI"})
        assert result["success"] is False


class TestGitHubAdapter:
    """Tests for GitHub adapter."""

    @pytest.mark.asyncio
    async def test_query_returns_repos(self):
        """Given query, returns repositories."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {
            "json": lambda: {
                "items": [
                    {"full_name": "user/repo1", "html_url": "https://github.com/user/repo1"},
                    {"full_name": "user/repo2", "html_url": "https://github.com/user/repo2"},
                ],
                "total_count": 2,
            }
        }
        adapter = GitHubAdapter(http_client=mock_http, token="ghp_test")
        result = await adapter.query({"q": "AI framework", "per_page": 10})
        assert result["success"] is True
        assert result["source"] == "github"
        assert len(result["data"]) == 2

    @pytest.mark.asyncio
    async def test_query_includes_auth_header(self):
        """Given token, includes Authorization header."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {"json": lambda: {"items": [], "total_count": 0}}
        adapter = GitHubAdapter(http_client=mock_http, token="ghp_test")
        await adapter.query({"q": "AI"})
        call_kwargs = mock_http.get.call_args[1]
        assert "Authorization" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_query_no_http_returns_error(self):
        """Given no HTTP client, returns error."""
        adapter = GitHubAdapter(http_client=None)
        result = await adapter.query({"q": "AI"})
        assert result["success"] is False


class TestGenericFallbackAdapter:
    """Tests for generic fallback adapter."""

    @pytest.mark.asyncio
    async def test_query_returns_web_results(self):
        """Given query, returns web search results."""
        mock_http = AsyncMock()
        mock_http.get.return_value = {"text": "<html>Search results</html>"}
        adapter = GenericFallbackAdapter(http_client=mock_http)
        result = await adapter.query({"q": "AI"})
        assert result["success"] is True
        assert result["source"] == "fallback"

    @pytest.mark.asyncio
    async def test_query_no_http_returns_error(self):
        """Given no HTTP client, returns error."""
        adapter = GenericFallbackAdapter(http_client=None)
        result = await adapter.query({"q": "AI"})
        assert result["success"] is False


class TestAPIAdapterRegistry:
    """Tests for enhanced registry with circuit breaker."""

    @pytest.fixture
    def mock_db_adapter(self):
        mock = AsyncMock()
        mock.query.return_value = {"success": True, "data": [{"title": "Test"}], "source": "db"}
        return mock

    @pytest.fixture
    def failing_adapter(self):
        mock = AsyncMock()
        mock.query.return_value = {"success": False, "error": "Connection failed", "source": "fail"}
        return mock

    @pytest.mark.asyncio
    async def test_registry_routes_to_registered_adapter(self, mock_db_adapter):
        """Given registered adapter, registry routes queries to it."""
        registry = APIAdapterRegistry()
        registry.register("openalex", mock_db_adapter)
        result = await registry.query("openalex", {"q": "AI"})
        assert result["success"] is True
        assert result["source"] == "db"

    @pytest.mark.asyncio
    async def test_registry_falls_back(self):
        """Given unknown adapter, falls back to fallback."""
        fallback = AsyncMock()
        fallback.query.return_value = {"success": True, "data": [], "source": "fallback"}
        registry = APIAdapterRegistry(fallback=fallback)
        result = await registry.query("unknown", {"q": "AI"})
        assert result["success"] is True
        assert result["source"] == "fallback"

    def test_registry_lists_adapters(self, mock_db_adapter):
        """Given registered adapters, lists their names."""
        registry = APIAdapterRegistry()
        registry.register("openalex", mock_db_adapter)
        registry.register("github", mock_db_adapter)
        names = registry.list_adapters()
        assert "openalex" in names
        assert "github" in names

    @pytest.mark.asyncio
    async def test_registry_tracks_stats(self, mock_db_adapter):
        """Given queries, tracks statistics."""
        registry = APIAdapterRegistry()
        registry.register("openalex", mock_db_adapter)
        await registry.query("openalex", {"q": "AI"})
        stats = registry.get_stats("openalex")
        assert stats["total"] == 1
        assert stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_registry_circuit_breaker_opens(self, failing_adapter):
        """Given repeated failures, circuit breaker opens."""
        registry = APIAdapterRegistry()
        registry.register("fail", failing_adapter)
        # Trigger 5 failures
        for _ in range(5):
            await registry.query("fail", {"q": "AI"})
        # 6th query should be blocked by circuit breaker
        result = await registry.query("fail", {"q": "AI"})
        assert result["success"] is False
        assert "Circuit breaker" in result["error"]

    @pytest.mark.asyncio
    async def test_registry_query_all(self, mock_db_adapter):
        """Given query_all, queries all adapters in parallel."""
        registry = APIAdapterRegistry()
        registry.register("a", mock_db_adapter)
        registry.register("b", mock_db_adapter)
        results = await registry.query_all({"q": "AI"})
        assert "a" in results
        assert "b" in results
        assert results["a"]["success"] is True
        assert results["b"]["success"] is True

    @pytest.mark.asyncio
    async def test_registry_empty_raises(self):
        """Given no fallback, unknown adapter raises ValueError."""
        registry = APIAdapterRegistry()
        with pytest.raises(ValueError, match="No adapter registered"):
            await registry.query("unknown", {})

    @pytest.mark.asyncio
    async def test_registry_latency_tracking(self, mock_db_adapter):
        """Given query, tracks latency."""
        registry = APIAdapterRegistry()
        registry.register("openalex", mock_db_adapter)
        await registry.query("openalex", {"q": "AI"})
        stats = registry.get_stats("openalex")
        assert "latency_ms" in stats


class TestAdapterResult:
    """Tests for adapter result data model."""

    def test_default_values(self):
        """Given no args, has default values."""
        result = AdapterResult()
        assert result.success is True
        assert result.data == []
        assert result.total == 0
        assert result.error == ""

    def test_custom_values(self):
        """Given custom values, stores them."""
        result = AdapterResult(
            success=False,
            data=[{"title": "Test"}],
            total=1,
            source="openalex",
            error="Timeout",
            latency_ms=150.0,
        )
        assert result.success is False
        assert result.total == 1
        assert result.latency_ms == 150.0
