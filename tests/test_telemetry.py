"""Tests for the /api/telemetry endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient
from research_engine.api import app
from research_engine.sources.circuit_breaker import CircuitBreakerManager

client = TestClient(app)


def test_get_telemetry_empty():
    """Test telemetry endpoint returns cache stats and circuit status."""
    # Reset shared domains
    CircuitBreakerManager._shared_domains.clear()

    response = client.get("/api/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert "total_cached_queries" in data
    assert "total_scraped_pages" in data
    assert "active_circuit_breakers" in data
    assert "scraper_success_rate" in data
    assert data["active_circuit_breakers"] == []


def test_get_telemetry_with_open_circuit():
    """Test telemetry endpoint returns open circuit breaker domains."""
    CircuitBreakerManager._shared_domains.clear()
    cb = CircuitBreakerManager()
    cb.register_failure("https://failing-domain.com")
    cb.register_failure("https://failing-domain.com")
    cb.register_failure("https://failing-domain.com")

    # Should be open now
    assert cb.domains["failing-domain.com"]["state"] == "OPEN"

    response = client.get("/api/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert "failing-domain.com" in data["active_circuit_breakers"]
