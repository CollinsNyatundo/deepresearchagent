# Technical Plan: Perplexity-Style UI/UX Redesign for Deep Research Agent

- **Status:** active
- **Date:** 2026-06-12
- **Topic:** perplexity-ui-redesign
- **Mode:** repo-grounded
- **Origin:** [2026-06-12-perplexity-ui-design-requirements.md](file:///d:/Projects/ai-ml/DeepResearchAgent/docs/brainstorms/2026-06-12-perplexity-ui-design-requirements.md)

---

## 1. Problem Frame & Scope

The Deep Research Agent frontend needs a high-density, real-time dashboard layout mirroring Perplexity's readability and density. Currently, layout elements scale poorly, and real-time scrapes lack visual step-by-step progress tracking.

### Scope Boundaries
- **In Scope:**
  - Sleek Slate Glassmorphic palette (`#020617` background, `#0f172a` panels, `#1e293b` borders, and `#22c55e` accents).
  - Compact Left Icon Sidebar (hover to expand history).
  - G6 Canvas container ResizeObservers.
  - Collapsible reasoning steps ( SSE `<thinking>` logs) + scraper queue telemetry.
  - 10 Advanced features (GenUI card streaming, domain filter toggles, re-synthesis endpoint, G6 highlight matching, etc.).
- **Out of Scope:**
  - Multi-user collaboration.
  - Video stream rendering inside cards.

---

## 2. Implementation Units (U-IDs)

### U1: Backend Re-synthesis Endpoint & Outputs Directory Init
- **Files:**
  - `research_engine/models.py`
  - `research_engine/api.py`
- **Approach:**
  - Define `ResynthesizeRequest` Pydantic model.
  - Create endpoint `POST /api/runs/{run_id}/resynthesize` accepting `disabled_domains`.
  - Load run details via `load_run(run_id)`.
  - Filter out search results and scraped pages belonging to `disabled_domains`.
  - Execute `_generate_report` on the filtered research context to stream the regenerated markdown report via SSE.
  - Initialize the `outputs/` folder in the FastAPI lifespan startup hook.

### U2: Compact Left Icon Sidebar & Global Workspace Layout
- **Files:**
  - `frontend/src/App.tsx`
  - `frontend/src/components/runs/RunList.tsx`
- **Approach:**
  - Replace top navbar with a `48px` wide Left Sidebar.
  - Style with a deep slate background `#0f172a`, thin border `#1e293b`, and brand badge.
  - Bind hover state to toggle visibility of a `240px` wide Mantine Drawer containing the run history.
  - Add workspace toggle buttons (Research vs Code Arch).

### U3: Accordion steps & Scraper Queue Telemetry
- **Files:**
  - `frontend/src/components/views/ResearchProgress.tsx`
- **Approach:**
  - Implement a collapsible `Accordion` containing step checklists (Planning, Searching, Scraping, Synthesizing).
  - Add an elapsed run timer.
  - Render a scraper queue table showing resolving URLs, timings, bytes saved, and badged fetcher tiers (`[Stealthy]` vs `[Dynamic]` vs `[Basic]`).

### U4: GenUI Streaming Parser & Shimmer Loader
- **Files:**
  - `frontend/src/components/views/ReportView.tsx`
- **Approach:**
  - Implement custom parsing inside ReportView to scan for ````genui ... ```` code blocks.
  - If the code block is incomplete, render a shimmer loading state (`Mantine Skeleton`).
  - Once the closing ```` tag is detected, parse the JSON and mount custom widgets (tables, event timelines).

### U5: Citation Hover Mapping & G6 Node Highlighting
- **Files:**
  - `frontend/src/components/views/ReportView.tsx`
  - `frontend/src/components/mindmap/G6MindmapGraph.tsx`
  - `frontend/src/components/knowledge-graph/KnowledgeGraphView.tsx`
- **Approach:**
  - Add a hover listener to citations `[1]` that dispatches a custom highlight event with the source node URL/ID.
  - Subscribe G6 graphs to this event and update node styling (e.g. gold stroke/ring) when active.

### U6: Power CLI Search Input Monospace Mode
- **Files:**
  - `frontend/src/App.tsx`
- **Approach:**
  - Create a checkbox/toggle to enable "CLI Mode".
  - In CLI mode, convert input text area to a monospace font (`Fira Code`) with autocomplete tooltips suggesting flags (e.g. `--model`, `--provider`).

### U7: Scraper Circuit Breaker
- **Files:**
  - `research_engine/sources/circuit_breaker.py`
- **Approach:**
  - Maintain a count of consecutive scrape failures per domain.
  - If failures >= 3, set domain status to `OPEN` for 5 minutes, routing requests to static fetcher fallbacks.

### U8: G6 Canvas ResizeObserver
- **Files:**
  - `frontend/src/components/mindmap/G6MindmapGraph.tsx`
  - `frontend/src/components/knowledge-graph/KnowledgeGraphView.tsx`
- **Approach:**
  - Instantiate `ResizeObserver` pointing to the G6 canvas container element.
  - On bounds change, invoke `graph.resize()` (G6 v5).

### U9: Session Crossover Mapping & Mindmap Drill-down Drawer
- **Files:**
  - `frontend/src/components/knowledge-graph/KnowledgeGraphView.tsx`
  - `frontend/src/components/mindmap/MindmapView.tsx`
- **Approach:**
  - Add a selection checkbox in the run history sidebar to select comparisons.
  - Draw highlighting lines/nodes in G6 representing concepts shared across selected past sessions.
  - Add a detail panel drawer in the mindmap view that includes a "Drill Deeper" button.

### U10: Dry-Run Scoping Tree Editor & Export Panel Upgrades
- **Files:**
  - `frontend/src/components/views/PlanReview.tsx`
  - `frontend/src/components/views/ExportPanel.tsx`
- **Approach:**
  - Before execution, render the generated scoping tree with checkboxes for each predicted sub-query and domain.
  - In `ExportPanel.tsx`, add size and margin customization sliders.

---

## 3. Verification Plan

### Automated Tests
- Run tests:
  ```bash
  uv run pytest tests/ -v
  ```
- Build frontend:
  ```bash
  cd frontend && npm run build
  ```

### Manual Verification
- Test Left Sidebar hover expand/collapse.
- Verify G6 canvas adjusts bounds smoothly without tearing.
- Validate that disabling a domain on the badge filters triggers the SSE-based `/resynthesize` endpoint and updates the report dynamically.
- Test streamed incomplete ````genui```` blocks to ensure they display the shimmer loader instead of causing parser crashes.
