#!/usr/bin/env python3
"""End-to-end test script for Deep Research Agent with real LLM calls and DB persistence.

Runs actual research queries using configured providers and verifies DB population.
"""

import asyncio
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from research_engine.agent.orchestrator import DeepResearchOrchestrator
from research_engine.config import get_config
from research_engine.db.supabase.client import get_supabase_client
from research_engine.models import ResearchMode, ResearchRequest


TEST_WORKSPACE_ID = "11111111-1111-1111-1111-111111111111"
TEST_USER_ID = "22222222-2222-2222-2222-222222222222"


def ensure_test_workspace():
    """Create test workspace and membership if they don't exist."""
    client = get_supabase_client()
    
    # Check if workspace exists
    res = client.table("workspaces").select("*").eq("id", TEST_WORKSPACE_ID).execute()
    if not res.data:
        logger.info(f"Creating test workspace: {TEST_WORKSPACE_ID}")
        client.table("workspaces").insert({
            "id": TEST_WORKSPACE_ID,
            "name": "E2E Test Workspace",
        }).execute()
    
    # Check membership
    member_res = client.table("workspace_members").select("*").eq("workspace_id", TEST_WORKSPACE_ID).eq("user_id", TEST_USER_ID).execute()
    if not member_res.data:
        logger.info(f"Adding test user to workspace")
        client.table("workspace_members").insert({
            "workspace_id": TEST_WORKSPACE_ID,
            "user_id": TEST_USER_ID,
        }).execute()


def verify_db_state(run_id: str) -> dict:
    """Verify the research run exists in the DB with all expected fields."""
    client = get_supabase_client()
    
    res = client.table("research_runs").select("*").eq("id", run_id).execute()
    if not res.data:
        return {"found": False, "error": "Run not found in DB"}
    
    run = res.data[0]
    checks = {
        "found": True,
        "has_id": bool(run.get("id")),
        "has_query": bool(run.get("query")),
        "has_model_used": bool(run.get("model_used")),
        "has_status": bool(run.get("status")),
        "has_started_at": bool(run.get("started_at")),
        "has_workspace_id": bool(run.get("workspace_id")),
        "has_user_id": bool(run.get("user_id")),
        "has_depth": run.get("depth") is not None,
        "has_mode": bool(run.get("mode")),
    }
    
    # Check graph nodes/edges
    nodes_res = client.table("graph_nodes").select("count").eq("run_id", run_id).execute()
    edges_res = client.table("graph_edges").select("count").eq("run_id", run_id).execute()
    
    checks["graph_nodes_count"] = len(nodes_res.data) if nodes_res.data else 0
    checks["graph_edges_count"] = len(edges_res.data) if edges_res.data else 0
    
    return checks


async def run_test(
    query: str,
    model: str | None,
    provider: str | None,
    depth: int = 1,
    max_pages: int = 2,
) -> dict:
    """Run a single research test and save to DB."""
    logger.info(f"\n{'='*60}")
    logger.info(f"TEST: {query}")
    logger.info(f"Model: {model}, Provider: {provider}, Depth: {depth}")
    logger.info(f"{'='*60}")
    
    config = get_config()
    orchestrator = DeepResearchOrchestrator(config)
    
    request = ResearchRequest(
        query=query,
        model=model,
        depth=depth,
        max_pages=max_pages,
        enable_crossover=False,
        provider=provider,
        mode=ResearchMode.WEB,
        workspace_id=TEST_WORKSPACE_ID,
    )
    
    started = time.time()
    try:
        result = await orchestrator.run(request)
        duration = time.time() - started
        
        logger.info(f"Run completed in {duration:.1f}s")
        logger.info(f"Run ID: {result.run_id}")
        logger.info(f"Cycles: {len(result.steps)}")
        logger.info(f"Citations: {len(result.citations)}")
        logger.info(f"Report length: {len(result.report)} chars")
        
        # Save to Supabase DB
        client = get_supabase_client()
        run_record = {
            "id": result.run_id,
            "workspace_id": TEST_WORKSPACE_ID,
            "user_id": TEST_USER_ID,
            "query": result.query,
            "model_used": result.model_used,
            "status": "complete",
            "progress": result.progress or 100,
            "started_at": result.started_at.isoformat(),
            "completed_at": result.completed_at.isoformat(),
            "depth": depth,
            "mode": "web",
            "report": result.report[:50000],  # Truncate for DB
            "citations": [
                {**c.model_dump(), "accessed_at": c.accessed_at.isoformat() if hasattr(c, "accessed_at") and c.accessed_at else None}
                for c in result.citations[:100]
            ],
            "sources": [c.url for c in result.citations[:100]],
            "total_cycles": len(result.steps),
        }
        
        try:
            client.table("research_runs").upsert(run_record).execute()
            logger.info(f"Saved run to DB: {result.run_id}")
        except Exception as e:
            logger.error(f"Failed to save run to DB: {e}")
        
        # Verify DB state
        db_checks = verify_db_state(result.run_id)
        logger.info(f"DB verification: {db_checks}")
        
        return {
            "success": True,
            "run_id": result.run_id,
            "duration": duration,
            "cycles": len(result.steps),
            "citations": len(result.citations),
            "db_checks": db_checks,
        }
        
    except Exception as e:
        duration = time.time() - started
        logger.error(f"Run failed after {duration:.1f}s: {e}")
        return {
            "success": False,
            "error": str(e),
            "duration": duration,
        }


async def main():
    """Run end-to-end tests with different providers."""
    ensure_test_workspace()
    
    results = []
    
    # Test 1: NVIDIA direct API (since OpenRouter key is returning 401)
    logger.info("Starting Test 1: NVIDIA Nemotron direct API")
    r1 = await run_test(
        query="latest advancements in solar panel efficiency 2025",
        model="nvidia/nemotron-3-super-120b-a12b",
        provider="nvidia",
        depth=1,
        max_pages=2,
    )
    results.append(("NVIDIA Nemotron", r1))
    
    # Test 2: NVIDIA with a different topic
    logger.info("Starting Test 2: NVIDIA Nemotron - AI agents")
    await asyncio.sleep(5)  # Rate limit buffer
    r2 = await run_test(
        query="AI agent architectures comparison",
        model="nvidia/nemotron-3-super-120b-a12b",
        provider="nvidia",
        depth=1,
        max_pages=2,
    )
    results.append(("NVIDIA AI Agents", r2))
    
    # Test 3: NVIDIA with edge computing topic
    logger.info("Starting Test 3: NVIDIA Nemotron - Edge computing")
    await asyncio.sleep(5)
    r3 = await run_test(
        query="edge computing vs cloud computing tradeoffs",
        model="nvidia/nemotron-3-super-120b-a12b",
        provider="nvidia",
        depth=1,
        max_pages=2,
    )
    results.append(("NVIDIA Edge Computing", r3))
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*60}")
    for name, result in results:
        status = "PASS" if result.get("success") else "FAIL"
        logger.info(f"{name}: {status}")
        if result.get("success"):
            logger.info(f"  Run ID: {result['run_id']}")
            logger.info(f"  Duration: {result['duration']:.1f}s")
            logger.info(f"  Cycles: {result['cycles']}")
            logger.info(f"  Citations: {result['citations']}")
        else:
            logger.info(f"  Error: {result.get('error')}")
    
    # Count DB records
    client = get_supabase_client()
    db_res = client.table("research_runs").select("*").eq("workspace_id", TEST_WORKSPACE_ID).execute()
    logger.info(f"\nTotal runs in DB for test workspace: {len(db_res.data)}")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
