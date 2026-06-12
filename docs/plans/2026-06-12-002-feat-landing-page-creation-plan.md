# Feat: DeepResearch.ai Premium Developer Landing Page

This implementation plan outlines the creation of a premium, developer-focused landing page for DeepResearch.ai, integrating simulated terminal demos, quick query presets, and local system telemetry.

- **Status:** active
- **Date:** 2026-06-12
- **Topic:** landing-page-creation
- **Mode:** repo-grounded
- **Origin:** [survivors.md](file:///C:/Users/COLLINS/.gemini/antigravity/brain/815053cc-37b6-4d24-b5cb-ec11e125834e/scratch/ce-ideate/c7e4d8a1/survivors.md)

---

## 1. Problem Frame & Goal

The current `idle` landing screen of DeepResearch.ai is a functional but bare developer console. It lacks visual cues explaining how the deep research engine works under the hood, has no onboarding guidance for new users (blank-canvas syndrome), and doesn't showcase the system's local performance metrics or capabilities. 

### Goal
Redesign the landing page to deliver a state-of-the-art developer landing experience. We will introduce:
1. An animated live terminal typing demo showing mock SSE streams.
2. One-click preset search badges.
3. A local telemetry stats dashboard showing cache hit rates and circuit breaker cooldowns.
4. Clean, high-contrast typography and layout styling.

---

## 2. Proposed Changes & Implementation Units

### [MODIFY] [api.py](file:///d:/Projects/ai-ml/DeepResearchAgent/research_engine/api.py)
* Create a `/api/telemetry` endpoint on the FastAPI backend that queries:
  - Cache size and hit statistics from the cache manager.
  - Active domain-level circuit breaker status.
  - Overall scraper success rates from scraping history.

### [NEW] [TerminalDemo.tsx](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/components/landing/TerminalDemo.tsx)
* Build a mock console component that simulates typing a query (e.g. `research_engine --query "superconductor breakthroughs"`) and streams a series of mock research phase logs (`planning`, `searching`, `scraping`, `synthesizing`).
* Features a retro gold-on-black terminal screen, red/yellow/green window buttons, and a blinking cursor.
* Supports user interactions: hover-to-pause and click-to-skip.

### [MODIFY] [App.tsx](file:///d:/Projects/ai-ml/DeepResearchAgent/frontend/src/App.tsx)
* Integrate the new `TerminalDemo` component.
* Render interactive preset badges below the main prompt textarea. Clicking a preset dynamically populates the query input, provider, model, and depth sliders.
* Fetch metrics from `/api/telemetry` on mount and display them inside a sleek "Local Telemetry Health" bento card on the landing dashboard.

---

## 3. Implementation Units

### U1: Backend Telemetry API
* **File:** `research_engine/api.py`
* **Details:**
  - Import the cache manager and circuit breaker instances.
  - Add an async route `@app.get("/api/telemetry")` returning:
    - `total_cached_queries`: count of rows in cache database.
    - `total_scraped_pages`: count of scraped pages in cache.
    - `active_circuit_breakers`: list of domains currently in `Open` state.
    - `scraper_success_rate`: calculated percentage of successful scrapes.

### U2: Terminal Typing Demo Component
* **File:** `frontend/src/components/landing/TerminalDemo.tsx`
* **Details:**
  - Create a React component using React hooks (`setInterval`) to type out simulated logs character-by-character.
  - Style with a black background, Fira Code font, and gold-500 text (`#f59e0b`).
  - Add standard window headers (window buttons, title).

### U3: Presets & Telemetry dashboard in App.tsx
* **File:** `frontend/src/App.tsx`
* **Details:**
  - Add preset buttons for common tasks (e.g. `Llama 3.3 performance`, `Superconductivity breakthroughs`, `Next.js App Router migration`).
  - Implement a `useEffect` hook to fetch data from `/api/telemetry` and render a dashboard panel showing the metrics.
  - Integrate all elements into a cohesive, responsive layout inside the `idle` state screen.

---

## 4. Verification Plan

### Automated Tests
* Run `npm run build` in `frontend/` to verify no compilation errors.
* Run backend tests via `uv run pytest` to ensure existing API routes and modules remain unbroken.

### Manual Verification
* Start backend: `uv run research serve`
* Start frontend: `npm run dev`
* Load landing page at `http://localhost:5173`.
* Verify that:
  - Presets correctly populate the input fields.
  - The typing terminal demo simulates query execution and logs.
  - Telemetry statistics load correctly from the backend endpoint.
