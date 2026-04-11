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
    MindmapGraph,
    NodeExpansion,
    PlanApproval,
    PlanPreview,
    ResearchRequest,
    ResearchResult,
    RunSummary,
)
from research_engine.output.storage import (
    list_runs,
    load_mindmap,
    load_report,
    load_run,
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
            validate_model_id(request.model)
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
            validate_model_id(request.model)
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
            model = validate_model_id(request.model)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    llm = LLMProvider(config.llm)

    try:
        from research_engine.agent import planner as planner_module

        # Generate the research plan
        plan = await planner_module.create_plan(
            request.query, llm=llm, model=model
        )

        # Decompose query into sub-queries (uses planner module function)
        try:
            sub_queries = await planner_module.decompose_query(
                request.query, llm=llm, model=model
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
            validate_model_id(approval.model)
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
    """List available OpenRouter model presets and the current default.

    Returns the configured presets from config.toml/defaults, plus any
    models the user might want to try. Useful for the model selector UI.
    """
    presets = config.llm.presets  # e.g. {"nemotron": "nvidia/...", ...}
    return {
        "default": config.llm.default_model,
        "presets": [
            {"name": name, "id": model_id}
            for name, model_id in presets.items()
        ],
        # Common free OpenRouter models the user might want
        "suggested": [
            {"name": "Nemotron 120B (Free)",    "id": "nvidia/nemotron-3-super-120b-a12b:free"},
            {"name": "Qwen 235B (Free)",         "id": "qwen/qwen3-235b-a22b:free"},
            {"name": "Gemini Flash 1.5 (Free)",  "id": "google/gemini-flash-1.5:free"},
            {"name": "Llama 3.3 70B (Free)",     "id": "meta-llama/llama-3.3-70b-instruct:free"},
            {"name": "Mistral 7B (Free)",        "id": "mistralai/mistral-7b-instruct:free"},
            {"name": "DeepSeek R1 (Free)",       "id": "deepseek/deepseek-r1:free"},
        ],
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
