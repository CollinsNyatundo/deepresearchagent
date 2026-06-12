---
date: 2026-06-12
topic: landing-page-design-ideas
focus: 10 landing page ideas for system appearance transition
mode: repo-grounded
---

# Ideation: Landing Page & System Appearance Redesign

This document outlines 10 distinct UI/UX design directions for the DeepResearch.ai landing page and system appearance. These ideas aim to transition the interface into a premium, developer-centric environment.

## Grounding Context

### Codebase Context
- The project is a Python FastAPI backend + React/Vite/Mantine v7/AntV G6/GitNexus frontend.
- Current styling uses custom HSL variables, dark slate background `#020617`, mint green accents `#10b981`, and gold text `#f59e0b` for the terminal.
- We have just added a GET `/api/telemetry` endpoint returning SQLite cache statistics and active circuit breakers.
- The UI contains an interactive simulated `TerminalDemo` log-viewer and a "Local Telemetry Health" bento card on the idle screen.

### Topic Axes
1. **Layout & Grid Structure** (e.g., modular bento, hard split-screen, vertical timeline)
2. **Interactivity & Sandboxes** (e.g., interactive prompt typing, radar sweeps, floating drag panels)
3. **Theme & Material** (e.g., glassmorphism, terminal gold, cyberpunk, solarized sage)
4. **Data Observability** (e.g., circular dials, sparklines, falling matrix streams)

---

## Ranked Ideas

### 1. Cyberpunk Bento Grid Dashboard
- **Description:** A high-fidelity modular layout featuring glowing neon purple and blue grids, live observability dials, and circular charts showing cache/breaker telemetry, paired with a small CLI terminal window.
- **Axis:** Layout & Grid Structure
- **Basis:** `external: Web design trends 2026 prioritizing Bento grids for scannability and structural compartmentalization.`
- **Rationale:** Groups stats, input fields, and log streams into dedicated glowing containers, giving it a premium SaaS dashboard vibe.
- **Downsides:** Neon glow shadows can be rendering-intensive on older browsers if not optimized.
- **Confidence:** 95%
- **Complexity:** Medium
- **Mockup Visual:** ![Cyberpunk Bento Grid](file:///C:/Users/COLLINS/.gemini/antigravity/brain/815053cc-37b6-4d24-b5cb-ec11e125834e/cyberpunk_bento_grid_1781241756618.png)
- **Status:** Unexplored

### 2. Retro-Futuristic Gold Console
- **Description:** A terminal-first layout with clean, gold-on-black monospace windows, Mac-style title bar buttons, ASCII sparklines, and a retro blinking block cursor.
- **Axis:** Theme & Material
- **Basis:** `direct: Current terminal log viewer using gold monospace text. Expanding this to the full system appearance.`
- **Rationale:** Solidifies the system's "developer-first tool" credibility by turning the UI into an authentic, highly polished hacker workstation.
- **Downsides:** Pure terminal layout might feel less accessible to non-technical users.
- **Confidence:** 92%
- **Complexity:** Low
- **Mockup Visual:** ![Retro Gold Console](file:///C:/Users/COLLINS/.gemini/antigravity/brain/815053cc-37b6-4d24-b5cb-ec11e125834e/retro_terminal_console_1781241773598.png)
- **Status:** Unexplored

### 3. Glassmorphic Radial Editorial
- **Description:** Elegant frosted glass panels with thin, light-emitting borders floating over a dark slate space radial gradient background. Pairs massive serif headlines with neon mint accents.
- **Axis:** Theme & Material
- **Basis:** `external: Modern design systems using glassmorphism (frosted backgrounds with backdrop-filter) to convey depth and premium feel.`
- **Rationale:** Provides an editorial, high-end visual anchor that makes the tool feel like an AI research laboratory.
- **Downsides:** Requires careful contrast adjustments to maintain readability on lighter background sections.
- **Confidence:** 88%
- **Complexity:** Medium
- **Mockup Visual:** ![Glassmorphic Editorial](file:///C:/Users/COLLINS/.gemini/antigravity/brain/815053cc-37b6-4d24-b5cb-ec11e125834e/glassmorphic_editorial_1781241790591.png)
- **Status:** Unexplored

### 4. Interactive Node Network Space
- **Description:** A dynamic, full-bleed particle network background (using G6) where nodes represent cache keys and web resources. Users can click nodes to explore cached pages.
- **Axis:** Interactivity & Sandboxes
- **Basis:** `direct: Existing AntV G6 integration in MindmapView. Leveraging it on the landing page for interactive cache discovery.`
- **Rationale:** Visualizes the structure of the local research database as a living entity, inviting immediate user play.
- **Downsides:** High CPU usage on startup if rendering too many nodes simultaneously.
- **Confidence:** 85%
- **Complexity:** High
- **Status:** Unexplored

### 5. Split-Screen Control Room
- **Description:** A split-viewport split 50/50 vertically. The left side is a modern clean configuration dashboard (sliders, providers, model ids), and the right side is a live scrolling terminal output.
- **Axis:** Layout & Grid Structure
- **Basis:** `reasoned: Developers want configuration control and output visibility simultaneously. A vertical split satisfies both cleanly.`
- **Rationale:** Separates input setup from output monitoring, creating a clean "control console" workflow.
- **Downsides:** Hard to fit on portrait mobile screens without stack fallback.
- **Confidence:** 90%
- **Complexity:** Low
- **Status:** Unexplored

### 6. Minimalist Brutalist Type
- **Description:** Brutalist high-contrast typography, zero cards or shadows, massive headlines, and vast whitespace. Stats are written as highlighted, giant inline numbers.
- **Axis:** Theme & Material
- **Basis:** `external: Brutalist web design principles focusing on content and raw typography rather than layout decorations.`
- **Rationale:** Extremely fast loading, highly accessible, and speaks to developers who prefer zero UI clutter.
- **Downsides:** Can look "unfinished" or bare if not balanced with excellent font selections.
- **Confidence:** 80%
- **Complexity:** Low
- **Status:** Unexplored

### 7. Solarized Zen Sage
- **Description:** A calming dark-mode layout built with organic sage-green hues (`#14532d`), solarized cream text, and soft transitions, designed to reduce cognitive load during long research cycles.
- **Axis:** Theme & Material
- **Basis:** `reasoned: Research cycles take minutes. A warm, solarized organic theme reduces fatigue compared to high-intensity neon screens.`
- **Rationale:** Creates a cozy, thoughtful environment suited for deep reading and reflection.
- **Downsides:** Diverges from the classic high-tech "neon/black" developer aesthetic.
- **Confidence:** 82%
- **Complexity:** Low
- **Status:** Unexplored

### 8. Digital Matrix Rain Observability
- **Description:** Classic matrix green falling digital rain background animations nested inside the telemetry cards, representing page scrape streams.
- **Axis:** Data Observability
- **Basis:** `external: Nostalgic hacking sci-fi references popular in developer communities.`
- **Rationale:** High nostalgia factor that serves as a fun visual "Easter egg" on the local server.
- **Downsides:** Animated falling code can distract from readable telemetry stats.
- **Confidence:** 75%
- **Complexity:** Medium
- **Status:** Unexplored

### 9. Radar Scope Scraper HUD
- **Description:** A heads-up display (HUD) styling where telemetry is rendered as circular scopes, rotating dials, and sweeping radar overlays representing active scraping.
- **Axis:** Interactivity & Sandboxes
- **Basis:** `reasoned: Scraping requires sweeping domains. Showing it as a sonar/radar sweeps makes active fetching tactile.`
- **Rationale:** Gamifies the wait time during deep search cycles by showing domain targets being "locked and scraped."
- **Downsides:** Circular SVG dials are more complex to animate and keep responsive.
- **Confidence:** 78%
- **Complexity:** Medium
- **Status:** Unexplored

### 10. Historic Chronology Stream
- **Description:** A vertical timeline layout replacing the standard grid. Past research runs and database metrics are displayed as scannable cards along a central timeline vector.
- **Axis:** Layout & Grid Structure
- **Basis:** `direct: GET /runs endpoint returning research history. Chronological representation fits the user's research diary model.`
- **Rationale:** Prioritizes continuous learning and quick resumption of past research.
- **Downsides:** Less focused on starting *new* queries as a primary action.
- **Confidence:** 80%
- **Complexity:** Medium
- **Status:** Unexplored

---

## Rejection Summary

| # | Idea | Reason Rejected |
|---|------|-----------------|
| 1 | Flat Light Mode Theme | Rejected. Stated codebase constraints prioritize dark slate and retro developer aesthetics; light mode conflicts with developer terminal theme. |
| 2 | Pure 3D WebGL Room | Rejected. Too expensive to implement and maintain relative to value; doesn't align with local utility script profile. |
