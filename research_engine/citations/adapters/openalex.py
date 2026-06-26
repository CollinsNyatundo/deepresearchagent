"""OpenAlex API adapter for citation verification."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AdapterResult:
    """Result of a citation lookup from an external API."""
    found: bool
    title: str = ""
    authors: list[str] | None = None
    year: int | None = None
    doi: str = ""
    url: str = ""
    confidence: float = 0.0
    raw: dict[str, Any] | None = None


class OpenAlexAdapter:
    """Adapter for OpenAlex REST API (https://api.openalex.org).

    Uses the polite pool when an email is provided (better rate limits).
    Rate limit: 100 requests per 5 seconds (20 req/s).
    """

    BASE_URL = "https://api.openalex.org/works"

    def __init__(
        self,
        *,
        http_client,
        email: str = "",
        rate_limit: int = 100,
    ):
        self._http = http_client
        self._email = email
        self._rate_limit = rate_limit
        self._request_times: list[float] = []

    def _user_agent(self) -> str:
        if self._email:
            return f"DeepResearchAgent/1.0 (mailto:{self._email})"
        return "DeepResearchAgent/1.0"

    async def _throttle(self):
        """Enforce rate limit: 100 req/5s → sleep if exceeded."""
        now = time.monotonic()
        window = 5.0  # 5-second window
        self._request_times = [t for t in self._request_times if now - t < window]

        if len(self._request_times) >= self._rate_limit:
            oldest = self._request_times[0]
            sleep_time = window - (now - oldest)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        self._request_times.append(time.monotonic())

    async def lookup(self, citation) -> AdapterResult:
        """Lookup a citation in OpenAlex.

        Uses DOI if available, otherwise falls back to title search.
        """
        await self._throttle()
        try:
            if citation.doi:
                return await self._lookup_by_doi(citation.doi)
            return await self._lookup_by_title(citation.title)
        except Exception:
            return AdapterResult(found=False, confidence=0.0)

    async def _lookup_by_doi(self, doi: str) -> AdapterResult:
        """Query OpenAlex by DOI."""
        url = f"{self.BASE_URL}/{doi}"
        headers = {"User-Agent": self._user_agent()}
        response = await self._http.get(url, headers=headers)

        if response.get("status") == 200:
            data = response["json"]()
            return AdapterResult(
                found=True,
                title=self._extract_title(data),
                authors=self._extract_authors(data),
                year=self._extract_year(data),
                doi=self._extract_doi(data),
                url=self._extract_url(data),
                confidence=0.95,
                raw=data,
            )
        return AdapterResult(found=False, confidence=0.0)

    async def _lookup_by_title(self, title: str) -> AdapterResult:
        """Query OpenAlex by title (fuzzy search)."""
        url = f"{self.BASE_URL}"
        params = {"filter": f"title.search:{title}", "per-page": 1}
        headers = {"User-Agent": self._user_agent()}
        response = await self._http.get(url, headers=headers, params=params)

        if response.get("status") == 200:
            data = response["json"]()
            results = data.get("results", [])
            if results:
                item = results[0]
                return AdapterResult(
                    found=True,
                    title=self._extract_title(item),
                    authors=self._extract_authors(item),
                    year=self._extract_year(item),
                    doi=self._extract_doi(item),
                    url=self._extract_url(item),
                    confidence=0.85,
                    raw=item,
                )
        return AdapterResult(found=False, confidence=0.0)

    def _extract_title(self, data: dict) -> str:
        return data.get("title", "")

    def _extract_authors(self, data: dict) -> list[str]:
        authorships = data.get("authorships", [])
        return [a["author"]["display_name"] for a in authorships]

    def _extract_year(self, data: dict) -> int | None:
        return data.get("publication_year")

    def _extract_doi(self, data: dict) -> str:
        doi = data.get("doi", "")
        if doi.startswith("https://doi.org/"):
            return doi.replace("https://doi.org/", "")
        return doi

    def _extract_url(self, data: dict) -> str:
        oa = data.get("open_access", {})
        return oa.get("oa_url", "")
