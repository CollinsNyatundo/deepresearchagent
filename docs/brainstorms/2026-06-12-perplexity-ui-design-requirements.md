---
date: 2026-06-12
topic: perplexity-ui-design-requirements
mode: repo-grounded
---

# Requirements: Perplexity-Style UI/UX and System Design Infrastructure Improvements

This document outlines the detailed product requirements and behavior for implementing a premium, Perplexity-grade visual redesign and advanced feature modules for the Deep Research Agent.

---

## 1. Summary

Transition the Deep Research Agent workspace to a high-density, dark mode **Sleek Slate Glassmorphic** layout. This includes a compact utility sidebar, collapsible step-by-step thinking accordions, a live scrape status progress dashboard, and 10 advanced user-facing feature modules.

---

## 2. Problem Frame

The current frontend layout of the Deep Research Agent provides limited visual structure and lacks real-time transparency during long research tasks. Long scraping times look like application freezes, and complex citations or entity relationships are hard to navigate. By upgrading the information density and creating interactive bridges between text reports and visual graphs, we transform the tool into a professional research console.

---

## 3. Key Decisions

- **Visual Palette:** OLED Dark Mode (`#020617` background, `#0f172a` panels, `#1e293b` borders, and `#22c55e` emerald accents) using `Fira Sans` for UI copy and `Fira Code` for telemetry logs.
- **Generative UI Streaming:** The backend LLM streams custom JSON blocks (enclosed in ````genui ... ```` code blocks) inside the markdown stream. The frontend parses and renders these dynamically as interactive cards once completed.
- **Unified Two-Pane Grid:** A horizontal split with the report reader on the left and the G6 visualization views (Mindmap/Graph) on the right.
- **Sidebar Collapse:** Left-hand navigation is collapsed by default into a 48px icon-only bar, sliding out to a 240px run history drawer on hover.

---

## 4. Requirements

### General Visual Theme & Typography
R1. The workspace must default to the OLED Dark Mode palette, utilizing a CSS blur-backdrop glassmorphism effect on overlay cards.
R2. Typography must pair Fira Sans for body and headings with Fira Code for all monospace logs, query views, and telemetry.

### Core Workspace & Compact Sidebar
R3. The app layout must employ a 48px wide Left Utility Sidebar displaying brand mark, workspace toggles (Research vs Code Arch), New Research button, and a settings icon.
R4. Hovering or clicking the Left Sidebar must slide open a 240px drawer showing the full research run history.
R5. The main workspace must split 50/50 horizontally between the Report Viewer (left) and the G6 Canvas Tabs (right). The G6 canvas containers must utilize `ResizeObserver` instances to automatically resize the canvas via `graph.resize()` whenever their container dimensions change (e.g., due to panel resizing, window resizing, or sidebar collapse/expand).

### Collapsible Reasoning & Scrape Progress
R6. Backend streamed `<thinking>` blocks must be transmitted via Server-Sent Events (SSE) using the `thinking_chunk` event type.
R7. The frontend must render thinking chunks inside a collapsible Mantine Accordion panel displaying active status checkmarks, an elapsed timer, and a pulsing typewriter cursor.
R8. The thinking accordion must contain a real-time Scraper Queue displaying resolving URLs, crawl duration, and a badge indicating the active fetcher tier (`[Stealthy]` Camoufox vs `[Dynamic]` Playwright).

### Advanced Feature Modules
R9. **GenUI Dynamic Cards:** The markdown renderer must intercept ````genui ... ```` JSON blocks. During active streaming, the client must render a shimmer placeholder for any incomplete ````genui```` block and only parse and render the complete custom interactive widgets once the closing ```` tag is received.
R10. **Citation-Graph Hover Mapping:** Hovering a citation superscript `[1]` in the report must trigger a highlight event that applies a gold outline to the matching source node in the G6 Knowledge Graph.
R11. **Power CLI Search Input:** Toggling CLI mode must convert the research input field into a monospace console supporting autocomplete for provider and model flags.
R12. **Live Source Toggles:** A row of domain badges must allow users to toggle specific websites off, triggering a rapid LLM re-synthesis without a full search rerun.
R13. **Mindmap Exploration Drawer:** Clicking a G6 Mindmap node must slide out a drawer containing node details, original scraped source snippets, and a "Drill Deeper" button to spawn sub-research tasks.
R14. **Dry-Run Scoping Editor:** Before starting a search, the app must display a scoping checklist of planned search terms and domains for the user to prune or approve.
R15. **Dual-Layer Cache Telemetry:** A stats popup in the sidebar must show total cached items in SQLite, cache hit rate percentages, and estimated token/API costs saved.
R16. **Session Crossover Mapping:** A visual graph mode must highlight nodes shared between the active run and selected historical research runs.
R17. **Interactive Export Studio:** An export panel must allow users to choose typography themes and toggle image inclusions before compiling reports to PDF, Word, or Markdown.

### System & Backend Integrations
R18. Scraper domain failures must trigger an in-memory circuit breaker that trips to `Open` after 3 consecutive failures, falling back to static fetches for 5 minutes.
R19. The backend must implement a dual-layer SQLite cache storing search listings (12h TTL) and full scraped page content (24h TTL) in `outputs/cache.db`.
R20. Disconnection of the client SSE connection must propagate a cancellation chain down to the python orchestrator, aborting active OpenRouter LLM requests and Scrapling crawler sessions immediately.
R21. **Re-synthesis Endpoint:** The backend must expose a re-synthesis API endpoint (e.g. `POST /api/runs/{run_id}/resynthesize`) that takes a list of disabled domains/sources. It must retrieve the cached search results and scraped page content for that run from SQLite (`outputs/cache.db`), filter out the disabled domains/sources, re-run the LLM synthesizer/compressor to generate the updated report and knowledge representations, and stream the updated results back to the client.

---

## 5. Scope Boundaries

### Included in v1
- Sleek Slate Glassmorphic visual theme.
- Accordion thinking blocks and live scrape status progress.
- Left utility icon sidebar with history drawer.
- The 10 advanced feature modules (R9 to R17).
- Circuit breaker, SQLite cache, and task cancellation.

### Deferred for later
- Collaborative multi-user shared research sessions.
- Real-time video generation inside GenUI cards.
- Directly editing the SQLite cache from the frontend.

---

## 6. Acceptance Examples

### AE1. GenUI Rendering
- **Scenario:** The LLM streams ````genui { "type": "comparison", "headers": ["A", "B"], "rows": [["1", "2"]] } ````.
- **When:** The parser detects the complete code block.
- **Then:** The text is hidden and replaced by a beautifully styled Mantine table component.

### AE2. Citation Hover Mapping
- **Scenario:** User hovers over citation badge `[1]`.
- **When:** Hover occurs.
- **Then:** A dispatch highlights node ID `citation-1` in the G6 canvas with a gold stroke overlay.
