"""GitNexus background scheduler.

Runs two periodic tasks for *every repo* that is currently indexed in the
GitNexus eval-server:
1. `npx gitnexus analyze` — re-indexes the codebase (default: every 30 min)
2. `build_and_save(repo)` — refreshes outputs/gitnexus_graph_{repo}.json

The scheduler discovers available repos dynamically from the eval-server
/health endpoint, so adding a new repo to GitNexus is automatically picked up
on the next scheduled run — no code change required.

Usage:
    from research_engine.gitnexus_scheduler import start_scheduler, stop_scheduler

    # Call at FastAPI startup:
    lifespan context → start_scheduler()
    # Call at shutdown:
    stop_scheduler()
"""

from __future__ import annotations

import asyncio
import logging
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

# Path to the project root (two levels up from this file)
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
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)

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


async def _refresh_all_repos() -> None:
    """Re-index then rebuild cached graphs for every indexed repo.

    Repo list is discovered dynamically from the eval-server /health endpoint
    so new repos are picked up automatically on the next scheduled run.
    """
    await _run_gitnexus_analyze()

    from research_engine.knowledge_graph.gitnexus_bridge import (
        build_and_save,
        is_eval_server_running,
        list_indexed_repos,
    )

    if not await is_eval_server_running():
        logger.warning(
            "[gitnexus-scheduler] Eval-server not running — skipping graph refresh. "
            "Start it with: npx gitnexus eval-server --port 4848"
        )
        return

    repos = await list_indexed_repos()
    if not repos:
        logger.warning("[gitnexus-scheduler] No repos found in eval-server — nothing to refresh.")
        return

    logger.info("[gitnexus-scheduler] Refreshing graphs for repos: %s", repos)
    for repo in repos:
        try:
            path = await build_and_save(repo)
            logger.info("[gitnexus-scheduler] Graph for '%s' saved → %s", repo, path)
        except Exception as e:
            logger.error("[gitnexus-scheduler] Graph refresh failed for '%s': %s", repo, e)


async def refresh_repo(repo_name: str) -> Path:
    """Manually trigger a graph rebuild for a single *repo_name*.

    Called by the POST /gitnexus/analyze?repo=X API endpoint.
    Returns the path of the saved graph file.
    """
    from research_engine.knowledge_graph.gitnexus_bridge import build_and_save
    return await build_and_save(repo_name)


def start_scheduler(interval_minutes: int = 30) -> None:
    """Start the APScheduler background scheduler.

    Args:
        interval_minutes: How often to re-index and refresh all repo graphs.
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
        _refresh_all_repos,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="gitnexus_refresh",
        name="GitNexus graph refresh (all repos)",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info(
        "[gitnexus-scheduler] Scheduler started — refreshing all repos every %d minutes.",
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
