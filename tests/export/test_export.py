"""Exhaustive tests for export handlers."""
import io
import zipfile

import pytest

from research_engine.export.manager import (
    MarkdownHandler,
    BibTeXHandler,
    ObsidianHandler,
    DocxHandler,
    ExportManager,
)
from research_engine.citations.parser import Citation


class TestMarkdownHandler:
    """Tests for enhanced Markdown export."""

    def test_export_includes_yaml_frontmatter(self):
        """Given metadata, export includes YAML frontmatter."""
        handler = MarkdownHandler()
        metadata = {"title": "AI in Healthcare", "run_id": "abc-123", "model": "deepseek-chat"}
        result = handler.export("# Report\n\nContent.", [], metadata)

        assert result.startswith("---")
        assert "title: AI in Healthcare" in result
        assert "run_id: abc-123" in result
        assert "---" in result

    def test_export_includes_toc(self):
        """Given report with headings, export includes TOC."""
        handler = MarkdownHandler(include_toc=True)
        report = "# Main\n\n## Section 1\n\n### Subsection\n\n## Section 2"
        result = handler.export(report, [], {})

        assert "## Table of Contents" in result
        assert "[Main]" in result
        assert "[Section 1]" in result
        assert "[Section 2]" in result

    def test_export_includes_citation_section(self):
        """Given citations, export includes references."""
        handler = MarkdownHandler()
        citations = [
            Citation(title="AI Progress", authors=["Smith, J."], year=2020, doi="10.1/ai"),
            Citation(title="ML Advances", authors=["Jones, K."], year=2021, url="https://example.com"),
        ]
        result = handler.export("Report", citations, {})

        assert "## References" in result
        assert "Smith, J. (2020)" in result
        assert "Jones, K. (2021)" in result
        assert "10.1/ai" in result

    def test_export_truncates_long_report(self):
        """Given long report, export truncates."""
        handler = MarkdownHandler(max_report_len=100)
        long_report = "x" * 500
        result = handler.export(long_report, [], {})
        assert "truncated" in result

    def test_export_no_toc_when_no_headings(self):
        """Given no headings, no TOC."""
        handler = MarkdownHandler(include_toc=True)
        result = handler.export("Plain text without headings.", [], {})
        assert "Table of Contents" not in result

    def test_export_frontmatter_with_list(self):
        """Given metadata with list, frontmatter renders correctly."""
        handler = MarkdownHandler()
        metadata = {"tags": ["ai", "healthcare"]}
        result = handler.export("Report", [], metadata)
        assert "tags:" in result
        assert "  - ai" in result


class TestBibTeXHandler:
    """Tests for BibTeX export."""

    def test_export_generates_article_entry(self):
        """Given citation with DOI, generates @article entry."""
        handler = BibTeXHandler()
        citations = [Citation(title="AI Progress", authors=["Smith, John"], year=2020, doi="10.1/ai")]
        result = handler.export("", citations)

        assert "@article" in result
        assert "title = {AI Progress}" in result
        assert "author = {Smith, John}" in result
        assert "year = {2020}" in result
        assert "doi = {10.1/ai}" in result

    def test_export_generates_misc_for_github(self):
        """Given GitHub URL, generates @misc entry."""
        handler = BibTeXHandler()
        citations = [Citation(title="Repo", authors=["Dev"], year=2023, url="https://github.com/user/repo")]
        result = handler.export("", citations)
        assert "@misc" in result

    def test_export_escapes_special_chars(self):
        """Given special characters, escapes them."""
        handler = BibTeXHandler()
        citations = [Citation(title="AI & ML: 100% $uccess", authors=["Smith_ Jr."], year=2020)]
        result = handler.export("", citations)

        assert "\\&" in result
        assert "\\%" in result
        assert "\\$" in result
        assert "\\_" in result

    def test_export_builds_key_from_author_year(self):
        """Given author and year, builds BibTeX key."""
        handler = BibTeXHandler()
        citations = [Citation(title="Paper", authors=["Smith, John"], year=2020)]
        result = handler.export("", citations)
        assert "20200" in result  # Year + index
        assert "@article{" in result

    def test_export_empty_citations(self):
        """Given no citations, returns empty string."""
        handler = BibTeXHandler()
        result = handler.export("", [])
        assert result == ""


class TestObsidianHandler:
    """Tests for Obsidian vault export."""

    def test_export_creates_zip(self):
        """Given report, export creates valid ZIP."""
        handler = ObsidianHandler()
        result = handler.export("# Report\n\nContent.", [], {"title": "Test"})

        assert isinstance(result, bytes)
        assert result[:4] == b'PK\x03\x04'  # ZIP header

    def test_export_creates_readme(self):
        """Given report, ZIP contains README."""
        handler = ObsidianHandler()
        result = handler.export("Report", [], {"title": "My Research"})

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            assert "README.md" in zf.namelist()
            readme = zf.read("README.md").decode()
            assert "My Research" in readme

    def test_export_creates_research_folder(self):
        """Given report, ZIP contains Research/ folder."""
        handler = ObsidianHandler()
        result = handler.export("# Title\n\nBody.", [], {"title": "Research"})

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            names = zf.namelist()
            assert any("Research/" in n for n in names)

    def test_export_creates_citation_notes(self):
        """Given citations, ZIP contains Citations/ folder."""
        handler = ObsidianHandler()
        citations = [Citation(title="AI Progress", authors=["Smith"], year=2020)]
        result = handler.export("Report", citations, {})

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            names = zf.namelist()
            assert any("Citations/" in n for n in names)

    def test_export_creates_wiki_links(self):
        """Given report with citations, creates wiki links."""
        handler = ObsidianHandler()
        citations = [Citation(title="AI Progress", authors=["Smith"], year=2020)]
        result = handler.export("AI Progress is important.", citations, {})

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            for name in zf.namelist():
                if name.startswith("Research/"):
                    content = zf.read(name).decode()
                    assert "[[" in content

    def test_safe_filename(self):
        """Given unsafe title, converts to safe filename."""
        handler = ObsidianHandler()
        assert handler._safe_filename("AI/ML: Report!") == "AIML_Report"
        assert handler._safe_filename("") == "untitled"


class TestDocxHandler:
    """Tests for DOCX export."""

    def test_export_returns_bytes(self):
        """Given report, export returns bytes."""
        handler = DocxHandler(pandoc_path=None)  # No pandoc, use fallback
        result = handler.export("# Report\n\nContent.", [])

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_with_pandoc_if_available(self):
        """Given Pandoc available, uses it."""
        import shutil
        pandoc = shutil.which("pandoc")
        handler = DocxHandler(pandoc_path=pandoc)
        result = handler.export("# Report\n\nContent.", [])

        assert isinstance(result, bytes)
        if pandoc:
            # Should be valid DOCX (ZIP)
            assert result[:4] == b'PK\x03\x04'

    def test_export_without_pandoc_uses_fallback(self):
        """Given no Pandoc, uses fallback."""
        handler = DocxHandler(pandoc_path="/nonexistent/pandoc")
        result = handler.export("# Report", [])
        assert isinstance(result, bytes)

    def test_export_with_citations(self):
        """Given citations, includes references section."""
        handler = DocxHandler(pandoc_path=None)
        citations = [Citation(title="Paper", authors=["Smith"], year=2020)]
        result = handler.export("Report", citations)
        assert isinstance(result, bytes)


class TestExportManager:
    """Tests for export manager."""

    def test_export_markdown(self):
        """Given markdown format, returns markdown."""
        manager = ExportManager()
        result = manager.export("# Test", [], "markdown", {"title": "Test"})
        assert isinstance(result, str)
        assert "---" in result

    def test_export_bibtex(self):
        """Given bibtex format, returns bibtex."""
        manager = ExportManager()
        citations = [Citation(title="Paper", authors=["Smith"], year=2020)]
        result = manager.export("", citations, "bibtex")
        assert isinstance(result, str)
        assert "@article" in result

    def test_export_obsidian_returns_bytes(self):
        """Given obsidian format, returns bytes."""
        manager = ExportManager()
        result = manager.export("Report", [], "obsidian", {"title": "Test"})
        assert isinstance(result, bytes)
        assert result[:4] == b'PK\x03\x04'

    def test_export_docx_returns_bytes(self):
        """Given docx format, returns bytes."""
        manager = ExportManager()
        result = manager.export("# Report", [], "docx")
        assert isinstance(result, bytes)

    def test_export_unknown_format_raises(self):
        """Given unknown format, raises ValueError."""
        manager = ExportManager()
        with pytest.raises(ValueError, match="Unknown export format"):
            manager.export("", [], "unknown")

    def test_supported_formats(self):
        """Given supported_formats, returns all formats."""
        manager = ExportManager()
        formats = manager.supported_formats()
        assert "markdown" in formats
        assert "bibtex" in formats
        assert "obsidian" in formats
        assert "docx" in formats

    def test_register_custom_handler(self):
        """Given custom handler, registers it."""
        manager = ExportManager()
        custom = MarkdownHandler()
        manager.register("custom", custom)
        assert "custom" in manager.supported_formats()

    def test_get_handler(self):
        """Given format, returns handler."""
        manager = ExportManager()
        handler = manager.get_handler("markdown")
        assert isinstance(handler, MarkdownHandler)

    def test_is_binary_format(self):
        """Given format, returns binary status."""
        manager = ExportManager()
        assert manager.is_binary_format("obsidian") is True
        assert manager.is_binary_format("docx") is True
        assert manager.is_binary_format("markdown") is False
        assert manager.is_binary_format("bibtex") is False

    def test_export_with_metadata(self):
        """Given metadata, passes to handler."""
        manager = ExportManager()
        result = manager.export("# Report", [], "markdown", {"title": "My Report", "date": "2024-01-01"})
        assert "My Report" in result
        assert "2024-01-01" in result
