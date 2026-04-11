"""GitNexus background scheduler.

Runs two periodic tasks:
1. `npx gitnexus analyze` — re-indexes the codebase (default: every 30 min)
2. `build_and_save()` — refreshes gitnexus_graph.json right after indexing

Usage:
    from research_engine.gitnexus_scheduler import start_scheduler, stop_scheduler

    # Call at FastAPI startup:
    lifespan context → start_scheduler()
    # Call at shutdown:
    stop_scheduler()

The scheduler is non-blocking (runs in thread-pool via APScheduler AsyncIOScheduler).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# APScheduler optional import guard
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    _APScheduler_available = True
except ImportError:
    _APScheduler_available = False
    logger.warning(
        "apscheduler not installed — GitNexus background scheduling disabled. "
        "Run: pip install apscheduler"
    )

_scheduler: "AsyncIOScheduler | None" = None  # type: ignore[name-defined]

# Path to the DeepResearchAgent project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).parent.parent.parent


async def _run_gitnexus_analyze() -> None:
    """Run `npx gitnexus analyze` as an async subprocess."""
    logger.info("[gitnexus-scheduler] Running npx gitnexus analyze …")
    try:
        proc = await asyncio.create_subprocess_exec(
            "npx", "gitnexus", "analyze",
            cwd=str(_PROJECT_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)  # 10-min cap

        if proc.returncode == 0:
            logger.info("[gitnexus-scheduler] analyze completed successfully.")
        else:
            logger.warning(
                "[gitnexus-scheduler] analyze exited %d: %s",
                proc.returncode,
                stderr.decode(errors="replace")[:500],
            )
    except asyncio.TimeoutError:
        logger.error("[gitnexus-scheduler] analyze timed out after 10 minutes.")
    except Exception as e:
        logger.error("[gitnexus-scheduler] analyze failed: %s", e)


async def _refresh_graph() -> None:
    """Re-index then rebuild the cached gitnexus_graph.json."""
    await _run_gitnexus_analyze()

    # Only refresh the cached graph if the eval-server is running
    from research_engine.knowledge_graph.gitnexus_bridge import (
        build_and_save,
        is_eval_server_running,
    )

    if await is_eval_server_running():
        try:
            path = await build_and_save()
            logger.info("[gitnexus-scheduler] Graph refreshed at %s", path)
        except Exception as e:
            logger.error("[gitnexus-scheduler] Graph refresh failed: %s", e)
    else:
        logger.warning(
            "[gitnexus-scheduler] Eval-server not running — skipping graph refresh. "
            "Start it with: npx gitnexus eval-server --port 4848"
        )


def start_scheduler(interval_minutes: int = 30) -> None:
    """Start the APScheduler background scheduler.

    Args:
        interval_minutes: How often to re-index and refresh the graph.
            Default is 30 minutes.
    """
    global _scheduler

    if not _APScheduler_available:
        logger.warning("[gitnexus-scheduler] APScheduler unavailable — scheduler not started.")
        return

    if _scheduler is not None and _scheduler.running:
        logger.info("[gitnexus-scheduler] Scheduler already running.")
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _refresh_graph,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="gitnexus_refresh",
        name="GitNexus graph refresh",
        replace_existing=True,
        max_instances=1,  # Prevent overlap
    )
    _scheduler.start()
    logger.info(
        "[gitnexus-scheduler] Scheduler started — refresh every %d minutes.",
        interval_minutes,
    )


def stop_scheduler() -> None:
    """Gracefully stop the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[gitnexus-scheduler] Scheduler stopped.")
    _scheduler = None


def is_scheduler_running() -> bool:
    """Return True if the background scheduler is active."""
    return _scheduler is not None and _scheduler.running
