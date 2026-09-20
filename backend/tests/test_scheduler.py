import asyncio

import pytest

from app import scheduler, services
from app.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_background_queries_follow_configured_languages(monkeypatch):
    monkeypatch.setenv("REFRESH_LANGUAGES", "rust, java")
    get_settings.cache_clear()
    qs = services.background_queries(limit=6)
    assert qs and all(q.startswith("is:issue is:open no:assignee") for q in qs)
    assert any("language:rust" in q for q in qs)
    assert any("language:java" in q for q in qs)
    assert not any("language:python" in q for q in qs)


def test_background_queries_survive_an_empty_setting(monkeypatch):
    monkeypatch.setenv("REFRESH_LANGUAGES", "  , ,")
    get_settings.cache_clear()
    assert any("language:python" in q for q in services.background_queries())


def test_refresh_stays_idle_without_a_github_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "")
    monkeypatch.setenv("CORPUS_REFRESH_ENABLED", "true")
    get_settings.cache_clear()
    r = scheduler.CorpusRefresher()
    assert r.enabled is False
    r.start()  # must not raise, and must not spawn a task
    assert r.status()["running"] is False


def test_refresh_can_be_disabled_outright(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    monkeypatch.setenv("CORPUS_REFRESH_ENABLED", "false")
    get_settings.cache_clear()
    assert scheduler.CorpusRefresher().enabled is False


def test_concurrent_runs_do_not_overlap(monkeypatch):
    """A slow refresh must not be started again by the next tick or a user click."""
    r = scheduler.CorpusRefresher()
    calls = []

    async def fake_ingest(db, token, queries, *, cap, analyze=False):
        calls.append(queries)
        await asyncio.sleep(0.05)
        return [], {"fetched": 0, "ingested": 0}

    monkeypatch.setattr(services, "run_search_ingest", fake_ingest)

    async def drive():
        first = asyncio.create_task(r.run_once(["q1"]))
        await asyncio.sleep(0.01)
        second = await r.run_once(["q2"])  # should be refused while first runs
        return await first, second

    first, second = asyncio.run(drive())
    assert second == {"skipped": "already running"}
    assert calls == [["q1"]]
    assert first["duration_seconds"] >= 0


def test_a_failing_run_records_the_rate_limit(monkeypatch):
    from app.github import RateLimited
    import time

    r = scheduler.CorpusRefresher()

    async def boom(db, token, queries, *, cap, analyze=False):
        raise RateLimited(int(time.time()) + 120)

    monkeypatch.setattr(services, "run_search_ingest", boom)
    out = asyncio.run(r.run_once(["q"]))
    assert out["rate_limited"] is True
    assert out["retry_after_seconds"] > 0
    assert r.status()["last_result"]["rate_limited"] is True
