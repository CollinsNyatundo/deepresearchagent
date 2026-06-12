# Design Spec: Perplexity-Style UI/UX Redesign for Deep Research Agent

This specification outlines the visual style, layout composition, and interactive behaviors for upgrading the Deep Research Agent's client workspace to a professional, Perplexity-grade research console.

---

## 1. Goal Description

Provide a premium, high-density dashboard that gives deep visibility into active research tasks while maintaining top-tier readability for final research reports. We will replace the standard layout with a custom **Sleek Slate Glassmorphic** theme, optimize panel real-estate using a **Compact Left Icon Sidebar**, and show real-time agent status via **Accordion Thinking Steps** and a **Live Scrape Queue**.

Additionally, we will implement 10 advanced UI/UX feature modules that elevate the platform to a state-of-the-art research workstation, giving users granular control over data sourcing, real-time feedback cascades, and cross-session knowledge comparison.

---

## 2. Design System Blueprint

### Color Tokens (OLED Dark Mode)
| Role | Hex Code | Usage |
| :--- | :--- | :--- |
| **Background** | `#020617` (Slate 950) | App workspace base container |
| **Panels / Cards** | `#0f172a` (Slate 900) | Sidebar, main grid panes, cards |
| **Borders** | `#1e293b` (Slate 800) | Grid lines, cards, divider borders |
| **Primary Text** | `#f8fafc` (Slate 50) | Headers, active report text |
| **Muted Text** | `#94a3b8` (Slate 400) | Telemetry descriptions, metadata |
| **Accent / CTA** | `#22c55e` (Emerald 500) | Successful status ticks, links, active buttons |
| **Info / Glow** | `#06b6d4` (Cyan 500) | Live processing highlights, loaders |

### Typography Pairing
- **Headings & UI Labels:** `Fira Sans`, sans-serif (Precision, modern, clean)
- **Technical/Telemetry Logs:** `Fira Code`, monospace (High-density precise monospace)

---

## 3. Core Component Layout & Behavior

### A. Compact Left Icon Sidebar
- **Appearance:** A `48px` wide vertical utility bar on the left edge. Styled in `#0f172a` with a `#1e293b` border.
- **Top Elements:**
  - Application Brand Mark (`DR` in Emerald 500).
  - Toggle between **Research Workspace** and **Code Arch (GitNexus)**.
  - Button to start a "New Research" session.
- **Bottom Elements:**
  - System Settings gear icon.
  - Telemetry stats dashboard popup (shows SQLite cache hit rates and API cycle counts on click or hover).
- **Expandability:** Hovering or clicking the sidebar slides open a `240px` drawer displaying full navigation history and descriptive names for past runs.

### B. Two-Pane Main Workspace
When viewing a research run, the dashboard splits horizontally:
1. **Left Panel (50%):** Report View. Scrollable, rendering the markdown research report.
2. **Right Panel (50%):** Analytics Tabs. Contains:
   - **Mindmap View:** G6 tree layout showing research nodes.
   - **Knowledge Graph:** G6 force-directed graph detailing inferred entities and communities.
   - **Export Controls:** Options to export the report to PDF, Word, Markdown, or JSON.

### C. Accordion Thinking Steps & Scrape Queue
During active runs (SSE `streaming` phase), the top of the Left Panel displays the progress block:
- **Planning Stage:** Expands to show the scoping plan and target queries.
- **Web Scraping Stage:** Includes the live scraper queue:
  - Lists target URLs in-queue, resolving, or completed.
  - Shows badge for fetcher tier: `[Stealthy]` (Camoufox) or `[Dynamic]` (Playwright).
- **Thinking Blocks:** Renders texts streamed inside `<thinking>` tags (via `thinking_chunk` events) inside a collapsible accordion card. Features a pulsing typewriter cursor.

---

## 4. Advanced Feature Modules

### 1. Generative UI (GenUI) Dynamic Cards
- **Behavior:** Parses structured JSON payloads in the LLM markdown stream to dynamically render React components rather than static text.
- **Components:** Supporting side-by-side product comparisons, financial ledgers, and interactive event timelines.

### 2. Citation-Graph Hover Mapping
- **Behavior:** Hovering an inline citation like `[1]` highlights its source node in the G6 Knowledge Graph in the right pane, showing its connections.

### 3. Power CLI Search Input Mode
- **Behavior:** Toggling CLI mode transforms the query textbox into a monospace prompt matching CLI tools. Supports flags like `--depth 5` and `--provider groq` with autocomplete.

### 4. Visual Scraper Queue & Telemetry Waterfall
- **Behavior:** Displays active crawls, fetch speeds (ms), HTML bytes saved via boilerplate stripping, and the Stealthy/Dynamic fetcher status.

### 5. Live Source Toggles & Re-scoping
- **Behavior:** A filter row displaying all crawled domains. Clicking a domain toggles it off and prompts a quick LLM synthesis update without a full re-scrape.

### 6. Mindmap Drill-Down & Exploration Drawer
- **Behavior:** Clicking a mindmap node opens a drawer with summaries, citation source snippets, and a "Drill Deeper" button for nested research cycles.

### 7. Dry-Run Scoping Tree Editor
- **Behavior:** Generates a scoping plan preview containing predicted queries and domains. Users can check/uncheck branches before starting execution.

### 8. Dual-Layer Cache Telemetry Panel
- **Behavior:** Renders database statistics showing total entries in SQLite, total search queries cached, and estimated money/time saved by avoiding API/LLM calls.

### 9. Session Crossover & Divergence Mapping
- **Behavior:** A comparative graph view overlaying the current research run with past research sessions, highlighting shared sources or conflicting points.

### 10. Interactive Export Studio
- **Behavior:** Customize typography sizes, margins, table grids, and G6 graph screenshots before compiling reports to PDF, Markdown, or Word.

---

## 5. Verification Plan

### Manual Verification
1. **Layout Integrity:** Verify the 48px Left Sidebar collapses correctly and expands smoothly on hover.
2. **Tab Stability:** Check that toggling between "Mindmap", "Graph", and "Export" tabs in the Right Panel does not cause any blank screens or rendering glitches.
3. **SSE Simulation:** Simulate an SSE stream with a mock generator containing `<thinking>` blocks and progress updates to ensure the accordion updates correctly without unmounting.

### Automated Tests
Run Vitest browser tests to ensure:
- Elements in the sidebar are clickable.
- No React unmount errors occur during state transitions (`idle` → `plan_loading` → `streaming` → `results`).
