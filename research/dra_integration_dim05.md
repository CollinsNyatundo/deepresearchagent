# Dimension 05: Academic Document Export Pipeline

## Overview

This dimension investigates the implementation of five new export formats (DOCX, LaTeX, BibTeX, RIS, Obsidian Vault) for DRA's research reports. It covers library selection, formatting challenges, and quality assurance.

---

## Key Findings

### 1. python-docx is Mature but Limited for Academic Formatting

**Claim:** python-docx is the standard Python library for creating Word documents, but it does not support LaTeX-style academic formatting (equations, cross-references, complex tables of contents).[^1]

**Source:** python-docx Documentation

**URL:** https://python-docx.readthedocs.io/en/latest/

**Date:** 2026

**Excerpt:**
> "python-docx is a Python library for creating and updating Microsoft Word (.docx) files."

**Context:** The DRA plan proposes `export_docx()` using python-docx. For academic formatting (numbered headings, figure captions, bibliography), python-docx requires significant custom styling. A simpler approach may be to generate Markdown and convert via Pandoc, which handles academic formatting better.

**Confidence:** High

---

**Claim:** Pandoc is the gold standard for document conversion, supporting Markdown → DOCX, LaTeX, PDF, and many other formats with excellent academic formatting.[^2]

**Source:** Pandoc Documentation

**URL:** https://pandoc.org/

**Date:** 2026

**Excerpt:**
> "Pandoc is a universal document converter. If you need to convert files from one markup format into another, pandoc is your swiss-army knife."

**Context:** opendraft uses Pandoc for DOCX generation ("MD → DOCX via Pandoc when available"). DRA should follow this pattern rather than building custom python-docx formatting. Pandoc also handles LaTeX → PDF natively, which would simplify the export pipeline.

**Confidence:** High

---

### 2. pylatex is Not the Best Choice for LaTeX Generation

**Claim:** pylatex is a Python library for generating LaTeX code, but it requires users to have a LaTeX distribution installed (TeX Live, MiKTeX) to compile documents.[^3]

**Source:** PyLaTeX Documentation

**URL:** https://jeltef.github.io/PyLaTeX/current/

**Date:** 2026

**Excerpt:**
> "PyLaTeX is a Python library for creating and compiling LaTeX files."

**Context:** The DRA plan lists `pylatex` as a dependency but does not show any actual usage. For a web-based research platform, requiring users to install a LaTeX distribution is a significant barrier. A better approach is to generate Markdown with LaTeX math syntax and convert via Pandoc or MathJax for preview.

**Confidence:** High

---

**Claim:** WeasyPrint is a Python library that converts HTML+CSS to PDF without requiring LaTeX.[^4]

**Source:** WeasyPrint Documentation

**URL:** https://weasyprint.org/

**Date:** 2026

**Excerpt:**
> "WeasyPrint is a visual rendering engine for HTML and CSS that can export to PDF."

**Context:** opendraft uses WeasyPrint for PDF export. DRA already has a PDF export path; the new formats should be additive. For LaTeX export, generating `.tex` source files (plain text) is more useful than compiling PDFs, since users can edit the LaTeX before submission.

**Confidence:** High

---

### 3. BibTeX and RIS are Simple Text Formats

**Claim:** BibTeX and RIS are plain-text bibliography formats that are straightforward to generate from structured citation data. No special libraries are needed — just string templating.[^5]

**Source:** BibTeX Format Specification / RIS Format Specification

**URL:** http://www.bibtex.org/Format/

**Date:** 2026

**Excerpt:**
> "BibTeX is a tool and file format which can be used for describing lists of references."

**Context:** The DRA plan lists `pylatex` as a dependency for LaTeX generation, but BibTeX generation is just string templating. DRA can generate BibTeX entries using Jinja2 templates or f-strings. No heavy dependency needed.

**Confidence:** High

---

**Claim:** RIS (Research Information Systems) format is widely supported by reference managers (Zotero, Mendeley, EndNote) and has a well-defined tag structure.[^6]

**Source:** RIS Format Wikipedia / Reference Manager Documentation

**URL:** https://en.wikipedia.org/wiki/RIS_(file_format)

**Date:** 2026

**Excerpt:**
> "RIS is a standardized tag format developed by Research Information Systems, Incorporated to enable citation programs to exchange data."

**Context:** Like BibTeX, RIS is just text templating. A simple Python function can generate RIS output from the `Citation` model. No external library needed.

**Confidence:** High

---

### 4. Obsidian Vault Export is a Directory Structure Challenge

**Claim:** Obsidian vaults are just directories of Markdown files with YAML frontmatter and wiki-links. Exporting to Obsidian requires generating a directory structure, not a single file.[^7]

**Source:** Obsidian Help Documentation

**URL:** https://help.obsidian.md/Files+and+folders/Manage+attachments

**Date:** 2026

**Excerpt:**
> "An Obsidian vault is essentially a folder on your local file system."

**Context:** The DRA plan's `export_obsidian_vault()` concept is good, but the implementation should:
1. Create a ZIP file containing Markdown files + attachments
2. Add YAML frontmatter with DRA metadata (run_id, query, date)
3. Convert citations to Obsidian's `[[note]]` wiki-link format or standard Markdown links
4. Include a `README.md` with vault usage instructions

DRA already has wiki-link parsing (`[[Title]]` syntax) in the Notes module, so this can be reused.

**Confidence:** High

---

## Tensions and Counter-Arguments

### Tension 1: Format Coverage vs. Maintenance Burden

Five export formats (DOCX, LaTeX, BibTeX, RIS, Obsidian) means five code paths to maintain, five test suites, and five potential bug surfaces. Each format has edge cases (Unicode in BibTeX, images in DOCX, math in LaTeX).

**Counter-argument:** Start with the two most valuable formats: **Obsidian Vault** (reuses existing wiki-link infrastructure) and **BibTeX** (simplest to implement). Add DOCX and LaTeX only after user demand is proven. RIS is low-value since BibTeX covers the same use case.

### Tension 2: LaTeX Compilation vs. Source Export

The DRA plan mentions "LaTeX export" but it's ambiguous whether this means:
- Exporting `.tex` source files (useful for journal submission)
- Compiling PDFs via LaTeX (requires TeX Live installation)

**Counter-argument:** Exporting `.tex` source is more useful for DRA's academic audience. Users can compile locally with their preferred LaTeX setup. Compiling PDFs server-side adds significant infrastructure complexity (TeX Live is ~4GB).

### Tension 3: python-docx vs. Pandoc

The DRA plan explicitly lists `python-docx` as a dependency. However, for academic formatting with citations, Pandoc is far superior. Pandoc can convert Markdown → DOCX with a custom reference document for styling, preserving headings, tables, and citations.

**Counter-argument:** If Pandoc is available on the server, use it. If not, fall back to python-docx with simple formatting. The plan should mention both options.

---

## Recommendations

### 1. Remove `pylatex` Dependency

BibTeX and RIS are plain text — no library needed. LaTeX source export is just `.tex` text files — no compilation needed. `pylatex` adds unnecessary weight.

### 2. Prioritize Export Formats by Value

| Priority | Format | Effort | User Value | Implementation |
|----------|--------|--------|------------|----------------|
| P1 | Obsidian Vault | Medium | High (reuses Notes module) | ZIP generator + wiki-links |
| P1 | BibTeX | Low | High (standard academic format) | String templates |
| P2 | Markdown (enhanced) | Low | High (already exists) | Add YAML frontmatter |
| P2 | DOCX | Medium | Medium | Pandoc if available, else python-docx |
| P3 | LaTeX source | Medium | Medium | Jinja2 templates |
| P3 | RIS | Low | Low | String templates (post-BibTeX) |

### 3. Use Pandoc for DOCX When Available

```python
async def export_docx(report: str, citations: list) -> bytes:
    # Generate enhanced Markdown with citations
    md = generate_markdown(report, citations)
    
    # Try Pandoc first (better quality)
    if shutil.which("pandoc"):
        return await pandoc_convert(md, "docx")
    
    # Fallback to python-docx (simpler formatting)
    return python_docx_convert(md)
```

---

## Confidence Assessment

| Finding | Confidence |
|---------|------------|
| python-docx limited for academic formatting | High |
| Pandoc is gold standard for document conversion | High |
| pylatex requires LaTeX distribution | High |
| BibTeX/RIS are plain text, no library needed | High |
| Obsidian vault is directory of Markdown | High |

---

## Sources

[^1]: python-docx Documentation. 2026. https://python-docx.readthedocs.io/en/latest/

[^2]: Pandoc Documentation. 2026. https://pandoc.org/

[^3]: PyLaTeX Documentation. 2026. https://jeltef.github.io/PyLaTeX/current/

[^4]: WeasyPrint Documentation. 2026. https://weasyprint.org/

[^5]: BibTeX Format Specification. 2026. http://www.bibtex.org/Format/

[^6]: RIS Format Wikipedia. 2026. https://en.wikipedia.org/wiki/RIS_(file_format)

[^7]: Obsidian Help Documentation. 2026. https://help.obsidian.md/Files+and+folders/Manage+attachments

