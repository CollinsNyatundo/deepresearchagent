# DeepResearch.ai - Version 7 Polished Telemetry Implementation Plan

This implementation plan details the technical rollout for the **Version 7: Polished Telemetry** layout. It redesigns the frontend to feature an elegant dark-mode dashboard with a three-pane workspace, collapsible reasoning logs, and premium developer-focused typography.

## Design System Specifications (ui-ux-pro-max)

- **Layout Style:** Data-Dense Dashboard (Three-pane split telemetry view)
- **Palette (Slate + Mint + Monospace Gold):**
  - Background (slate-950): `#020617`
  - Cards & Sidebars (slate-900): `#0f172a`
  - Primary Accent (mint-500): `#10b981`
  - Telemetry/Warnings (gold-500): `#f59e0b`
  - Main Text (slate-100): `#f1f5f9`
  - Muted Text (slate-400): `#94a3b8`
- **Typography:**
  - Headings / Code / Terminal: **Fira Code**
  - Body / UI Labels: **Fira Sans**
  - Google Fonts import:
    ```css
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');
    ```

---

## Proposed Changes

### 1. Typography & Global Styles

We will load the Fira Code/Fira Sans fonts and define global CSS variables for colors, borders, and smooth transitions.

#### [MODIFY] [index.css](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/index.css)
- Add the `@import` url for Google Fonts: Fira Code and Fira Sans.
- Set global CSS variables under `:root` matching the slate, mint, and monospace gold palette.
- Override default body styles to use Fira Sans as the base typeface and Fira Code for all monospace/code elements.
- Add utility transition helper classes for animations.

---

### 2. Main Workspace Navigation & Sidebar

We will structure `App.tsx` to display the sleek landing console in the `idle` state, and transition into a beautiful three-pane workspace in active states (`streaming` and `results`).

#### [MODIFY] [App.tsx](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/App.tsx)
- Reorganize the root `App` component shell using Mantine's `AppShell` with deep slate colors.
- Define layout structure for the **Three-Pane Dashboard**:
  - **Sidebar (Pane 1):** Past research runs list, rendered in `#0f172a` with thin `#1e293b` borders.
  - **Main Screen (Pane 2):** Landing console input (idle state) or active research telemetry.
  - **Details Panel (Pane 3):** Splittable knowledge graph and report view.
- Inject the `@import` typography and configure Mantine's theme override to default to Fira Sans and Fira Code.

---

### 3. Reasoning Telemetry & Scraper Dashboard

We will redesign the progress component to render a collapsible terminal log representing the LLM's active thinking stream, paired with a grid showing the scraping queue.

#### [MODIFY] [ResearchProgress.tsx](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/components/views/ResearchProgress.tsx)
- Restyle the "Thinking Process" block:
  - Embed inside a Mantine `Collapse` or `Accordion`.
  - Style as a retro-style terminal window (black background, Fira Code font, golden text, blinking cursor).
  - Animate text rendering to simulate stdout streams.
- Restyle the "Live Scrape Dashboard":
  - Use a high-density table grid with minimal padding.
  - Color active rows with a subtle mint background glow.
  - Render status badges (`STEALTHY_FETCH`, `CACHE_HIT`, etc.) using solid themed fills.

---

### 4. Splittable Report & Citation HoverCards

We will implement a side-by-side view for the generated Markdown report and the G6 mindmap, alongside hovercard citations.

#### [MODIFY] [ReportView.tsx](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/components/views/ReportView.tsx)
- Render the Markdown report alongside the G6 mindmap in a responsive 50/50 horizontal split (or vertical split on small viewports).
- Apply editorial typography styling: Fira Sans for markdown headers and clean readable text.
- Render inline citations (`[1]`) using a styled Mantine `HoverCard` that opens on hover to display snippet text, title, domain, and direct URL.

---

## Verification Plan

### Automated Tests
- Run the frontend build to verify compilation:
  ```bash
  npm run build
  ```
- Run pytest backend suite to ensure API compliance:
  ```bash
  uv run pytest
  ```

### Manual Verification
- Launch the application:
  ```bash
  npm run dev
  ```
- Verify the landing page console input UI layout.
- Initiate a research run, verify that the terminal thinking accordion streams tokens in Fira Code, and check that citations render inline hovercards correctly.
