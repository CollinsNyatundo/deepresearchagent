"""Prompt templates for the DRE research pipeline.

Each template uses Python str.format() placeholders. The orchestrator / agent
modules fill them in at runtime.
"""

# ─── Planning ────────────────────────────────────────────────────────

RESEARCH_PLANNING_TEMPLATE = """\
You are an expert research planner. Given a research topic, create a detailed,
step-by-step research plan that covers all important aspects of the topic.

Research Topic: {topic}

Create a comprehensive research plan with 5-10 specific steps. Each step should
be a clear, actionable research task. Return your response as a JSON object:

{{
  "steps": [
    "Step 1 description",
    "Step 2 description",
    ...
  ]
}}
"""

SEARCH_QUERY_GENERATION_TEMPLATE = """\
You are a skilled search query generator. Given a research topic, a research plan,
and what has already been researched, generate the next optimal search query.

Research Topic: {topic}

Current Research Plan:
{plan}

Research History (what we already know):
{history}

Generate the next search query that will help advance the research. Choose a query
that covers an area not yet explored. Return JSON:

{{
  "query": "your search query here",
  "rationale": "brief explanation of why this query"
}}
"""

# ─── Answer Synthesis (enhanced for full-page content) ───────────────

SEARCH_ANSWER_GENERATION_TEMPLATE = """\
You are an expert research analyst. You have been given a research topic, a specific
search query, and the FULL TEXT CONTENT from multiple web pages (not just snippets).

Research Topic: {topic}

Search Query: {query}

Full Page Content from Sources:
{page_contents}

Using the full content above, synthesize a comprehensive, well-cited answer to
the search query as it relates to the research topic. Include specific facts,
data points, and quotes where relevant. For each claim, note which source URL
it came from.

Return your answer as JSON:

{{
  "answer": "Your comprehensive synthesized answer with inline citations like [1], [2]...",
  "citations": [
    {{
      "id": "c1",
      "url": "source url",
      "title": "page title",
      "domain": "domain.com",
      "snippet": "relevant excerpt from the source"
    }}
  ]
}}
"""

# ─── Reflection & Progress ──────────────────────────────────────────

RESEARCH_PLAN_REFLECTION_TEMPLATE = """\
You are a research plan evaluator. Given the topic, current plan, and what has been
researched so far, determine if the plan needs to be updated.

Research Topic: {topic}

Current Plan:
{plan}

Research Completed So Far:
{history}

Should the plan be updated? Consider:
- Are there important subtopics we missed?
- Should we pivot based on what we've learned?
- Are any remaining steps no longer relevant?

Return JSON:
{{
  "should_update": true/false,
  "updates": "description of what should change (empty if no update needed)"
}}
"""

RESEARCH_PLAN_UPDATE_TEMPLATE = """\
You are a research plan optimizer. Update the research plan based on reflection.

Research Topic: {topic}

Current Plan:
{plan}

Requested Updates:
{reflection}

Research Done So Far:
{history}

Return an updated plan that incorporates the reflection. JSON:
{{
  "steps": ["updated step 1", "updated step 2", ...]
}}
"""

RESEARCH_PROGRESS_TEMPLATE = """\
You are a research progress evaluator. Estimate how complete the research is.

Research Topic: {topic}

Research Plan:
{plan}

Research Completed:
{history}

Estimate the percentage of research that has been completed (0-100).
Consider the depth and breadth of coverage. Return JSON:
{{
  "progress": 75
}}
"""

# ─── Candidate Crossover ────────────────────────────────────────────

CANDIDATES_CROSSOVER_TEMPLATE = """\
You are an expert answer synthesizer. You have {num_candidates} different answer
candidates for the same research question. Your job is to merge them into a single,
superior answer that takes the best parts from each.

Research Topic: {topic}
Search Query: {query}

Candidate Answers:
{candidates}

Create a merged answer that:
1. Keeps the most accurate and detailed information from each candidate.
2. Resolves any contradictions by preferring the most well-sourced claim.
3. Maintains proper citations.
4. Is more comprehensive than any individual candidate.

Return JSON:
{{
  "answer": "the merged, superior answer with citations",
  "citations": [
    {{"id": "c1", "url": "...", "title": "...", "domain": "...", "snippet": "..."}}
  ]
}}
"""

# ─── Report Writing ─────────────────────────────────────────────────

REPORT_WRITER_TEMPLATE = """\
You are an expert report writer. Given a research topic and all the research notes
gathered during an exhaustive investigation, write a comprehensive, well-structured
research report.

Research Topic: {topic}

Research Notes (all findings from the investigation):
{research_log}

Write a detailed report in Markdown format with:
1. **Title** — clear, descriptive
2. **Executive Summary** — 2-3 paragraph overview of key findings
3. **Table of Contents** — linked sections
4. **Main Sections** — organized thematically (not chronologically). Each section should:
   - Have a clear heading
   - Present findings with specific facts and data
   - Include inline citations as [1], [2], etc.
5. **Key Findings** — bulleted summary of most important discoveries
6. **Conclusion** — synthesis and implications
7. **References** — numbered list of all sources cited

Use tables where data comparison is appropriate. Be thorough but readable.
Target length: 2000-4000 words depending on topic complexity.
"""

# ─── Mindmap Expansion ──────────────────────────────────────────────

MINDMAP_EXPANSION_TEMPLATE = """\
You are expanding a research mindmap node. Given a node's topic and summary,
generate 3-5 more detailed sub-points that would help someone understand this
topic better.

Parent Node Topic: {node_label}
Parent Node Summary: {node_summary}

Overall Research Context: {research_context}

Generate detailed sub-points. Each should be a specific aspect, finding, or
implication. Return JSON:

{{
  "points": [
    {{
      "label": "Short title for this sub-point",
      "summary": "1-2 sentence detailed explanation"
    }}
  ]
}}
"""

# ─── Protocol-H: Reflective Retry (Phase 6) ─────────────────────────

REFLECTIVE_RETRY_TEMPLATE = """\
A research step failed. Analyze the error and suggest a correction so we can retry.

Error type: {error_type}
Error message: {error_message}
Step type: {step_type} (search, scrape, or synthesis)
Current query: {current_query}
Research cycle: {cycle}

Common failure patterns:
- Search rate limit → rephrase query with different keywords
- Scraping blocked/timeout → broaden query to find different sources
- LLM timeout → simplify context (will be handled automatically)
- Empty search results → use more general search terms
- Connection error → wait and retry (will be handled automatically)

Analyze the error and suggest:
1. A corrected query that might avoid the issue
2. An alternative search strategy if applicable
3. Whether to skip this cycle entirely

Return JSON:
{{
  "corrected_query": "a rephrased search query, or null if original is fine",
  "alternative_strategy": "strategy description, or null",
  "reasoning": "brief explanation of the correction",
  "should_skip": false
}}
"""

# ─── Protocol-H: Confidence Scoring (Phase 6) ───────────────────────

CONFIDENCE_SCORING_TEMPLATE = """\
You just synthesized an answer for a research query. Rate your confidence.

Research topic: {topic}
Search query: {query}
Answer excerpt (first 500 chars): {answer_excerpt}
Number of source pages used: {source_count}

Rate your confidence in this answer:
- score: 0.0 (no confidence, mostly guessing) to 1.0 (fully confident, well-sourced)
- Consider: source quality, claim coverage, data specificity, potential gaps
- needs_more_research: true if critical aspects are still missing

Return JSON:
{{
  "score": 0.7,
  "reasoning": "brief explanation of confidence level",
  "needs_more_research": false
}}
"""

# ─── Query Decomposition (Phase 3) ──────────────────────────────────

QUERY_DECOMPOSITION_TEMPLATE = """\
You are a research query strategist. Break this complex research topic into
2-4 focused sub-queries that together cover the topic comprehensively.

Research Topic: {topic}

Rules:
- Each sub-query should target a distinct aspect of the topic
- Sub-queries should be specific enough for effective web search
- Together, they should cover the topic's breadth
- 2 sub-queries for simple topics, 4 for complex ones

Return JSON:
{{
  "sub_queries": [
    "focused sub-query 1",
    "focused sub-query 2",
    "focused sub-query 3"
  ],
  "reasoning": "brief explanation of decomposition strategy"
}}
"""

QUERY_INTENT_CLASSIFICATION_TEMPLATE = """\
You are a research intent classifier. Analyze the user's research topic and classify its category and requirements.

Research Topic: {topic}

Classify into one of these categories:
- academic: Scientific papers, research publications, highly technical medical or physics theories, patents.
- news: Current events, stock updates, political news, product launches, trending affairs.
- technical: Software libraries, code specifications, technical documentation, developer tools.
- general: General business topics, historical events, travel, lifestyle, general facts.

Based on the topic, suggest:
1. Category (academic, news, technical, general).
2. Rationale for this classification.
3. List of target domains to prioritize (e.g. ["arxiv.org", "ncbi.nlm.nih.gov"] for academic, ["github.com", "readthedocs.io"] for technical).
4. List of domains to avoid (e.g. spam sites, generic forums like Reddit if academic).
5. Optional list of custom plan steps (e.g. custom research phases).
6. Optional list of custom initial sub-queries.

Return JSON matching this schema:
{{
  "category": "academic",
  "rationale": "Reasoning here...",
  "target_domains": ["arxiv.org", "ncbi.nlm.nih.gov"],
  "avoid_domains": ["quora.com", "pinterest.com"],
  "steps_override": ["Step 1", "Step 2", ...],
  "sub_queries": ["sub query 1", "sub query 2"]
}}
"""

POINTWISE_RELEVANCE_EVALUATION_TEMPLATE = """\
You are an expert information relevance assessor. Rate the relevance of this search result snippet against the target sub-query.

Target Sub-query: {sub_query}
SearchResult Snippet: {snippet}

Evaluate if the search snippet contains useful, relevant, and credible context that answers the sub-query.
Rate your confidence/relevance score:
- score: 0.0 (completely irrelevant, spam, or ad) to 1.0 (highly relevant, directly answers query, high-signal content).
- score must be between 0.0 and 1.0.

Return JSON:
{{
  "score": 0.85,
  "rationale": "Explain briefly why the snippet is relevant or irrelevant"
}}
"""

BATCH_RELEVANCE_EVALUATION_TEMPLATE = """\
You are an expert information relevance assessor. Rate the relevance of these search result snippets against the target sub-query.

Target Sub-query: {sub_query}

SearchResult Snippets:
{snippets_list}

For each snippet, evaluate if it contains useful, relevant, and credible context that answers the sub-query.
Rate your confidence/relevance score:
- score: 0.0 (completely irrelevant, spam, or ad) to 1.0 (highly relevant, directly answers query, high-signal content).
- score must be between 0.0 and 1.0.

Return JSON:
{{
  "evaluations": [
    {{
      "index": 0,
      "score": 0.85,
      "rationale": "Explain briefly why snippet 0 is relevant or irrelevant"
    }},
    ...
  ]
}}
"""
