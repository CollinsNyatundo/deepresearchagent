"""FastAPI server — REST + SSE endpoints for the Deep Research Agent frontend.

Endpoints:
- GET /runs              — List past research runs
- GET /runs/{id}/report  — Get Markdown report
- GET /runs/{id}/mindmap — Get mindmap graph (G6 format)
- POST /research         — Start research (blocking, shielded)
- POST /research/stream  — Start research with SSE streaming (Phase 2)
- POST /research/plan    — Generate plan for user review (Phase 4)
- POST /research/execute/stream — Execute user-approved plan with SSE (Phase 4)
- GET /runs/{id}/export/{format} — Download export (Phase 5)
- POST /runs/{id}/mindmap/expand — Expand mindmap node
- POST /validate-model   — Validate OpenRouter model ID
- GET /health            — Health check

Knowledge Graph (Graphify) Endpoints:
- GET  /runs/{id}/knowledge-graph          — Get knowledge graph JSON
- GET  /runs/{id}/knowledge-graph/html     — Download interactive graph.html
- POST /runs/{id}/knowledge-graph/build    — Trigger manual KG build
- POST /runs/{id}/knowledge-graph/query    — Query the graph via MCP bridge
- GET  /runs/{id}/knowledge-graph/mcp      — MCP server status
- POST /runs/{id}/knowledge-graph/mcp/start — Start MCP server
- POST /runs/{id}/knowledge-graph/mcp/stop  — Stop MCP server
"""

from __future__ import annotations

import asyncio
import json
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from research_engine.config import get_config
from research_engine.llm.provider import LLMProvider, validate_model_id
from research_engine.models import (
    ExpandRequest,
    KGQueryRequest,
    KGQueryResult,
    KnowledgeGraph,
    MindmapGraph,
    NodeExpansion,
    PlanApproval,
    PlanPreview,
    ResearchRequest,
    ResearchResult,
    RunSummary,
)
from research_engine.output.storage import (
    graph_html_available,
    knowledge_graph_available,
    list_runs,
    load_knowledge_graph,
    load_mindmap,
    load_report,
    load_run,
    save_knowledge_graph,
    save_mindmap,
)

# Load .env before ANYTHING else — must be before get_config() singleton init
# override=True ensures .env values take precedence over stale system env vars
load_dotenv(override=True)

logger = logging.getLogger(__name__)
config = get_config()

# ─── FastAPI App ─────────────────────────────────────────────────────

app = FastAPI(
    title="Deep Research Agent",
    description="Exhaustive, citation-backed deep research with mindmap visualization",
    version="0.2.0",
)

# CORS for frontend (default: http://localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Run Listing & Retrieval ─────────────────────────────────────────

@app.get("/runs", response_model=list[RunSummary])
async def get_runs():
    """List all past research runs, newest first."""
    return list_runs()


@app.get("/runs/{run_id}/report")
async def get_report(run_id: str):
    """Get the Markdown report for a research run."""
    try:
        report = load_report(run_id)
        return {"content": report}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")


@app.get("/runs/{run_id}/mindmap", response_model=MindmapGraph)
async def get_mindmap(run_id: str):
    """Get the mindmap graph (G6 format) for a research run."""
    try:
        return load_mindmap(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Mindmap not found for run: {run_id}")


# ─── Research Execution ──────────────────────────────────────────────

@app.post("/research")
async def start_research(request: ResearchRequest):
    """Start a new deep research run (blocking endpoint).

    Protected with asyncio.shield() so browser disconnects don't cancel research.
    For real-time progress, use POST /research/stream instead.
    """
    from research_engine.agent.orchestrator import DeepResearchOrchestrator

    # Validate model if provided
    if request.model:
        try:
            validate_model_id(request.model, provider=request.provider)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    orchestrator = DeepResearchOrchestrator(config)

    try:
        # shield() prevents CancelledError from propagating when client disconnects
        result = await asyncio.shield(orchestrator.run(request))
        return {
            "run_id": result.run_id,
            "query": result.query,
            "model_used": result.model_used,
            "progress": result.progress,
            "total_cycles": len(result.steps),
            "total_citations": len(result.citations),
        }
    except asyncio.CancelledError:
        logger.info("Client disconnected but research was shielded — continuing in background")
        return {"status": "research_continues", "message": "Client disconnected but research is still running"}
    except Exception as e:
        logger.error(f"Research failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")


@app.post("/research/stream")
async def stream_research(request: ResearchRequest):
    """Start research and stream progress via Server-Sent Events (Phase 2).

    The browser connects via fetch() + ReadableStream (not EventSource,
    since we need POST). Events include: initializing, planning, plan_ready,
    searching, scraping, validating, synthesizing, reflecting, retry,
    progress, cycle_complete, error, generating_report, complete.

    A heartbeat comment is sent every 30s to keep the connection alive.
    """
    from research_engine.agent.orchestrator import DeepResearchOrchestrator

    # Validate model if provided
    if request.model:
        try:
            validate_model_id(request.model, provider=request.provider)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    event_queue: asyncio.Queue = asyncio.Queue()
    orchestrator = DeepResearchOrchestrator(config)

    # Start research as background task that pushes events to the queue
    research_task = asyncio.create_task(
        orchestrator.run(request, event_queue=event_queue)
    )

    async def event_generator():
        """Yield SSE-formatted events from the research queue."""
        try:
            while True:
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=30)
                    event_name = event.get("event", "message")
                    event_data = json.dumps(event.get("data", {}))
                    yield f"event: {event_name}\ndata: {event_data}\n\n"

                    if event_name == "complete":
                        break
                except asyncio.TimeoutError:
                    # Heartbeat to keep connection alive
                    yield ": heartbeat\n\n"

                # Check if the research task has completed or errored
                if research_task.done():
                    exc = research_task.exception()
                    if exc:
                        error_data = json.dumps({
                            "error": f"{type(exc).__name__}: {str(exc)}"
                        })
                        yield f"event: error\ndata: {error_data}\n\n"
                    break

        except asyncio.CancelledError:
            logger.info("SSE client disconnected, research continues in background")
        except Exception as e:
            logger.error(f"SSE generator error: {e}")
            error_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# ─── Interactive Plan Review (Phase 4) ───────────────────────────────

@app.post("/research/plan", response_model=PlanPreview)
async def generate_plan(request: ResearchRequest):
    """Generate a research plan for user review before execution.

    Returns a PlanPreview that the frontend renders as an editable plan.
    The user can modify steps, sub-queries, and export preferences before
    approving via POST /research/execute/stream.
    """
    from research_engine.agent import planner as planner_module

    # Validate model if provided
    model = config.llm.default_model
    if request.model:
        try:
            model = validate_model_id(request.model, provider=request.provider)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    llm = LLMProvider(config.llm)

    try:
        from research_engine.agent import planner as planner_module

        # Generate the research plan
        plan = await planner_module.create_plan(
            request.query, llm=llm, model=model, provider=request.provider
        )

        # Decompose query into sub-queries (uses planner module function)
        try:
            sub_queries = await planner_module.decompose_query(
                request.query, llm=llm, model=model, provider=request.provider
            )
        except Exception as e:
            logger.warning(f"Query decomposition failed, using original query: {e}")
            sub_queries = [request.query]

        # Estimate cycles and duration
        max_cycles = min(request.depth * 6, config.research.max_cycles)
        estimated_minutes = max_cycles * 1.5  # ~1.5 min per cycle average

        return PlanPreview(
            plan=plan,
            sub_queries=sub_queries,
            estimated_cycles=max_cycles,
            estimated_duration_minutes=estimated_minutes,
        )

    except Exception as e:
        logger.error(f"Plan generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {str(e)}")


@app.post("/research/execute/stream")
async def execute_approved_plan(approval: PlanApproval):
    """Execute a user-approved research plan with SSE streaming (Phase 4).

    The user has reviewed and potentially modified the plan from
    POST /research/plan. Now we execute it with real-time streaming.
    """
    from research_engine.agent.orchestrator import DeepResearchOrchestrator

    # Validate model if provided
    if approval.model:
        try:
            validate_model_id(approval.model, provider=approval.provider)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    event_queue: asyncio.Queue = asyncio.Queue()
    orchestrator = DeepResearchOrchestrator(config)

    research_task = asyncio.create_task(
        orchestrator.run_with_plan(approval, event_queue=event_queue)
    )

    async def event_generator():
        """Yield SSE-formatted events from the approved plan execution."""
        try:
            while True:
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=30)
                    event_name = event.get("event", "message")
                    event_data = json.dumps(event.get("data", {}))
                    yield f"event: {event_name}\ndata: {event_data}\n\n"

                    if event_name == "complete":
                        break
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"

                if research_task.done():
                    exc = research_task.exception()
                    if exc:
                        error_data = json.dumps({
                            "error": f"{type(exc).__name__}: {str(exc)}"
                        })
                        yield f"event: error\ndata: {error_data}\n\n"
                    break
        except asyncio.CancelledError:
            logger.info("SSE client disconnected from plan execution")
        except Exception as e:
            logger.error(f"SSE generator error: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Mindmap Operations ─────────────────────────────────────────────

@app.post("/runs/{run_id}/mindmap/expand", response_model=NodeExpansion)
async def expand_mindmap_node(run_id: str, request: ExpandRequest):
    """Expand a mindmap node — drill deeper into a specific topic.

    Generates child nodes using the LLM and merges them into the existing graph.
    """
    from research_engine.output.mindmap import expand_node as do_expand

    try:
        mindmap = load_mindmap(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Mindmap not found for run: {run_id}")

    # Find the target node
    node = next((n for n in mindmap.nodes if n.id == request.node_id), None)
    if node is None:
        raise HTTPException(
            status_code=404,
            detail=f"Node '{request.node_id}' not found in mindmap",
        )

    # Get research context for informed expansion
    try:
        result = load_run(run_id)
        context = result.report[:5000]  # Use report as context
    except FileNotFoundError:
        context = f"Research about: {node.label}"

    llm = LLMProvider(config.llm)
    model = request.model  # Optional per-request model override

    expansion = await do_expand(node, context, llm=llm, model=model)

    # Persist the updated mindmap
    if expansion.new_nodes:
        mindmap.nodes.extend(expansion.new_nodes)
        mindmap.edges.extend(expansion.new_edges)
        save_mindmap(mindmap, run_id)

    return expansion


# ─── Export Downloads (Phase 5) ─────────────────────────────────────

@app.get("/runs/{run_id}/exports")
async def list_exports(run_id: str):
    """List available export formats for a research run."""
    from research_engine.output.exporter import EXTENSIONS

    run_dir = __import__("pathlib").Path("outputs") / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    available = []
    for fmt, ext in EXTENSIONS.items():
        export_path = run_dir / f"export{ext}"
        available.append({
            "format": fmt,
            "extension": ext,
            "cached": export_path.exists(),
        })
    return {"run_id": run_id, "formats": available}


@app.get("/runs/{run_id}/export/{fmt}")
async def export_research(run_id: str, fmt: str):
    """Download research in specified format (Phase 5).

    Formats: markdown, pdf, docx, xlsx, mindmap_json
    """
    from research_engine.output.exporter import MEDIA_TYPES, export_run

    if fmt not in MEDIA_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{fmt}'. Valid: {', '.join(MEDIA_TYPES.keys())}",
        )

    try:
        export_path = await export_run(run_id, fmt)
        filename = f"research_{run_id}{export_path.suffix}"
        return FileResponse(
            path=str(export_path),
            media_type=MEDIA_TYPES[fmt],
            filename=filename,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Export failed for run {run_id} fmt {fmt}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# ─── Models ─────────────────────────────────────────────────────────

@app.get("/models")
async def list_models():
    """List all available model presets across all providers.

    Returns OpenRouter presets, suggested free models, and the full
    Groq free-tier preset catalogue. The frontend model selector uses
    this to populate the dropdown UI with provider-annotated options.
    """
    or_presets = config.llm.presets  # OpenRouter presets from config
    groq_presets = config.llm.groq_presets  # Groq free-tier models

    return {
        "default": config.llm.default_model,
        # OpenRouter configured presets
        "presets": [
            {"name": name, "id": model_id, "provider": "openrouter"}
            for name, model_id in or_presets.items()
        ],
        # Free OpenRouter models (no API key required beyond OpenRouter key)
        "suggested": [
            {"name": "Nemotron 120B (Free)",         "id": "nvidia/nemotron-3-super-120b-a12b:free", "provider": "openrouter"},
            {"name": "Qwen3 235B (Free)",             "id": "qwen/qwen3-235b-a22b:free",             "provider": "openrouter"},
            {"name": "Gemini Flash 1.5 (Free)",       "id": "google/gemini-flash-1.5:free",          "provider": "openrouter"},
            {"name": "Llama 3.3 70B (Free)",          "id": "meta-llama/llama-3.3-70b-instruct:free","provider": "openrouter"},
            {"name": "Mistral 7B (Free)",             "id": "mistralai/mistral-7b-instruct:free",    "provider": "openrouter"},
            {"name": "DeepSeek R1 (Free)",            "id": "deepseek/deepseek-r1:free",             "provider": "openrouter"},
        ],
        # Groq free-tier models (requires GROQ_API_KEY, use provider='groq')
        "groq_presets": [
            {"name": name, "id": model_id, "provider": "groq"}
            for name, model_id in groq_presets.items()
        ],
    }


@app.get("/scraper/status")
async def scraper_status():
    """Inspect which Scrapling fetcher tiers are available on this server.

    Returns availability for all 4 tiers:
      async_fetcher         — curl_cffi native async (always available)
      dynamic_fetcher       — Playwright Chromium JS rendering (needs msgspec)
      stealthy_patchright   — patchright stealth Chromium (needs patchright)
      stealthy_camoufox     — Camoufox Firefox (needs camoufox binary fetched)

    Use this to debug missing content — if dynamic_fetcher=false, JS sites
    will return empty content and you need to install/launch missing deps.
    """
    from research_engine.sources.web_scraper import get_fetcher_availability

    availability = get_fetcher_availability()
    configured_tier = config.scraping.fetcher_tier

    warnings = []
    if not availability.get("dynamic"):
        warnings.append("DynamicFetcher unavailable — JS pages will return empty content. Run: pip install msgspec && python -m playwright install chromium")
    if not availability.get("stealthy_patchright"):
        warnings.append("StealthyFetcher (patchright) unavailable. Run: pip install patchright")
    if not availability.get("stealthy_camoufox"):
        warnings.append("Camoufox unavailable — install with: pip install camoufox && python -m camoufox fetch")

    return {
        "configured_tier": configured_tier,
        "availability": availability,
        "active_tiers": [k for k, v in availability.items() if v],
        "warnings": warnings,
        "health": "ok" if availability.get("async") else "degraded",
    }


# ─── Utilities ───────────────────────────────────────────────────────

class ModelValidationRequest(BaseModel):
    model: str


@app.post("/validate-model")
async def validate_model(request: ModelValidationRequest):
    """Validate an OpenRouter model ID format."""
    try:
        validated = validate_model_id(request.model)
        return {"valid": True, "model": validated}
    except ValueError as e:
        return {"valid": False, "error": str(e)}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.2.0"}


# ─── Knowledge Graph (Graphify) ─────────────────────────────────

@app.get("/runs/{run_id}/knowledge-graph", response_model=KnowledgeGraph)
async def get_knowledge_graph(run_id: str):
    """Get the Graphify knowledge graph for a run.

    Returns the full node/edge/community data for frontend rendering.
    Raises 404 if the graph has not been built yet.
    """
    if not knowledge_graph_available(run_id):
        raise HTTPException(
            status_code=404,
            detail="Knowledge graph not built for this run. Try POST /runs/{run_id}/knowledge-graph/build",
        )
    try:
        return load_knowledge_graph(run_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/runs/{run_id}/knowledge-graph/html")
async def get_knowledge_graph_html(run_id: str):
    """Download the Graphify interactive graph.html for a run."""
    from pathlib import Path
    from research_engine.output.storage import DEFAULT_OUTPUT_DIR

    html_path = Path(DEFAULT_OUTPUT_DIR) / run_id / "graph.html"
    if not html_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Interactive graph.html not available for this run.",
        )
    return FileResponse(
        path=str(html_path),
        media_type="text/html",
        filename=f"knowledge_graph_{run_id}.html",
    )


@app.post("/runs/{run_id}/knowledge-graph/build", response_model=KnowledgeGraph)
async def build_knowledge_graph(run_id: str):
    """Trigger manual knowledge graph build for an existing run.

    Useful when the run completed before graphify was enabled,
    or when re-building with a different mode.
    """
    from pathlib import Path
    from research_engine.knowledge_graph import builder as kg_builder
    from research_engine.output.storage import DEFAULT_OUTPUT_DIR

    try:
        result = load_run(run_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    run_dir = Path(DEFAULT_OUTPUT_DIR) / run_id
    try:
        kg = await kg_builder.build_knowledge_graph(
            result=result,
            run_dir=run_dir,
            graphify_mode=config.graphify.mode,
        )
        await save_knowledge_graph(kg, run_id)
        return kg
    except Exception as e:
        logger.error(f"Manual KG build failed for {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Knowledge graph build failed: {e}")


@app.post("/runs/{run_id}/knowledge-graph/query", response_model=KGQueryResult)
async def query_knowledge_graph(run_id: str, request: KGQueryRequest):
    """Query the knowledge graph using the Graphify MCP bridge.

    Returns a graph-traversal answer optimized for token efficiency.
    The graph must be built first (GET /knowledge-graph to check).
    """
    from research_engine.knowledge_graph import mcp_bridge as kg_mcp

    if not knowledge_graph_available(run_id):
        raise HTTPException(
            status_code=404,
            detail="Knowledge graph not found. Build it first.",
        )

    try:
        result = await kg_mcp.query_graph(run_id, request)
        return result
    except Exception as e:
        logger.error(f"KG query failed for {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Graph query failed: {e}")


@app.get("/runs/{run_id}/knowledge-graph/mcp")
async def get_mcp_status(run_id: str):
    """Get the MCP server status for a run."""
    from research_engine.knowledge_graph import mcp_bridge as kg_mcp
    return kg_mcp.get_server_status(run_id)


@app.post("/runs/{run_id}/knowledge-graph/mcp/start")
async def start_mcp_server(run_id: str):
    """Start the Graphify MCP server for a run."""
    from pathlib import Path
    from research_engine.knowledge_graph import mcp_bridge as kg_mcp
    from research_engine.output.storage import DEFAULT_OUTPUT_DIR

    kg_json_path = Path(DEFAULT_OUTPUT_DIR) / run_id / "knowledge_graph.json"
    if not kg_json_path.exists():
        raise HTTPException(status_code=404, detail="knowledge_graph.json not found.")

    success = await kg_mcp.start_mcp_server(run_id, kg_json_path)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to start MCP server.")
    return {"status": "started", "run_id": run_id}


@app.post("/runs/{run_id}/knowledge-graph/mcp/stop")
async def stop_mcp_server(run_id: str):
    """Stop the Graphify MCP server for a run."""
    from research_engine.knowledge_graph import mcp_bridge as kg_mcp
    await kg_mcp.stop_mcp_server(run_id)
    return {"status": "stopped", "run_id": run_id}


@app.get("/runs/{run_id}/knowledge-graph/available")
async def knowledge_graph_status(run_id: str):
    """Check whether a knowledge graph is available for a run."""
    return {
        "run_id": run_id,
        "knowledge_graph_available": knowledge_graph_available(run_id),
        "graph_html_available": graph_html_available(run_id),
    }
