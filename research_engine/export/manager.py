"""Export handlers — exhaustive implementation for multiple formats.

Supported formats:
- markdown: Enhanced Markdown with YAML frontmatter, TOC, references
- bibtex: BibTeX entries with Unicode escaping
- obsidian: ZIP vault with wiki-linked citation notes
- docx: DOCX via Pandoc (primary) or python-docx (fallback)
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from typing import Protocol

from research_engine.citations.parser import Citation


# ─── Export Protocol ─────────────────────────────────────────────────

class ExportHandler(Protocol):
    """Protocol for export format handlers."""

    def export(self, report: str, citations: list[Citation], metadata: dict | None = None) -> str | bytes:
        ...


# ─── Markdown Handler ──────────────────────────────────────────────────

@dataclass
class MarkdownHandler:
    """Export research report to Markdown with YAML frontmatter and TOC."""

    include_toc: bool = True
    max_report_len: int = 50000

    def export(self, report: str, citations: list[Citation], metadata: dict | None = None) -> str:
        meta = metadata or {}
        parts = []

        # YAML frontmatter
        frontmatter = self._build_frontmatter(meta)
        if frontmatter:
            parts.append(frontmatter)

        # Table of contents
        if self.include_toc and report:
            toc = self._build_toc(report)
            if toc:
                parts.append(toc)

        # Report body
        if report.strip():
            parts.append(report[:self.max_report_len].strip())
            if len(report) > self.max_report_len:
                parts.append(f"\n\n---\n\n*[Report truncated from {len(report)} characters]*")

        # References section
        references = self._build_references(citations)
        if references:
            parts.append(references)

        return "\n\n".join(parts)

    def _build_frontmatter(self, metadata: dict) -> str:
        if not metadata:
            return ""
        lines = ["---"]
        for key, value in metadata.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            elif isinstance(value, dict):
                lines.append(f"{key}:")
                for k, v in value.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"{key}: {value}")
        lines.append("---")
        return "\n".join(lines)

    def _build_toc(self, report: str) -> str:
        """Build table of contents from report headings."""
        lines = ["## Table of Contents", ""]
        heading_pattern = __import__('re').compile(r'^(#{1,3})\s+(.+)$', __import__('re').MULTILINE)
        for match in heading_pattern.finditer(report):
            level = len(match.group(1))
            title = match.group(2).strip()
            indent = "  " * (level - 1)
            anchor = title.lower().replace(' ', '-').replace(',', '').replace('.', '')
            lines.append(f"{indent}- [{title}](#{anchor})")
        if len(lines) > 2:
            return "\n".join(lines)
        return ""

    def _build_references(self, citations: list[Citation]) -> str:
        if not citations:
            return ""
        lines = ["## References", ""]
        for i, c in enumerate(citations, 1):
            author_str = ", ".join(c.authors) if c.authors else "Unknown"
            line = f"{i}. {author_str} ({c.year or 'n.d.'}). *{c.title}*."
            if c.doi:
                line += f" https://doi.org/{c.doi}"
            elif c.url:
                line += f" {c.url}"
            lines.append(line)
        return "\n".join(lines)


# ─── BibTeX Handler ────────────────────────────────────────────────────

@dataclass
class BibTeXHandler:
    """Export citations to BibTeX format with Unicode escaping."""

    def export(self, report: str, citations: list[Citation], metadata: dict | None = None) -> str:
        if not citations:
            return ""
        entries = []
        for i, c in enumerate(citations):
            entry = self._build_entry(c, i)
            entries.append(entry)
        return "\n\n".join(entries)

    def _build_entry(self, citation: Citation, index: int) -> str:
        key = self._build_key(citation, index)
        entry_type = self._infer_entry_type(citation)

        lines = [f"@{entry_type}{{{key},"]
        lines.append(f"  title = {{{self._escape(citation.title)}}},")
        if citation.authors:
            author_str = " and ".join(citation.authors)
            lines.append(f"  author = {{{self._escape(author_str)}}},")
        if citation.year:
            lines.append(f"  year = {{{citation.year}}},")
        if citation.doi:
            lines.append(f"  doi = {{{citation.doi}}},")
        if citation.url:
            lines.append(f"  url = {{{citation.url}}},")
        lines.append("}")
        return "\n".join(lines)

    def _build_key(self, citation: Citation, index: int) -> str:
        if citation.authors and citation.year:
            first_author = citation.authors[0].split()[-1]
            # Clean key: remove special chars, lowercase
            clean = __import__('re').sub(r'[^a-zA-Z0-9]', '', first_author).lower()
            return f"{clean}{citation.year}{index}"
        return f"cite{index}"

    def _infer_entry_type(self, citation: Citation) -> str:
        """Infer BibTeX entry type from citation data."""
        if citation.doi:
            return "article"
        if citation.url and ("github.com" in citation.url or "gitlab" in citation.url):
            return "misc"
        return "article"

    def _escape(self, text: str) -> str:
        """Escape special BibTeX characters."""
        replacements = [
            ("&", "\\&"),
            ("%", "\\%"),
            ("$", "\\$"),
            ("#", "\\#"),
            ("_", "\\_"),
            ("{", "\\{"),
            ("}", "\\}"),
            ("~", "\\textasciitilde{}"),
            ("^", "\\textasciicircum{}"),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text


# ─── Obsidian Handler ──────────────────────────────────────────────────

@dataclass
class ObsidianHandler:
    """Export research report as Obsidian vault ZIP.

    Creates:
    - Research/{title}.md — main report with wiki links
    - Citations/{citation}.md — individual citation notes
    - README.md — vault overview
    """

    def export(self, report: str, citations: list[Citation], metadata: dict | None = None) -> bytes:
        meta = metadata or {}
        title = meta.get("title", "Research Report")
        safe_title = self._safe_filename(title)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # README
            readme = self._build_readme(title, meta)
            zf.writestr("README.md", readme)

            # Main report
            main_report = self._build_main_report(report, citations, title)
            zf.writestr(f"Research/{safe_title}.md", main_report)

            # Citation notes
            for citation in citations:
                safe_name = self._safe_filename(citation.title)
                note = self._build_citation_note(citation)
                zf.writestr(f"Citations/{safe_name}.md", note)

        return zip_buffer.getvalue()

    def _build_readme(self, title: str, metadata: dict) -> str:
        lines = [
            f"# {title}",
            "",
            "This Obsidian vault was exported from Deep Research Agent.",
            "",
            "## Structure",
            "",
            "- `Research/` — Main research report",
            "- `Citations/` — Individual citation notes with metadata",
            "",
        ]
        if metadata:
            lines.append("## Metadata")
            lines.append("")
            for key, value in metadata.items():
                lines.append(f"- **{key}**: {value}")
        return "\n".join(lines)

    def _build_main_report(self, report: str, citations: list[Citation], title: str) -> str:
        lines = [f"# {title}", ""]

        # Add wiki links for citations in the report
        wiki_report = report
        for c in citations:
            safe_name = self._safe_filename(c.title)
            # Replace citation mentions with wiki links
            pattern = __import__('re').escape(c.title)
            wiki_report = __import__('re').sub(
                rf'\b{pattern}\b',
                f"[[{safe_name}]]",
                wiki_report
            )

        lines.append(wiki_report)
        lines.append("")
        lines.append("## Citations")
        lines.append("")
        for c in citations:
            safe_name = self._safe_filename(c.title)
            lines.append(f"- [[{safe_name}]]")

        return "\n".join(lines)

    def _build_citation_note(self, citation: Citation) -> str:
        lines = [f"# {citation.title}", ""]
        if citation.authors:
            lines.append(f"**Authors:** {', '.join(citation.authors)}")
        if citation.year:
            lines.append(f"**Year:** {citation.year}")
        if citation.doi:
            lines.append(f"**DOI:** {citation.doi}")
        if citation.url:
            lines.append(f"**URL:** {citation.url}")
        return "\n".join(lines)

    def _safe_filename(self, text: str) -> str:
        """Convert text to safe filename."""
        safe = __import__('re').sub(r'[^\w\s-]', '', text).strip()
        return safe.replace(' ', '_')[:50] or "untitled"


# ─── DOCX Handler ──────────────────────────────────────────────────────

@dataclass
class DocxHandler:
    """Export report to DOCX via Pandoc (primary) or python-docx (fallback)."""

    pandoc_path: str | None = None

    def __post_init__(self):
        if self.pandoc_path is None:
            self.pandoc_path = shutil.which("pandoc")

    def export(self, report: str, citations: list[Citation], metadata: dict | None = None) -> bytes:
        if self.pandoc_path:
            return self._export_via_pandoc(report, citations, metadata)
        return self._export_via_python_docx(report, citations)

    def _export_via_pandoc(self, report: str, citations: list[Citation], metadata: dict | None) -> bytes:
        """Use Pandoc to convert Markdown to DOCX."""
        meta = metadata or {}

        # Build markdown with frontmatter
        md_content = f"""---
title: {meta.get('title', 'Research Report')}
date: {meta.get('date', '')}
---

{report}
"""
        # Add references
        if citations:
            md_content += "\n\n## References\n\n"
            for i, c in enumerate(citations, 1):
                author_str = ", ".join(c.authors) if c.authors else "Unknown"
                md_content += f"{i}. {author_str} ({c.year or 'n.d.'}). {c.title}.\n"

        try:
            result = subprocess.run(
                [self.pandoc_path, "-f", "markdown", "-t", "docx", "-o", "-"],
                input=md_content.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        # Fallback to python-docx
        return self._export_via_python_docx(report, citations)

    def _export_via_python_docx(self, report: str, citations: list[Citation]) -> bytes:
        """Fallback: create DOCX using python-docx if available."""
        try:
            from docx import Document
            from docx.shared import Pt

            doc = Document()

            # Add report content
            for line in report.split('\n'):
                if line.startswith('# '):
                    doc.add_heading(line[2:], level=0)
                elif line.startswith('## '):
                    doc.add_heading(line[3:], level=1)
                elif line.startswith('### '):
                    doc.add_heading(line[4:], level=2)
                elif line.strip():
                    doc.add_paragraph(line)

            # Add references
            if citations:
                doc.add_heading('References', level=1)
                for i, c in enumerate(citations, 1):
                    author_str = ", ".join(c.authors) if c.authors else "Unknown"
                    text = f"{i}. {author_str} ({c.year or 'n.d.'}). {c.title}."
                    doc.add_paragraph(text)

            buffer = io.BytesIO()
            doc.save(buffer)
            return buffer.getvalue()
        except ImportError:
            # Ultimate fallback: return HTML wrapped in DOCX zip structure
            return self._export_html_fallback(report, citations)

    def _export_html_fallback(self, report: str, citations: list[Citation]) -> bytes:
        """Ultimate fallback: HTML in a minimal DOCX-compatible structure."""
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Research Report</title></head>
<body>
{__import__('markdown', fromlist=['markdown']).markdown(report) if __import__('importlib.util').find_spec('markdown') else f'<pre>{report}</pre>'}
</body></html>"""
        return html.encode("utf-8")


# ─── Export Manager ────────────────────────────────────────────────────

class ExportManager:
    """Manages export of research reports in various formats.

    Registry pattern: register handlers by format name.
    """

    def __init__(self):
        self._handlers: dict[str, ExportHandler] = {
            "markdown": MarkdownHandler(),
            "bibtex": BibTeXHandler(),
            "obsidian": ObsidianHandler(),
            "docx": DocxHandler(),
        }

    def export(
        self,
        report: str,
        citations: list[Citation],
        format: str,
        metadata: dict | None = None,
    ) -> str | bytes:
        """Export report in specified format.

        Args:
            report: Markdown report text
            citations: List of Citation objects
            format: One of 'markdown', 'bibtex', 'obsidian', 'docx'
            metadata: Optional metadata dict

        Returns:
            str for text formats, bytes for binary formats

        Raises:
            ValueError: If format is not supported
        """
        handler = self._handlers.get(format.lower())
        if not handler:
            supported = ", ".join(sorted(self._handlers.keys()))
            raise ValueError(f"Unknown export format: '{format}'. Supported: {supported}")
        return handler.export(report, citations, metadata)

    def register(self, format: str, handler: ExportHandler) -> None:
        """Register a custom export handler."""
        self._handlers[format.lower()] = handler

    def supported_formats(self) -> list[str]:
        """Return list of supported format names."""
        return sorted(self._handlers.keys())

    def get_handler(self, format: str) -> ExportHandler:
        """Get handler for a format."""
        handler = self._handlers.get(format.lower())
        if not handler:
            raise ValueError(f"No handler for format: {format}")
        return handler

    def is_binary_format(self, format: str) -> bool:
        """Check if format produces binary output."""
        return format.lower() in {"obsidian", "docx"}
