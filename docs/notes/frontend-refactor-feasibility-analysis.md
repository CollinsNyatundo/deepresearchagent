# Deep Research Agent — Frontend Refactor Feasibility Analysis

## Document Control
| Field | Value |
|-------|-------|
| Generated | 2026-01-23 |
| Based on | `frontend/design.md` (607 lines) + Full codebase review |
| Scope | Visual reskin + UX reorganization — backend unchanged |
| Status | Exploration — no code changes committed |

---

## 1. Executive Summary

**The refactor is entirely feasible.** The `frontend/design.md` describes a visual skin and interaction layer, not a fundamentally different application architecture. Both the target design and the current application are React + TypeScript SPAs. The refactor is a **frontend reskinning + UX reorganization** that preserves the existing FastAPI backend completely.

The design is **not a drop-in replacement**. It requires a full component library swap (Mantine → shadcn/ui + Tailwind), a global CSS rewrite with custom liquid-glass effects, and the addition of WebGL/Canvas background components. This is a **large but well-scoped** refactor with a clear boundary: everything inside `frontend/src/` changes; nothing in `research_engine/` or the backend API changes.

**Recommendation:** Proceed with a **REST-First Reskin** (Option A). Keep the existing FastAPI backend, Supabase JWT auth, and `fetch`-based API client intact. Only the visual layer, component library, and layout shell change.

---

## 2. What the Design.md Actually Describes

The `frontend/design.md` (607 lines) documents **Moon Note**, a Zettelkasten personal knowledge-base application built around a dark, cinematic aesthetic.

### 2.1 Target Stack (Design.md)

| Layer | Technology |
|-------|------------|
| Framework | React 19 + TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS v3 + `tailwindcss-animate` |
| UI Components | shadcn/ui (40+ Radix primitives) |
| Routing | `react-router` v7 |
| API Layer | tRPC 11 + `@tanstack/react-query` |
| Backend | Hono + Drizzle ORM + MySQL |
| Auth | Kimi OAuth 2.0 + JWT sessions (HTTP-only cookie) |
| Data Viz | D3.js (`d3-force`) |
| Markdown | `react-markdown` + `remark-gfm` |
| Icons | `lucide-react` |
| Utilities | `class-variance-authority`, `clsx`, `tailwind-merge`, `zod`, `superjson` |

### 2.2 Visual Design System

| Token | Value | Usage |
|-------|-------|-------|
| Base/Background | `#000000` | Page background |
| Foreground Primary | `#e0e0e0` | Primary text, headings |
| Dim | `#999999` | Secondary text, hover states |
| Subtle | `#555555` | Muted labels, inactive icons |
| Muted | `#333333` | Borders, dividers |
| Accent | `#c8956c` | Buttons, links, interactive highlights |
| Link | `#d4a574` | Wiki links, external references |
| Success | `#7dac5a` | Positive states |
| Danger | `#c45a5a` | Delete actions, errors |
| Warning | `#e0af68` | Caution indicators |
| Border | `#1a1a1a` | Panel borders, separators |

**Typography:** System font stack, body at 14px/0.875rem, code at 13px `SF Mono`/`Fira Code`, headings at 20px–24px with weight 600.

**Spacing:** Header 44px, Sidebar 240px, Content max-width 672px, panel padding 12–16px, button radius 12px, input radius 8px.

**Signature Effect — Liquid Glass:**
- Standard: `backdrop-filter: blur(6px) saturate(140%)` over `rgba(255,255,255,0.01)` with `background-blend-mode: luminosity`
- Strong: `backdrop-filter: blur(40px) saturate(150%)`
- Requires pseudo-elements `::before` (edge highlight gradient at 25% opacity) and `::after` (surface sheen radial gradients)
- `box-shadow: inset 0 1px 1px rgba(255,255,255,0.1), 0 8px 32px rgba(0,0,0,0.15)`

**Custom Scrollbar:** 4px width, track transparent, thumb `rgba(255,255,255,0.08)` with 2px radius, hover at `rgba(255,255,255,0.15)`.

### 2.3 Layout Architecture (3-Zone Single Page)

```
┌─────────────────────────────────────────────────────────────┐
│  Header Bar (44px, liquid-glass)                              │
│  [Brand] [Note Count]              [Tabs] [Background] [User]│
├──────────┬──────────────────────────────────────────────────┤
│          │                                                  │
│ Sidebar  │  Main Content Area                               │
│ (240px)  │  • Editor view  OR  • Graph view                 │
│          │                                                  │
│ [Moon]   │                                                  │
│ [Search] │                                                  │
│ [List]   │                                                  │
│ [Btns]   │                                                  │
│          │                                                  │
└──────────┴──────────────────────────────────────────────────┘
           ↑ z-index 0: Full-viewport procedural background
```

### 2.4 Background System (4 Procedural GPU Backgrounds)

All rendered at z-index 0, 60fps via `requestAnimationFrame`:

1. **Moonlit Ripple** (`MoonlitRipple.tsx`) — Full WebGL fragment shader with 7-layer wave simulation, procedural moon disc with craters, mouse-reactive ripples, fully desaturated to grayscale at 70% luminance.

2. **Silk Flow Field** (`FlowField.tsx`) — 3-layer silk fabric simulation with domain warping, Kajiya-Kay anisotropic specular reflection, mouse-controlled lighting, ACES tone mapping, film grain, fully desaturated grayscale.

3. **Rain on Glass** (`RainOnGlass.tsx`) — Canvas 2D + WebGL hybrid, up to 900 physics-based raindrops with collision/merging/trail spawning, procedural cityscape background, water refraction through droplets, desaturated with `saturate(0.7) brightness(0.55)`.

4. **Solid Color** — Static CSS background with four presets: `#000000` (Ink Black), `#1a1a2e` (Deep Blue), `#1a1308` (Brown), `#0d1f0d` (Dark Green).

**Critical:** All four backgrounds must be **lazy-loaded** (`React.lazy`) to avoid blocking initial render.

### 2.5 Moon Note Features (Not Applicable to Deep Research)

These are domain-specific to the notes app and **should not be ported**:

- Moon phase widget (canvas-rendered real-time lunar phase, 48x48px)
- Note editor with title + content textarea, 400ms debounced auto-save
- Wiki link system: `[[Note Title]]` syntax, click-to-navigate, click-to-create
- Backlinks / outgoing links panel below rendered Markdown
- D3 force-directed knowledge graph with 6 forces (link, charge, center, collision, x, y)
- 12 starter notes about LLMs auto-seeded on first login
- Note count in header
- Edit/Preview toggle tabs on editor
- `Ctrl/Cmd+S` manual save shortcut

---

## 3. Current Deep Research Agent Frontend

### 3.1 Existing Stack

| Layer | Technology | File |
|-------|------------|------|
| Framework | React 18 + TypeScript | `frontend/src/main.tsx` |
| Build Tool | Vite | `frontend/vite.config.ts` |
| UI Library | Mantine v7 (`@mantine/core`, `@mantine/hooks`) | `frontend/src/main.tsx:5` |
| Icons | Tabler Icons (`@tabler/icons-react`) | `frontend/src/App.tsx:27` |
| Styling | Mantine theme object | `frontend/src/styles/theme.ts` |
| API Client | Raw `fetch` wrapper with Bearer token injection | `frontend/src/api/client.ts:24` |
| Auth | Supabase JWT via `AuthContext` | `frontend/src/lib/authContext.tsx` |
| Data Viz | AntV G6 v5 (unified `Graph` class) | `frontend/src/components/mindmap/G6MindmapGraph.tsx` |
| Markdown | `react-markdown` (implied by rendering) | Report view components |

### 3.2 Current Color System (Mantine Theme)

```typescript
// frontend/src/styles/theme.ts
primaryColor: 'mint',
colors: {
  mint: ['#e6fcf5', '#c3fae8', '#96f2d7', '#63e6be', '#38d9a9',
         '#20c997', '#12b886', '#0ca678', '#099268', '#087f5b'],
},
```

Background colors use CSS custom properties:
- `--color-slate-950` — main background
- `--color-slate-900` — header, sidebar, card backgrounds
- `--color-slate-800` — borders
- `--color-text-main` — primary text
- `--color-mint-500` — accent (teal/green)

### 3.3 Current Layout Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  AppShell.Header (60px)                                      │
│  [Brain Icon] DeepResearch.ai  [Workspace] [Badge] [Model]   │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                  │
│ AppShell │  AppShell.Main                                   │
│.Navbar   │  State machine: idle → modal → plan_loading →    │
│ (280px)  │  plan_review → streaming → results               │
│          │                                                  │
│ [Segment │  Views:                                          │
│  Control]│  • Idle: Hero + Query Composer + TerminalDemo   │
│ [New]    │  • Plan Review: PlanReview component             │
│ [RunList]│  • Streaming: ResearchProgress (SSE events)       │
│          │  • Results: ReportView + CitationsView/Export    │
│ [SignOut]│  • Code-Arch: GitNexusWebView (iframe)           │
│          │                                                  │
└──────────┴──────────────────────────────────────────────────┘
```

### 3.4 Current App State Machine

```typescript
// frontend/src/App.tsx:106-112
type AppState =
  | 'idle'           // No research selected — shows hero + query composer
  | 'modal'          // New research modal open
  | 'plan_loading'   // Generating plan
  | 'plan_review'    // User reviewing/editing plan
  | 'streaming'      // Research in progress with SSE
  | 'results';       // Viewing completed results
```

### 3.5 Current API Endpoints (All Preserved)

From `frontend/src/api/client.ts` and `research_engine/api.py`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/workspaces` | GET, POST | List / create workspaces |
| `/runs` | GET | List research runs (workspace-scoped) |
| `/runs/{id}` | GET | Full run details |
| `/runs/{id}/report` | GET | Markdown report content |
| `/runs/{id}/mindmap` | GET | G6 mindmap graph JSON |
| `/runs/{id}/mindmap/expand` | POST | Drill deeper into node |
| `/runs/{id}/export/{format}` | GET | Download export file |
| `/runs/{id}/exports` | GET | List available export formats |
| `/runs/{id}/knowledge-graph` | GET | Knowledge graph JSON |
| `/runs/{id}/knowledge-graph/available` | GET | KG availability check |
| `/runs/{id}/knowledge-graph/build` | POST | Trigger manual KG build |
| `/runs/{id}/knowledge-graph/query` | POST | BFS/DFS graph query |
| `/runs/{id}/knowledge-graph/html` | GET | Interactive graph.html |
| `/runs/{id}/knowledge-graph/mcp` | GET, POST | MCP server status/start/stop |
| `/runs/{id}/resynthesize` | POST | Re-synthesize with domain filter |
| `/research` | POST | Start research (blocking) |
| `/research/stream` | POST | Start research with SSE |
| `/research/plan` | POST | Generate plan for review |
| `/research/execute/stream` | POST | Execute approved plan with SSE |
| `/validate-model` | POST | Validate model ID |
| `/api/telemetry` | GET | Cache + circuit breaker stats |
| `/gitnexus/serve/start` | POST | Start GitNexus bridge |
| `/gitnexus/serve/stop` | POST | Stop GitNexus bridge |
| `/gitnexus/serve/status` | GET | Bridge status |
| `/open-file` | POST | Open file in local editor |
| `/scraper/refresh-cache` | POST | Re-probe fetcher availability |
| `/health` | GET | Health check |

### 3.6 Current Features (All to Be Retained)

1. **Authentication** — Supabase JWT, workspace-based access control
2. **Workspace Selector** — Create/select workspace, all runs scoped
3. **Query Composer** — Research query input, model selection, provider toggle (OpenRouter/Groq), mode toggle (web/github), depth slider (1–5), quick presets
4. **Plan Review** — AI-generated research plan with steps, sub-queries, estimated duration, approve/regenerate
5. **SSE Streaming** — Real-time research progress events (classifying, planning, searching, scraping, validating, synthesizing, reflecting)
6. **Report Viewer** — Markdown report rendering with G6 mindmap
7. **Citations Panel** — Source citations with URLs, domains, snippets
8. **Export Panel** — Download in markdown, PDF, docx, xlsx, mindmap JSON, knowledge graph, graph HTML
9. **Mindmap (G6)** — Interactive tree visualization with node expansion
10. **Knowledge Graph** — Graphify-built graph with communities, BFS/DFS query, MCP server
11. **GitNexus Code Architecture** — Web UI bridge to `gitnexus serve` on port 4747
12. **Telemetry Dashboard** — Cache stats, scraper success rate, active circuit breakers
13. **Resynthesis** — Re-generate report excluding disabled domains

---

## 4. What Changes vs. What Stays

### 4.1 Backend — No Changes (100% Preserved)

| Component | File | Status |
|-----------|------|--------|
| FastAPI server | `research_engine/api.py` | **Unchanged** |
| Auth middleware | `research_engine/auth.py` | **Unchanged** |
| Orchestrator | `research_engine/agent/orchestrator.py` | **Unchanged** |
| Planner | `research_engine/agent/planner.py` | **Unchanged** |
| Searcher | `research_engine/agent/searcher.py` | **Unchanged** |
| Web scraper | `research_engine/sources/web_scraper.py` | **Unchanged** |
| Cache/Circuit breaker | `research_engine/sources/cache.py`, `sources/circuit_breaker.py` | **Unchanged** |
| LLM provider | `research_engine/llm/provider.py` | **Unchanged** |
| Output storage | `research_engine/output/storage.py` | **Unchanged** |
| Mindmap builder | `research_engine/output/mindmap.py` | **Unchanged** |
| Knowledge graph | `research_engine/knowledge_graph/` | **Unchanged** |
| Exporter | `research_engine/output/exporter.py` | **Unchanged** |
| Models (Pydantic) | `research_engine/models.py` | **Unchanged** |
| Config | `research_engine/config.py` | **Unchanged** |
| Database | Supabase (PostgreSQL) | **Unchanged** |
| API endpoints | All 25+ endpoints | **Unchanged** |
| SSE streaming | `research_engine/api.py` streaming handlers | **Unchanged** |
| CORS | Already allows `localhost:5173` | **Unchanged** |

### 4.2 Frontend — Full Rewrite Required

| Layer | Current | Target | Action |
|-------|---------|--------|--------|
| **UI Framework** | Mantine v7 | shadcn/ui + Tailwind CSS v3 | Full swap |
| **Styling approach** | Mantine `theme` object + inline `style` props | Tailwind utility classes + custom `index.css` | Rewrite |
| **Global CSS** | Minimal | `index.css` with liquid glass, scrollbar, dark theme vars | Add |
| **Layout shell** | `AppShell` (header 60px, navbar 280px) | Custom flex/grid (header 44px, sidebar 240px) | Rewrite |
| **API transport** | `fetch` wrapper | `fetch` wrapper (retained) | **Keep** |
| **Auth** | Supabase JWT context | Supabase JWT context | **Keep** |
| **Routing** | State machine (no router) | `react-router` v7 (optional, minor) | Add if desired |
| **Icons** | `@tabler/icons-react` | `lucide-react` | Swap |
| **Font** | Fira Sans + Fira Code | Fira Sans + Fira Code | **Keep** |
| **Build tool** | Vite | Vite | **Keep** |
| **TypeScript** | ~5.6 | ~5.9 | Upgrade |
| **React** | 18 | 19 | Upgrade |
| **Backgrounds** | Solid slate | 4 procedural GPU backgrounds | Add |
| **Component primitives** | 40+ Mantine components | 40+ shadcn/ui components | Swap |
| **Data viz** | AntV G6 v5 | AntV G6 v5 | **Keep** |

### 4.3 Color Mapping (Exact Translations)

| Semantic Role | Current Value | Moon Note Target | Where Used |
|---------------|---------------|------------------|------------|
| Page background | `var(--color-slate-950)` ≈ `#0B0F19` | `#000000` | `body`, `AppShell.Main` |
| Card/panel background | `var(--color-slate-900)` ≈ `#111827` | `liquid-glass` (transparent + blur) | `Paper`, panels |
| Border | `var(--color-slate-800)` ≈ `#1E293B` | `#1a1a1a` | Borders, dividers |
| Primary text | `var(--color-text-main)` ≈ `#E2E8F0` | `#e0e0e0` | Headings, body |
| Secondary text | `c="dimmed"` ≈ `#94A3B8` | `#999999` | Descriptions, labels |
| Muted text | Inline grays | `#555555` | Placeholders, inactive |
| Accent | `var(--color-mint-500)` ≈ `#20C997` (teal) | `#c8956c` (warm amber) | Buttons, badges, highlights |
| Link color | Mantine default | `#d4a574` | Anchor tags |
| Danger | `red` / `#EF4444` | `#c45a5a` | Errors, delete |
| Success | `green` / `#22C55E` | `#7dac5a` | Success states |
| Warning | `yellow` / `#EAB308` | `#e0af68` | Caution |

### 4.4 Typography Mapping (Exact Translations)

| Role | Current | Moon Note Target |
|------|---------|------------------|
| Body | 14px, system-ui, weight 400 | 14px/0.875rem, system stack, weight 400 |
| Code/Monospace | Fira Code, 13px | Fira Code, 13px/0.8125rem |
| Page Title | 20px, Fira Sans, weight 700 | 20px/1.25rem, system stack, weight 600 |
| Section Heading (H1) | 24px, Fira Sans, weight 700 | 24px/1.5em, system stack, weight 600 |
| Subheading (H2) | 20px, Fira Sans, weight 700 | 19.2px/1.2em, system stack, weight 600 |
| Sidebar Label | 10px, dimmed | 10px/0.625rem, `#555` |
| Button Label | 14px | 12px/0.75rem |
| Markdown Body | 14px | 14px/1em, `#bbb` |
| Line height (body) | Default | 1.7 |
| Line height (editor) | Default | ~1.625 (`leading-relaxed`) |

---

## 5. Integration Strategy

### 5.1 Option A: REST-First Reskin (Recommended)

**Keep the existing `fetch`-based API client and FastAPI backend exactly as-is.** Only the UI layer changes.

```
┌─────────────────────────────────────────────────────────────┐
│  NEW FRONTEND (Moon Note aesthetic)                         │
│  ├── React 19 + TypeScript + Vite                           │
│  ├── Tailwind CSS v3 + shadcn/ui                            │
│  ├── Liquid glass CSS (index.css)                           │
│  ├── 4 procedural WebGL/Canvas backgrounds                  │
│  ├── Custom layout shell (header 44px + sidebar 240px)      │
│  ├── lucide-react icons                                     │
│  ├── SAME api/client.ts (fetch wrapper)                     │
│  └── SAME authContext.tsx (Supabase JWT)                    │
│                                                             │
│  All features preserved:                                   │
│  • Query composer, plan review, SSE streaming              │
│  • Report view, citations, export panel                    │
│  • Mindmap (G6), knowledge graph, GitNexus                 │
│  • Telemetry dashboard, resynthesis                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ REST + SSE (unchanged)
┌─────────────────────────────────────────────────────────────┐
│  EXISTING BACKEND (100% unchanged)                          │
│  ├── FastAPI (research_engine/api.py)                       │
│  ├── Supabase JWT auth (verify_supabase_jwt)              │
│  ├── Workspace-based access control                         │
│  ├── All 25+ REST endpoints                               │
│  ├── SSE streaming (/research/stream, /research/execute)   │
│  ├── File-based storage (outputs/)                         │
│  ├── G6 mindmap generation                                 │
│  ├── Graphify knowledge graph                              │
│  └── GitNexus bridge                                       │
└─────────────────────────────────────────────────────────────┘
```

**Pros:**
- Fastest path — no backend changes, no schema migration, no auth migration
- All SSE streaming logic stays identical (same `fetch` + `ReadableStream` pattern)
- All API endpoints preserved with zero modifications
- Can incrementally migrate components
- No risk of breaking research engine logic
- Supabase auth and workspace system remain intact

**Cons:**
- Does not adopt tRPC (the design.md's chosen API layer)
- Slightly less "type-safe" at the transport layer than tRPC (but TypeScript types in `api.ts` already provide compile-time safety)
- The design.md's Hono/Drizzle/MySQL backend is not used

**Verdict:** The cons are irrelevant for a visual refactor. The API layer is an implementation detail that does not affect the user experience.

### 5.2 Option B: Full Stack Alignment (Not Recommended)

Add tRPC to the FastAPI backend and switch the frontend to tRPC.

**Required changes:**
1. Add tRPC server alongside FastAPI (or migrate from FastAPI to Hono)
2. Rewrite all endpoint handlers as tRPC procedures with Zod schemas
3. Rewrite auth middleware from FastAPI `Depends` to tRPC context
4. Switch Supabase JWT to a cookie-based session (or keep Supabase but adapt to tRPC)
5. Rewrite `api/client.ts` from `fetch` to `@trpc/client`
6. Add `@tanstack/react-query` + tRPC React hooks
7. Add `superjson` for Date serialization

**Pros:**
- Fully aligned with design.md's architecture
- End-to-end type safety (tRPC infers types from backend)
- Automatic query caching and invalidation via React Query

**Cons:**
- Massive backend rewrite — all FastAPI routes, auth, middleware
- Schema migration from Supabase to MySQL (or keep Supabase but add tRPC wrapper)
- High risk — could break the research engine
- 2–3 weeks of backend work before any frontend changes
- No user-facing benefit — the transport layer is invisible

**Verdict:** Not justified for a visual refactor. The design.md's backend stack was designed for a *notes app*, not a research agent. The research engine's FastAPI architecture is mature and feature-complete.

---

## 6. Feature Mapping: Moon Note Layout → Deep Research Features

### 6.1 Header Bar (44px, liquid-glass)

| Moon Note Element | Deep Research Equivalent | Notes |
|-------------------|--------------------------|-------|
| Diamond icon (`◊`) + brand wordmark | `IconBrain` (or custom logo) + "DeepResearch" | Keep the `.ai` accent styling |
| Note count | Run count for selected workspace | Optional — can show in sidebar instead |
| Editor / Graph toggle tabs | **Research / Code-Arch toggle** | Already exists as `SegmentedControl` in sidebar; can move to header |
| Background switcher button (sun/moon icon) | Background switcher dropdown | New feature — toggles 4 procedural backgrounds |
| User name + logout | User email + logout button | Already exists |

**Implementation:** The header uses `liquid-glass` class. Active tabs use `bg-white/[0.06]` background. Segmented control style for the Research/Code-Arch toggle.

### 6.2 Sidebar (240px, liquid-glass)

| Moon Note Element | Deep Research Equivalent | Notes |
|-------------------|--------------------------|-------|
| Moon phase widget | **Remove** — replace with app logo or telemetry mini-card | Moon phase is domain-specific to notes app |
| Search input | **Workspace-scoped run search** | Keep functionality, reskin with `bg-white/[0.03]` |
| Note list (scrollable, selected highlight) | **Run list** (`RunList.tsx`) | Already exists — reskin list items with `bg-white/[0.06]` selected state |
| "+ New Note" button | **"+ New Research"** button | Already exists — reskin with `liquid-glass-strong` |
| "Manage" mode (multi-select + delete) | **Multi-select runs + bulk delete** | Can add this feature; backend already has `/runs` |
| — | **Workspace Selector** | Currently in header; can move to sidebar top |
| — | **Sign Out** | Currently at sidebar bottom; keep position |

**Implementation:** Sidebar is a `liquid-glass` panel. List items have hover states with 150ms `transition-colors`. Selected item gets `bg-white/[0.06]`. Scrollbar is 4px thin.

### 6.3 Main Content Area

| Moon Note View | Deep Research State | Component | Notes |
|----------------|---------------------|-----------|-------|
| Editor view (title + textarea) | **Idle state — Query Composer** | Hero panel + `Paper` with form | Replace note editor with research query form |
| Preview mode (rendered Markdown) | **Results — Report Viewer** | `ReportView.tsx` | Render Markdown in 672px max-width centered container |
| D3 Graph view | **Mindmap view** | `MindmapView.tsx` + `G6MindmapGraph.tsx` | Keep G6 v5; reskin container only |
| — | **Plan Review** | `PlanReview.tsx` | New view — show plan steps in liquid-glass cards |
| — | **SSE Streaming** | `ResearchProgress.tsx` | Show events in a scrollable liquid-glass panel |
| — | **Citations + Export** | `CitationsView.tsx` + `ExportPanel.tsx` | Tabbed panels within results view |
| — | **Knowledge Graph** | `KGQueryPanel.tsx` + `KnowledgeGraphView.tsx` | Full-screen or panel view |
| — | **GitNexus Code Architecture** | `GitNexusWebView.tsx` | Iframe in liquid-glass container |
| — | **Telemetry Dashboard** | Bento cards in idle state | System stats with 4 stat cards |

**Layout for Results Mode:** The current results mode uses a two-column grid (`repeat(auto-fit, minmax(400px, 1fr))`). In the Moon Note aesthetic, this becomes a **split-pane layout** with the left column (report) having a max-width of 672px and the right column (citations/export tabs) having a left border separator.

```
┌─────────────────────────────┬───────────────────────────────┐
│  Report (max-width 672px)   │  Citations / Export / KG     │
│  (scrollable)               │  (tabbed, scrollable)        │
│                             │                               │
│  Markdown rendering         │  ─── Citations ───           │
│  with liquid-glass           │  Citation list               │
│  container                   │                               │
│                             │  ─── Export ───              │
│                             │  Format buttons              │
│                             │                               │
└─────────────────────────────┴───────────────────────────────┘
```

---

## 7. Component-by-Component Migration Plan

### 7.1 Phase 1: Foundation (Day 1–2)

**Dependencies:**
```bash
# Remove Mantine
npm uninstall @mantine/core @mantine/hooks @mantine/form @mantine/modals @mantine/notifications @mantine/spotlight @mantine/tiptap @mantine/dates @mantine/carousel @mantine/charts @mantine/code-highlight
npm uninstall @tabler/icons-react

# Add Tailwind + shadcn/ui stack
npm install tailwindcss@^3.4.19 tailwindcss-animate@^1.0.7 postcss@^8.5.6 autoprefixer@^10.4.23
npm install class-variance-authority@^0.7.1 clsx@^2.1.1 tailwind-merge@^3.4.0 lucide-react@^0.562.0

# Add shadcn/ui primitives (selectively install as needed)
npm install @radix-ui/react-tabs @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-select @radix-ui/react-slider @radix-ui/react-separator @radix-ui/react-tooltip @radix-ui/react-accordion @radix-ui/react-avatar @radix-ui/react-badge @radix-ui/react-button @radix-ui/react-input @radix-ui/react-textarea @radix-ui/react-label @radix-ui/react-checkbox @radix-ui/react-scroll-area @radix-ui/react-toast @radix-ui/react-progress @radix-ui/react-switch @radix-ui/react-popover @radix-ui/react-hover-card @radix-ui/react-collapsible @radix-ui/react-resizable

# Add utilities
npm install react-router@^7.6.1
npm install cmdk@^1.1.1 sonner@^2.0.7 vaul@^1.1.2 react-resizable-panels@^4.2.2

# Upgrade React
npm install react@^19.2.0 react-dom@^19.2.0
```

**Configuration:**
1. Initialize Tailwind: `npx tailwindcss init -p` → creates `tailwind.config.js` and `postcss.config.js`
2. Configure `tailwind.config.js` with design tokens (colors, spacing, border-radius, font families)
3. Create `frontend/src/index.css` with:
   - `@tailwind` directives
   - Liquid glass `.liquid-glass` and `.liquid-glass-strong` classes
   - Custom scrollbar styles
   - Dark theme CSS variables (shadcn convention)
   - All base styles (body, headings, links, etc.)
4. Create `frontend/src/lib/utils.ts` with `cn()` helper (`clsx` + `tailwind-merge`)
5. Rewrite `frontend/src/main.tsx` — remove `MantineProvider`, keep `AuthProvider`, add React Router if desired

### 7.2 Phase 2: Background System (Day 2–3)

**Components to add (ported from design.md):**

1. `frontend/src/components/backgrounds/MoonlitRipple.tsx`
   - Full WebGL fragment shader background
   - 7-layer wave simulation with FBM noise
   - Procedural moon disc with crater detail
   - Mouse interaction for ripple waves
   - Desaturated to grayscale at 70% luminance
   - `requestAnimationFrame` at 60fps

2. `frontend/src/components/backgrounds/FlowField.tsx`
   - 3-layer silk fabric simulation
   - Domain warping for fabric folds
   - Kajiya-Kay anisotropic specular reflection
   - Mouse controls light direction
   - Film grain post-processing
   - ACES tone mapping + gamma correction
   - Desaturated grayscale output

3. `frontend/src/components/backgrounds/RainOnGlass.tsx`
   - Canvas 2D + WebGL hybrid
   - Up to 900 physics-based raindrops
   - Collision, merging, trail spawning
   - Procedural cityscape background
   - WebGL refraction through droplets
   - CSS filter: `saturate(0.7) brightness(0.55)`

4. `frontend/src/components/backgrounds/SolidBackground.tsx`
   - Simple CSS `background-color` based on selected preset
   - Four presets: `#000000`, `#1a1a2e`, `#1a1308`, `#0d1f0d`

**Background state management:**
```typescript
// frontend/src/hooks/useBackground.ts
type BackgroundMode = 'moonlit' | 'silk' | 'rain' | 'solid';
type SolidColor = '#000000' | '#1a1a2e' | '#1a1308' | '#0d1f0d';

interface BackgroundState {
  mode: BackgroundMode;
  solidColor: SolidColor;
}
```

**Lazy loading:**
```typescript
const MoonlitRipple = React.lazy(() => import('./components/backgrounds/MoonlitRipple'));
const FlowField = React.lazy(() => import('./components/backgrounds/FlowField'));
const RainOnGlass = React.lazy(() => import('./components/backgrounds/RainOnGlass'));
```

### 7.3 Phase 3: Layout Shell (Day 3–4)

**Replace `AppShell` with custom layout:**

```tsx
// frontend/src/components/Layout.tsx
export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-screen flex flex-col overflow-hidden bg-black relative">
      {/* Background layer — z-0 */}
      <div className="absolute inset-0 z-0">
        <BackgroundRenderer />
      </div>
      
      {/* Header — z-10, liquid-glass */}
      <header className="h-11 flex-shrink-0 liquid-glass z-10 relative">
        {/* Header content */}
      </header>
      
      {/* Body — z-10 */}
      <div className="flex-1 flex overflow-hidden z-10 relative">
        {/* Sidebar — 240px, liquid-glass */}
        <aside className="w-60 flex-shrink-0 liquid-glass overflow-hidden flex flex-col">
          {/* Sidebar content */}
        </aside>
        
        {/* 1px gap */}
        <div className="w-px flex-shrink-0" />
        
        {/* Main content */}
        <main className="flex-1 overflow-hidden flex flex-col">
          {children}
        </main>
      </div>
    </div>
  );
}
```

**Key CSS rules for liquid glass:**
```css
/* frontend/src/index.css */
.liquid-glass {
  background: rgba(255, 255, 255, 0.01);
  background-blend-mode: luminosity;
  backdrop-filter: blur(6px) saturate(140%);
  border: none;
  box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.1),
              0 8px 32px rgba(0, 0, 0, 0.15);
  position: relative;
}

.liquid-glass::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(180deg, rgba(255,255,255,0.25) 0%, rgba(255,255,255,0) 100%);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}

.liquid-glass::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: 
    radial-gradient(ellipse 90% 40% at 50% 0%, rgba(255,255,255,0.12) 0%, transparent 55%),
    radial-gradient(ellipse 50% 25% at 50% 0%, rgba(255,255,255,0.08) 0%, transparent 50%);
  pointer-events: none;
}

.liquid-glass-strong {
  background: rgba(255, 255, 255, 0.01);
  background-blend-mode: luminosity;
  backdrop-filter: blur(40px) saturate(150%);
  border: none;
  box-shadow: 4px 4px 4px rgba(0, 0, 0, 0.05),
              inset 0 1px 1px rgba(255, 255, 255, 0.15);
  position: relative;
}

.liquid-glass-strong::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(180deg, rgba(255,255,255,0.30) 0%, rgba(255,255,255,0) 100%);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}

.liquid-glass-strong::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: 
    radial-gradient(ellipse 90% 40% at 50% 0%, rgba(255,255,255,0.22) 0%, transparent 55%),
    radial-gradient(ellipse 50% 25% at 50% 0%, rgba(255,255,255,0.15) 0%, transparent 50%);
  pointer-events: none;
}
```

### 7.4 Phase 4: Component-by-Component Reskin (Day 4–10)

| Component | Current File | Action | Priority |
|-----------|-------------|--------|----------|
| **Header** | `App.tsx` lines 364–394 | Rewrite as liquid-glass bar with brand, view toggle, background switcher, user | High |
| **Sidebar** | `App.tsx` lines 397–462 | Rewrite as 240px liquid-glass panel with search, run list, actions | High |
| **RunList** | `components/runs/RunList.tsx` | Reskin list items with hover/selected states, scrollbar | High |
| **Query Composer** | `App.tsx` lines 546–781 | Reskin hero panel with liquid-glass cards, keep all form fields | High |
| **PlanReview** | `components/views/PlanReview.tsx` | Reskin plan cards with liquid-glass, amber accents | High |
| **ResearchProgress** | `components/views/ResearchProgress.tsx` | Reskin event stream with liquid-glass panel, progress bars | High |
| **ReportView** | `components/views/ReportView.tsx` | Render in 672px max-width centered container, `md-body` class | High |
| **CitationsView** | `components/views/CitationsView.tsx` | Reskin citation cards, links in amber | Medium |
| **ExportPanel** | `components/views/ExportPanel.tsx` | Reskin export buttons with liquid-glass-strong | Medium |
| **MindmapView** | `components/views/MindmapView.tsx` | Keep G6 v5, reskin container div with explicit width/height | Medium |
| **G6MindmapGraph** | `components/mindmap/G6MindmapGraph.tsx` | Keep G6 logic, update node/edge colors to warm amber palette | Medium |
| **NodeDetailsPanel** | `components/mindmap/NodeDetailsPanel.tsx` | Reskin panel with liquid-glass | Medium |
| **KnowledgeGraphView** | `components/knowledge-graph/KnowledgeGraphView.tsx` | Reskin container and node colors | Medium |
| **KGQueryPanel** | `components/knowledge-graph/KGQueryPanel.tsx` | Reskin query interface | Medium |
| **KGStatsPanel** | `components/knowledge-graph/KGStatsPanel.tsx` | Reskin stat cards | Medium |
| **CommunityLegend** | `components/knowledge-graph/CommunityLegend.tsx` | Reskin legend | Low |
| **GitNexusWebView** | `components/code-arch/GitNexusWebView.tsx` | Reskin iframe container with liquid-glass | Medium |
| **TerminalDemo** | `components/landing/TerminalDemo.tsx` | Keep logic, reskin container | Medium |
| **AuthModal** | `components/Auth/AuthModal.tsx` | Reskin as full-screen gate with Moonlit Ripple background + liquid-glass login panel | High |
| **WorkspaceSelector** | `components/Auth/WorkspaceSelector.tsx` | Reskin dropdown | Medium |

### 7.5 Phase 5: shadcn/ui Component Library (Ongoing)

Build shadcn/ui primitives as needed. The design.md lists 40+ components. For the Deep Research Agent, the actively used ones are:

**Required shadcn/ui primitives:**
- `button` — All action buttons
- `input` — Search, model ID, form fields
- `textarea` — Research query input
- `select` — Model presets, export formats
- `slider` — Depth slider (1–5)
- `tabs` — Citations/Export tabs, Edit/Preview
- `dialog` — New Research modal
- `dropdown-menu` — Background switcher, user menu
- `tooltip` — Icon buttons, info hints
- `badge` — Status badges, model indicator
- `scroll-area` — Custom scrollbar for panels
- `separator` — Dividers
- `card` / `paper` — Content panels (or use custom liquid-glass)
- `toast` / `sonner` — Notifications (replace Mantine `Notification`)
- `progress` — Research progress bar
- `accordion` — Collapsible sections (plan steps, citations)
- `skeleton` — Loading states
- `label` — Form labels
- `checkbox` — Multi-select in manage mode
- `popover` — Quick info panels
- `resizable` — Split-pane layout (optional)

**Custom app components (not from shadcn/ui):**
- `Sidebar` — Left panel with search, run list, actions
- `Header` — Top bar with brand, toggles, user
- `BackgroundSwitcher` — Dropdown to select 4 backgrounds
- `RunList` — Scrollable list of research runs
- `QueryComposer` — Research query form with all controls
- `ResearchProgress` — SSE event stream display
- `ReportView` — Markdown report renderer
- `PlanReview` — Plan step cards with approve/regenerate
- `CitationsView` — Citation list with links
- `ExportPanel` — Export format buttons
- `MindmapView` — G6 graph container
- `KnowledgeGraphView` — Graphify graph container
- `GitNexusWebView` — Iframe wrapper
- `TerminalDemo` — Simulated terminal
- `AuthModal` — Login gate with background
- `WorkspaceSelector` — Workspace dropdown
- `MoonlitRipple` / `FlowField` / `RainOnGlass` / `SolidBackground` — Backgrounds

### 7.6 Phase 6: Polish & Interactions (Day 10–12)

1. **Hover states:** All interactive elements use `transition-colors duration-150 ease` — text shifts from `#555` to `#999` on hover
2. **Glass panel hover:** Subtle opacity shifts on interactive elements inside liquid-glass panels
3. **Button hover:** Primary buttons shift from `bg-accent/20` to `bg-accent/30`
4. **Tab transitions:** Instant (no animation — content switches immediately, as per design.md)
5. **Background switching:** Real-time toggle with no page reload
6. **Loading states:** Replace Mantine `Loader` with custom skeleton or minimal text
7. **Keyboard shortcuts:** `Ctrl/Cmd+S` — if applicable, trigger manual action or save
8. **Responsive:** Mobile breakpoint handling — sidebar collapses, stack layout

---

## 8. API Client Compatibility

The existing `frontend/src/api/client.ts` uses raw `fetch` with Bearer token injection. This is **fully compatible** with the new frontend. No changes needed.

```typescript
// frontend/src/api/client.ts — EXISTING, NO CHANGES REQUIRED
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
let authToken: string | null = null;

const fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
  const headers = new Headers(init?.headers);
  if (authToken) { headers.set('Authorization', `Bearer ${authToken}`); }
  return originalFetch(input, { ...init, headers });
};
```

All 25+ API methods remain unchanged:
- `api.setToken()` — token injection
- `api.listWorkspaces()`, `api.createWorkspace()`
- `api.listRuns()`, `api.getRunDetails()`, `api.getReport()`
- `api.getMindmap()`, `api.expandNode()`
- `api.startResearch()`, `api.streamResearch()`, `api.generatePlan()`, `api.streamApprovedPlan()`
- `api.exportRun()`, `api.listExports()`
- `api.getKnowledgeGraph()`, `api.buildKnowledgeGraph()`, `api.queryKnowledgeGraph()`
- `api.getMcpStatus()`, `api.startMcpServer()`, `api.stopMcpServer()`
- `api.getGraphHtmlUrl()`
- `api.startGitnexusServe()`, `api.stopGitnexusServe()`, `api.getGitnexusServeStatus()`
- `api.openFile()`
- `api.resynthesizeRun()`
- `api.getTelemetry()`
- `api.validateModel()`

The SSE streaming implementation (`streamResearch`, `streamApprovedPlan`, `resynthesizeRun`) uses `fetch` + `ReadableStream` with `TextDecoder` — this is the correct pattern and works perfectly with the new frontend.

---

## 9. Auth Compatibility

The existing auth uses **Supabase JWT** with an `AuthContext` provider:

```typescript
// frontend/src/lib/authContext.tsx — EXISTING, NO CHANGES REQUIRED
export interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}
```

The `api/client.ts` injects the Supabase JWT as a Bearer token:
```typescript
api.setToken(session.access_token);
```

This is **fully compatible** with the FastAPI backend's `verify_supabase_jwt` dependency. No auth migration needed.

The Moon Note design's **Kimi OAuth** is specific to its deployment context. For the Deep Research Agent, **keep Supabase auth** — it is already working and supports workspace-based access control.

**Visual change only:** The login screen should be redesigned to match the Moon Note aesthetic (full-screen gate with Moonlit Ripple background + centered liquid-glass-strong login panel), but the auth **logic** remains unchanged.

---

## 10. Data Visualization Compatibility

### 10.1 G6 Mindmap (Retained)

The current mindmap uses **AntV G6 v5** with the unified `Graph` class (not the deprecated `TreeGraph`). The design.md's AGENTS.md (line 6) explicitly states:

> "Use the unified `Graph` class (not the deprecated `TreeGraph`). Mindmap layout configuration uses `type: 'mindmap'`, `direction: 'H'`. Node updates use `graph.changeData()`."

**Action:** Keep all G6 code exactly as-is. Only change:
- Container styling (add `liquid-glass` or border treatment)
- Node color palette (from current colors to warm amber palette: `#c8956c`, `#d4a574`, `#b8845e`, `#a07050`, `#c0a080`, `#d09060`, `#b09070`, `#c8a888`)
- Background color (transparent over procedural background)

**Critical:** The G6 container `div` MUST have explicit `width` and `height`. If the container is 0×0, the graph renders invisibly. This is already handled in the current code but must be preserved.

### 10.2 Knowledge Graph (Retained)

The Graphify knowledge graph is rendered as an interactive `graph.html` file or via custom components. Keep all existing KG logic. Reskin the container panels with liquid-glass.

### 10.3 D3 Graph (Not Needed)

The design.md describes a D3 force-directed graph for the notes app. The Deep Research Agent does **not** use D3 — it uses G6 for mindmaps and Graphify for knowledge graphs. Do **not** add D3.

---

## 11. Risks & Mitigations

| Risk | Severity | Impact | Mitigation |
|------|----------|--------|------------|
| **WebGL backgrounds are GPU-intensive** | Medium | May cause performance issues on low-end devices, battery drain | Lazy-load with `React.lazy` + `Suspense`. Provide "Solid Color" fallback. Design.md already specifies this. |
| **Full Mantine → shadcn/ui rewrite is large** | High | Every component must be rebuilt. Estimate 2–3 weeks. | Phase the migration: shell first, then components one by one. Keep app functional at each phase. |
| **Liquid glass CSS is fragile** | Medium | Effect depends on exact pseudo-element gradients. Browser compatibility issues with `backdrop-filter`. | Copy CSS precisely from design.md. Test on Chrome, Firefox, Safari. Add `-webkit-backdrop-filter` fallback. |
| **G6 container sizing regression** | Low | If container loses explicit width/height, graph becomes invisible | Audit all G6 container divs. Ensure they have explicit `width` and `height` styles. |
| **Auth state during refactor** | Low | Login/logout flow could break if `AuthContext` is modified | Do not touch `authContext.tsx` or `supabase.ts` in early phases. Reskin the login UI only. |
| **Loss of Mantine convenience components** | Medium | shadcn/ui primitives are lower-level. Need more custom CSS for `Slider`, `SegmentedControl`, `Loader`, `Notification` | Build wrapper components or use Radix primitives directly. Add `sonner` for toasts, custom progress/loading components. |
| **Scrollbar styling inconsistency** | Low | Custom scrollbar CSS may not apply to all scrollable containers | Use a global `::-webkit-scrollbar` rule + `scrollbar-width` for Firefox. Test all panels. |
| **Build size increase** | Low | WebGL shaders + shadcn/ui may increase bundle size | Lazy-load backgrounds. Tree-shake shadcn/ui. Use Vite's code splitting. |
| **React 19 compatibility** | Low | React 19 has minor breaking changes from React 18 | Test all components. Most changes are automatic with `react-dom/client` already in use. |
| **Mantine CSS removal** | Low | Residual Mantine CSS classes may conflict with Tailwind | Fully uninstall `@mantine/core/styles.css` import from `main.tsx`. Search for `mantine` class names. |

---

## 12. File Structure (Target)

```
frontend/
├── index.html                          # HTML entry (unchanged)
├── vite.config.ts                      # Vite config (add tailwindcss plugin)
├── tailwind.config.js                  # NEW — Tailwind theme + shadcn colors
├── postcss.config.js                   # NEW — PostCSS with tailwindcss + autoprefixer
├── tsconfig.json                       # TypeScript config (upgrade React types)
│
├── src/
│   ├── main.tsx                        # Entry — React 19 + AuthProvider + Router
│   ├── App.tsx                         # Root routes + layout shell
│   ├── index.css                       # NEW — Global styles + liquid glass + scrollbar
│   ├── types/
│   │   └── api.ts                      # UNCHANGED — All backend types
│   │
│   ├── api/
│   │   └── client.ts                   # UNCHANGED — Fetch-based API client
│   │
│   ├── lib/
│   │   ├── utils.ts                    # NEW — cn() helper (clsx + tailwind-merge)
│   │   ├── authContext.tsx             # UNCHANGED — Supabase auth context
│   │   └── supabase.ts                 # UNCHANGED — Supabase client
│   │
│   ├── hooks/
│   │   ├── useAuth.ts                  # UNCHANGED — Auth hook (if separate from context)
│   │   ├── useBackground.ts            # NEW — Background mode state + persistence
│   │   └── use-mobile.ts               # NEW — Mobile breakpoint detection (shadcn)
│   │
│   ├── components/
│   │   ├── ui/                         # shadcn/ui primitives (button, input, textarea, select, slider, tabs, dialog, dropdown-menu, tooltip, badge, scroll-area, separator, card, toast, progress, accordion, skeleton, label, checkbox, popover, resizable, etc.)
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── textarea.tsx
│   │   │   ├── select.tsx
│   │   │   ├── slider.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   ├── tooltip.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── scroll-area.tsx
│   │   │   ├── separator.tsx
│   │   │   ├── card.tsx
│   │   │   ├── toast.tsx
│   │   │   ├── progress.tsx
│   │   │   ├── accordion.tsx
│   │   │   ├── skeleton.tsx
│   │   │   ├── label.tsx
│   │   │   ├── checkbox.tsx
│   │   │   ├── popover.tsx
│   │   │   └── resizable.tsx
│   │   │
│   │   ├── backgrounds/              # NEW — Procedural GPU backgrounds
│   │   │   ├── MoonlitRipple.tsx
│   │   │   ├── FlowField.tsx
│   │   │   ├── RainOnGlass.tsx
│   │   │   └── SolidBackground.tsx
│   │   │
│   │   ├── layout/                     # NEW — Layout shell components
│   │   │   ├── Header.tsx              # 44px liquid-glass header bar
│   │   │   ├── Sidebar.tsx             # 240px liquid-glass sidebar
│   │   │   ├── BackgroundSwitcher.tsx  # Background dropdown menu
│   │   │   └── Layout.tsx              # Root layout composing header + sidebar + main
│   │   │
│   │   ├── runs/
│   │   │   └── RunList.tsx             # Reskinned — Run list in sidebar
│   │   │
│   │   ├── views/                      # Reskinned — Main content views
│   │   │   ├── ResearchProgress.tsx
│   │   │   ├── ReportView.tsx
│   │   │   ├── PlanReview.tsx
│   │   │   ├── ExportPanel.tsx
│   │   │   ├── CitationsView.tsx
│   │   │   └── MindmapView.tsx
│   │   │
│   │   ├── mindmap/
│   │   │   ├── G6MindmapGraph.tsx      # Keep logic, update colors
│   │   │   └── NodeDetailsPanel.tsx
│   │   │
│   │   ├── knowledge-graph/
│   │   │   ├── KnowledgeGraphView.tsx
│   │   │   ├── KGQueryPanel.tsx
│   │   │   ├── KGStatsPanel.tsx
│   │   │   └── CommunityLegend.tsx
│   │   │
│   │   ├── code-arch/
│   │   │   └── GitNexusWebView.tsx     # Reskinned container
│   │   │
│   │   ├── landing/
│   │   │   └── TerminalDemo.tsx        # Reskinned container
│   │   │
│   │   └── Auth/
│   │       ├── AuthModal.tsx           # Reskinned — Full-screen login gate
│   │       └── WorkspaceSelector.tsx   # Reskinned dropdown
│   │
│   └── styles/
│       └── theme.ts                    # REMOVED — Replaced by tailwind.config.js + index.css
```

---

## 13. Estimated Effort

| Phase | Duration | Focus |
|-------|----------|-------|
| Phase 1: Foundation | 2 days | Dependencies, Tailwind config, global CSS, `cn()` utility, main.tsx rewrite |
| Phase 2: Backgrounds | 1–2 days | Port 4 WebGL/Canvas background components, lazy loading, state hook |
| Phase 3: Layout Shell | 1–2 days | Header, Sidebar, BackgroundSwitcher, Layout composition |
| Phase 4: Component Reskin | 5–7 days | All views, run list, auth modal, form controls |
| Phase 5: shadcn/ui Primitives | Ongoing | Install/build primitives as needed during Phase 4 |
| Phase 6: Polish | 2–3 days | Hover states, animations, responsive, performance, scrollbar, keyboard |
| **Total** | **11–16 days** | Single developer, full-time |

With AI-assisted development (parallel component generation, CSS automation), this could compress to **5–8 days**.

---

## 14. Final Recommendation

### 14.1 Proceed with Option A: REST-First Reskin

**Do this:**
1. ✅ Keep the FastAPI backend exactly as-is — all 25+ endpoints, SSE streaming, auth middleware, file storage
2. ✅ Keep the `fetch`-based API client (`api/client.ts`) — no transport layer changes
3. ✅ Keep Supabase JWT auth (`authContext.tsx`, `supabase.ts`) — no auth migration
4. ✅ Keep all research features — query composer, plan review, SSE streaming, report viewer, citations, export, mindmap, knowledge graph, GitNexus, telemetry, resynthesis
5. ✅ Adopt the Moon Note visual system fully — pure black `#000000` canvas, warm amber `#c8956c` accents, liquid-glass panels, 4 procedural GPU backgrounds, custom scrollbars, thin typography
6. ✅ Swap Mantine → shadcn/ui + Tailwind CSS v3
7. ✅ Add `react-router` v7 for routing (optional, can be deferred)
8. ✅ Upgrade to React 19 + TypeScript 5.9
9. ✅ Port all 4 procedural backgrounds as lazy-loaded components
10. ✅ Rewrite the layout shell (header 44px, sidebar 240px, main content area)
11. ✅ Reskin every component with liquid-glass treatment and amber accent colors

**Do NOT do this:**
1. ❌ Do NOT switch to tRPC or Hono — the design.md's backend stack was for a notes app, not a research agent
2. ❌ Do NOT switch to MySQL/Drizzle — keep Supabase PostgreSQL
3. ❌ Do NOT switch to Kimi OAuth — keep Supabase JWT auth
4. ❌ Do NOT add note editor, wiki links, backlinks, or D3 graph — these are Moon Note domain features, not research features
5. ❌ Do NOT add the moon phase widget — domain-specific to notes app
6. ❌ Do NOT change API endpoints, data models, or storage layer

### 14.2 Success Criteria

The refactor is successful when:
- [ ] All 25+ backend API endpoints remain untouched and functional
- [ ] All existing features work identically (query, plan, stream, report, citations, export, mindmap, KG, GitNexus, telemetry, resynthesis)
- [ ] Supabase auth and workspace system works unchanged
- [ ] The visual appearance matches the Moon Note design system: pure black background, warm amber accents, liquid-glass panels, procedural backgrounds
- [ ] The layout uses the 3-zone architecture: 44px header, 240px sidebar, fluid main content
- [ ] All interactive elements have hover states with 150ms transitions
- [ ] Custom 4px scrollbar appears on all scrollable panels
- [ ] The 4 procedural backgrounds can be switched in real-time via a dropdown
- [ ] The app is fully responsive (mobile sidebar collapses)
- [ ] No Mantine dependencies remain in the bundle
- [ ] Build succeeds with `npm run build` and type-checks pass

---

## 15. Appendix: Source Files Reviewed

### 15.1 Frontend Files

| File | Lines | Content |
|------|-------|---------|
| `frontend/design.md` | 607 | Full Moon Note design system specification |
| `frontend/src/App.tsx` | 946 | Main application component with state machine, layout, API calls |
| `frontend/src/api/client.ts` | 503 | Fetch-based API client with Bearer token injection, all endpoints |
| `frontend/src/types/api.ts` | 372 | TypeScript types mirroring backend Pydantic models |
| `frontend/src/main.tsx` | 18 | App entry with MantineProvider, AuthProvider, StrictMode |
| `frontend/src/styles/theme.ts` | 28 | Mantine theme object with mint color palette |
| `frontend/src/lib/authContext.tsx` | — | Supabase auth context (noted in imports) |
| `frontend/src/components/runs/RunList.tsx` | — | Sidebar run list component |
| `frontend/src/components/views/ResearchProgress.tsx` | — | SSE event stream display |
| `frontend/src/components/views/ReportView.tsx` | — | Markdown report renderer |
| `frontend/src/components/views/PlanReview.tsx` | — | Plan approval/review UI |
| `frontend/src/components/views/ExportPanel.tsx` | — | Export format selection |
| `frontend/src/components/views/CitationsView.tsx` | — | Citation list |
| `frontend/src/components/views/MindmapView.tsx` | — | Mindmap container |
| `frontend/src/components/mindmap/G6MindmapGraph.tsx` | — | AntV G6 v5 mindmap graph |
| `frontend/src/components/mindmap/NodeDetailsPanel.tsx` | — | Mindmap node details |
| `frontend/src/components/knowledge-graph/KnowledgeGraphView.tsx` | — | Knowledge graph view |
| `frontend/src/components/knowledge-graph/KGQueryPanel.tsx` | — | KG query interface |
| `frontend/src/components/knowledge-graph/KGStatsPanel.tsx` | — | KG statistics panel |
| `frontend/src/components/knowledge-graph/CommunityLegend.tsx` | — | KG community legend |
| `frontend/src/components/code-arch/GitNexusWebView.tsx` | — | GitNexus iframe wrapper |
| `frontend/src/components/landing/TerminalDemo.tsx` | — | Simulated terminal demo |
| `frontend/src/components/Auth/AuthModal.tsx` | — | Login modal/gate |
| `frontend/src/components/Auth/WorkspaceSelector.tsx` | — | Workspace dropdown |

### 15.2 Backend Files

| File | Lines | Content |
|------|-------|---------|
| `research_engine/api.py` | 1,634 | FastAPI server with all REST + SSE endpoints |
| `research_engine/auth.py` | — | Supabase JWT verification middleware |
| `research_engine/models.py` | — | Pydantic models (mirrored by frontend types) |
| `research_engine/config.py` | — | Configuration singleton |
| `research_engine/agent/orchestrator.py` | — | Deep research orchestration |
| `research_engine/agent/planner.py` | — | Research plan generation |
| `research_engine/output/storage.py` | — | File-based run storage |
| `research_engine/output/mindmap.py` | — | G6 mindmap generation |
| `research_engine/knowledge_graph/` | — | Graphify knowledge graph builder + MCP bridge |
| `research_engine/sources/web_scraper.py` | — | Scrapling-based web scraping |
| `research_engine/sources/web_search.py` | — | Search provider abstraction |
| `research_engine/llm/provider.py` | — | OpenRouter LLM gateway |

### 15.3 Configuration & Documentation

| File | Content |
|------|---------|
| `AGENTS.md` | Agent guidelines: async I/O, model IDs as runtime params, Scrapling as sole scraper, Pydantic models as source of truth, Mantine for UI, AntV G6 v5 patterns, exhaustive depth default, OpenRouter gateway, structured output fallback |
| `frontend/vite.config.ts` | Vite build configuration |
| `frontend/package.json` | Current dependencies (Mantine, Tabler, React 18, etc.) |

---

*Document generated from comprehensive codebase review. All technical claims are verifiable against the source files listed in Section 15.*
