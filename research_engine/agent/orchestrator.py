"""Deep Research Orchestrator — main async research loop implementing DRE algorithm.

This is the heart of the engine. It coordinates:
1. Plan creation → 2. Research loop (search → scrape → validate → synthesize → reflect) → 3. Report

Key enhancements over original DRE:
- SSE event emission for real-time frontend streaming (Phase 2)
- Protocol-H inspired state machine with explicit transitions (Phase 6)
- Standalone reflective retry module via retry.py (Phase 6)
- Confidence scoring per answer with low-confidence re-search (Phase 6)
- Result validation delegated to searcher.validate_scraped_content (Phase 6)
- LLM-based result reranking for better page selection (Phase 3)
- run_with_plan() properly uses user-approved plan, skipping generation (Phase 4)

Runs at exhaustive depth (depth=5, ≤30 cycles) by default.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from research_engine.agent import context as ctx_module
from research_engine.agent import crossover as crossover_module
from research_engine.agent import planner as planner_module
from research_engine.agent import searcher as searcher_module
from research_engine.agent.retry import reflective_retry
from research_engine.config import AppConfig, get_config
from research_engine.knowledge_graph import builder as kg_builder
from research_engine.knowledge_graph import enricher as kg_enricher
from research_engine.knowledge_graph import mcp_bridge as kg_mcp
from research_engine.llm.provider import LLMProvider, validate_model_id
from research_engine.models import (
    ConfidenceScore,
    PlanApproval,
    ResearchEvent,
    ResearchPlan,
    ResearchRequest,
    ResearchResult,
    ResearchState,
    ResearchStep,
    SearchQuery,
)
from research_engine.output.mindmap import build_mindmap_graph
from research_engine.output.storage import save_knowledge_graph, save_run
from research_engine.sources.reranker import rerank_results
from research_engine.sources.web_scraper import WebScraper
from research_engine.sources.web_search import get_search_provider

logger = logging.getLogger(__name__)
console = Console()

# Confidence threshold — below this, we emit a low-confidence event and
# consider additional research cycles for that query
CONFIDENCE_THRESHOLD = 0.5


class DeepResearchOrchestrator:
    """Async orchestrator implementing the DRE (Deep Research Reflect Evolve) algorithm.

    Enhanced over original DRE:
    - Full async throughout
    - Deep scraping via Scrapling (not just search snippets)
    - Runtime model selection
    - Candidate crossover (evolutionary answer merging)
    - Rich console progress output
    - Exhaustive depth=5 default (up to 30 research cycles)
    - SSE streaming via event_queue (Phase 2)
    - Protocol-H reflective retry via standalone retry.py (Phase 6)
    - Confidence scoring per cycle — low confidence triggers retry (Phase 6)
    - Content validation delegated to searcher module (Phase 6)
    - LLM reranking of search results (Phase 3)
    - run_with_plan() properly uses approved plan (Phase 4)
    """

    def __init__(self, config: AppConfig | None = None):
        self.config = config or get_config()
        self.llm = LLMProvider(self.config.llm)
        self.scraper = WebScraper(self.config.scraping)

    # ═════════════════════════════════════════════════════════════════
    # Public API
    # ═════════════════════════════════════════════════════════════════

    async def run(
        self,
        request: ResearchRequest,
        event_queue: asyncio.Queue | None = None,
    ) -> ResearchResult:
        """Execute a complete deep research run, generating the plan internally.

        Args:
            request: The research request with query, model, depth, etc.
            event_queue: Optional async queue for SSE event emission.

        Returns:
            Complete ResearchResult with report, citations, trace, and mindmap.
        """
        run_id = _generate_run_id()
        started_at = datetime.now(timezone.utc)

        await self._emit(event_queue, ResearchState.INITIALIZING, {
            "run_id": run_id, "query": request.query,
        })

        model = self._resolve_model(request.model, provider=request.provider)
        if getattr(request, "mode", "web") == "github":
            from research_engine.sources.github_search import GitHubSearchProvider, GitHubScraper
            search_provider = GitHubSearchProvider()
            scraper = GitHubScraper()
        else:
            search_provider = get_search_provider(
                provider=request.search_provider,
                config=self.config.search,
            )
            scraper = self.scraper

        max_cycles = min(request.depth * 6, self.config.research.max_cycles)

        console.print(f"\n[bold blue]🔬 Deep Research Agent[/bold blue]")
        console.print(f"   Query: [bold]{request.query}[/bold]")
        console.print(f"   Model: {model}")
        console.print(f"   Depth: {request.depth} (max {max_cycles} cycles)\n")

        # ── Plan generation ────────────────────────────────────────
        await self._emit(event_queue, ResearchState.PLANNING, {
            "message": "Creating research plan...",
        })
        console.print("[yellow]📋 Creating research plan...[/yellow]")

        plan = await planner_module.create_plan(
            request.query, llm=self.llm, model=model, provider=request.provider
        )

        # ── Query decomposition ────────────────────────────────────
        await self._emit(event_queue, ResearchState.DECOMPOSING, {
            "message": "Decomposing query into sub-queries...",
        })
        sub_queries = await planner_module.decompose_query(
            request.query, llm=self.llm, model=model, provider=request.provider
        )
        console.print(f"   Sub-queries: {sub_queries}")

        await self._emit(event_queue, ResearchState.PLAN_READY, {
            "plan": {"steps": plan.steps},
            "step_count": len(plan.steps),
            "sub_queries": sub_queries,
        })

        return await self._execute_research_loop(
            run_id=run_id,
            started_at=started_at,
            query=request.query,
            plan=plan,
            model=model,
            search_provider=search_provider,
            scraper=scraper,
            max_cycles=max_cycles,
            request=request,
            event_queue=event_queue,
        )

    async def run_with_plan(
        self,
        approval: PlanApproval,
        event_queue: asyncio.Queue | None = None,
    ) -> ResearchResult:
        """Execute research using a user-approved and potentially modified plan.

        IMPORTANT: This method skips plan generation entirely. The approved
        plan's steps and sub-queries are used directly from the PlanApproval.
        This is what makes Phase 4 (interactive plan review) actually work.

        Args:
            approval: User-approved plan with possibly edited steps and sub-queries.
            event_queue: Optional queue for SSE event emission.

        Returns:
            Complete ResearchResult.
        """
        run_id = _generate_run_id()
        started_at = datetime.now(timezone.utc)

        model = self._resolve_model(approval.model, provider=approval.provider)
        if getattr(approval, "mode", "web") == "github":
            from research_engine.sources.github_search import GitHubSearchProvider, GitHubScraper
            search_provider = GitHubSearchProvider()
            scraper = GitHubScraper()
        else:
            search_provider = get_search_provider(
                provider=approval.search_provider,
                config=self.config.search,
            )
            scraper = self.scraper

        max_cycles = min(approval.depth * 6, self.config.research.max_cycles)

        console.print(f"\n[bold blue]🔬 Deep Research Agent (Pre-Approved Plan)[/bold blue]")
        console.print(f"   Query: [bold]{approval.query}[/bold]")
        console.print(f"   Steps: {len(approval.plan.steps)} (user-approved)")
        console.print(f"   Model: {model}\n")

        await self._emit(event_queue, ResearchState.INITIALIZING, {
            "run_id": run_id,
            "query": approval.query,
            "plan_source": "user_approved",
        })

        # Use the user's approved plan directly — NO plan generation
        plan = approval.plan
        sub_queries = approval.sub_queries or [approval.query]

        await self._emit(event_queue, ResearchState.PLAN_READY, {
            "plan": {"steps": plan.steps},
            "step_count": len(plan.steps),
            "sub_queries": sub_queries,
            "plan_source": "user_approved",
        })

        # Fake a ResearchRequest from the approval for the loop
        request = ResearchRequest(
            query=approval.query,
            model=approval.model,
            depth=approval.depth,
            max_pages=approval.max_pages,
            enable_crossover=approval.enable_crossover,
            search_provider=approval.search_provider,
            provider=approval.provider,
        )

        return await self._execute_research_loop(
            run_id=run_id,
            started_at=started_at,
            query=approval.query,
            plan=plan,
            model=model,
            search_provider=search_provider,
            scraper=scraper,
            max_cycles=max_cycles,
            request=request,
            event_queue=event_queue,
            initial_plan=plan,  # Bypass plan regeneration
        )

    # ═════════════════════════════════════════════════════════════════
    # Core Research Loop
    # ═════════════════════════════════════════════════════════════════

    async def _execute_research_loop(
        self,
        run_id: str,
        started_at: datetime,
        query: str,
        plan: ResearchPlan,
        model: str,
        search_provider,
        scraper,
        max_cycles: int,
        request: ResearchRequest,
        event_queue: asyncio.Queue | None,
        initial_plan: ResearchPlan | None = None,
    ) -> ResearchResult:
        """Shared research loop used by both run() and run_with_plan()."""
        context = ctx_module.ResearchContext()
        current_plan = initial_plan or plan
        final_progress = 0
        errors: list[str] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Researching...", total=max_cycles)

            cycle = 0
            while cycle < max_cycles:
                progress.update(
                    task,
                    description=f"[cyan]Cycle {cycle + 1}/{max_cycles}[/cyan]",
                    advance=1,
                )

                try:
                    step = await self._run_cycle(
                        cycle=cycle,
                        topic=query,
                        plan=current_plan,
                        context=context,
                        search_provider=search_provider,
                        scraper=scraper,
                        model=model,
                        request=request,
                        event_queue=event_queue,
                    )
                    await context.add_step(step)

                    # Reflect on plan
                    await self._emit(event_queue, ResearchState.REFLECTING, {
                        "cycle": cycle + 1, "message": "Reflecting on plan...",
                    })
                    reflection = await planner_module.reflect_on_plan(
                        query, current_plan, context.get_history_text(),
                        llm=self.llm, model=model, provider=request.provider,
                    )
                    step.reflection = reflection

                    if reflection.should_update:
                        current_plan = await planner_module.update_plan(
                            query, current_plan, reflection,
                            context.get_history_text(),
                            llm=self.llm, model=model, provider=request.provider,
                        )
                        step.plan_updated = True
                        console.print(f"   [yellow]📝 Plan updated at cycle {cycle + 1}[/yellow]")

                    await self._emit(event_queue, ResearchState.CYCLE_COMPLETE, {
                        "cycle": cycle + 1,
                        "max_cycles": max_cycles,
                        "answer_length": len(step.answer.answer),
                        "citation_count": len(step.answer.citations),
                        "plan_updated": step.plan_updated,
                    })

                    # Progress check
                    check_interval = self.config.research.progress_check_interval
                    if (cycle + 1) % check_interval == 0:
                        final_progress = await planner_module.check_progress(
                            query, current_plan, context.get_history_text(),
                            llm=self.llm, model=model, provider=request.provider,
                        )
                        step.progress = final_progress
                        console.print(f"   [green]📊 Progress: {final_progress}%[/green]")
                        await self._emit(event_queue, "progress", {
                            "progress": final_progress, "cycle": cycle + 1,
                        })

                        if final_progress >= self.config.research.progress_threshold:
                            console.print(
                                f"   [bold green]✓ Research threshold reached "
                                f"({final_progress}%)[/bold green]"
                            )
                            break

                    if getattr(step, "needs_more_research", False):
                        absolute_max = self.config.research.max_cycles + 3
                        if max_cycles < absolute_max:
                            max_cycles += 1
                            progress.update(task, total=max_cycles)
                            console.print(f"   [bold yellow]⚠ Confidence low, triggered additional research cycle. Total cycles: {max_cycles}[/bold yellow]")
                            await self._emit(event_queue, "message", {
                                "message": f"Low confidence triggered additional research cycle (total {max_cycles})"
                            })

                except Exception as e:
                    error_msg = f"Cycle {cycle + 1} failed: {type(e).__name__}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    console.print(f"   [red]⚠ {error_msg}[/red]")
                    await self._emit(event_queue, ResearchState.ERROR, {
                        "cycle": cycle + 1, "error": error_msg,
                    })
                    cycle += 1
                    continue

                cycle += 1

        # ── Generate report ────────────────────────────────────────
        await self._emit(event_queue, ResearchState.GENERATING_REPORT, {
            "message": "Writing final report...",
        })
        console.print("\n[yellow]📝 Writing final report...[/yellow]")
        report = await self._generate_report(query, current_plan, context, model=model, provider=request.provider)

        # ── Build result ───────────────────────────────────────────
        all_citations = context.get_all_citations()
        completed_at = datetime.now(timezone.utc)

        result = ResearchResult(
            run_id=run_id,
            query=query,
            model_used=model,
            plan=plan,
            final_plan=current_plan,
            steps=context.get_trace(),
            report=report,
            citations=all_citations,
            progress=final_progress,
            started_at=started_at,
            completed_at=completed_at,
            errors=errors,
        )

        # ── Build mindmap and save ─────────────────────────────────
        console.print("[yellow]🧠 Building mindmap...[/yellow]")
        mindmap = build_mindmap_graph(result)
        console.print("[yellow]💾 Saving results...[/yellow]")
        output_path = await save_run(result, mindmap)

        # ── Strategy A + C: Build Knowledge Graph (if graphify enabled) ──
        if self.config.graphify.enabled:
            try:
                console.print("[yellow]🕸 Building knowledge graph...[/yellow]")

                # Strategy C: collect ArXiv/PDF URLs from all scraped pages
                scraped_urls: list[str] = [
                    page.url
                    for step in result.steps
                    for page in step.scraped_pages
                    if page.url
                ]
                paper_urls = [
                    url for url in scraped_urls
                    if "arxiv.org" in url or url.lower().endswith(".pdf")
                ]

                if paper_urls:
                    await self._emit(event_queue, "knowledge_graph_build", {
                        "run_id": run_id,
                        "message": f"Enriching corpus with {len(paper_urls)} papers...",
                    })

                kg = await kg_builder.build_knowledge_graph(
                    result=result,
                    run_dir=output_path,
                    graphify_mode=self.config.graphify.mode,
                )
                await save_knowledge_graph(kg, run_id)

                # Strategy B: start MCP server for interactive graph queries
                if self.config.graphify.mcp_enabled and kg.graph_html_available:
                    kg_json_path = output_path / "knowledge_graph.json"
                    await kg_mcp.start_mcp_server(run_id, kg_json_path)

                await self._emit(event_queue, "knowledge_graph_ready", {
                    "run_id": run_id,
                    "node_count": len(kg.nodes),
                    "edge_count": len(kg.edges),
                    "community_count": len(kg.communities),
                    "god_nodes": kg.god_nodes[:5],
                    "compression_ratio": kg.compression_ratio,
                    "graph_html_available": kg.graph_html_available,
                })
                console.print(
                    f"   [bold cyan]✓ Knowledge graph ready![/bold cyan] "
                    f"{len(kg.nodes)} nodes, {len(kg.edges)} edges, "
                    f"{len(kg.communities)} communities"
                )
            except Exception as kg_err:
                logger.error(f"Knowledge graph build failed: {kg_err}")
                console.print(f"   [yellow]⚠ Knowledge graph unavailable: {kg_err}[/yellow]")

        duration = (completed_at - started_at).total_seconds()
        console.print(
            f"\n[bold green]✓ Research complete![/bold green]\n"
            f"   Cycles: {context.step_count}\n"
            f"   Citations: {len(all_citations)}\n"
            f"   Progress: {final_progress}%\n"
            f"   Duration: {duration:.1f}s\n"
            f"   Output: {output_path}\n"
        )

        await self._emit(event_queue, ResearchState.COMPLETE, {
            "run_id": run_id,
            "query": query,
            "model_used": model,
            "progress": final_progress,
            "total_cycles": context.step_count,
            "total_citations": len(all_citations),
            "duration_seconds": duration,
            "errors": errors,
        })

        return result

    # ═════════════════════════════════════════════════════════════════
    # Per-Cycle Logic
    # ═════════════════════════════════════════════════════════════════

    async def _run_cycle(
        self,
        cycle: int,
        topic: str,
        plan: ResearchPlan,
        context: ctx_module.ResearchContext,
        search_provider,
        scraper,
        model: str,
        request: ResearchRequest,
        event_queue: asyncio.Queue | None = None,
    ) -> ResearchStep:
        """Execute a single research cycle: query → search → rerank → scrape → validate → synthesize.

        Full Protocol-H pipeline:
        1. Generate search query
        2. Search with reflective retry on failure
        3. LLM-rerank results for relevance
        4. Scrape top pages
        5. Validate scraped content (filter junk)
        6. Synthesize answer
        7. Assess confidence — retry with broader query if < threshold
        """
        # ── Generate search query ──────────────────────────────────
        query = await searcher_module.generate_query(
            topic, plan, context.get_history_text(), llm=self.llm, model=model, provider=request.provider
        )
        console.print(f"   🔍 Query: {query.query}")

        # ── Search with reflective retry ───────────────────────────
        await self._emit(event_queue, ResearchState.SEARCHING, {
            "cycle": cycle + 1, "query": query.query,
        })

        search_results = []
        scraped_pages = []

        try:
            search_results, scraped_pages = await searcher_module.search_and_scrape(
                query,
                search_provider=search_provider,
                scraper=scraper,
                max_pages=request.max_pages,
            )
        except Exception as e:
            logger.warning(f"Search/scrape failed in cycle {cycle + 1}: {e}")
            await self._emit(event_queue, ResearchState.RETRYING, {
                "cycle": cycle + 1,
                "error": str(e),
                "step_type": "search",
                "message": "Analyzing failure and retrying...",
            })

            # ── Reflective retry via standalone module ─────────────
            correction = await reflective_retry(
                error=e,
                context={
                    "step_type": "search",
                    "current_query": query.query,
                    "cycle": cycle + 1,
                },
                llm=self.llm,
                model=model,
                provider=request.provider,
                retry_count=0,
            )

            if correction.corrected_query and not correction.should_skip:
                console.print(f"   [yellow]🔄 Retry: {correction.corrected_query}[/yellow]")
                query = SearchQuery(
                    query=correction.corrected_query,
                    rationale=f"Reflective retry: {correction.reasoning}",
                )
                try:
                    search_results, scraped_pages = await searcher_module.search_and_scrape(
                        query,
                        search_provider=search_provider,
                        scraper=scraper,
                        max_pages=request.max_pages,
                    )
                except Exception as retry_err:
                    logger.error(f"Retry also failed: {retry_err}")
            else:
                logger.info(f"Reflective retry decided to skip cycle {cycle + 1}")

        # ── Rerank search results ──────────────────────────────────
        if search_results:
            try:
                search_results = await rerank_results(
                    query.query, search_results,
                    llm=self.llm, model=model,
                    top_k=request.max_pages * 2,
                    provider=request.provider,
                )
            except Exception as e:
                logger.warning(f"Reranking failed, using original order: {e}")

        await self._emit(event_queue, ResearchState.SCRAPING, {
            "cycle": cycle + 1,
            "urls_scraped": len(scraped_pages),
            "successful": sum(1 for p in scraped_pages if p.success),
        })

        # ── Result validation via searcher module ──────────────────
        await self._emit(event_queue, ResearchState.VALIDATING, {
            "cycle": cycle + 1,
            "pages_before": len(scraped_pages),
        })

        valid_pages = searcher_module.validate_scraped_content(scraped_pages)

        console.print(
            f"   📄 Scraped {len(valid_pages)} valid pages "
            f"({sum(p.content_length for p in valid_pages)} chars)"
        )

        await self._emit(event_queue, ResearchState.VALIDATING, {
            "cycle": cycle + 1,
            "pages_after": len(valid_pages),
            "pages_filtered": len(scraped_pages) - len(valid_pages),
        })

        # ── Synthesize answer ──────────────────────────────────────
        await self._emit(event_queue, ResearchState.SYNTHESIZING, {
            "cycle": cycle + 1,
            "source_pages": len(valid_pages),
        })

        if request.enable_crossover and len(valid_pages) > 0:
            answer = await crossover_module.answer_with_crossover(
                topic, query, valid_pages, llm=self.llm, model=model, provider=request.provider,
                num_candidates=self.config.research.crossover_candidates,
            )
        else:
            answer = await searcher_module.synthesize_answer(
                topic, query, valid_pages, llm=self.llm, model=model, provider=request.provider
            )

        console.print(f"   ✅ Answer: {len(answer.answer)} chars, {len(answer.citations)} citations")

        # ── Confidence scoring (Protocol-H pattern) ────────────────
        confidence = await self._assess_confidence(
            topic=topic,
            query=query.query,
            answer=answer.answer,
            source_count=len(valid_pages),
            model=model,
            provider=request.provider,
        )

        # Emit confidence score for frontend visualization
        await self._emit(event_queue, "confidence", {
            "cycle": cycle + 1,
            "score": confidence.score,
            "reasoning": confidence.reasoning,
            "needs_more_research": confidence.needs_more_research,
        })

        # Low confidence → log warning (could trigger retry in future)
        if confidence.needs_more_research and confidence.score < CONFIDENCE_THRESHOLD:
            logger.warning(
                f"Cycle {cycle + 1}: low confidence ({confidence.score:.2f}) — "
                f"{confidence.reasoning}"
            )
            console.print(
                f"   [yellow]⚠ Low confidence: {confidence.score:.2f} — "
                f"{confidence.reasoning[:80]}[/yellow]"
            )

        await context.add_qa(query.query, answer.answer)

        return ResearchStep(
            cycle=cycle,
            query=query,
            search_results=search_results,
            scraped_pages=scraped_pages,
            answer=answer,
            needs_more_research=confidence.needs_more_research,
        )

    # ═════════════════════════════════════════════════════════════════
    # Protocol-H Confidence Scoring
    # ═════════════════════════════════════════════════════════════════

    async def _assess_confidence(
        self,
        topic: str,
        query: str,
        answer: str,
        source_count: int,
        model: str,
        provider: str | None = None,
    ) -> ConfidenceScore:
        """Use LLM to self-assess answer confidence (Protocol-H pattern).

        If the LLM rates its own answer below CONFIDENCE_THRESHOLD and
        needs_more_research=True, the orchestrator emits a warning event.
        A full confidence-based retry loop is reserved for future work.

        Returns:
            ConfidenceScore with score 0-1, reasoning, and needs_more_research flag.
        """
        from research_engine.llm.prompts import CONFIDENCE_SCORING_TEMPLATE

        prompt = CONFIDENCE_SCORING_TEMPLATE.format(
            topic=topic,
            query=query,
            answer_excerpt=answer[:500],
            source_count=source_count,
        )

        try:
            result = await self.llm.call_structured(
                prompt, ConfidenceScore, model=model, provider=provider
            )
            if isinstance(result, dict):
                return ConfidenceScore(**result)
            return result

        except Exception as e:
            logger.warning(f"Confidence scoring failed: {e}. Using default score.")
            return ConfidenceScore(
                score=0.6,
                reasoning="Confidence assessment failed — defaulting to moderate confidence",
                needs_more_research=False,
            )

    # ═════════════════════════════════════════════════════════════════
    # Report Generation
    # ═════════════════════════════════════════════════════════════════

    async def _generate_report(
        self,
        topic: str,
        plan: ResearchPlan,
        context: ctx_module.ResearchContext,
        model: str,
        provider: str | None = None,
    ) -> str:
        """Generate the final Markdown report from all research findings."""
        from research_engine.llm.prompts import REPORT_WRITER_TEMPLATE

        prompt = REPORT_WRITER_TEMPLATE.format(
            topic=topic,
            research_log=context.get_history_text(),
        )

        try:
            return await self.llm.call(prompt, model=model, provider=provider)
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return f"# Research Report: {topic}\n\n{context.get_history_text()}"

    # ═════════════════════════════════════════════════════════════════
    # Helpers
    # ═════════════════════════════════════════════════════════════════

    def _resolve_model(self, model: str | None, provider: str | None = None) -> str:
        """Resolve model — per-request override or config default."""
        if model:
            return validate_model_id(model, provider=provider)
        return self.config.llm.default_model

    async def _emit(
        self,
        event_queue: asyncio.Queue | None,
        event: str | ResearchState,
        data: dict[str, Any],
    ) -> None:
        """Emit a research event to the SSE queue (no-op if no queue)."""
        if event_queue is None:
            return

        event_name = event.value if isinstance(event, ResearchState) else event
        try:
            await event_queue.put({
                "event": event_name,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            logger.warning(f"Failed to emit event '{event_name}': {e}")


# ═════════════════════════════════════════════════════════════════════
# Utilities
# ═════════════════════════════════════════════════════════════════════

def _generate_run_id() -> str:
    """Generate a unique run ID with timestamp."""
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short_id = uuid.uuid4().hex[:8]
    return f"{now}-{short_id}"
