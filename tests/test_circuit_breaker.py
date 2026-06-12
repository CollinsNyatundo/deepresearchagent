"""Tests for the domain-scoped circuit breaker."""

import pytest
from datetime import datetime, timezone, timedelta
from research_engine.sources.circuit_breaker import CircuitBreakerManager

@pytest.fixture(autouse=True)
def clear_circuit_breaker_shared_state():
    CircuitBreakerManager._shared_domains.clear()

def test_domain_parsing():
    cb = CircuitBreakerManager()
    assert cb._get_domain("https://example.com/some/path?param=1") == "example.com"
    assert cb._get_domain("http://sub.domain.org") == "sub.domain.org"
    assert cb._get_domain("example.com") == "example.com"

def test_initial_state():
    cb = CircuitBreakerManager()
    url = "https://example.com"
    assert cb.check_circuit(url) is True
    domain = cb._get_domain(url)
    assert cb.domains[domain]["state"] == "CLOSED"

def test_trip_to_open():
    cb = CircuitBreakerManager(failure_threshold=3, cooldown_seconds=60)
    url = "https://example.com"

    # Register 2 failures, still CLOSED
    cb.register_failure(url)
    cb.register_failure(url)
    assert cb.check_circuit(url) is True

    # Register 3rd failure, transitions to OPEN
    cb.register_failure(url)
    assert cb.check_circuit(url) is False
    domain = cb._get_domain(url)
    assert cb.domains[domain]["state"] == "OPEN"

def test_cooldown_to_half_open():
    cb = CircuitBreakerManager(failure_threshold=3, cooldown_seconds=1.0)
    url = "https://example.com"

    # Trip the circuit
    cb.register_failure(url)
    cb.register_failure(url)
    cb.register_failure(url)
    assert cb.check_circuit(url) is False

    # Simulate cooldown elapsed by setting last_fail in the past
    domain = cb._get_domain(url)
    cb.domains[domain]["last_fail"] = datetime.now(timezone.utc) - timedelta(seconds=2)

    # Check should transition to HALF_OPEN and allow scrape
    assert cb.check_circuit(url) is True
    assert cb.domains[domain]["state"] == "HALF_OPEN"

def test_success_on_half_open():
    cb = CircuitBreakerManager(failure_threshold=3, cooldown_seconds=60)
    url = "https://example.com"
    domain = cb._get_domain(url)

    # Trip and force HALF_OPEN
    cb.register_failure(url)
    cb.register_failure(url)
    cb.register_failure(url)
    cb.domains[domain]["state"] = "HALF_OPEN"

    # Register success, transitions to CLOSED and resets failures
    cb.register_success(url)
    assert cb.check_circuit(url) is True
    assert cb.domains[domain]["state"] == "CLOSED"
    assert cb.domains[domain]["fails"] == 0

def test_failure_on_half_open_doubles_cooldown():
    cb = CircuitBreakerManager(failure_threshold=3, cooldown_seconds=10.0)
    url = "https://example.com"
    domain = cb._get_domain(url)

    # Trip and force HALF_OPEN
    cb.register_failure(url)
    cb.register_failure(url)
    cb.register_failure(url)
    cb.domains[domain]["state"] = "HALF_OPEN"

    # Register failure on HALF_OPEN
    cb.register_failure(url)
    assert cb.domains[domain]["state"] == "OPEN"
    assert cb.domains[domain]["cooldown"] == 20.0  # Doubled from 10.0
