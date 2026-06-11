---
date: 2026-06-11
topic: perplexity-ui-design
focus: perplexity-style UI/UX and system design infrastructure improvements to improve the deep research agent (latency, timeouts, formatting, and expandable thinking section)
mode: repo-grounded
---

# Ideation: Perplexity-Style UI/UX and System Design Infrastructure Improvements

This document lists the prioritized engineering improvements designed to bring the Deep Research Agent up to Perplexity-grade usability. By combining patterns from Karan Pratap Singh's system design course and real-world machine learning architectures (such as Airbnb, Yelp, Stripe, and Swiggy), these designs solve critical problems with timeouts, latency, information formatting, and reasoning observability.

---

## Grounding Context

### Codebase Context
*   **Backend:** FastAPI async python app inside `research_engine/`. Uses Scrapling (`web_scraper.py`) with a tiered fetcher chain (Stealthy -> Dynamic -> Fetcher fallback), OpenRouter (`llm/provider.py`) with `ChatOpenAI`, and a DRE multi-cycle loop in `orchestrator.py` running at depth 5 (max 30 cycles) by default.
*   **Frontend:** Vite/React app in `frontend/`. Uses Mantine v7 UI library, AntV G6 v5 for mindmap visualization, and `react-markdown` for reports.
*   **Notable Pain Points:** Potential client timeouts or loading delays due to slow scraping steps, lack of fine-grained streaming of internal thinking processes, and incoherent inline citation formatting.

### External Context (System Design Curated Lists)
*   **Latency & SSE:** EventSource (SSE) is the industry standard for real-time AI search typing effects.
*   **Caching:** Semantic cache (query embeddings) avoids redundant searches and LLM calls in RAG/search pipelines.
*   **Resilience:** Circuit Breakers protect system resources when external calls (search APIs or website fetches) fail or latency spikes.
*   **Parallelization:** Parallel execution of retrieval and scraping queries reduces overall time-to-first-token.
*   **Search & Ranking Funnels:** Real-world architectures (Airbnb, Yelp) divide retrieval into multi-stage pipelines (candidate generation followed by lightweight embedding ranking followed by heavy LLM/LTR ranking) to manage performance.

## Topic Axes
1. Streaming & Observability (UX/UI)
2. Latency & Timeout Infrastructure
3. Caching Strategy (Retrieval & Output)
4. Information Synthesis & Formatting

---

## Ranked Ideas

### 1. Collapsible Reasoning (Thinking) Block Rendering
*   **Description:** Stream the agent's internal reasoning (from the LLM or planner/reflect steps) enclosed in `<thinking>` and `</thinking>` tags on the backend. In the frontend, parse these tags out of the streamed response or report, and render them in a collapsible Mantine Accordion/Collapse component with custom styling (e.g. typewriter loader, steps completed status).
*   **Axis:** Streaming & Observability (UX/UI)
*   **Basis:** `direct:` User request: *"plus an expandable thinking section tags before and after thinking to enable users to view agent process."*
*   **Rationale:** Users can inspect the agent's step-by-step reasoning (e.g., query generation, page scraping validation, reflection, candidate crossover), just like Perplexity's "Pro Search" thinking details, preventing the interface from feeling frozen during long-running tasks.
*   **Downsides:** Requires custom text parsers on the frontend to handle partial/unterminated HTML tags during streaming.
*   **Confidence:** 95%
*   **Complexity:** Low-Medium
*   **Status:** Unexplored

### 2. Circuit Breaker & Adaptive Scraping Timeout
*   **Description:** Implement aggressive page-level timeouts and a Circuit Breaker pattern (using a state machine: Closed, Open, Half-Open) on the scraping layer (`WebScraper` / `StealthyFetcher`). If scraping a specific domain or page takes too long or fails repeatedly, open the circuit and immediately fallback to a static HTTP fetcher or skip the page.
*   **Axis:** Latency & Timeout Infrastructure
*   **Basis:** `external:` Karan Pratap Singh's system design course Chapter IV "#circuit-breaker" outlines how to handle failing/slow services to avoid resource exhaustion and timeouts.
*   **Rationale:** Currently, a single slow website can block the entire multi-step DRE loop, causing HTTP timeouts on the client side. A circuit breaker ensures the agent fails-fast and maintains high throughput.
*   **Downsides:** May occasionally miss content if the scraper falls back too aggressively.
*   **Confidence:** 90%
*   **Complexity:** Medium
*   **Status:** Unexplored

### 3. Local Semantic Cache for Queries and Answers
*   **Description:** Implement semantic caching of LLM queries and web search results using local SQLite or Redis to store query embeddings. If a new sub-query's embedding similarity is above a threshold (e.g., 0.90), return the cached answer/scraped pages directly, bypassing the web search and scraping phases.
*   **Axis:** Caching Strategy (Retrieval & Output)
*   **Basis:** `external:` Karan Pratap Singh's system design course Chapter I "#caching" and modern RAG caching architectures (like Milvus/GPTCache) suggest using semantic embeddings to avoid repetitive retrieval and inference latency.
*   **Rationale:** Sub-queries across deep cycles often overlap or repeat similar topics. Semantic caching avoids redundant searches and LLM calls, lowering latency and OpenRouter costs.
*   **Downsides:** Stale web search data might be served for rapidly changing topics unless cache invalidation/TTL rules are strictly enforced.
*   **Confidence:** 85%
*   **Complexity:** Medium-High
*   **Status:** Unexplored

### 4. Interactive Hovercards & Structured Citation Tooltips
*   **Description:** Create a strict validation layer for markdown synthesis that parses and formats citations (e.g., `[1]`, `[2]`) as interactive Mantine Tooltips or HoverCards. Hovering over a citation displays a card with page metadata (title, snippet, URL, and a quick-action link to view the scraped context).
*   **Axis:** Information Synthesis & Formatting
*   **Basis:** `direct:` User complained about *"incoherent information/formatting."*
*   **Rationale:** Traditional citation lists or plain links are hard to verify and read. Hovercards present grounded evidence inline without forcing the user to leave the document.
*   **Downsides:** Requires clean citation extraction from LLM outputs and frontend parsing logic.
*   **Confidence:** 95%
*   **Complexity:** Low
*   **Status:** Unexplored

### 5. Multi-Stage Funnel Reranker (Sparse-Dense Hybrid)
*   **Description:** Implement a two-stage filter for search results. Stage 1 (Fast Sparse-Dense Filter): score web results based on keyword overlap (BM25) and light semantic similarity to filter the top 15 results. Stage 2 (LLM Reranker): use a small, fast model to rank and select the top 5 pages for extraction.
*   **Axis:** Caching Strategy (Retrieval & Output)
*   **Basis:** `external:` Airbnb's "Learning To Rank Diversely" and Yelp's "Content As Embeddings" case studies (from the curated ML system design repo) demonstrate multi-stage candidate retrieval and ranking pipelines to optimize latency and diversity.
*   **Rationale:** Scrapes only highly-relevant, diverse pages. This prevents extracting redundant or spammy search results, reducing overall processing cost and avoiding context-bloating.
*   **Downsides:** Higher initial latency for embedding generation, but offset by scraping fewer pages.
*   **Confidence:** 90%
*   **Complexity:** Medium
*   **Status:** Unexplored

### 6. Context-Aware Ad-hoc Scraping (Boilerplate Removal)
*   **Description:** Incorporate a DOM-based content extraction model or custom selector heuristic to filter out navigation menus, footers, headers, ads, and sidebars before passing scraped page texts to the LLM. Only target the core article body containing the search intent.
*   **Axis:** Information Synthesis & Formatting
*   **Basis:** `external:` Stripe Radar's feature extraction and Swiggy's menu item understanding case studies (from the curated ML system design repo) use structured extraction to remove page noise and isolate key data features.
*   **Rationale:** Eliminates token bloat (reducing scraped context by up to 70%), which accelerates LLM reasoning speed and avoids incoherent syntheses caused by scraping navigation menus.
*   **Downsides:** Might fail on poorly structured sites if the DOM heuristic is too strict.
*   **Confidence:** 90%
*   **Complexity:** Medium
*   **Status:** Unexplored

### 7. Task Cancellation & Client Disconnect Propagation
*   **Description:** Implement full signal propagation from the FastAPI SSE connection down to the LLM provider and web scraper tasks. When the user disconnects or hits "Stop" in the UI, cancel the active asyncio tasks instead of letting them finish in the background.
*   **Axis:** Latency & Timeout Infrastructure
*   **Basis:** `reasoned:` When a client disconnects, the backend currently shields the research task, which wastes OpenRouter quota, hits rate limits, and locks the local browser profile. Aborting tasks frees resource immediately.
*   **Rationale:** Frees up resources, prevents rate-limit lockouts, and keeps the server responsive for subsequent runs.
*   **Downsides:** Aborting a run means partial state is lost unless we cache intermediate results.
*   **Confidence:** 90%
*   **Complexity:** Medium
*   **Status:** Unexplored

---

## Rejection Summary

| # | Idea | Reason Rejected |
|---|---|---|
| 5 | Event-Driven Concurrent Retrieval & Scraper Worker Pool | Rejected due to high implementation complexity and elevated search API rate-limit risks when running multiple deep cycles in parallel. |
| 8 | Speculative Web Searching and Pre-fetching | Rejected because speculative query prediction in a stateful feedback loop has high prediction error rates and causes search quota/token wastage. |
| 10 | Hierarchical Citations Aggregator (Thematic Deduplication) | Merged into Idea 4 (Citations are aggregated and formatted inside the interactive hovercards and structured citation tooltips). |
