"""Domain-scoped circuit breaker for scraping resiliency."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class CircuitBreakerManager:
    """Tracks scraping failures per domain and triggers fail-fast behavior."""

    _shared_domains: dict[str, dict] = {}

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 300.0):
        self.failure_threshold = failure_threshold
        self.default_cooldown = cooldown_seconds
        # Share domains state across all instances
        self.domains = self._shared_domains

    def _get_domain(self, url: str) -> str:
        """Parse domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower() or url.lower()
        except Exception:
            return url.lower()

    def _init_domain(self, domain: str) -> dict:
        """Initialize domain state dictionary if not already tracked."""
        if domain not in self.domains:
            self.domains[domain] = {
                "state": "CLOSED",
                "fails": 0,
                "cooldown": self.default_cooldown,
                "last_fail": None,
            }
        return self.domains[domain]

    def check_circuit(self, url: str) -> bool:
        """Return True if scraping the URL is allowed, or False to fail-fast.

        If the circuit is OPEN but the cooldown has elapsed, transitions to HALF_OPEN.
        """
        domain = self._get_domain(url)
        state = self._init_domain(domain)

        if state["state"] == "CLOSED":
            return True

        if state["state"] == "OPEN":
            last_fail = state["last_fail"]
            if last_fail:
                elapsed = (datetime.now(timezone.utc) - last_fail).total_seconds()
                if elapsed >= state["cooldown"]:
                    logger.info(f"Circuit Breaker: Domain {domain} cooldown elapsed. Transitioning to HALF-OPEN.")
                    state["state"] = "HALF_OPEN"
                    return True
            logger.warning(f"Circuit Breaker: Domain {domain} is OPEN. Fail-fast block active.")
            return False

        # HALF_OPEN allows a single test request
        return True

    def register_success(self, url: str) -> None:
        """Register a successful scrape, closing the circuit if it was open."""
        domain = self._get_domain(url)
        state = self._init_domain(domain)

        if state["state"] != "CLOSED":
            logger.info(f"Circuit Breaker: Successful scrape on {domain}. Closing circuit.")
        
        state["state"] = "CLOSED"
        state["fails"] = 0
        state["cooldown"] = self.default_cooldown
        state["last_fail"] = None

    def register_failure(self, url: str) -> None:
        """Register a scrape failure. Trips circuit to OPEN if threshold is exceeded."""
        domain = self._get_domain(url)
        state = self._init_domain(domain)

        state["fails"] += 1
        state["last_fail"] = datetime.now(timezone.utc)

        if state["state"] == "HALF_OPEN":
            # Failure in HALF-OPEN state trips circuit back to OPEN and doubles cooldown
            state["state"] = "OPEN"
            state["cooldown"] *= 2
            logger.warning(
                f"Circuit Breaker: Test scrape failed on HALF-OPEN domain {domain}. "
                f"Tripping to OPEN. New cooldown: {state['cooldown']}s"
            )
        elif state["fails"] >= self.failure_threshold:
            state["state"] = "OPEN"
            logger.warning(
                f"Circuit Breaker: Domain {domain} exceeded {self.failure_threshold} consecutive failures. "
                f"Tripping circuit to OPEN."
            )
        else:
            logger.info(f"Circuit Breaker: Domain {domain} failure registered ({state['fails']}/{self.failure_threshold}).")
