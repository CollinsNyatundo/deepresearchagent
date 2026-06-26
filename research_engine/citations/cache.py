"""In-memory verification cache with TTL."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CacheEntry:
    """A cached verification result."""
    result: Any
    timestamp: float


class VerificationCache:
    """Simple in-memory cache with TTL for verification results.

    Key: DOI or title (lowercase, stripped)
    Value: AdapterResult with timestamp
    """

    def __init__(self, ttl_seconds: float = 3600.0):
        self._ttl = ttl_seconds
        self._store: dict[str, CacheEntry] = {}

    def _key(self, identifier: str) -> str:
        return identifier.lower().strip()

    def get(self, identifier: str) -> Any | None:
        """Retrieve cached result if not expired."""
        key = self._key(identifier)
        entry = self._store.get(key)
        if not entry:
            return None
        if time.monotonic() - entry.timestamp > self._ttl:
            del self._store[key]
            return None
        return entry.result

    def set(self, identifier: str, result: Any) -> None:
        """Store result in cache."""
        self._store[self._key(identifier)] = CacheEntry(
            result=result,
            timestamp=time.monotonic(),
        )

    def clear(self) -> None:
        """Clear all cache entries."""
        self._store.clear()

    def size(self) -> int:
        """Return number of cached entries."""
        return len(self._store)
