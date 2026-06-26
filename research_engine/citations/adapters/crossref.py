"""CrossRef API adapter — async DOI resolution and title search."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass
class AdapterResult:
    """Result from a citation database adapter."""
    found: bool = False
    title: str = ""
    authors: list[str] = None
    year: int | None = None
    doi: str | None = None
    url: str | None = None
    confidence: float = 0.0

    def __post_init__(self):
        if self.authors is None:
            self.authors = []


class CrossRefAdapter:
    """Async adapter for CrossRef REST API.

    Deep module: public interface is one method (lookup).
    Implementation: HTTP requests, rate limiting, response parsing.
    """

    BASE_URL = "https://api.crossref.org/works"
    RATE_LIMIT = 10  # requests per second (polite pool)

    def __init__(self, http_client, email: str, rate_limit: int = RATE_LIMIT):
        self._http = http_client
        self._email = email
        self._rate_limit = rate_limit
        self._request_times: list[float] = []

    async def lookup(self, citation) -> AdapterResult:
        """Lookup a citation in CrossRef by DOI or title."""
        await self._throttle()

        try:
            if citation.doi:
                return await self._lookup_by_doi(citation.doi)
            return await self._lookup_by_title(citation.title)
        except Exception:
            return AdapterResult(found=False, confidence=0.0)

    async def _lookup_by_doi(self, doi: str) -> AdapterResult:
        """Query CrossRef by DOI."""
        url = f"{self.BASE_URL}/{doi}"
        headers = {"User-Agent": self._user_agent()}
        response = await self._http.get(url, headers=headers)

        if response.get("status") == 200:
            data = response["json"]()["message"]
            return AdapterResult(
                found=True,
                title=self._extract_title(data),
                authors=self._extract_authors(data),
                year=self._extract_year(data),
                doi=data.get("DOI", doi),
                url=data.get("URL"),
                confidence=0.95,
            )
        return AdapterResult(found=False, confidence=0.0)

    async def _lookup_by_title(self, title: str) -> AdapterResult:
        """Query CrossRef by title (fuzzy search)."""
        url = f"{self.BASE_URL}"
        params = {"query.title": title, "rows": 1}
        headers = {"User-Agent": self._user_agent()}
        response = await self._http.get(url, headers=headers, params=params)

        if response.get("status") == 200:
            items = response["json"]().get("message", {}).get("items", [])
            if items:
                data = items[0]
                return AdapterResult(
                    found=True,
                    title=self._extract_title(data),
                    authors=self._extract_authors(data),
                    year=self._extract_year(data),
                    doi=data.get("DOI"),
                    url=data.get("URL"),
                    confidence=0.85,  # Lower confidence for title search
                )
        return AdapterResult(found=False, confidence=0.0)

    def _user_agent(self) -> str:
        """Build polite User-Agent header with contact email."""
        return f"DRA/1.0 (mailto:{self._email})"

    async def _throttle(self):
        """Enforce rate limit: max N requests per second."""
        now = time.monotonic()
        # Keep only requests from the last second
        self._request_times = [t for t in self._request_times if now - t < 1.0]

        if len(self._request_times) >= self._rate_limit:
            # Calculate how long to sleep
            oldest = self._request_times[0]
            sleep_time = 1.0 - (now - oldest)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        self._request_times.append(time.monotonic())

    def _extract_title(self, data: dict) -> str:
        """Extract title from CrossRef response."""
        titles = data.get("title", [])
        return titles[0] if titles else ""

    def _extract_authors(self, data: dict) -> list[str]:
        """Extract author names from CrossRef response."""
        authors = []
        for author in data.get("author", []):
            family = author.get("family", "")
            given = author.get("given", "")
            if family and given:
                authors.append(f"{family}, {given}")
            elif family:
                authors.append(family)
        return authors

    def _extract_year(self, data: dict) -> int | None:
        """Extract publication year from CrossRef response."""
        for key in ["published-print", "published-online", "created"]:
            if key in data:
                date_parts = data[key].get("date-parts", [])
                if date_parts and date_parts[0]:
                    return date_parts[0][0]
        return None
