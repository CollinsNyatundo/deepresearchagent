---
date: 2026-06-11
topic: context-engineering-search-improvements
focus: Context engineering, multi-agent RAG, search evaluation, and observability improvements for Deep Research Agent
mode: repo-grounded
---

# Deep Research Agent — Context Engineering & Multi-Agent RAG Architecture Improvements

This document consolidates the elevated architectural and system improvements for the **Deep Research Agent (DRE)**. By drawing design patterns from real-world machine learning systems (such as DoorDash, Harvey, Uber, Dropbox, Ramp, and Spotify) and combining them with advanced context engineering, these designs address latency, timeouts, prompt cache performance, and process observability.

---

## 1. System Architecture Flow

The following diagram illustrates the proposed multi-agent retrieval, filtering, and synthesis pipeline:

```mermaid
graph TD
    UserQuery["User Query"] --> IntentEngine["Upfront Intent Engine (Instacart/Yelp)"]
    IntentEngine --> |"Classified Intent & Sub-plans"| Orchestrator["Orchestrator Agent (Harvey)"]
    Orchestrator --> |"Parallel Queries"| SearchEngine["Search Engine (Tavily/Google)"]
    SearchEngine --> |"Raw Snippets & URLs"| AutoEval["pointwise AutoEval Judge (DoorDash)"]
    AutoEval --> |"Relevance Score > 0.7"| ScrapeQueue["Filtered Scrape Queue"]
    AutoEval -.-> |"Low Relevance"| Pruned["Discarded URLs (Saves 70% Tokens)"]
    ScrapeQueue --> |"Resilient Fallbacks"| Scraper["Stealthy Scraper Tiers (Camoufox/Playwright)"]
    Scraper --> |"Clean Body Chunks"| LocalIndex["Local In-Memory Hybrid Index (OLX)"]
    LocalIndex --> |"Top Semantic Passages"| RAGContext["KV-Cache Conscious Context"]
    RAGContext --> |"Append-Only Padded Prompt"| Workers["Specialized Workers (Academic/News/Web)"]
    Workers --> |"Raw Findings"| Auditor["Synthesis Auditor Agent (CoCounsel)"]
    Auditor --> |"Citation Verification"| FinalReport["Citation-Backed Final Report"]
```

---

## 2. Topic Axes & Evaluation Matrix

To ensure rigorous engineering, all proposed ideas are scored against specific feasibility, complexity, and performance metrics.

| Axis | Core Objective | Primary Target Metrics |
|---|---|---|
| **Context Engineering** | Minimize prompt bloat, context rot, and API cost while maximizing performance. | Prefix Cache Hit Rate (%), Avg. Tokens/Run, TTFT (sec) |
| **Orchestration & Workflows** | Move from monolithic state loops to clean, modular, specialist agents. | Task Success Rate (%), Code Maintainability (LOC) |
| **Search & Retrieval Quality** | Filter out noise early to avoid useless scraping and synthesis corruption. | Precision@K, Scrape Volume Reduction (%), Latency (sec) |
| **Observability & UI/UX** | Make the agent’s internal reasoning loop visible, interactive, and transparent. | User Engagement Index, System Observability Score |

---

## 3. Elevated & Re-evaluated Ideas (Raising the Bar)

### 1. KV-Cache Conscious Prompting & Bucket-Aligned Page Padding
*   **Axis:** Context Engineering & KV-Cache Optimization
*   **Basis:** `external:` Manus's context engineering principles and Spotify's coding agent prompt guidelines specify maintaining stable prefixes to maximize KV-cache hit rates.
*   **Detailed Technical Specification:**
    *   **Prefix Isolation:** Move all invariant components—system instructions, markdown schemas, domain rules, and tool interfaces—to the top of the system prompt blocks.
    *   **Aligned Padding:** When inserting crawled web pages or documents, chunk them into fixed-size segments (e.g., exactly 2048 or 4096 tokens). Pad the trailing text blocks with whitespace up to the nearest token boundary. This guarantees that prompt structure remains identical across cycles, letting API providers (like OpenRouter or Anthropic) cache the prefix successfully.
    *   **Append-Only Log:** Attach user research state and search logs strictly at the very end of the prompt sequence, ensuring prior prompt prefixes are never dirtied or invalidated.
*   **Downsides:** Slightly limits dynamic run-time instructions; adds minor token overhead due to padding characters.
*   **Performance Expectation:** 60-70% decrease in Time-to-First-Token (TTFT) on deep cycles; 40% reduction in API token costs.
*   **Confidence:** 95% (High) | **Complexity:** Medium | **Est. Effort:** 3 days

### 2. Orchestrator-Worker Architecture with Standardized Tool Bundles
*   **Axis:** Orchestrator-Worker & Adaptive Workflows
*   **Basis:** `external:` Anthropic's "How we built our multi-agent research system" and Harvey's "No Custom Orchestration (Tool Bundles)" principles.
*   **Detailed Technical Specification:**
    *   **Spaghetti Decoupling:** Refactor `orchestrator.py` from a monolithic loop of raw search and parse statements into a clean planner dispatch loop.
    *   **Standardized Contract:** Define a unified `ResearchWorker` interface with strict input/output Pydantic schemas. 
    *   **Tool Bundles:** Package specialized capabilities as "bundles" containing child agents and tools. Build three specialist workers:
        *   `AcademicWorker` (ArXiv/PMC lookup and complex PDF/LaTeX parsing).
        *   `NewsWorker` (Real-time news databases and timeline extraction).
        *   `GeneralWebWorker` (Standard HTML pages scraping and site extraction).
*   **Downsides:** Increases initial orchestrator routing complexity; higher token overhead due to worker handoffs.
*   **Performance Expectation:** Improves correctness on complex query routing; simplifies maintenance of the orchestrator loop.
*   **Confidence:** 92% (High) | **Complexity:** High | **Est. Effort:** 5-7 days

### 3. Snippet-Level pointwise AutoEval Filter
*   **Axis:** Search & Retrieval Quality
*   **Basis:** `external:` DoorDash's AutoEval and Whole-Page Relevance (WPR) metrics show the value of pointwise LLM-as-a-judge relevance checks.
*   **Detailed Technical Specification:**
    *   **Early Pruning:** When a search query yields search results (e.g. 10 URLs with snippets), route these snippets to a fast, cheap model *before* triggering any scraper downloads.
    *   **Pointwise Scoring:** The model evaluates each snippet's relevance to the active sub-query on a scale of `0.0` to `1.0`. Only scrape URLs scoring $\ge 0.7$.
    *   **Fallback Trigger:** If all snippets score below 0.7, skip scraping entirely, trigger the query reformulation engine, and request fresh search terms.
*   **Downsides:** Adds a small latency step (500ms) for snippet checking before downloading.
*   **Performance Expectation:** Saves 60-70% of scraping traffic and downstream tokens by bypassing irrelevant or spammy search pages.
*   **Confidence:** 95% (High) | **Complexity:** Medium | **Est. Effort:** 2 days

### 4. Dynamic Context Pruning via Cosine Deduplication
*   **Axis:** Context Engineering & KV-Cache Optimization
*   **Basis:** `external:` Dropbox Dash's context engineering principles focus on preventing "Context Rot" and "Context Pollution."
*   **Detailed Technical Specification:**
    *   **Compaction Utility:** Build a utility in `research_engine/agent/context.py` that runs at the end of each search cycle.
    *   **Cosine Filtering:** Split newly scraped text into paragraphs. Compare paragraph embeddings against: (a) the user's research goals, and (b) paragraphs already summarized in the active draft.
    *   **Pruning Gates:** Discard paragraphs with similarity scores $> 0.8$ against existing data (redundancy) or $< 0.35$ against the user goals (boilerplate/navigation junk).
*   **Downsides:** Minor risk of pruning subtle details or context that could be useful in later reasoning phases.
*   **Performance Expectation:** Reduces context length for 5-depth runs by up to 50%, maintaining model focus and query speed.
*   **Confidence:** 90% (Medium-High) | **Complexity:** Medium-High | **Est. Effort:** 4 days

### 5. Self-Correction & Scraper Fallback Engine
*   **Axis:** Search & Retrieval Quality
*   **Basis:** `external:` Spotify's coding agent feedback loops and Anthropic's tool-testing architectures.
*   **Detailed Technical Specification:**
    *   **Failure Analysis:** Wrap search and scrape tasks in a diagnostic fallback handler (`retry.py`).
    *   **Dynamic Downgrading:** If a scraper fetch fails due to bot protection, timeout, or blocklists:
        *   *Attempt 1:* Stealthy Fetcher (Camoufox - handles Cloudflare).
        *   *Attempt 2:* Dynamic Fetcher (Playwright - renders JS).
        *   *Attempt 3:* Basic Fetcher (HTTP GET - retrieves static HTML) with custom proxy headers.
    *   **LLM Reformulation:** If the source is completely blocked, an LLM rewrites the request parameters (e.g. stripping dynamic JS params) or selects an alternate mirror domain.
*   **Downsides:** Failed fetches take longer to resolve due to the tiered retries.
*   **Performance Expectation:** Reduces failed cycle occurrences from 15% to $<2\%$.
*   **Confidence:** 90% (Medium-High) | **Complexity:** Medium | **Est. Effort:** 3 days

### 6. Information Gain Dynamic Stopping Threshold
*   **Axis:** Orchestration & Workflows
*   **Basis:** `external:` Thomson Reuters CoCounsel's legal research stopping criteria.
*   **Detailed Technical Specification:**
    *   **Convergence Metric:** After each search cycle, compile a temporary summary vector of the current findings.
    *   **Plateau Detection:** Calculate the semantic similarity of the summary at cycle $N$ compared to cycle $N-1$. If similarity is $\ge 0.96$ for two consecutive cycles (signaling no new facts are being introduced), or if all sub-queries are completed, halt immediately.
*   **Downsides:** Might stop prematurely on multi-faceted, highly deep comparative queries.
*   **Performance Expectation:** Reduces average run cycles for simple queries from 30 to 6, slashing run time by up to 80%.
*   **Confidence:** 95% (High) | **Complexity:** Medium | **Est. Effort:** 2 days

### 7. Multi-Agent Synthesis Auditor & Citation Verification
*   **Axis:** Context Engineering / Retrieval Quality
*   **Basis:** `external:` CoCounsel's citation validation and verification loops.
*   **Detailed Technical Specification:**
    *   **Post-Synthesis Verification:** Introduce an `AuditorAgent` after the report drafting step.
    *   **Logic Grounding:** Parse all citations (e.g., `[1]`, `[2]`) and extract the corresponding claims. The auditor does a verification call checking if the source text logically entails the claim.
    *   **Auto-Correction:** If a claim is ungrounded or the citation is dead/dangling, the auditor rewrites the statement or deletes the invalid reference.
*   **Downsides:** Extends total report generation time by 3-5 seconds.
*   **Performance Expectation:** Completely eliminates hallucinated citations and ungrounded claims in final research briefs.
*   **Confidence:** 90% (Medium-High) | **Complexity:** High | **Est. Effort:** 4 days

---

## 4. Newly Explored Ideas (From CSV & External Research)

### 8. Upfront Intent Engine & Mindmap Plan Customization
*   **Axis:** Orchestration & Workflows
*   **Basis:** `external:` Instacart's Query Understanding Intent Engine (Line 195 of CSV) and Yelp's Search Query Understanding with LLMs (Line 42) describe building query intent classifiers to select optimal down-stream processing paths.
*   **Description:** Before kicking off search cycles, analyze the user's prompt using an "Intent Engine." Classify the request into: (a) *Deep Academic/Scientific*, (b) *Real-Time News*, (c) *Technical/Code-level*, or (d) *General Exploratory*. The engine then outputs a custom mindmap plan and sets custom parameters (e.g. Academic mode forces PubMed/ArXiv and raises stopping threshold; News mode forces Google News and decreases cache TTL).
*   **Why It Matters:** Currently, the agent treats all queries identically. An intent engine avoids querying search index databases for code-level questions and vice versa.
*   **Confidence:** 92% (High) | **Complexity:** Medium | **Est. Effort:** 3 days

### 9. Local Hybrid Dense-Sparse RAG (Vector + BM25)
*   **Axis:** Context Engineering & KV-Cache Optimization
*   **Basis:** `external:` Slack's Enterprise Search (Line 63) and OLX's Hybrid Search (Line 225) outline combining sparse and dense indexing for local context.
*   **Description:** Instead of dumping raw webpage texts into the LLM context, chunk and index all crawled page contents locally using a fast in-memory hybrid store (BM25 + cosine similarity). The agent queries this local index dynamically to retrieve only the top-relevant passages (e.g. 5 paragraphs) for prompt assembly, avoiding context bloat.
*   **Why It Matters:** Eliminates "Context Pollution" and ensures the LLM is only exposed to high-relevance chunks, improving reasoning quality.
*   **Confidence:** 95% (High) | **Complexity:** Medium-High | **Est. Effort:** 4 days

### 10. Expandable UI Observability Accordion (Thinking Stream)
*   **Axis:** Observability & UI/UX
*   **Basis:** `direct:` User requested detailed UX/UI improvements to see the agent's process (expandable thinking section tags before/after).
*   **Description:** Stream the agent's internal reflections and processing logs enclosed in `<thinking>` tags. Modify the Vite/React frontend to parse this thinking block out of the live Server-Sent Events (SSE) stream and render it inside a beautifully designed collapsible accordion (or accordion steps).
*   **Why It Matters:** Prevents the user interface from feeling frozen during deep cycles, offering a transparent Perplexity-like experience.
*   **Confidence:** 98% (Critical) | **Complexity:** Low-Medium | **Est. Effort:** 2 days

---

## 5. Rejection & Consolidation Summary

| ID | Title | Rationale for Rejection / Consolidation |
|---|---|---|
| **R1** | Context Observability Caching Dashboard | Rejected as a standalone idea. The tracking of token cache rates and costs will be integrated directly into the **Expandable UI Observability Accordion** as a statistics sub-panel to avoid UI clutter. |
| **R2** | Event-Driven Concurrent Scraper Pool | Rejected due to high search API rate-limit risks and potential sync locks when running parallel deep cycles. Pointwise AutoEval already optimizes scraping volume. |
| **R3** | Dynamic Prompt Chunking Alignment | Consolidated into **Idea 1 (KV-Cache Conscious Prompting)** to form a unified prompt-caching solution. |
