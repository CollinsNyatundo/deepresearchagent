"""Citation parser — extracts structured citations from markdown text.

Deep module: small interface (parse), complex regex implementation hidden inside.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Citation:
    """A parsed citation with optional metadata fields.

    All fields are optional because different citation styles provide
    different levels of detail. The parser extracts what it can find.
    """
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    url: str | None = None
    number: int | None = None
    venue: str = ""


class CitationParser:
    """Parse citations from markdown/synthesized text.

    Public interface: one method (parse).
    Implementation: multiple regex patterns for different citation styles.
    """

    # DOI regex: matches https://doi.org/10.xxxx/... or doi:10.xxxx/...
    DOI_RE = re.compile(r"https?://doi\.org/([\w./-]+)", re.IGNORECASE)

    # Inline author-year: [Smith, 2020] or [Jones and Lee, 2021] or [Smith 2020] (no comma)
    # Groups: (1) authors, (2) year
    INLINE_CITATION_RE = re.compile(
        r"\[([A-Z][a-zA-Z\s]+(?:\s+and\s+[A-Z][a-zA-Z\s]+)?),?\s*(\d{4})\]"
    )

    # Numbered citation: [1], [42], etc.
    # Avoid matching [Author, Year] by requiring only digits
    NUMBERED_CITATION_RE = re.compile(r"\[(\d{1,3})\](?!\w)")

    # Footnote citation: superscript number followed by author, year, title, venue
    # Example: "¹ Smith, J. (2020). AI Progress. Nature."
    FOOTNOTE_RE = re.compile(
        r"^[\d\u00b9\u00b2\u00b3]+\s+"           # Superscript or regular digit prefix
        r"([^(]+)\s+"                           # Author(s) — group 1
        r"\((\d{4})\)\.\s+"                      # Year — group 2
        r"([^.]+)\.\s*"                          # Title — group 3
        r"([^.]*)\.?"                             # Venue — group 4
    )

    def parse(self, text: str) -> list[Citation]:
        """Extract citations from markdown text.

        Returns a list of Citation objects. Different citation styles may
        appear in the same text; all are extracted.
        """
        if not text:
            return []

        citations: list[Citation] = []

        # 1. Extract DOI citations
        for match in self.DOI_RE.finditer(text):
            citations.append(Citation(doi=match.group(1)))

        # 2. Extract inline author-year citations (with or without comma)
        for match in self.INLINE_CITATION_RE.finditer(text):
            authors_raw = match.group(1)
            year_str = match.group(2)
            authors = [a.strip() for a in authors_raw.split(" and ")]
            citations.append(Citation(authors=authors, year=int(year_str)))

        # 3. Extract numbered citations
        for match in self.NUMBERED_CITATION_RE.finditer(text):
            number_str = match.group(1)
            citations.append(Citation(number=int(number_str)))

        # 4. Extract footnote citations (line by line)
        for line in text.split("\n"):
            match = self.FOOTNOTE_RE.match(line.strip())
            if match:
                citations.append(Citation(
                    authors=[match.group(1).strip()],
                    year=int(match.group(2)),
                    title=match.group(3).strip(),
                    venue=match.group(4).strip() if match.group(4) else "",
                ))

        return citations
