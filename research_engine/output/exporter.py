"""Multi-format research export module (Phase 5).

Supports: Markdown (.md), PDF (.pdf via fpdf2), Word (.docx via python-docx),
Excel (.xlsx via openpyxl), and Mindmap JSON (.json).

fpdf2 is used instead of weasyprint to avoid GTK system dependency on Windows.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from research_engine.models import ResearchResult

logger = logging.getLogger(__name__)

# MIME types for each format
MEDIA_TYPES: dict[str, str] = {
    "markdown":     "text/markdown",
    "pdf":          "application/pdf",
    "docx":         "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx":         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "mindmap_json": "application/json",
}

EXTENSIONS: dict[str, str] = {
    "markdown":     ".md",
    "pdf":          ".pdf",
    "docx":         ".docx",
    "xlsx":         ".xlsx",
    "mindmap_json": ".json",
}


async def export_run(
    run_id: str,
    fmt: str,
    output_dir: Path = Path("outputs"),
) -> Path:
    """Generate an export file for a research run.

    Args:
        run_id: Research run ID.
        fmt: Export format ('markdown', 'pdf', 'docx', 'xlsx', 'mindmap_json').
        output_dir: Base output directory (default: ./outputs).

    Returns:
        Path to the generated export file.

    Raises:
        FileNotFoundError: If the run doesn't exist.
        ValueError: If the format is unsupported.
    """
    from research_engine.output.storage import load_run

    if fmt not in MEDIA_TYPES:
        raise ValueError(
            f"Unsupported format '{fmt}'. "
            f"Valid formats: {', '.join(MEDIA_TYPES.keys())}"
        )

    run_dir = output_dir / run_id
    if not run_dir.exists():
        raise FileNotFoundError(f"Run not found: {run_id}")

    # Check if export already exists (cache)
    export_path = run_dir / f"export{EXTENSIONS[fmt]}"
    if export_path.exists():
        logger.info(f"Using cached export: {export_path}")
        return export_path

    # Load research result
    result = load_run(run_id, output_dir)

    # Generate export
    logger.info(f"Generating {fmt} export for run: {run_id}")
    match fmt:
        case "markdown":
            _export_markdown(result, export_path)
        case "pdf":
            _export_pdf(result, export_path)
        case "docx":
            _export_docx(result, export_path)
        case "xlsx":
            _export_xlsx(result, export_path)
        case "mindmap_json":
            _export_mindmap_json(run_id, run_dir, export_path)

    logger.info(f"Export saved: {export_path}")
    return export_path


# ─── Markdown Export ──────────────────────────────────────────────────

def _export_markdown(result: ResearchResult, path: Path) -> None:
    """Export as clean Markdown with citations section."""
    lines = [result.report]

    if result.citations:
        lines.append("\n\n---\n\n## References\n")
        for i, citation in enumerate(result.citations, 1):
            title = citation.title or citation.url
            lines.append(f"{i}. [{title}]({citation.url})")
            if citation.snippet:
                lines.append(f"   > {citation.snippet[:200]}")

    path.write_text("\n".join(lines), encoding="utf-8")


# ─── PDF Export ───────────────────────────────────────────────────────

def _export_pdf(result: ResearchResult, path: Path) -> None:
    """Export as PDF using fpdf2 (no system dependencies on Windows)."""
    try:
        from fpdf import FPDF

        class ResearchPDF(FPDF):
            def header(self):
                self.set_font("Helvetica", "B", 10)
                self.set_text_color(100, 100, 100)
                self.cell(0, 8, "Deep Research Agent — Research Report", align="R")
                self.ln(12)

            def footer(self):
                self.set_y(-15)
                self.set_font("Helvetica", "", 8)
                self.set_text_color(150, 150, 150)
                self.cell(0, 10, f"Page {self.page_no()}", align="C")

        pdf = ResearchPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Strip markdown to plain text for PDF
        plain_report = _markdown_to_plain(result.report)

        # Title
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(50, 50, 200)
        pdf.multi_cell(0, 10, f"Research Report: {result.query[:80]}")
        pdf.ln(4)

        # Metadata
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 6, f"Model: {result.model_used}   |   Cycles: {len(result.steps)}   |   Citations: {len(result.citations)}")
        pdf.ln(10)

        # Report body
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(30, 30, 30)

        for line in plain_report.split("\n"):
            stripped = line.strip()
            if not stripped:
                pdf.ln(4)
                continue

            # H1
            if stripped.startswith("# "):
                pdf.set_font("Helvetica", "B", 16)
                pdf.set_text_color(30, 30, 120)
                pdf.ln(4)
                pdf.multi_cell(0, 8, stripped[2:])
                pdf.set_font("Helvetica", "", 11)
                pdf.set_text_color(30, 30, 30)
                pdf.ln(2)
            # H2
            elif stripped.startswith("## "):
                pdf.set_font("Helvetica", "B", 13)
                pdf.set_text_color(60, 60, 160)
                pdf.ln(2)
                pdf.multi_cell(0, 7, stripped[3:])
                pdf.set_font("Helvetica", "", 11)
                pdf.set_text_color(30, 30, 30)
                pdf.ln(1)
            # H3
            elif stripped.startswith("### "):
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(80, 80, 140)
                pdf.multi_cell(0, 6, stripped[4:])
                pdf.set_font("Helvetica", "", 11)
                pdf.set_text_color(30, 30, 30)
            # Bullet
            elif stripped.startswith(("- ", "* ", "• ")):
                pdf.multi_cell(0, 5.5, f"  • {stripped[2:]}", padding=(0, 0, 0, 5))
            # Normal text
            else:
                pdf.multi_cell(0, 5.5, stripped)

        # Citations section
        if result.citations:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(30, 30, 120)
            pdf.cell(0, 10, "References")
            pdf.ln(8)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(50, 50, 50)

            for i, citation in enumerate(result.citations, 1):
                title = citation.title or citation.url
                pdf.multi_cell(0, 5, f"{i}. {title}")
                pdf.set_text_color(0, 0, 200)
                pdf.multi_cell(0, 4.5, f"   {citation.url}")
                pdf.set_text_color(50, 50, 50)
                pdf.ln(2)

        pdf.output(str(path))

    except ImportError:
        logger.error("fpdf2 not installed. Run: pip install fpdf2")
        raise


# ─── Word Export (DOCX) ───────────────────────────────────────────────

def _export_docx(result: ResearchResult, path: Path) -> None:
    """Export as Word document (.docx) using python-docx."""
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()

        # Set margins
        section = doc.sections[0]
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

        # Title
        title_para = doc.add_heading(f"Research Report", 0)
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Query subtitle
        query_para = doc.add_paragraph(result.query)
        query_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        query_run = query_para.runs[0]
        query_run.font.size = Pt(14)
        query_run.font.color.rgb = RGBColor(80, 80, 160)

        doc.add_paragraph()  # Spacer

        # Metadata table
        meta_table = doc.add_table(rows=1, cols=3)
        meta_table.style = "Table Grid"
        cells = meta_table.rows[0].cells
        cells[0].text = f"Model: {result.model_used}"
        cells[1].text = f"Cycles: {len(result.steps)}"
        cells[2].text = f"Citations: {len(result.citations)}"
        doc.add_paragraph()

        # Report body — parse markdown headings
        for line in result.report.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("### "):
                doc.add_heading(stripped[4:], level=3)
            elif stripped.startswith("## "):
                doc.add_heading(stripped[3:], level=2)
            elif stripped.startswith("# "):
                doc.add_heading(stripped[2:], level=1)
            elif stripped.startswith(("- ", "* ")):
                para = doc.add_paragraph(stripped[2:], style="List Bullet")
            else:
                doc.add_paragraph(stripped)

        # Citations section
        if result.citations:
            doc.add_page_break()
            doc.add_heading("References", level=1)

            cit_table = doc.add_table(rows=1, cols=3)
            cit_table.style = "Table Grid"
            # Header row
            header_cells = cit_table.rows[0].cells
            header_cells[0].text = "#"
            header_cells[1].text = "Title"
            header_cells[2].text = "URL"

            for i, citation in enumerate(result.citations, 1):
                row_cells = cit_table.add_row().cells
                row_cells[0].text = str(i)
                row_cells[1].text = citation.title or "—"
                row_cells[2].text = citation.url

        doc.save(str(path))

    except ImportError:
        logger.error("python-docx not installed. Run: pip install python-docx")
        raise


# ─── Excel Export (XLSX) ─────────────────────────────────────────────

def _export_xlsx(result: ResearchResult, path: Path) -> None:
    """Export as Excel spreadsheet (.xlsx) using openpyxl."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter

        wb = Workbook()

        # ── Sheet 1: Summary ─────────────────────────────────────
        ws_summary = wb.active
        ws_summary.title = "Summary"

        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill("solid", fgColor="3333AA")
        center_align = Alignment(horizontal="center")

        summary_data = [
            ["Field", "Value"],
            ["Query", result.query],
            ["Run ID", result.run_id],
            ["Model", result.model_used],
            ["Research Cycles", len(result.steps)],
            ["Total Citations", len(result.citations)],
            ["Progress (%)", result.progress],
            ["Started At", result.started_at.isoformat()],
            ["Completed At", result.completed_at.isoformat()],
        ]

        for row_idx, row_data in enumerate(summary_data, 1):
            for col_idx, value in enumerate(row_data, 1):
                cell = ws_summary.cell(row=row_idx, column=col_idx, value=value)
                if row_idx == 1:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = center_align

        ws_summary.column_dimensions["A"].width = 20
        ws_summary.column_dimensions["B"].width = 60

        # ── Sheet 2: Citations ────────────────────────────────────
        ws_cit = wb.create_sheet("Citations")
        cit_headers = ["#", "Title", "URL", "Domain", "Snippet"]
        for col_idx, header in enumerate(cit_headers, 1):
            cell = ws_cit.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align

        for i, citation in enumerate(result.citations, 1):
            ws_cit.cell(row=i + 1, column=1, value=i)
            ws_cit.cell(row=i + 1, column=2, value=citation.title or "")
            ws_cit.cell(row=i + 1, column=3, value=citation.url)
            ws_cit.cell(row=i + 1, column=4, value=citation.domain or "")
            ws_cit.cell(row=i + 1, column=5, value=citation.snippet[:200] if citation.snippet else "")

        col_widths_cit = [5, 40, 50, 20, 60]
        for col_idx, width in enumerate(col_widths_cit, 1):
            ws_cit.column_dimensions[get_column_letter(col_idx)].width = width

        # ── Sheet 3: Research Steps ───────────────────────────────
        ws_steps = wb.create_sheet("Research Steps")
        step_headers = ["Cycle", "Query", "Search Results", "Pages Scraped", "Answer Length", "Citations"]
        for col_idx, header in enumerate(step_headers, 1):
            cell = ws_steps.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align

        for i, step in enumerate(result.steps, 1):
            ws_steps.cell(row=i + 1, column=1, value=step.cycle + 1)
            ws_steps.cell(row=i + 1, column=2, value=step.query.query)
            ws_steps.cell(row=i + 1, column=3, value=len(step.search_results))
            ws_steps.cell(row=i + 1, column=4, value=len(step.scraped_pages))
            ws_steps.cell(row=i + 1, column=5, value=len(step.answer.answer))
            ws_steps.cell(row=i + 1, column=6, value=len(step.answer.citations))

        step_col_widths = [8, 60, 15, 15, 15, 12]
        for col_idx, width in enumerate(step_col_widths, 1):
            ws_steps.column_dimensions[get_column_letter(col_idx)].width = width

        wb.save(str(path))

    except ImportError:
        logger.error("openpyxl not installed. Run: pip install openpyxl")
        raise


# ─── Mindmap JSON Export ──────────────────────────────────────────────

def _export_mindmap_json(run_id: str, run_dir: Path, path: Path) -> None:
    """Export the mindmap as G6-compatible JSON."""
    mindmap_path = run_dir / "mindmap.json"
    if mindmap_path.exists():
        # Already stored in G6 format, just copy
        path.write_bytes(mindmap_path.read_bytes())
    else:
        # Fallback: empty graph
        path.write_text(
            json.dumps({"run_id": run_id, "nodes": [], "edges": []}, indent=2),
            encoding="utf-8",
        )


# ─── Helpers ─────────────────────────────────────────────────────────

def _markdown_to_plain(text: str) -> str:
    """Strip basic markdown syntax for plain-text rendering in PDF."""
    # Remove code fences
    text = re.sub(r"```.*?```", "[code block]", text, flags=re.DOTALL)
    # Remove inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove bold/italic markers
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    # Remove links — keep text
    text = re.sub(r"\[(.+?)\]\(.*?\)", r"\1", text)
    # Remove images
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    # Tables: leave as-is (fpdf will just print them as text)
    return text
