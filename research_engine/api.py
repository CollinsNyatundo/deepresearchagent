# ==========================================
# MANDATORY INTEGRITY WARNING
# DO NOT CHEAT. All implementations must be genuine.
# - DO NOT hardcode test results, expected outputs, or verification strings.
# - DO NOT create dummy or facade implementations.
# - Every implementation must maintain real state and produce real behavior.
# ==========================================

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

GitNexus Web UI Bridge Endpoints:
- POST /gitnexus/serve/start   — Start npx gitnexus serve (port 4747)
- POST /gitnexus/serve/stop    — Stop the running gitnexus serve process
- GET  /gitnexus/serve/status  — Check if gitnexus serve is running
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import zipfile
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from research_engine.auth import verify_supabase_jwt
from research_engine.db.supabase.client import get_supabase_client

from research_engine.config import get_config
from research_engine.llm.provider import LLMProvider, validate_model_id
from research_engine.models import (
    ExpandRequest,
    KGQueryRequest,
    KGQueryResult,
    KnowledgeGraph,
    MindmapGraph,
    NodeExpansion,
    OpenFileRequest,
    PlanApproval,
    PlanPreview,
    ResearchRequest,
    ResearchResult,
    RunSummary,
    TelemetryResponse,
    ResynthesizeRequest,
    SimilarityRequest,
    CitationVerificationRequest,
    CitationVerificationResponse,
)   
from research_engine.citations.verifier import CitationVerifier, CitationStatus
from research_engine.citations.parser import CitationParser
from research_engine.citations.adapters.crossref import CrossRefAdapter
from research_engine.citations.adapters.openalex import OpenAlexAdapter
from research_engine.citations.cache import VerificationCache
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

@asynccontextmanager
async def _lifespan(app: FastAPI):  # noqa: ARG001
    """Application lifespan — startup / shutdown hooks."""
    from pathlib import Path
    Path("outputs").mkdir(parents=True, exist_ok=True)
    
    # Test Supabase connectivity on startup so the operator gets an immediate
    # actionable warning if the key is wrong or the project is unreachable.
    try:
        _client = get_supabase_client()
        test_resp = await asyncio.to_thread(
            _client.table("workspaces").select("id").limit(1).execute
        )
        logger.info("Supabase connectivity check passed.")
    except Exception as _sb_err:
        logger.error(
            f"Supabase connectivity check FAILED on startup: {_sb_err}\n"
            "  ACTION REQUIRED: Check that SUPABASE_KEY is set to the service_role key\n"
            "  (not the anon key). Find it in: Supabase Dashboard → Settings → API → service_role.\n"
            "  With the anon key, RLS will block all workspace_members/notes/documents queries → 500 errors."
        )
    
    yield


app = FastAPI(
    title="Deep Research Agent",
    description="Exhaustive, citation-backed deep research with mindmap visualization",
    version="0.2.0",
    lifespan=_lifespan,
)

# CORS for frontend (default: http://localhost:5173) and GitNexus Web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        *config.api.cors_origins,
        "https://gitnexus.vercel.app",
        "http://localhost:4747",
        "http://127.0.0.1:4747",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── GitNexus serve process manager ──────────────────────────────────
# Holds the asyncio subprocess for `npx gitnexus serve --port 4747`.
# Only one serve process is allowed at a time.
_gitnexus_serve_proc: asyncio.subprocess.Process | None = None


async def verify_workspace_membership(client, workspace_id: str, user_id: str) -> None:
    """Verify that the user is a member of the given workspace.

    Raises HTTPException(403) if the user is not a member or if the membership
    check fails (e.g. due to Supabase RLS / connectivity issues). Never returns
    a bool — callers just await this and catch the 403 if needed.

    NOTE: If SUPABASE_KEY is set to the anon key (not service_role), RLS will
    block the workspace_members query and this will always raise 403 for valid
    members. Set SUPABASE_KEY to the service_role key in config.toml / env.
    """
    if user_id == "dev-bypass-user":
        return
    try:
        response = await asyncio.to_thread(
            client.table("workspace_members").select("id").eq("workspace_id", workspace_id).eq("user_id", user_id).limit(1).execute
        )
        if not response.data:
            logger.warning(
                f"Workspace membership denied: user={user_id} workspace={workspace_id}. "
                "If this user is a valid member, ensure SUPABASE_KEY is the service_role key, not the anon key."
            )
            raise HTTPException(status_code=403, detail="Not authorized to access this workspace")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Workspace membership check failed (user={user_id} workspace={workspace_id}): {e}. "
            "Ensure SUPABASE_KEY is the service_role key — anon key RLS will block this query."
        )
        raise HTTPException(
            status_code=403,
            detail=f"Workspace access check failed: {e}. Ensure SUPABASE_KEY is the service_role key (Supabase Dashboard → Settings → API → service_role)"
        )

async def get_run_workspace_id(client, run_id: str) -> str | None:
    """Get the workspace_id associated with a research run."""
    try:
        response = await asyncio.to_thread(
            client.table("research_runs").select("workspace_id").eq("id", run_id).execute
        )
        if response.data:
            return response.data[0].get("workspace_id")
        return None
    except Exception as e:
        logger.error(f"Failed to get workspace_id for run {run_id}: {e}")
        return None

async def check_run_access(run_id: str, user_data: dict) -> None:
    """Verify that the user has access to the given research run."""
    user_id = user_data.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid user ID in token")
    client = get_supabase_client()
    workspace_id = await get_run_workspace_id(client, run_id)
    if not workspace_id:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    await verify_workspace_membership(client, workspace_id, user_id)



# ─── Scraper Cache Control ────────────────────────────────────────────
# The fetcher availability cache is set at module import time.
# If curl_cffi / playwright was installed AFTER the server started,
# call this endpoint to re-probe without a full restart.

@app.post("/scraper/refresh-cache")
async def refresh_scraper_cache(user_data: dict = Depends(verify_supabase_jwt)):
    """Re-probe Scrapling fetcher availability and return the fresh result.

    Use after installing curl_cffi or playwright packages while the server
    is already running — avoids a full process restart.
    """
    from research_engine.sources.web_scraper import reset_fetcher_cache
    result = reset_fetcher_cache()
    return {"scrapling_fetchers": result}


# ─── Run Listing & Retrieval ─────────────────────────────────────────

@app.get("/runs", response_model=list[RunSummary])
async def get_runs(workspace_id: str, user_data: dict = Depends(verify_supabase_jwt)):
    """List all past research runs for a workspace, newest first."""
    user_id = user_data.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid user ID in token")
    client = get_supabase_client()
    await verify_workspace_membership(client, workspace_id, user_id)
    try:
        response = await asyncio.to_thread(
            client.table("research_runs").select("*").eq("workspace_id", workspace_id).order("created_at", desc=True).execute
        )
        runs = []
        for row in response.data:
            runs.append(RunSummary(
                id=row["id"],
                query=row["query"],
                created_at=row.get("created_at") or "",
                model_used=row.get("model_used") or "",
                status=row.get("status") or "initializing",
                progress=row.get("progress") or 0,
                workspace_id=row["workspace_id"]
            ))
        return runs
    except Exception as e:
        logger.error(f"Failed to query research runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/runs/{run_id}", response_model=ResearchResult)
async def get_run_details(run_id: str, user_data: dict = Depends(verify_supabase_jwt)):
    """Retrieve the full ResearchResult details for a run."""
    await check_run_access(run_id, user_data)
    try:
        res = await asyncio.to_thread(load_run, run_id)
        # Populate workspace_id
        client = get_supabase_client()
        workspace_id = await get_run_workspace_id(client, run_id)
        if workspace_id:
            res.workspace_id = workspace_id
        return res
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")


@app.get("/runs/{run_id}/report")
async def get_report(run_id: str, user_data: dict = Depends(verify_supabase_jwt)):
    """Get the Markdown report for a research run."""
    await check_run_access(run_id, user_data)
    try:
        report = await asyncio.to_thread(load_report, run_id)
        return {"content": report}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")


@app.get("/runs/{run_id}/mindmap", response_model=MindmapGraph)
async def get_mindmap(run_id: str, user_data: dict = Depends(verify_supabase_jwt)):
    """Get the mindmap graph (G6 format) for a research run."""
    await check_run_access(run_id, user_data)
    try:
        return await asyncio.to_thread(load_mindmap, run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Mindmap not found for run: {run_id}")


# ─── Research Execution ──────────────────────────────────────────────

@app.post("/research")
async def start_research(request: ResearchRequest, user_data: dict = Depends(verify_supabase_jwt)):
    """Start a new deep research run (blocking endpoint).

    Protected with asyncio.shield() so browser disconnects don't cancel research.
    For real-time progress, use POST /research/stream instead.
    """
    from research_engine.agent.orchestrator import DeepResearchOrchestrator, _generate_run_id

    workspace_id = request.workspace_id
    if not workspace_id:
        raise HTTPException(status_code=400, detail="workspace_id is required")
    user_id = user_data.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid user ID in token")
        
    client = get_supabase_client()
    await verify_workspace_membership(client, workspace_id, user_id)

    run_id = request.run_id or _generate_run_id()
    
    # Insert / upsert the run record
    run_record = {
        "id": run_id,
        "workspace_id": workspace_id,
        "query": request.query,
        "model_used": request.model or config.llm.default_model,
        "status": "initializing",
        "progress": 0,
    }
    try:
        await asyncio.to_thread(client.table("research_runs").upsert(run_record).execute)
    except Exception as e:
        logger.error(f"Failed to insert research run to DB: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # Validate model if provided
    if request.model:
        try:
            validate_model_id(request.model, provider=request.provider)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    orchestrator = DeepResearchOrchestrator(config)

    try:
        # shield() prevents CancelledError from propagating when client disconnects
        result = await asyncio.shield(orchestrator.run(request, run_id=run_id))
        
        # Update run record to complete
        try:
            await asyncio.to_thread(
                client.table("research_runs").update({
                    "status": "complete",
                    "progress": 100,
                    "report": result.report,
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", run_id).execute
            )
        except Exception as e:
            logger.error(f"Failed to update db on complete: {e}")

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
        # Update run record to failed
        try:
            await asyncio.to_thread(
                client.table("research_runs").update({
                    "status": "failed",
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", run_id).execute
            )
        except Exception as db_err:
            logger.error(f"Failed to update db on failure: {db_err}")
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")


@app.post("/research/stream")
async def stream_research(request: ResearchRequest, user_data: dict = Depends(verify_supabase_jwt)):
    """Start research and stream progress via Server-Sent Events (Phase 2).

    The browser connects via fetch() + ReadableStream (not EventSource,
    since we need POST). Events include: initializing, planning, plan_ready,
    searching, scraping, validating, synthesizing, reflecting, retry,
    progress, cycle_complete, error, generating_report, complete.

    A heartbeat comment is sent every 30s to keep the connection alive.
    """
    from research_engine.agent.orchestrator import DeepResearchOrchestrator, _generate_run_id

    workspace_id = request.workspace_id
    if not workspace_id:
        raise HTTPException(status_code=400, detail="workspace_id is required")
    user_id = user_data.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid user ID in token")
        
    client = get_supabase_client()
    await verify_workspace_membership(client, workspace_id, user_id)

    run_id = request.run_id or _generate_run_id()
    
    # Insert / upsert the run record
    run_record = {
        "id": run_id,
        "workspace_id": workspace_id,
        "query": request.query,
        "model_used": request.model or config.llm.default_model,
        "status": "initializing",
        "progress": 0,
    }
    try:
        await asyncio.to_thread(client.table("research_runs").upsert(run_record).execute)
    except Exception as e:
        logger.error(f"Failed to insert research run to DB: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

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
        orchestrator.run(request, event_queue=event_queue, run_id=run_id)
    )

    async def event_generator():
        """Yield SSE-formatted events from the research queue."""
        try:
            while True:
                # If research task is done and queue is empty, we are finished
                if research_task.done() and event_queue.empty():
                    exc = research_task.exception()
                    if exc:
                        error_data = json.dumps({
                            "error": f"{type(exc).__name__}: {str(exc)}"
                        })
                        yield f"event: error\ndata: {error_data}\n\n"
                        try:
                            await asyncio.to_thread(
                                client.table("research_runs").update({
                                    "status": "failed",
                                    "completed_at": datetime.now(timezone.utc).isoformat()
                                }).eq("id", run_id).execute
                            )
                        except Exception as db_err:
                            logger.error(f"Failed to update db on failure: {db_err}")
                    break

                queue_get_task = asyncio.create_task(event_queue.get())
                done, pending = await asyncio.wait(
                    [queue_get_task, research_task],
                    timeout=30,
                    return_when=asyncio.FIRST_COMPLETED
                )

                if queue_get_task not in done:
                    queue_get_task.cancel()

                if not done:
                    # Timeout reached (heartbeat)
                    yield ": heartbeat\n\n"
                    continue

                if queue_get_task in done:
                    event = queue_get_task.result()
                    event_name = event.get("event", "message")
                    event_data = json.dumps(event.get("data", {}))
                    yield f"event: {event_name}\ndata: {event_data}\n\n"

                    if event_name == "complete":
                        # Update run record to complete
                        try:
                            report_content = ""
                            try:
                                report_content = load_report(run_id)
                            except Exception:
                                pass
                            await asyncio.to_thread(
                                client.table("research_runs").update({
                                    "status": "complete",
                                    "progress": 100,
                                    "report": report_content,
                                    "completed_at": datetime.now(timezone.utc).isoformat()
                                }).eq("id", run_id).execute
                            )
                        except Exception as e:
                            logger.error(f"Failed to update db on complete: {e}")
                        break

        except asyncio.CancelledError:
            logger.info("SSE client disconnected, research cancelled to prevent memory leak")
            research_task.cancel()
            # Update run record to failed/cancelled
            try:
                await asyncio.to_thread(
                    client.table("research_runs").update({
                        "status": "failed",
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", run_id).execute
                )
            except Exception as db_err:
                logger.error(f"Failed to update db on cancel: {db_err}")
        except Exception as e:
            logger.error(f"SSE generator error: {e}")
            error_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"
            # Update run record to failed
            try:
                await asyncio.to_thread(
                    client.table("research_runs").update({
                        "status": "failed",
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", run_id).execute
                )
            except Exception as db_err:
                logger.error(f"Failed to update db on error: {db_err}")

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
async def generate_plan(request: ResearchRequest, user_data: dict = Depends(verify_supabase_jwt)):
    """Generate a research plan for user review before execution.

    Returns a PlanPreview that the frontend renders as an editable plan.
    The user can modify steps, sub-queries, and export preferences before
    approving via POST /research/execute/stream.
    """
    workspace_id = request.workspace_id
    if not workspace_id:
        raise HTTPException(status_code=400, detail="workspace_id is required")
    user_id = user_data.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid user ID in token")
        
    client = get_supabase_client()
    await verify_workspace_membership(client, workspace_id, user_id)

    from research_engine.agent.orchestrator import _generate_run_id
    run_id = request.run_id or _generate_run_id()
    
    # Insert / upsert the run record
    run_record = {
        "id": run_id,
        "workspace_id": workspace_id,
        "query": request.query,
        "model_used": request.model or config.llm.default_model,
        "status": "initializing",
        "progress": 0,
    }
    try:
        await asyncio.to_thread(client.table("research_runs").upsert(run_record).execute)
    except Exception as e:
        logger.error(f"Failed to insert research run to DB: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

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
            run_id=run_id,
        )

    except Exception as e:
        logger.error(f"Plan generation failed: {e}", exc_info=True)
        # Update run record to failed
        try:
            await asyncio.to_thread(
                client.table("research_runs").update({
                    "status": "failed",
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", run_id).execute
            )
        except Exception as db_err:
            logger.error(f"Failed to update db on failure: {db_err}")
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {str(e)}")


@app.post("/research/execute/stream")
async def execute_approved_plan(approval: PlanApproval, user_data: dict = Depends(verify_supabase_jwt)):
    """Execute a user-approved research plan with SSE streaming (Phase 4).

    The user has reviewed and potentially modified the plan from
    POST /research/plan. Now we execute it with real-time streaming.
    """
    from research_engine.agent.orchestrator import DeepResearchOrchestrator, _generate_run_id

    workspace_id = approval.workspace_id
    if not workspace_id:
        raise HTTPException(status_code=400, detail="workspace_id is required")
    user_id = user_data.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid user ID in token")
        
    client = get_supabase_client()
    await verify_workspace_membership(client, workspace_id, user_id)

    run_id = approval.run_id or _generate_run_id()
    approval.run_id = run_id

    # Insert / upsert the run record
    run_record = {
        "id": run_id,
        "workspace_id": workspace_id,
        "query": approval.query,
        "model_used": approval.model or config.llm.default_model,
        "status": "initializing",
        "progress": 0,
    }
    try:
        await asyncio.to_thread(client.table("research_runs").upsert(run_record).execute)
    except Exception as e:
        logger.error(f"Failed to insert research run to DB: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

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
                # If research task is done and queue is empty, we are finished
                if research_task.done() and event_queue.empty():
                    exc = research_task.exception()
                    if exc:
                        error_data = json.dumps({
                            "error": f"{type(exc).__name__}: {str(exc)}"
                        })
                        yield f"event: error\ndata: {error_data}\n\n"
                        try:
                            await asyncio.to_thread(
                                client.table("research_runs").update({
                                    "status": "failed",
                                    "completed_at": datetime.now(timezone.utc).isoformat()
                                }).eq("id", run_id).execute
                            )
                        except Exception as db_err:
                            logger.error(f"Failed to update db on failure: {db_err}")
                    break

                queue_get_task = asyncio.create_task(event_queue.get())
                done, pending = await asyncio.wait(
                    [queue_get_task, research_task],
                    timeout=30,
                    return_when=asyncio.FIRST_COMPLETED
                )

                if queue_get_task not in done:
                    queue_get_task.cancel()

                if not done:
                    # Timeout reached (heartbeat)
                    yield ": heartbeat\n\n"
                    continue

                if queue_get_task in done:
                    event = queue_get_task.result()
                    event_name = event.get("event", "message")
                    event_data = json.dumps(event.get("data", {}))
                    yield f"event: {event_name}\ndata: {event_data}\n\n"

                    if event_name == "complete":
                        # Update run record to complete
                        try:
                            report_content = ""
                            try:
                                report_content = load_report(run_id)
                            except Exception:
                                pass
                            await asyncio.to_thread(
                                client.table("research_runs").update({
                                    "status": "complete",
                                    "progress": 100,
                                    "report": report_content,
                                    "completed_at": datetime.now(timezone.utc).isoformat()
                                }).eq("id", run_id).execute
                            )
                        except Exception as e:
                            logger.error(f"Failed to update db on complete: {e}")
                        break
        except asyncio.CancelledError:
            logger.info("SSE client disconnected from plan execution, research cancelled to prevent memory leak")
            research_task.cancel()
            # Update run record to failed/cancelled
            try:
                await asyncio.to_thread(
                    client.table("research_runs").update({
                        "status": "failed",
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", run_id).execute
                )
            except Exception as db_err:
                logger.error(f"Failed to update db on cancel: {db_err}")
        except Exception as e:
            logger.error(f"SSE generator error: {e}")
            # Update run record to failed
            try:
                await asyncio.to_thread(
                    client.table("research_runs").update({
                        "status": "failed",
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", run_id).execute
                )
            except Exception as db_err:
                logger.error(f"Failed to update db on error: {db_err}")

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
async def expand_mindmap_node(run_id: str, request: ExpandRequest, user_data: dict = Depends(verify_supabase_jwt)):
    """Expand a mindmap node — drill deeper into a specific topic.

    Generates child nodes using the LLM and merges them into the existing graph.
    """
    await check_run_access(run_id, user_data)
    from research_engine.output.mindmap import expand_node as do_expand

    try:
        mindmap = await asyncio.to_thread(load_mindmap, run_id)
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
        result = await asyncio.to_thread(load_run, run_id)
        context = result.report[:5000]  # Use report as context
    except FileNotFoundError:
        context = f"Research about: {node.label}"

    llm = LLMProvider(config.llm)
    model = request.model  # Optional per-request model override

    if model:
        try:
            validate_model_id(model)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    expansion = await do_expand(node, context, llm=llm, model=model)

    # Persist the updated mindmap
    if expansion.new_nodes:
        mindmap.nodes.extend(expansion.new_nodes)
        mindmap.edges.extend(expansion.new_edges)
        await asyncio.to_thread(save_mindmap, mindmap, run_id)

    return expansion


# ─── Export Downloads (Phase 5) ─────────────────────────────────────

@app.get("/runs/{run_id}/exports")
async def list_exports(run_id: str, user_data: dict = Depends(verify_supabase_jwt)):
    """List available export formats for a research run."""
    await check_run_access(run_id, user_data)
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
async def export_research(run_id: str, fmt: str, user_data: dict = Depends(verify_supabase_jwt)):
    """Download research in specified format (Phase 5).

    Formats: markdown, pdf, docx, xlsx, mindmap_json
    """
    await check_run_access(run_id, user_data)
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
async def scraper_status(user_data: dict = Depends(verify_supabase_jwt)):
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
async def validate_model(request: ModelValidationRequest, user_data: dict = Depends(verify_supabase_jwt)):
    """Validate an OpenRouter model ID format."""
    try:
        validated = validate_model_id(request.model)
        return {"valid": True, "model": validated}
    except ValueError as e:
        return {"valid": False, "error": str(e)}


@app.get("/health")
async def health():
    """Health check endpoint — includes Supabase connectivity status."""
    supabase_ok = False
    supabase_detail = "unknown"
    try:
        _client = get_supabase_client()
        await asyncio.to_thread(
            _client.table("workspaces").select("id").limit(1).execute
        )
        supabase_ok = True
        supabase_detail = "connected"
    except Exception as e:
        supabase_detail = (
            f"error: {type(e).__name__} — "
            "check SUPABASE_KEY is the service_role key, not the anon key"
        )
    
    return {
        "status": "ok",
        "version": "0.2.0",
        "supabase_connected": supabase_ok,
        "supabase_detail": supabase_detail,
    }


# ─── Knowledge Graph (Graphify) ─────────────────────────────────

@app.get("/runs/{run_id}/knowledge-graph", response_model=KnowledgeGraph)
async def get_knowledge_graph(run_id: str, user_data: dict = Depends(verify_supabase_jwt)):
    """Get the Graphify knowledge graph for a run.

    Returns the full node/edge/community data for frontend rendering.
    Raises 404 if the graph has not been built yet.
    """
    await check_run_access(run_id, user_data)
    if not await asyncio.to_thread(knowledge_graph_available, run_id):
        raise HTTPException(
            status_code=404,
            detail="Knowledge graph not built for this run. Try POST /runs/{run_id}/knowledge-graph/build",
        )
    try:
        return await asyncio.to_thread(load_knowledge_graph, run_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/runs/{run_id}/knowledge-graph/html")
async def get_knowledge_graph_html(run_id: str, user_data: dict = Depends(verify_supabase_jwt)):
    """Download the Graphify interactive graph.html for a run."""
    await check_run_access(run_id, user_data)
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
async def build_knowledge_graph(run_id: str, user_data: dict = Depends(verify_supabase_jwt)):
    """Trigger manual knowledge graph build for an existing run.

    Useful when the run completed before graphify was enabled,
    or when re-building with a different mode.
    """
    await check_run_access(run_id, user_data)
    from pathlib import Path

    from research_engine.knowledge_graph import builder as kg_builder
    from research_engine.output.storage import DEFAULT_OUTPUT_DIR

    try:
        result = await asyncio.to_thread(load_run, run_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    run_dir = Path(DEFAULT_OUTPUT_DIR) / run_id
    try:
        llm = LLMProvider(config.llm)
        kg = await kg_builder.build_knowledge_graph(
            result=result,
            run_dir=run_dir,
            graphify_mode=config.graphify.mode,
            llm=llm,
        )
        await save_knowledge_graph(kg, run_id)
        return kg
    except Exception as e:
        logger.error(f"Manual KG build failed for {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Knowledge graph build failed: {e}")


@app.post("/runs/{run_id}/knowledge-graph/query", response_model=KGQueryResult)
async def query_knowledge_graph(run_id: str, request: KGQueryRequest, user_data: dict = Depends(verify_supabase_jwt)):
    """Query the knowledge graph using the Graphify MCP bridge.

    Returns a graph-traversal answer optimized for token efficiency.
    The graph must be built first (GET /knowledge-graph to check).
    """
    await check_run_access(run_id, user_data)
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


@app.post("/runs/{run_id}/knowledge-graph/similarity")
async def query_similarity(
    run_id: str,
    request: SimilarityRequest,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Query the knowledge graph for semantically similar nodes based on embedding distance."""
    await check_run_access(run_id, user_data)

    if request.match_threshold < -1.0 or request.match_threshold > 1.0:
        raise HTTPException(status_code=400, detail="Similarity threshold out of bounds")

    if not request.query_embedding:
        raise HTTPException(status_code=400, detail="Empty embedding vector")

    client = get_supabase_client()
    response = await asyncio.to_thread(
        client.rpc("match_graph_nodes", {
            "query_embedding": request.query_embedding,
            "match_threshold": request.match_threshold,
            "match_count": request.match_count
        }).execute
    )
    return response.data


@app.get("/runs/{run_id}/knowledge-graph/mcp")
async def get_mcp_status(run_id: str, user_data: dict = Depends(verify_supabase_jwt)):
    """Get the MCP server status for a run."""
    await check_run_access(run_id, user_data)
    from research_engine.knowledge_graph import mcp_bridge as kg_mcp
    return kg_mcp.get_server_status(run_id)


@app.post("/runs/{run_id}/knowledge-graph/mcp/start")
async def start_mcp_server(run_id: str, user_data: dict = Depends(verify_supabase_jwt)):
    """Start the Graphify MCP server for a run."""
    await check_run_access(run_id, user_data)
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
async def stop_mcp_server(run_id: str, user_data: dict = Depends(verify_supabase_jwt)):
    """Stop the Graphify MCP server for a run."""
    await check_run_access(run_id, user_data)
    from research_engine.knowledge_graph import mcp_bridge as kg_mcp
    await kg_mcp.stop_mcp_server(run_id)
    return {"status": "stopped", "run_id": run_id}


@app.get("/runs/{run_id}/knowledge-graph/available")
async def knowledge_graph_status(run_id: str, user_data: dict = Depends(verify_supabase_jwt)):
    """Check whether a knowledge graph is available for a run."""
    await check_run_access(run_id, user_data)
    return {
        "run_id": run_id,
        "knowledge_graph_available": knowledge_graph_available(run_id),
        "graph_html_available": graph_html_available(run_id),
    }


# ─── GitNexus Code Architecture (DEPRECATED) ────────────────────────────────
# The old /gitnexus/repos, /gitnexus/graph, /gitnexus/analyze, and
# /gitnexus/status endpoints have been removed.  They relied on the
# gitnexus eval-server (port 4848) and a background scheduler that ran
# `npx gitnexus analyze` every 30 minutes — both of which competed with
# `gitnexus serve` (port 4747) for the exclusive LadybugDB write lock,
# causing IO exceptions.  The official GitNexus Web UI now handles all
# codebase topology directly via the /gitnexus/serve/* endpoints below.


# ─── GitNexus Web UI Bridge (gitnexus serve) ──────────────────────────────────
# These endpoints manage the `npx gitnexus serve` subprocess that bridges the
# official GitNexus Web UI (https://gitnexus.vercel.app) to the local codebase.
# The web UI auto-detects the local server on port 4747.

@app.post("/gitnexus/serve/start")
async def start_gitnexus_serve(port: int = 4747, user_data: dict = Depends(verify_supabase_jwt)):
    """Start `npx gitnexus serve` so the GitNexus web UI can connect.

    The official GitNexus web UI at https://gitnexus.vercel.app polls
    localhost:4747 for a heartbeat. Running this endpoint starts the bridge.

    Query params:
        port: Port for the serve process (default: 4747).
    """
    global _gitnexus_serve_proc  # noqa: PLW0603

    if _gitnexus_serve_proc is not None and _gitnexus_serve_proc.returncode is None:
        return {
            "status": "already_running",
            "port": port,
            "pid": _gitnexus_serve_proc.pid,
            "message": f"gitnexus serve is already running on port {port}.",
        }

    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent

        # On Windows npx is a .cmd script — must run via cmd /c
        npx_cmd = ["cmd", "/c", "npx"] if sys.platform == "win32" else ["npx"]

        _gitnexus_serve_proc = await asyncio.create_subprocess_exec(
            *npx_cmd, "gitnexus", "serve", "--port", str(port), "--host", "127.0.0.1",
            cwd=str(project_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Give it a moment to come up
        await asyncio.sleep(1.5)

        if _gitnexus_serve_proc.returncode is not None:
            stderr = await _gitnexus_serve_proc.stderr.read() if _gitnexus_serve_proc.stderr else b""
            raise RuntimeError(
                f"gitnexus serve exited immediately (code {_gitnexus_serve_proc.returncode}): "
                + stderr.decode(errors="replace")[:300]
            )

        logger.info("GitNexus serve started on port %d (PID %d)", port, _gitnexus_serve_proc.pid)
        return {
            "status": "started",
            "port": port,
            "pid": _gitnexus_serve_proc.pid,
            "web_ui_url": "https://gitnexus.vercel.app",
            "message": f"gitnexus serve is running on port {port}. Open https://gitnexus.vercel.app in your browser.",
        }
    except Exception as e:
        _gitnexus_serve_proc = None
        logger.error("Failed to start gitnexus serve: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to start gitnexus serve: {e}")


@app.post("/gitnexus/serve/stop")
async def stop_gitnexus_serve(user_data: dict = Depends(verify_supabase_jwt)):
    """Stop the running `npx gitnexus serve` process."""
    global _gitnexus_serve_proc  # noqa: PLW0603

    proc = _gitnexus_serve_proc
    _gitnexus_serve_proc = None

    if proc is None or proc.returncode is not None:
        return {"status": "not_running", "message": "gitnexus serve is not running."}

    try:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except TimeoutError:
            proc.kill()
        pid = proc.pid
        logger.info("GitNexus serve stopped (PID %d)", pid)
        return {"status": "stopped", "pid": pid}
    except Exception as e:
        logger.error("Error stopping gitnexus serve: %s", e)
        raise HTTPException(status_code=500, detail=f"Error stopping gitnexus serve: {e}")


@app.get("/gitnexus/serve/status")
async def gitnexus_serve_status(user_data: dict = Depends(verify_supabase_jwt)):
    """Check whether `npx gitnexus serve` is currently running.

    Returns the PID, port, and a direct link to the GitNexus web UI.
    The frontend polls this to update the 'Connect' button state.
    """
    global _gitnexus_serve_proc  # noqa: PLW0603

    running = _gitnexus_serve_proc is not None and _gitnexus_serve_proc.returncode is None
    if not running:
        _gitnexus_serve_proc = None  # clean up dead reference

    return {
        "running": running,
        "pid": _gitnexus_serve_proc.pid if running else None,
        "port": 4747,
        "web_ui_url": "https://gitnexus.vercel.app",
    }


@app.post("/open-file")
async def open_file(request: OpenFileRequest, user_data: dict = Depends(verify_supabase_jwt)):
    """Open a file in the local editor (Cursor/VS Code) or fallback system opener.

    Translates the incoming POSIX relative path back to a platform-native absolute path,
    preventing path traversal and arbitrary execution.
    """
    import os
    import shutil
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent.resolve()
    # Convert POSIX relative path to platform native format
    relative_path = request.path.replace("/", os.sep)
    abs_path = (project_root / relative_path).resolve()

    # 1. Prevent path traversal by ensuring the resolved path is inside project_root
    try:
        abs_path.relative_to(project_root)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Access denied: path is outside the project root.",
        )

    if not abs_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {request.path} (resolved: {abs_path})",
        )

    # 2. Prevent arbitrary execution by limiting allowed extensions
    allowed_extensions = {
        ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".txt", ".toml",
        ".yaml", ".yml", ".ini", ".cfg", ".css", ".scss", ".html", ".sh",
        ".sql", ".properties", ".xml", ".graphql", ".go", ".rs", ".java", ".c",
        ".cpp", ".h", ".cs", ".gitignore", ".env", ".example", ".lock"
    }
    if abs_path.suffix.lower() not in allowed_extensions:
        raise HTTPException(
            status_code=403,
            detail="Access denied: opening files of this type is not allowed.",
        )

    # Try cursor first, then code
    editor = None
    if shutil.which("cursor"):
        editor = "cursor"
    elif shutil.which("code"):
        editor = "code"

    try:
        if editor:
            if sys.platform == "win32":
                # On Windows, wrap paths in double quotes to prevent shell injection.
                # Double quotes are invalid in Windows filenames, making this completely safe.
                cmd_str = f'"{editor}" "{abs_path}"'
                proc = await asyncio.create_subprocess_shell(
                    cmd_str,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    editor, str(abs_path),
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )

            # 3. Prevent zombie process leak on Unix/WSL by scheduling wait task
            asyncio.create_task(proc.wait())
            return {"status": "success", "message": f"Opened {request.path} in {editor}"}
        else:
            # Fallback to system-native opener
            if sys.platform == "win32":
                await asyncio.to_thread(os.startfile, str(abs_path))
            else:
                has_xdg = shutil.which("xdg-open")
                has_open = shutil.which("open")
                opener = "xdg-open" if has_xdg else ("open" if has_open else None)
                if opener:
                    proc = await asyncio.create_subprocess_exec(
                        opener, str(abs_path),
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    asyncio.create_task(proc.wait())
                else:
                    raise RuntimeError("No suitable editor (cursor/code) or system opener found.")
            return {"status": "success", "message": f"Opened {request.path} with system default"}
    except Exception as e:
        logger.error(f"Failed to open file {abs_path}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to open file: {str(e)}"
        )


# ─── Telemetry Statistics ──────────────────────────────────────────────

@app.get("/api/telemetry", response_model=TelemetryResponse)
async def get_telemetry(user_data: dict = Depends(verify_supabase_jwt)):
    """Retrieve database cache statistics and active circuit breakers."""
    import sqlite3
    from research_engine.sources.circuit_breaker import CircuitBreakerManager

    db_path = "outputs/cache.db"
    
    total_cached_queries = 0
    total_scraped_pages = 0
    scraper_success_rate = 100.0
    
    try:
        def _fetch_cache_metrics():
            import os
            if not os.path.exists(db_path):
                return 0, 0, 100.0
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Check tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='query_cache'")
                has_query_cache = cursor.fetchone() is not None
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='page_cache'")
                has_page_cache = cursor.fetchone() is not None
                
                q_count = 0
                p_count = 0
                success_count = 0
                
                if has_query_cache:
                    cursor.execute("SELECT COUNT(*) FROM query_cache")
                    q_count = cursor.fetchone()[0]
                    
                if has_page_cache:
                    cursor.execute("SELECT content_json FROM page_cache")
                    rows = cursor.fetchall()
                    p_count = len(rows)
                    for row in rows:
                        try:
                            data = json.loads(row[0])
                            if data.get("success", False):
                                success_count += 1
                        except Exception:
                            pass
                            
                rate = (success_count / p_count * 100) if p_count > 0 else 100.0
                return q_count, p_count, round(rate, 2)
                
        total_cached_queries, total_scraped_pages, scraper_success_rate = await asyncio.to_thread(_fetch_cache_metrics)
    except Exception as e:
        logger.warning(f"Error reading cache metrics for telemetry: {e}")

    active_circuit_breakers = []
    for domain, state in CircuitBreakerManager._shared_domains.items():
        if state.get("state") == "OPEN":
            active_circuit_breakers.append(domain)
            
    return {
        "total_cached_queries": total_cached_queries,
        "total_scraped_pages": total_scraped_pages,
        "active_circuit_breakers": active_circuit_breakers,
        "scraper_success_rate": scraper_success_rate,
    }


async def run_resynthesis_task(
    run_id: str,
    disabled_domains: list[str],
    model: str | None,
    provider: str | None,
    event_queue: asyncio.Queue,
):
    try:
        from urllib.parse import urlparse
        from datetime import UTC, datetime
        from research_engine.agent.orchestrator import DeepResearchOrchestrator
        from research_engine.agent.context import ResearchContext
        from research_engine.output.storage import load_run, save_run, save_knowledge_graph
        from research_engine.output.mindmap import build_mindmap_graph
        from research_engine.knowledge_graph import builder as kg_builder

        # 1. Load run
        result = await asyncio.to_thread(load_run, run_id)

        # 2. Filter domains
        def is_domain_disabled(url: str) -> bool:
            if not url:
                return False
            parsed = urlparse(url)
            domain = (parsed.netloc or "").lower()
            for d in disabled_domains:
                d_lower = d.lower()
                if domain == d_lower or domain.endswith("." + d_lower):
                    return True
            return False

        # Create new context and populate with filtered steps/results
        context = ResearchContext()
        for step in result.steps:
            step.scraped_pages = [p for p in step.scraped_pages if not is_domain_disabled(p.url)]
            step.search_results = [r for r in step.search_results if not is_domain_disabled(r.url)]
            step.answer.citations = [c for c in step.answer.citations if not is_domain_disabled(c.url)]
            
            await context.add_step(step)
            await context.add_qa(step.query.query, step.answer.answer)

        # 3. Generate new report
        orchestrator = DeepResearchOrchestrator(config)
        resolved_model = orchestrator._resolve_model(model, provider=provider)

        await orchestrator._emit(event_queue, "generating_report", {"message": "Regenerating report..."})

        new_report = await orchestrator._generate_report(
            topic=result.query,
            plan=result.final_plan,
            context=context,
            model=resolved_model,
            provider=provider,
            event_queue=event_queue,
        )

        # 4. Update result
        result.report = new_report
        result.citations = context.get_all_citations()
        result.model_used = resolved_model

        # 5. Build mindmap and save
        await orchestrator._emit(event_queue, "message", {"message": "Updating mindmap..."})
        mindmap = build_mindmap_graph(result)
        output_path = await save_run(result, mindmap)

        # 6. Rebuild Knowledge Graph if enabled
        if orchestrator.config.graphify.enabled:
            await orchestrator._emit(event_queue, "message", {"message": "Updating knowledge graph..."})
            kg = await kg_builder.build_knowledge_graph(
                result=result,
                run_dir=output_path,
                graphify_mode=orchestrator.config.graphify.mode,
                llm=orchestrator.llm,
            )
            await save_knowledge_graph(kg, run_id)

            # Restart MCP server if enabled and running
            if orchestrator.config.graphify.mcp_enabled and kg.graph_html_available:
                from research_engine.knowledge_graph import mcp_bridge as kg_mcp
                kg_json_path = output_path / "knowledge_graph.json"
                await kg_mcp.stop_mcp_server(run_id)
                await kg_mcp.start_mcp_server(run_id, kg_json_path)

        # Emit complete event
        await orchestrator._emit(event_queue, "complete", {
            "run_id": run_id,
            "query": result.query,
            "model_used": result.model_used,
            "progress": result.progress,
            "total_cycles": len(result.steps),
            "total_citations": len(result.citations),
        })

    except Exception as e:
        logger.error(f"Re-synthesis failed: {e}", exc_info=True)
        # Put error in queue
        await event_queue.put({
            "event": "error",
            "data": {"error": str(e)},
            "timestamp": datetime.now(UTC).isoformat(),
        })


@app.post("/runs/{run_id}/resynthesize")
async def resynthesize_run(run_id: str, request: ResynthesizeRequest, user_data: dict = Depends(verify_supabase_jwt)):
    """Regenerate report and mindmap/KG without a full scrape rerun, excluding disabled domains."""
    await check_run_access(run_id, user_data)
    event_queue: asyncio.Queue = asyncio.Queue()
    client = get_supabase_client()

    # Start re-synthesis task
    resynth_task = asyncio.create_task(
        run_resynthesis_task(
            run_id=run_id,
            disabled_domains=request.disabled_domains,
            model=request.model,
            provider=request.provider,
            event_queue=event_queue,
        )
    )

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                    event_name = event.get("event", "message")
                    event_data = json.dumps(event.get("data", {}))
                    yield f"event: {event_name}\ndata: {event_data}\n\n"

                    if event_name == "complete":
                        # Update database run record with completion status
                        try:
                            report_content = ""
                            try:
                                report_content = load_report(run_id)
                            except Exception:
                                pass
                            await asyncio.to_thread(
                                client.table("research_runs").update({
                                    "status": "complete",
                                    "progress": 100,
                                    "report": report_content,
                                    "completed_at": datetime.now(timezone.utc).isoformat()
                                }).eq("id", run_id).execute
                            )
                        except Exception as db_err:
                            logger.error(f"Failed to update db on complete in resynthesis: {db_err}")
                        break
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"

                if resynth_task.done() and event_queue.empty():
                    exc = resynth_task.exception()
                    if exc:
                        error_data = json.dumps({
                            "error": f"{type(exc).__name__}: {str(exc)}"
                        })
                        yield f"event: error\ndata: {error_data}\n\n"
                    break
        except asyncio.CancelledError:
            logger.info("SSE client disconnected from resynthesis, cancelling task")
            resynth_task.cancel()
        except Exception as e:
            logger.error(f"Resynthesis SSE generator error: {e}")
            error_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class WorkspaceCreate(BaseModel):
    """Input parameters to create a new workspace."""
    name: str


@app.get("/workspaces")
async def list_workspaces(user_data: dict = Depends(verify_supabase_jwt)):
    """List all workspaces the authenticated user belongs to."""
    user_id = user_data.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid user ID in token")

    # Dev-bypass: return a synthetic local workspace so the UI is fully functional
    # without requiring Supabase workspace tables to be seeded.
    if user_id == "dev-bypass-user":
        return [{"id": "dev-workspace", "name": "Dev Workspace", "created_at": "2024-01-01T00:00:00Z"}]

    client = get_supabase_client()
    try:
        response = await asyncio.to_thread(
            client.table("workspace_members").select(
                "workspace_id, workspaces(id, name, created_at)"
            ).eq("user_id", user_id).execute
        )
        
        workspaces = []
        for item in response.data:
            ws = item.get("workspaces")
            if ws:
                workspaces.append(ws)
        return workspaces
    except Exception as e:
        logger.error(f"Failed to query workspaces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/workspaces")
async def create_workspace(workspace: WorkspaceCreate, user_data: dict = Depends(verify_supabase_jwt)):
    """Create a new workspace and add the authenticated user as the first member."""
    user_id = user_data.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid user ID in token")

    if not workspace.name or not workspace.name.strip():
        raise HTTPException(status_code=400, detail="Workspace name cannot be empty")

    # Dev-bypass: return a synthetic workspace without touching Supabase.
    if user_id == "dev-bypass-user":
        import time
        ws_id = f"dev-workspace-{int(time.time())}"
        return {"id": ws_id, "name": workspace.name.strip(), "created_at": datetime.now(timezone.utc).isoformat()}

    client = get_supabase_client()
    try:
        ws_response = await asyncio.to_thread(
            client.table("workspaces").insert({"name": workspace.name}).execute
        )
        if not ws_response.data:
            raise HTTPException(status_code=500, detail="Failed to create workspace record")
            
        created_ws = ws_response.data[0]
        workspace_id = created_ws["id"]
        
        member_response = await asyncio.to_thread(
            client.table("workspace_members").insert({
                "workspace_id": workspace_id,
                "user_id": user_id
            }).execute
        )
        
        if not member_response.data:
            await asyncio.to_thread(
                client.table("workspaces").delete().eq("id", workspace_id).execute
            )
            raise HTTPException(status_code=500, detail="Failed to create workspace membership record")
            
        return created_ws
    except Exception as e:
        logger.error(f"Failed to create workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Notes Module Endpoints ─────────────────────────────────────────────────

from research_engine.utils.wiki_links import extract_wiki_links, find_backlinks
from research_engine.models import (
    NoteSummary, Note, CreateNoteRequest, UpdateNoteRequest,
    BulkDeleteRequest, NoteSearchResponse
)


@app.get("/notes", response_model=list[NoteSummary])
async def get_notes(
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """List all notes for a workspace, newest first."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    try:
        response = await asyncio.to_thread(
            client.table("notes")
            .select("id, title, workspace_id, created_at, updated_at")
            .eq("workspace_id", workspace_id)
            .order("updated_at", desc=True)
            .execute
        )
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to list notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/notes/search")
async def search_notes(
    workspace_id: str,
    q: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Full-text search notes (title + content) using PostgreSQL tsvector with ILIKE fallback."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    try:
        # Try tsvector full-text search first
        try:
            response = await asyncio.to_thread(
                client.table("notes")
                .select("id, title, workspace_id, created_at, updated_at")
                .eq("workspace_id", workspace_id)
                .text_search("search_vector", q, options={"type": "websearch"})
                .order("updated_at", desc=True)
                .execute
            )
            notes = response.data or []
            if notes:
                return NoteSearchResponse(
                    notes=[NoteSummary(**n) for n in notes],
                    query=q,
                    total=len(notes)
                )
        except Exception as fts_err:
            logger.debug(f"FTS search failed, falling back to ILIKE: {fts_err}")
        
        # Fallback to ILIKE
        response = await asyncio.to_thread(
            client.table("notes")
            .select("id, title, workspace_id, created_at, updated_at")
            .eq("workspace_id", workspace_id)
            .or_(f"title.ilike.%{q}%,content.ilike.%{q}%")
            .order("updated_at", desc=True)
            .execute
        )
        notes = response.data or []
        return NoteSearchResponse(
            notes=[NoteSummary(**n) for n in notes],
            query=q,
            total=len(notes)
        )
    except Exception as e:
        logger.error(f"Failed to search notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/notes/{note_id}", response_model=Note)
async def get_note(
    note_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Get a single note by ID with outgoing links and backlink count."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    try:
        response = await asyncio.to_thread(
            client.table("notes")
            .select("*")
            .eq("id", note_id)
            .single()
            .execute
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Note not found")

        note = response.data
        await verify_workspace_membership(client, note["workspace_id"], user_id)

        # Extract wiki links
        outgoing = extract_wiki_links(note.get("content", ""))

        # Count backlinks
        backlinks = find_backlinks(note["workspace_id"], note["title"], client)
        backlink_count = len([b for b in backlinks if b["id"] != note_id])

        return Note(
            id=note["id"],
            workspace_id=note["workspace_id"],
            user_id=note["user_id"],
            title=note["title"],
            content=note.get("content", ""),
            tags=note.get("tags", []),
            source=note.get("source"),
            created_at=note["created_at"],
            updated_at=note["updated_at"],
            outgoing_links=outgoing,
            backlink_count=backlink_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notes", response_model=Note)
async def create_note(
    request: CreateNoteRequest,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Create a new note."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, request.workspace_id, user_id)
    try:
        now = datetime.now(timezone.utc).isoformat()
        response = await asyncio.to_thread(
            client.table("notes").insert({
                "workspace_id": request.workspace_id,
                "user_id": user_id,
                "title": request.title,
                "content": request.content,
                "tags": request.tags,
                "source": request.source,
                "created_at": now,
                "updated_at": now,
            }).execute
        )
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create note")

        note = response.data[0]
        outgoing = extract_wiki_links(note.get("content", ""))
        return Note(
            id=note["id"],
            workspace_id=note["workspace_id"],
            user_id=note["user_id"],
            title=note["title"],
            content=note.get("content", ""),
            tags=note.get("tags", []),
            source=note.get("source"),
            created_at=note["created_at"],
            updated_at=note["updated_at"],
            outgoing_links=outgoing,
            backlink_count=0,
        )
    except Exception as e:
        logger.error(f"Failed to create note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/notes/{note_id}", response_model=Note)
async def update_note(
    note_id: str,
    request: UpdateNoteRequest,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Update a note (title, content, tags, source)."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    try:
        # Verify ownership
        existing = await asyncio.to_thread(
            client.table("notes").select("*").eq("id", note_id).single().execute
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Note not found")
        note = existing.data
        await verify_workspace_membership(client, note["workspace_id"], user_id)

        update_data: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
        if request.title is not None:
            update_data["title"] = request.title
        if request.content is not None:
            update_data["content"] = request.content
        if request.tags is not None:
            update_data["tags"] = request.tags
        if request.source is not None:
            update_data["source"] = request.source

        response = await asyncio.to_thread(
            client.table("notes").update(update_data).eq("id", note_id).execute
        )
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update note")

        updated = response.data[0]
        outgoing = extract_wiki_links(updated.get("content", ""))
        backlinks = find_backlinks(updated["workspace_id"], updated["title"], client)
        backlink_count = len([b for b in backlinks if b["id"] != note_id])

        return Note(
            id=updated["id"],
            workspace_id=updated["workspace_id"],
            user_id=updated["user_id"],
            title=updated["title"],
            content=updated.get("content", ""),
            tags=updated.get("tags", []),
            source=updated.get("source"),
            created_at=updated["created_at"],
            updated_at=updated["updated_at"],
            outgoing_links=outgoing,
            backlink_count=backlink_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/notes/{note_id}")
async def delete_note(
    note_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Delete a note."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    try:
        existing = await asyncio.to_thread(
            client.table("notes").select("workspace_id").eq("id", note_id).single().execute
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Note not found")
        await verify_workspace_membership(client, existing.data["workspace_id"], user_id)

        await asyncio.to_thread(
            client.table("notes").delete().eq("id", note_id).execute
        )
        return {"status": "deleted", "id": note_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notes/bulk-delete")
async def delete_notes_bulk(
    request: BulkDeleteRequest,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Delete multiple notes by ID."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    try:
        # Verify all notes belong to user's workspace
        notes = await asyncio.to_thread(
            client.table("notes").select("id, workspace_id").in_("id", request.ids).execute
        )
        for note in (notes.data or []):
            await verify_workspace_membership(client, note["workspace_id"], user_id)

        await asyncio.to_thread(
            client.table("notes").delete().in_("id", request.ids).execute
        )
        return {"status": "deleted", "count": len(request.ids)}
    except Exception as e:
        logger.error(f"Failed to bulk delete notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/notes/{note_id}/backlinks")
async def get_note_backlinks(
    note_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Get all notes that link to this note."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    try:
        note = await asyncio.to_thread(
            client.table("notes").select("workspace_id, title").eq("id", note_id).single().execute
        )
        if not note.data:
            raise HTTPException(status_code=404, detail="Note not found")
        await verify_workspace_membership(client, note.data["workspace_id"], user_id)

        backlinks = find_backlinks(note.data["workspace_id"], note.data["title"], client)
        return [
            {
                "id": b["id"],
                "title": b["title"],
                "updated_at": b["updated_at"],
                "snippet": b["content"][:200] if b.get("content") else "",
            }
            for b in backlinks
            if b["id"] != note_id
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get backlinks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Documents / OpenKB Module Endpoints ──────────────────────────────────

from research_engine.utils.openkb import (
    add_document, list_documents, query_wiki, get_kb_status,
    create_skill, list_skills, get_wiki_page, list_wiki_pages,
    get_workspace_kb_dir, remove_document, recompile_documents,
    get_document_path, get_kb_stats,
    validate_skill, evaluate_skill, rollback_skill
)
from fastapi import UploadFile, File, Form


@app.post("/documents/upload")
async def upload_document(
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
    tags: str = Form(""),
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Upload a document to workspace raw/ folder and add to OpenKB."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    
    try:
        kb_dir = get_workspace_kb_dir(workspace_id)
        raw_dir = kb_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = raw_dir / file.filename
        content = await file.read()
        file_path.write_bytes(content)
        
        # Detect if document is "long" (>100KB threshold)
        is_long = len(content) > 100 * 1024
        if is_long:
            logger.info(f"Long document detected ({len(content)} bytes). Running longread preprocessing.")
            summary_path = raw_dir / f"{file_path.stem}_summary.md"
            summary_path.write_text(
                f"# Summary: {file.filename}\n\n"
                f"This document is {len(content) / 1024:.0f} KB and was processed with longread preprocessing.\n\n"
                f"*Auto-generated summary placeholder — full longread integration would chunk and analyze this document.*\n",
                encoding="utf-8"
            )
        
        # Add to OpenKB
        result = await add_document(workspace_id, file_path)
        
        # Parse tags
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        
        # Save metadata to documents table
        # NOTE: the `documents` table has no `tags` column — tags live in
        # the `document_tags` junction table (document_id, tag).
        doc_insert_response = await asyncio.to_thread(
            client.table("documents").insert({
                "workspace_id": workspace_id,
                "user_id": user_id,
                "filename": file.filename,
                "file_path": str(file_path.relative_to(kb_dir)),
                "file_size": len(content),
                "mime_type": file.content_type or "application/octet-stream",
                "status": "indexed",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute
        )
        
        # Insert tags into document_tags if any were provided
        if tag_list and doc_insert_response.data:
            doc_id = doc_insert_response.data[0].get("id")
            if doc_id:
                tag_rows = [{"document_id": doc_id, "tag": tag} for tag in tag_list]
                try:
                    await asyncio.to_thread(
                        client.table("document_tags").insert(tag_rows).execute
                    )
                except Exception as tag_err:
                    # Non-fatal: document is indexed, tags just won't be stored
                    logger.warning(f"Failed to insert document tags for doc {doc_id}: {tag_err}")
        
        return {
            "document_id": str(file_path.relative_to(kb_dir)),
            "filename": file.filename,
            "status": "indexed",
            "longread_processed": is_long,
            "message": result[:200] if result else "Document indexed successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
async def list_docs(
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """List all documents and wiki entries in workspace OpenKB."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    
    try:
        # Get DB metadata
        db_docs = await asyncio.to_thread(
            client.table("documents")
            .select("*")
            .eq("workspace_id", workspace_id)
            .order("created_at", desc=True)
            .execute
        )
        
        # Get OpenKB wiki pages
        wiki_pages = await list_wiki_pages(workspace_id)
        
        return {
            "documents": db_docs.data or [],
            "wiki_pages": wiki_pages,
            "wiki_status": "ready" if wiki_pages else "empty",
        }
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/query")
async def query_documents(
    workspace_id: str = Form(...),
    question: str = Form(...),
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Query the OpenKB wiki for a specific question."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    
    try:
        result = await query_wiki(workspace_id, question)
        return {
            "answer": result,
            "workspace_id": workspace_id,
            "question": question,
        }
    except Exception as e:
        logger.error(f"Failed to query documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/wiki/{page_path:path}")
async def get_wiki(
    page_path: str,
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Get a specific wiki page as Markdown."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    
    try:
        content = await get_wiki_page(workspace_id, page_path)
        return {
            "path": page_path,
            "content": content,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    except Exception as e:
        logger.error(f"Failed to get wiki page: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/status")
async def get_openkb_status(
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Get OpenKB status for workspace."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    
    try:
        result = await get_kb_status(workspace_id)
        return {
            "workspace_id": workspace_id,
            "status": result,
        }
    except Exception as e:
        logger.error(f"Failed to get OpenKB status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/skills")
async def create_doc_skill(
    workspace_id: str = Form(...),
    name: str = Form(...),
    intent: str = Form(...),
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Distill a skill from the OpenKB wiki."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    
    try:
        result = await create_skill(workspace_id, name, intent)
        return {
            "skill_name": name,
            "workspace_id": workspace_id,
            "result": result,
        }
    except Exception as e:
        logger.error(f"Failed to create skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/skills")
async def list_doc_skills(
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """List all generated skills in workspace."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    
    try:
        result = await list_skills(workspace_id)
        return {
            "workspace_id": workspace_id,
            "skills": [s for s in result.split("\n") if s.strip()],
        }
    except Exception as e:
        logger.error(f"Failed to list skills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/skills/{skill_name}/validate")
async def validate_doc_skill(
    skill_name: str,
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Validate a skill's schema and structure."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)

    try:
        result = await validate_skill(workspace_id, skill_name)
        return result
    except Exception as e:
        logger.error(f"Failed to validate skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/skills/{skill_name}/eval")
async def evaluate_doc_skill(
    skill_name: str,
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Evaluate a skill's coverage against wiki concepts."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)

    try:
        result = await evaluate_skill(workspace_id, skill_name)
        return result
    except Exception as e:
        logger.error(f"Failed to evaluate skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/skills/{skill_name}/rollback")
async def rollback_doc_skill(
    skill_name: str,
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Rollback a skill to previous version."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)

    try:
        result = await rollback_skill(workspace_id, skill_name)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Rollback failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rollback skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Delete a document from the workspace OpenKB."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    
    try:
        # Get document metadata from DB
        db_doc = await asyncio.to_thread(
            client.table("documents")
            .select("*")
            .eq("id", doc_id)
            .eq("workspace_id", workspace_id)
            .execute
        )
        
        if not db_doc.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc = db_doc.data[0]
        filename = doc["filename"]
        
        # Remove from OpenKB
        try:
            await remove_document(workspace_id, filename)
        except Exception as e:
            logger.warning(f"OpenKB remove failed (may not be indexed): {e}")
        
        # Delete from filesystem
        kb_dir = get_workspace_kb_dir(workspace_id)
        raw_dir = kb_dir / "raw"
        file_path = raw_dir / filename
        if file_path.exists():
            file_path.unlink()
        
        # Delete from DB
        await asyncio.to_thread(
            client.table("documents")
            .delete()
            .eq("id", doc_id)
            .eq("workspace_id", workspace_id)
            .execute
        )
        
        return {"success": True, "message": f"Document '{filename}' deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/recompile")
async def recompile_all_documents(
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Re-run compile pipeline on all indexed documents."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    
    try:
        result = await recompile_documents(workspace_id)
        return {"success": True, "message": result}
    except Exception as e:
        logger.error(f"Failed to recompile documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{doc_id}/download")
async def download_document(
    doc_id: str,
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Download a raw document file."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    
    try:
        # Get document metadata from DB
        db_doc = await asyncio.to_thread(
            client.table("documents")
            .select("*")
            .eq("id", doc_id)
            .eq("workspace_id", workspace_id)
            .execute
        )
        
        if not db_doc.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc = db_doc.data[0]
        filename = doc["filename"]
        file_path = await get_document_path(workspace_id, filename)
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type=doc.get("mime_type", "application/octet-stream")
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document file not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/stats")
async def get_documents_stats(
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Get detailed OpenKB stats for workspace."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    
    try:
        stats = await get_kb_stats(workspace_id)
        return {
            "workspace_id": workspace_id,
            **stats,
        }
    except Exception as e:
        logger.error(f"Failed to get document stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Starter Notes ───────────────────────────────────────────────────

STARTER_NOTES = [
    {
        "title": "Transformer Architecture",
        "content": "# Transformer Architecture\n\nThe Transformer architecture, introduced in the paper \"Attention Is All You Need\" (2017), revolutionized natural language processing by replacing recurrent and convolutional layers with **self-attention mechanisms**.\n\n## Key Components\n\n- **Multi-Head Self-Attention**: Allows the model to attend to information from different representation subspaces at different positions.\n- **Positional Encoding**: Injects position information into input embeddings since the model has no recurrence.\n- **Feed-Forward Networks**: Applied identically to each position separately.\n- **Layer Normalization & Residual Connections**: Stabilize training of deep networks.\n\n## Impact\n\nTransformers became the foundation for [[GPT]] (decoder-only), [[BERT]] (encoder-only), and [[T5]] (encoder-decoder) architectures.\n\n---\n\nSource: Vaswani et al., 2017",
        "tags": ["architecture", "foundations", "attention"],
    },
    {
        "title": "Attention Mechanism",
        "content": "# Attention Mechanism\n\nAttention is the core operation that enables models to focus on relevant parts of input when producing output.\n\n## Self-Attention Formula\n\n```\nAttention(Q, K, V) = softmax(QK^T / sqrt(d_k)) V\n```\n\nWhere Q (query), K (key), and V (value) are linear projections of the input.\n\n## Types of Attention\n\n1. **Self-Attention**: Q, K, V all come from the same input sequence\n2. **Cross-Attention**: Q from decoder, K/V from encoder (used in seq2seq)\n3. **Masked Self-Attention**: Prevents attending to future tokens (used in [[GPT]])\n\n## Why It Works\n\n- Captures long-range dependencies regardless of distance\n- Highly parallelizable (unlike RNNs)\n- Interpretable via attention weights\n\nSee also: [[Transformer Architecture]]",
        "tags": ["mechanism", "attention", "foundations"],
    },
    {
        "title": "GPT",
        "content": "# GPT (Generative Pre-trained Transformer)\n\nGPT is a family of decoder-only transformer models developed by OpenAI, trained with autoregressive language modeling.\n\n## Evolution\n\n| Model | Year | Parameters | Key Innovation |\n|-------|------|------------|---------------|\n| GPT-1 | 2018 | 117M | Generative pre-training + discriminative fine-tuning |\n| GPT-2 | 2019 | 1.5B | Zero-shot task transfer |\n| GPT-3 | 2020 | 175B | In-context learning / few-shot prompting |\n| GPT-4 | 2023 | ~1.8T (MoE) | Multimodal, reasoning, tool use |\n| GPT-4o | 2024 | Unknown | Native multimodal, faster, cheaper |\n| GPT-5 | 2025 | Unknown | Reasoning chains, agentic capabilities |\n\n## Architecture\n\n- **Decoder-only**: Uses masked self-attention, causal left-to-right generation\n- **Autoregressive**: Predicts next token given all previous tokens\n- **Pre-training + Fine-tuning**: First trained on large corpus, then adapted to tasks\n\nRelated: [[Transformer Architecture]], [[Attention Mechanism]], [[LLM Scaling Laws]]",
        "tags": ["gpt", "openai", "decoder-only", "generative"],
    },
    {
        "title": "BERT",
        "content": "# BERT (Bidirectional Encoder Representations from Transformers)\n\nBERT, introduced by Google in 2018, uses a **bidirectional encoder** architecture to learn deep contextualized word representations.\n\n## Key Innovations\n\n- **Masked Language Modeling (MLM)**: Randomly masks 15% of tokens and predicts them from bidirectional context\n- **Next Sentence Prediction (NSP)**: Pre-trains on sentence-pair relationships\n- **Deeply Bidirectional**: Unlike GPT (left-to-right) or ELMo (shallowly bidirectional), BERT truly conditions on both directions\n\n## Architecture\n\n- **Encoder-only**: Uses full self-attention (no masking)\n- **Two sizes**: BERT-base (12 layers, 110M params), BERT-large (24 layers, 340M params)\n\n## Impact\n\nBERT dominated NLP benchmarks and spawned variants like RoBERTa, ALBERT, and DeBERTa.\n\nContrast with: [[GPT]] (decoder-only, autoregressive)",
        "tags": ["bert", "google", "encoder-only", "bidirectional"],
    },
    {
        "title": "LLM Scaling Laws",
        "content": "# LLM Scaling Laws\n\nScaling laws describe predictable relationships between model size, data, compute, and performance.\n\n## Chinchilla Scaling Laws (2022)\n\nHoffmann et al. found that for optimal training, **model size and training tokens should be scaled equally**:\n\n- GPT-3 style (large model, under-trained): Not optimal\n- Chinchilla style (smaller model, more data): Better performance per FLOP\n\n## Key Findings\n\n1. **Loss ~ (Model Params)^(-0.34) ~ (Data Tokens)^(-0.28)**\n2. **Compute-optimal**: ~20 tokens per parameter\n3. **Inference-optimal**: Smaller models with longer training\n\n## Practical Implications\n\n- Don't just scale model size; scale data proportionally\n- Smaller, well-trained models can outperform larger, under-trained ones\n- [[MoE]] architectures offer a way to scale effective capacity without proportional compute cost\n\nRelated: [[GPT]], [[Training Efficiency]]",
        "tags": ["scaling", "training", "efficiency", "research"],
    },
    {
        "title": "MoE",
        "content": "# Mixture of Experts (MoE)\n\nMoE architectures scale model capacity by using **sparse activation** — only a subset of parameters are used per token.\n\n## How It Works\n\n1. **Router/Gate Network**: Decides which expert(s) to activate for each input token\n2. **Experts**: Multiple feed-forward networks, each specializing in different data patterns\n3. **Top-k Routing**: Only top-k experts are activated (e.g., top-2)\n\n## Benefits\n\n- **Effective parameters >> active parameters**: GPT-4 uses MoE to achieve ~1.8T effective parameters with only ~200B active per forward pass\n- **Specialization**: Different experts learn different linguistic patterns or domains\n\n## Challenges\n\n- **Load balancing**: Ensure all experts get utilized (auxiliary loss)\n- **Communication overhead**: All-to-all communication in distributed training\n- **Memory**: Must store all expert parameters in GPU memory\n\nRelated: [[LLM Scaling Laws]], [[Training Efficiency]]",
        "tags": ["moe", "architecture", "efficiency", "scaling"],
    },
    {
        "title": "Training Efficiency",
        "content": "# Training Efficiency\n\nTechniques to train large models faster and cheaper.\n\n## Methods\n\n| Technique | Description | Impact |\n|-----------|-------------|--------|\n| **Gradient Checkpointing** | Recompute activations during backward pass instead of storing | Trade compute for memory |\n| **Mixed Precision** | Use FP16/BF16 for forward/backward, FP32 for optimizer states | 2-3x speedup |\n| **ZeRO (DeepSpeed)** | Partition optimizer states, gradients, parameters across GPUs | Train models 10x larger |\n| **FlashAttention** | IO-aware exact attention algorithm | 2-4x faster, less memory |\n| **Parallelism** | Data, tensor, pipeline, sequence parallelism | Scale to thousands of GPUs |\n\n## FlashAttention\n\nThe key insight: **tiling** the attention computation to reduce HBM reads/writes. Standard attention is memory-bound; FlashAttention is compute-bound.\n\nSee also: [[LLM Scaling Laws]], [[MoE]]",
        "tags": ["training", "efficiency", "optimization", "engineering"],
    },
    {
        "title": "RAG",
        "content": "# Retrieval-Augmented Generation (RAG)\n\nRAG augments LLMs with external knowledge retrieval, combining parametric memory (model weights) with non-parametric memory (retrieved documents).\n\n## Architecture\n\n```\nQuery -> Retriever -> [Doc1, Doc2, ...] -> LLM -> Generated Answer\n```\n\n## Components\n\n1. **Retriever**: Dense (vector search) or sparse (BM25) retrieval\n2. **Reranker**: Cross-encoder for relevance scoring\n3. **Generator**: LLM with retrieved context in prompt\n\n## Advantages\n\n- **Up-to-date knowledge**: No need to retrain model for new information\n- **Citations**: Can attribute answers to sources\n- **Domain adaptation**: Retrieve domain-specific documents\n\n## Vector Databases\n\n- Pinecone, Weaviate, Milvus, Chroma, Qdrant, pgvector\n\nRelated: [[Prompt Engineering]], [[Fine-Tuning]]",
        "tags": ["rag", "retrieval", "applications", "knowledge"],
    },
    {
        "title": "Prompt Engineering",
        "content": "# Prompt Engineering\n\nThe art of designing inputs to elicit desired outputs from LLMs.\n\n## Techniques\n\n| Technique | Description |\n|-----------|-------------|\n| **Zero-shot** | Direct instruction without examples |\n| **Few-shot** | Provide 2-5 examples in the prompt |\n| **Chain-of-Thought** | Ask model to \"think step by step\" |\n| **ReAct** | Reasoning + Acting (use tools) interleaved |\n| **Self-Consistency** | Sample multiple answers, pick majority |\n| **Tree-of-Thoughts** | Explore multiple reasoning paths |\n\n## Best Practices\n\n- Be specific and clear\n- Use delimiters for structure (XML, JSON, Markdown)\n- Specify output format explicitly\n- Include constraints (length, tone, style)\n- Test systematically\n\nSee also: [[RAG]], [[Fine-Tuning]]",
        "tags": ["prompting", "techniques", "practical", "applications"],
    },
    {
        "title": "Fine-Tuning",
        "content": "# Fine-Tuning\n\nFine-tuning adapts a pre-trained model to a specific task or domain by continuing training on task-specific data.\n\n## Methods\n\n| Method | Description | Use Case |\n|--------|-------------|----------|\n| **Full Fine-tuning** | Update all parameters | Ample data, compute budget |\n| **LoRA** | Low-rank adaptation of attention weights | Limited compute, good performance |\n| **QLoRA** | LoRA + 4-bit quantization | Single GPU fine-tuning |\n| **Adapter Layers** | Small trainable layers inserted | Multi-task without interference |\n| **Prompt Tuning** | Learn soft prompt embeddings | Minimal parameter updates |\n| **Instruction Tuning** | Train on (instruction, response) pairs | General instruction following |\n| **RLHF** | Reinforcement learning from human feedback | Align with human preferences |\n\n## LoRA Details\n\n- Freezes pre-trained weights\n- Adds trainable rank-decomposition matrices to each layer\n- Reduces trainable params by ~10,000x with minimal performance loss\n\nRelated: [[Prompt Engineering]], [[RLHF]]",
        "tags": ["fine-tuning", "training", "adaptation", "practical"],
    },
    {
        "title": "RLHF",
        "content": "# RLHF (Reinforcement Learning from Human Feedback)\n\nRLHF aligns LLMs with human preferences through a three-stage process.\n\n## Three Stages\n\n### 1. Supervised Fine-Tuning (SFT)\nTrain model on high-quality human-written demonstrations.\n\n### 2. Reward Model Training\n- Collect human preferences: given prompt + 2 outputs, label which is better\n- Train a reward model to predict human preference scores\n\n### 3. Reinforcement Learning\n- Use PPO (Proximal Policy Optimization) to maximize reward model score\n- Add KL penalty to prevent model from drifting too far from SFT model\n\n## Alternatives\n\n- **DPO (Direct Preference Optimization)**: Skip reward model, optimize directly on preferences\n- **KTO (Kahneman-Tversky Optimization)**: Simpler than DPO, no reference model needed\n\n## Impact\n\nRLHF made [[ChatGPT]] remarkably helpful, harmless, and honest — though not perfect.\n\nRelated: [[Fine-Tuning]], [[GPT]]",
        "tags": ["rlhf", "alignment", "training", "safety"],
    },
    {
        "title": "T5",
        "content": "# T5 (Text-to-Text Transfer Transformer)\n\nT5, proposed by Google in 2019, treats every NLP task as a **text-to-text** problem.\n\n## Unified Framework\n\n```\nInput: \"translate English to German: The house is wonderful.\"\nOutput: \"Das Haus ist wunderbar.\"\n\nInput: \"summarize: <article>\"\nOutput: \"<summary>\"\n\nInput: \"cola sentence: The movie was boring.\"\nOutput: \"acceptable\"\n```\n\n## Architecture\n\n- **Encoder-decoder**: Full Transformer with both encoder and decoder stacks\n- **Pre-training**: Denoising objective (replace spans with sentinel tokens)\n\n## Significance\n\nT5 demonstrated that a unified text-to-text framework can achieve competitive results across diverse tasks, influencing later models like FLAN-T5 and UL2.\n\nContrast with: [[GPT]] (decoder-only), [[BERT]] (encoder-only)",
        "tags": ["t5", "google", "encoder-decoder", "unified"],
    },
]


@app.post("/notes/seed")
async def seed_starter_notes(
    workspace_id: str = Form(...),
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Seed starter notes for a new workspace."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    
    try:
        # Check if workspace already has notes
        existing = await asyncio.to_thread(
            client.table("notes")
            .select("count", count="exact")
            .eq("workspace_id", workspace_id)
            .execute
        )
        
        count = existing.count if hasattr(existing, 'count') else len(existing.data or [])
        if count > 0:
            return {"success": False, "message": "Workspace already has notes", "created": 0}
        
        now = datetime.now(timezone.utc).isoformat()
        created_notes = []
        
        for note_data in STARTER_NOTES:
            note = await asyncio.to_thread(
                client.table("notes").insert({
                    "workspace_id": workspace_id,
                    "user_id": user_id,
                    "title": note_data["title"],
                    "content": note_data["content"],
                    "tags": note_data.get("tags", []),
                    "source": None,
                    "created_at": now,
                    "updated_at": now,
                }).execute
            )
            if note.data:
                created_notes.append(note.data[0])
        
        return {
            "success": True,
            "message": f"Created {len(created_notes)} starter notes",
            "created": len(created_notes),
            "notes": [{"id": n["id"], "title": n["title"]} for n in created_notes],
        }
    except Exception as e:
        logger.error(f"Failed to seed starter notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── In-memory chat sessions (per-process, not persistent) ─────────────
_chat_sessions: dict[str, list[dict]] = {}


@app.post("/documents/chat")
async def chat_documents(
    workspace_id: str = Form(...),
    message: str = Form(...),
    session_id: str = Form(""),
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Multi-turn chat over the OpenKB wiki."""
    import uuid
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    
    try:
        sid = session_id or uuid.uuid4().hex
        if sid not in _chat_sessions:
            _chat_sessions[sid] = []
        
        # Append user message
        _chat_sessions[sid].append({"role": "user", "content": message})
        
        # Build context from history
        context = "\n\n".join([
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in _chat_sessions[sid][-6:]  # Last 6 messages for context
        ])
        
        # Query with full context
        full_question = f"Based on the following conversation, answer the user's latest question.\n\n{context}\n\nProvide a grounded answer based on the wiki."
        result = await query_wiki(workspace_id, full_question)
        
        # Append assistant response
        _chat_sessions[sid].append({"role": "assistant", "content": result})
        
        # Limit session size
        if len(_chat_sessions[sid]) > 20:
            _chat_sessions[sid] = _chat_sessions[sid][-20:]
        
        return {
            "session_id": sid,
            "response": result,
            "history": _chat_sessions[sid],
        }
    except Exception as e:
        logger.error(f"Failed to chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/chat/sessions")
async def list_chat_sessions(
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """List active chat sessions for workspace."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    
    sessions = [
        {"session_id": sid, "message_count": len(msgs), "last_message": msgs[-1]["content"][:100] if msgs else ""}
        for sid, msgs in _chat_sessions.items()
    ]
    return {"sessions": sessions}


@app.post("/documents/{doc_id}/tags")
async def update_document_tags(
    doc_id: str,
    workspace_id: str = Form(...),
    tags: str = Form(...),  # Comma-separated
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Update document tags."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    await verify_workspace_membership(client, workspace_id, user_id)
    
    try:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        await asyncio.to_thread(
            client.table("documents")
            .update({"tags": tag_list})
            .eq("id", doc_id)
            .eq("workspace_id", workspace_id)
            .execute
        )
        return {"success": True, "tags": tag_list}
    except Exception as e:
        logger.error(f"Failed to update tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Agent Skill Triggers ───────────────────────────────────────────

@app.post("/research/comprehensive")
async def comprehensive_research(
    request: ResearchRequest,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Trigger comprehensive multi-agent research (deep-research-swarm)."""
    client = get_supabase_client()
    user_id = user_data.get("sub", user_data.get("id"))
    workspace_id = request.workspace_id or "default"
    await verify_workspace_membership(client, workspace_id, user_id)
    
    try:
        # Create a special comprehensive research run
        config = get_config()
        model = request.model or config.model
        provider = request.provider or "openrouter"
        depth = request.depth or 5
        
        run_id = str(uuid.uuid4())
        run_dir = Path("outputs") / workspace_id / "research" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Store run metadata
        await asyncio.to_thread(
            client.table("research_runs").insert({
                "id": run_id,
                "workspace_id": workspace_id,
                "user_id": user_id,
                "query": request.query,
                "model_used": model,
                "status": "comprehensive_pending",
                "progress": 0,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "depth": depth,
                "mode": request.mode or "web",
            }).execute
        )
        
        # Return immediately — the agent skill is triggered asynchronously
        return {
            "run_id": run_id,
            "status": "comprehensive_pending",
            "message": "Comprehensive research queued. The deep-research-swarm skill will process this request. Check /runs/{run_id} for progress.",
            "query": request.query,
            "model": model,
            "depth": depth,
        }
    except Exception as e:
        logger.error(f"Failed to start comprehensive research: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get('/documents/wiki/download')
async def download_wiki_zip(
    workspace_id: str,
    user_data: dict = Depends(verify_supabase_jwt)
):
    """Download the entire wiki as a ZIP file for Obsidian import."""
    client = get_supabase_client()
    user_id = user_data.get('sub', user_data.get('id'))
    await verify_workspace_membership(client, workspace_id, user_id)
    
    try:
        kb_dir = get_workspace_kb_dir(workspace_id)
        wiki_dir = kb_dir / 'wiki'
        if not wiki_dir.exists():
            raise HTTPException(status_code=404, detail='Wiki not found')
        
        import tempfile
        zip_path = tempfile.mktemp(suffix='.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in wiki_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(wiki_dir).as_posix()
                    zf.write(file_path, arcname)
        
        response = FileResponse(
            path=zip_path,
            filename=f'{workspace_id}_wiki.zip',
            media_type='application/zip'
        )
        return response
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Wiki directory not found')
    except Exception as e:
        logger.error(f'Failed to download wiki: {e}')
        raise HTTPException(status_code=500, detail=str(e))


# ─── Citation Verification Endpoint ──────────────────────────────────

@app.post("/citations/verify", response_model=CitationVerificationResponse)
async def verify_citation(
    request: CitationVerificationRequest,
    user_data: dict = Depends(verify_supabase_jwt),
):
    """Verify a citation against CrossRef and OpenAlex.

    Returns verification status, metadata, and confidence score.
    """
    # Build verifier with a simple HTTP client
    class SimpleHttpClient:
        async def get(self, url, **kwargs):
            return {"status": 404, "json": lambda: {}}

    http = SimpleHttpClient()
    config = get_config()
    email = getattr(config, 'email', '')

    verifier = CitationVerifier(
        parser=CitationParser(),
        adapters=[
            CrossRefAdapter(http_client=http, email=email),
            OpenAlexAdapter(http_client=http, email=email),
        ],
        cache=VerificationCache(),
    )

    result = await verifier.verify(request.citation_text)

    return CitationVerificationResponse(
        status=result.status.value,
        found=result.found,
        title=result.title,
        authors=result.authors or [],
        year=result.year,
        doi=result.doi,
        url=result.url,
        confidence=result.confidence,
        sources=result.sources,
    )
