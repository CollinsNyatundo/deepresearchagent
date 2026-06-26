import pytest

# RED Phase: Define expected behavior before implementation
# These tests will FAIL initially — that is the correct TDD state

from research_engine.citations.parser import CitationParser, Citation


class TestCitationParser:
    """Integration-style tests: verify behavior through public interface only."""

    def test_parse_empty_string_returns_empty_list(self):
        """Given empty markdown, parser returns empty list."""
        parser = CitationParser()
        result = parser.parse("")
        assert result == []

    def test_parse_doi_url_returns_citation_with_doi(self):
        """Given markdown with DOI URL, parser returns citation with DOI."""
        parser = CitationParser()
        text = "See https://doi.org/10.1234/example for details."
        result = parser.parse(text)

        assert len(result) == 1
        assert result[0].doi == "10.1234/example"
        assert result[0].title == ""
        assert result[0].authors == []

    def test_parse_inline_author_year_citation(self):
        """Given [Author, Year] citation, parser extracts authors and year."""
        parser = CitationParser()
        text = "According to [Smith, 2020], AI is transforming healthcare."
        result = parser.parse(text)

        assert len(result) == 1
        assert result[0].authors == ["Smith"]
        assert result[0].year == 2020

    def test_parse_multiple_inline_citations(self):
        """Given multiple [Author, Year] citations, parser extracts all."""
        parser = CitationParser()
        text = "[Smith, 2020] and [Jones and Lee, 2021] both support this."
        result = parser.parse(text)

        assert len(result) == 2
        assert result[0].authors == ["Smith"]
        assert result[0].year == 2020
        assert result[1].authors == ["Jones", "Lee"]
        assert result[1].year == 2021

    def test_parse_numbered_citation(self):
        """Given [1] style citation, parser extracts number."""
        parser = CitationParser()
        text = "This claim is supported [1]."
        result = parser.parse(text)

        assert len(result) == 1
        assert result[0].number == 1

    def test_parse_mixed_citation_styles(self):
        """Given mixed styles, parser extracts all citations."""
        parser = CitationParser()
        text = (
            "See https://doi.org/10.1/ai for overview. "
            "[Smith, 2020] discusses this further. "
            "Also see [1] for comparison."
        )
        result = parser.parse(text)

        assert len(result) == 3
        # DOI citation
        assert result[0].doi == "10.1/ai"
        # Author-year citation
        assert result[1].authors == ["Smith"]
        assert result[1].year == 2020
        # Numbered citation
        assert result[2].number == 1

    def test_parse_no_citations_returns_empty_list(self):
        """Given text without citations, parser returns empty list."""
        parser = CitationParser()
        text = "This is just regular text with no citations."
        result = parser.parse(text)

        assert result == []

    def test_citation_has_all_expected_fields(self):
        """Given a parsed citation, all fields have expected types."""
        parser = CitationParser()
        text = "See https://doi.org/10.1234/example and [Smith, 2020]."
        result = parser.parse(text)

        for citation in result:
            assert isinstance(citation.title, str)
            assert isinstance(citation.authors, list)
            assert citation.year is None or isinstance(citation.year, int)
            assert citation.doi is None or isinstance(citation.doi, str)
            assert citation.url is None or isinstance(citation.url, str)
            assert citation.number is None or isinstance(citation.number, int)

    def test_parse_footnote_citation(self):
        """Given footnote-style citation, parser extracts title and authors."""
        parser = CitationParser()
        text = (
            "AI has advanced significantly.\u00b9\n\n"
            "\u00b9 Smith, J. (2020). AI Progress. Nature."
        )
        result = parser.parse(text)

        assert len(result) == 1
        assert result[0].title == "AI Progress"
        assert result[0].authors == ["Smith, J."]
        assert result[0].year == 2020
        assert result[0].venue == "Nature"

    def test_parse_inline_citation_without_comma(self):
        """Given [Author Year] without comma, parser still extracts."""
        parser = CitationParser()
        text = "According to [Smith 2020], AI is transforming healthcare."
        result = parser.parse(text)

        assert len(result) == 1
        assert result[0].authors == ["Smith"]
        assert result[0].year == 2020

    def test_parse_does_not_match_wiki_links(self):
        """Given [[Wiki Link]] syntax, parser does not treat as citation."""
        parser = CitationParser()
        text = "See [[Project Architecture]] for details."
        result = parser.parse(text)

        assert result == []
