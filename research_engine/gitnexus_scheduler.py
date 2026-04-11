"""GitNexus background scheduler — pure asyncio, zero extra dependencies.

Runs two periodic tasks for *every repo* currently indexed in the GitNexus
eval-server:
  1. ``npx gitnexus analyze``  — re-indexes the codebase
  2. ``build_and_save(repo)``  — refreshes outputs/gitnexus_graph_{repo}.json

The scheduler discovers repos dynamically from the eval-server /health
endpoint, so new repos are picked up automatically — no code change needed.

Public API (unchanged from the APScheduler version):
    from research_engine.gitnexus_scheduler import start_scheduler, stop_scheduler

    # FastAPI lifespan:
    start_scheduler(interval_minutes=30)   # non-blocking, spawns asyncio task
    stop_scheduler()                       # cancels the task

No apscheduler, no celery, no extra packages — runs anywhere Python 3.11+ does.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to the project root
_PROJECT_ROOT = Path(__file__).parent.parent

# On Windows, npx is a .cmd script — must be invoked via cmd /c.
# On Linux/macOS it is a plain executable on PATH.
def _npx(*args: str) -> list[str]:
    """Return the correct command list to invoke npx on any platform."""
    if sys.platform == "win32":
        return ["cmd", "/c", "npx", *args]
    return ["npx", *args]

# The single background asyncio.Task — None when stopped
_task: asyncio.Task | None = None


# ─── Core refresh logic ───────────────────────────────────────────────────────

async def _run_gitnexus_analyze() -> None:
    """Run ``npx gitnexus analyze`` as an async subprocess (max 10 min)."""
    logger.info("[gitnexus-scheduler] Running npx gitnexus analyze …")
    try:
        proc = await asyncio.create_subprocess_exec(
            *_npx("gitnexus", "analyze"),
            cwd=str(_PROJECT_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
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
    except Exception as exc:
        logger.error("[gitnexus-scheduler] analyze failed: %s", exc)


async def _refresh_all_repos() -> None:
    """Re-index then rebuild cached graphs for every indexed repo."""
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
        except Exception as exc:
            logger.error("[gitnexus-scheduler] Graph refresh failed for '%s': %s", repo, exc)


# ─── Background loop ──────────────────────────────────────────────────────────

async def _scheduler_loop(interval_seconds: int) -> None:
    """Infinite loop: sleep → refresh → repeat.

    The first run fires immediately (no initial delay) so the graph cache is
    warm from the moment the server starts.
    """
    logger.info(
        "[gitnexus-scheduler] Background task started — interval: %ds (%d min).",
        interval_seconds,
        interval_seconds // 60,
    )
    while True:
        try:
            await _refresh_all_repos()
        except asyncio.CancelledError:
            raise  # propagate — this is how the task is stopped
        except Exception as exc:
            # Never crash the loop on unexpected errors
            logger.error("[gitnexus-scheduler] Unexpected error in refresh loop: %s", exc)

        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            break  # clean exit when stop_scheduler() cancels the task

    logger.info("[gitnexus-scheduler] Background task stopped.")


# ─── Public API ───────────────────────────────────────────────────────────────

def start_scheduler(interval_minutes: int = 30) -> None:
    """Spawn the background refresh task.

    Safe to call from a sync context (FastAPI lifespan) — internally calls
    ``asyncio.get_event_loop().create_task()``.

    Args:
        interval_minutes: Seconds between full refresh cycles. Default: 30 min.
    """
    global _task  # noqa: PLW0603

    if _task is not None and not _task.done():
        logger.info("[gitnexus-scheduler] Scheduler already running.")
        return

    interval_seconds = interval_minutes * 60

    try:
        loop = asyncio.get_event_loop()
        _task = loop.create_task(
            _scheduler_loop(interval_seconds),
            name="gitnexus_refresh",
        )
        logger.info(
            "[gitnexus-scheduler] Scheduler started — every %d minutes.",
            interval_minutes,
        )
    except RuntimeError as exc:
        # No event loop running (e.g. called outside async context during tests)
        logger.warning("[gitnexus-scheduler] Could not start scheduler: %s", exc)


def stop_scheduler() -> None:
    """Cancel the background refresh task gracefully."""
    global _task  # noqa: PLW0603

    if _task is not None and not _task.done():
        _task.cancel()
        logger.info("[gitnexus-scheduler] Scheduler stop requested.")
    _task = None


def is_scheduler_running() -> bool:
    """Return True if the background task is active."""
    return _task is not None and not _task.done()


# ─── Manual trigger ───────────────────────────────────────────────────────────

async def refresh_repo(repo_name: str) -> Path:
    """Manually trigger a graph rebuild for a single *repo_name*.

    Called by the ``POST /gitnexus/analyze?repo=X`` API endpoint.
    Returns the path of the saved graph file.
    """
    from research_engine.knowledge_graph.gitnexus_bridge import build_and_save
    return await build_and_save(repo_name)
