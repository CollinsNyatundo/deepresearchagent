#!/usr/bin/env python3
"""Quick DB verification test — runs one short research and verifies DB save."""
import asyncio
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root

from research_engine.agent.orchestrator import DeepResearchOrchestrator
from research_engine.config import get_config
from research_engine.db.supabase.client import get_supabase_client
from research_engine.models import ResearchMode, ResearchRequest


async def main():
    config = get_config()
    # Override max_cycles for quick test
    config.research.max_cycles = 3

    orchestrator = DeepResearchOrchestrator(config)
    request = ResearchRequest(
        query="renewable energy storage 2025",
        model="nvidia/nemotron-3-super-120b-a12b",
        depth=1,
        max_pages=2,
        enable_crossover=False,
        provider="nvidia",
        mode=ResearchMode.WEB,
        workspace_id="11111111-1111-1111-1111-111111111111",
    )

    logger.info("Starting quick test run with max_cycles=3")
    result = await orchestrator.run(request)

    logger.info(f"Run completed: {result.run_id}")
    logger.info(f"Cycles: {len(result.steps)}, Citations: {len(result.citations)}")

    # Save to DB
    client = get_supabase_client()
    run_record = {
        "id": result.run_id,
        "workspace_id": "11111111-1111-1111-1111-111111111111",
        "user_id": None,
        "query": result.query,
        "model_used": result.model_used,
        "status": "complete",
        "progress": result.progress or 100,
        "started_at": result.started_at.isoformat(),
        "completed_at": result.completed_at.isoformat(),
        "depth": 1,
        "mode": "web",
        "report": result.report[:50000],
        "citations": [{**c.model_dump(), "accessed_at": c.accessed_at.isoformat() if hasattr(c, "accessed_at") and c.accessed_at else None} for c in result.citations[:100]],
        "sources": [c.url for c in result.citations[:100]],
        "total_cycles": len(result.steps),
    }

    try:
        client.table("research_runs").upsert(run_record).execute()
        logger.info("Saved to DB successfully")
    except Exception as e:
        logger.error(f"DB save failed: {e}")

    # Verify
    res = client.table("research_runs").select("*").eq("id", result.run_id).execute()
    if res.data:
        logger.info(f"DB verification: Found run with {len(res.data[0].get('citations', []))} citations")
    else:
        logger.error("DB verification: Run NOT found")

if __name__ == "__main__":
    asyncio.run(main())
