"""Periodic issue-corpus refresh, in-process.

ponytail: an asyncio task on a sleep loop, not Celery + Redis + a beat scheduler.
This app has exactly one recurring job. Three extra services to run one job that
is idempotent and can miss a tick without consequence is not a trade worth making.

What this deliberately does NOT do, and when you would add it:
  - Survive a restart mid-run. It does not need to; the run is idempotent and the
    next tick redoes it.
  - Coordinate across processes. With >1 worker each would run its own refresh.
    That is wasteful but harmless (upserts). Add a Postgres advisory lock if the
    duplicate GitHub calls start costing quota.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from . import services
from .config import get_settings
from .db import SessionLocal
from .github import RateLimited

log = logging.getLogger("contribai.scheduler")


class CorpusRefresher:
    """Owns the background loop and the last-run status shown in /api/health."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = asyncio.Lock()
        self.last_run_at: datetime | None = None
        self.last_result: dict | None = None
        self.next_run_at: datetime | None = None

    # --- lifecycle ------------------------------------------------------
    @property
    def enabled(self) -> bool:
        settings = get_settings()
        # A refresh without a token burns the 60 req/hr anonymous budget in one
        # tick and then fails for the rest of the hour, so it is not worth doing.
        return settings.corpus_refresh_enabled and bool(settings.github_token)

    def start(self) -> None:
        settings = get_settings()
        if not settings.corpus_refresh_enabled:
            log.info("corpus refresh disabled (CORPUS_REFRESH_ENABLED=false)")
            return
        if not settings.github_token:
            log.info("corpus refresh idle: set GITHUB_TOKEN to enable scheduled discovery")
            return
        self._task = asyncio.create_task(self._loop(), name="corpus-refresh")
        log.info(
            "corpus refresh every %s min over [%s]",
            settings.refresh_interval_minutes,
            settings.refresh_languages,
        )

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        log.info("corpus refresh stopped")

    # --- the loop -------------------------------------------------------
    async def _loop(self) -> None:
        settings = get_settings()
        # Let the app finish booting and serve its first requests before
        # spending the GitHub budget.
        await asyncio.sleep(settings.refresh_startup_delay_seconds)
        while True:
            interval = max(5, settings.refresh_interval_minutes) * 60
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                # A failed refresh must never kill the loop: the next tick retries.
                log.exception("corpus refresh failed, retrying next tick")
            self.next_run_at = _now_plus(interval)
            await asyncio.sleep(interval)

    async def run_once(self, queries: list[str] | None = None) -> dict:
        """One refresh. Safe to call directly for an on-demand run."""
        if self._running.locked():
            log.info("refresh already in progress, skipping")
            return {"skipped": "already running"}

        async with self._running:
            settings = get_settings()
            queries = queries or services.background_queries()
            started = datetime.now(timezone.utc)
            try:
                with SessionLocal() as db:
                    _, stats = await services.run_search_ingest(
                        db,
                        settings.github_token or None,
                        queries,
                        cap=settings.max_candidate_issues,
                        analyze=True,
                    )
            except RateLimited as exc:
                stats = {"rate_limited": True, "retry_after_seconds": exc.seconds_remaining}
                log.warning("corpus refresh hit the GitHub rate limit")

            stats["duration_seconds"] = round(
                (datetime.now(timezone.utc) - started).total_seconds(), 1
            )
            self.last_run_at = started
            self.last_result = stats
            log.info(
                "corpus refresh: fetched=%s ingested=%s in %ss",
                stats.get("fetched"),
                stats.get("ingested"),
                stats.get("duration_seconds"),
            )
            return stats

    # --- status ---------------------------------------------------------
    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "running": bool(self._task and not self._task.done()),
            "in_progress": self._running.locked(),
            "interval_minutes": get_settings().refresh_interval_minutes,
            "languages": get_settings().refresh_languages,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_result": self.last_result,
        }


def _now_plus(seconds: float) -> datetime:
    from datetime import timedelta

    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


# One per process. The app is single-process by design; see the module docstring.
refresher = CorpusRefresher()
