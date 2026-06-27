# Enhanced Prompt for Research Page Redesign

A clean, premium, and focused dashboard for deep research execution and interactive analysis.

**DESIGN SYSTEM (REQUIRED):**
- Platform: Web, Desktop-first
- Theme: Dark, cinematic, minimal, professional
- Background: Ink Black (#000000)
- Primary Accent: Amber (#c8956c) for primary buttons, active tabs, and interactive indicators
- Secondary Text: Off-white (#e0e0e0) for primary content, Dim Gray (#999999) for secondary text
- Border / Muted: Dark Gray (rgba(255,255,255,0.06)) for panels and dividers
- Surface: Translucent Liquid Glass with `backdrop-filter: blur(6px) saturate(140%)` and subtle specular highlight border.

**Page Structure (Idle State):**
1. **Centered Search & Input Composer:** A large, elegant text area for the "Research Objective" query.
2. **Minimal Preset Tags:** Small, styled amber tags underneath the text area for quick presets.
3. **Collapsible Advanced Settings:** An expandable "Advanced Settings" accordion containing:
   - LLM Provider selector (segmented control: OpenRouter vs Groq)
   - Target Corpus selector (segmented control: Web-scale vs Local Repo)
   - Model ID text input
   - Search Depth slider (Quick, Standard, Exhaustive)
4. **Action Buttons:** Sleek "Generate Plan" and "Quick Start" buttons utilizing liquid-glass styling.
5. **Discreet System Status:** Sleek system status footer showing Telemetry (scraped cache counts, success rates, circuit breakers) without taking up giant bento grids. No mock hacking terminals.

**Page Structure (Results State):**
1. **Collapsible Left Secondary Navigation Sidebar:**
   - Width: 200px when expanded, collapses to 48px (icon-only) or hides completely to maximize chart area.
   - Allows choosing between:
     - 📄 Report (renders full Markdown report)
     - 🧠 Mindmap (renders interactive G6 mindmap graph with node drill-down panel)
     - 🕸️ Knowledge Graph (renders interactive force-directed concept graph with search/query/legend panels)
     - 📚 Citations (renders list of sources, domain exclusions)
     - 📤 Export (renders download options)
2. **Dynamic Content Canvas:** Takes up the remaining space. Renders the selected view (Report, Mindmap, Knowledge Graph, Citations, or Export Panel) in full width and height.
