"""Thin GitHub REST client with on-disk-free TTL caching and rate-limit awareness."""

from __future__ import annotations

import asyncio
import base64
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

from .config import get_settings

log = logging.getLogger("contribai.github")

API = "https://api.github.com"
_MANIFEST_FILES = (
    "requirements.txt", "pyproject.toml", "package.json", "go.mod", "Cargo.toml",
)


class RateLimited(Exception):
    def __init__(self, reset_at: int):
        self.reset_at = reset_at
        self.seconds_remaining = max(0, int(reset_at - time.time()))
        super().__init__(f"GitHub rate limit exhausted, resets in {self.seconds_remaining}s")


@dataclass
class _Entry:
    value: Any
    expires_at: float


class _TTLCache:
    """ponytail: process-local dict, not Redis. One backend process for the demo;
    swap for Redis only when there is more than one."""

    def __init__(self, ttl: float = 900.0, maxsize: int = 2000):
        self._data: dict[str, _Entry] = {}
        self.ttl = ttl
        self.maxsize = maxsize

    def get(self, key: str):
        entry = self._data.get(key)
        if entry and entry.expires_at > time.time():
            return entry.value
        self._data.pop(key, None)
        return None

    def set(self, key: str, value, ttl: float | None = None):
        if len(self._data) >= self.maxsize:
            oldest = min(self._data, key=lambda k: self._data[k].expires_at)
            self._data.pop(oldest, None)
        self._data[key] = _Entry(value, time.time() + (ttl or self.ttl))


_cache = _TTLCache()

# Search pacing. GitHub's documented search limit is 30 req/min; 2.5s between
# calls keeps a burst comfortably under it. Process-wide, like the cache above.
_SEARCH_MIN_INTERVAL = 2.5
_search_gate = asyncio.Lock()
_search_state: dict[str, float] = {"last": 0.0}


class GitHubClient:
    def __init__(self, token: str | None = None):
        settings = get_settings()
        self.token = token or settings.github_token or None
        self.rate_limit_reset: int | None = None

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ContribAI",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def get(self, path: str, params: dict | None = None, *, ttl: float = 900.0):
        key = f"{'auth' if self.token else 'anon'}:{path}:{sorted((params or {}).items())}"
        cached = _cache.get(key)
        if cached is not None:
            return cached

        url = path if path.startswith("http") else f"{API}{path}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=self._headers(), params=params)

        remaining = resp.headers.get("x-ratelimit-remaining")
        if remaining is not None:
            self.rate_limit_reset = int(resp.headers.get("x-ratelimit-reset", 0))
        log.info("github %s -> %s (remaining=%s)", path, resp.status_code, remaining)

        if resp.status_code in (403, 429):
            # GitHub has two distinct limits and they fail differently:
            #   primary   - quota exhausted, remaining == 0, resets at x-ratelimit-reset
            #   secondary - requests too fast in succession, remaining still > 0,
            #               signalled by Retry-After and/or a message in the body
            # Only checking `remaining == 0` misses the secondary limit entirely and
            # turns it into an unhandled HTTPStatusError.
            retry_after = resp.headers.get("retry-after")
            body = resp.text[:400].lower()
            secondary = "secondary rate limit" in body or "abuse" in body
            if remaining == "0" or retry_after or secondary:
                if retry_after and retry_after.isdigit():
                    reset = time.time() + int(retry_after)
                elif remaining == "0":
                    reset = int(resp.headers.get("x-ratelimit-reset", time.time() + 60))
                else:
                    reset = time.time() + 60
                raise RateLimited(int(reset))
        if resp.status_code == 404:
            _cache.set(key, None, ttl=300)
            return None
        resp.raise_for_status()
        data = resp.json()
        _cache.set(key, data, ttl=ttl)
        return data

    # --- profile -------------------------------------------------------
    async def user(self, username: str | None = None) -> dict | None:
        return await self.get(f"/users/{username}" if username else "/user")

    async def user_repos(self, username: str | None = None, limit: int = 30) -> list[dict]:
        path = f"/users/{username}/repos" if username else "/user/repos"
        repos = await self.get(path, {"sort": "pushed", "per_page": min(limit, 100)}) or []
        return repos[:limit]

    async def repo_languages(self, owner: str, name: str) -> dict[str, int]:
        return await self.get(f"/repos/{owner}/{name}/languages", ttl=86400) or {}

    async def manifests(self, owner: str, name: str) -> list[tuple[str, str]]:
        """Dependency manifests at the repo root. Missing files are cached as absent."""
        out = []
        for filename in _MANIFEST_FILES:
            data = await self.get(f"/repos/{owner}/{name}/contents/{filename}", ttl=86400)
            if data and data.get("encoding") == "base64":
                try:
                    out.append(
                        (filename, base64.b64decode(data["content"]).decode("utf-8", "replace"))
                    )
                except (ValueError, KeyError):
                    continue
        return out

    async def search_issues(self, query: str, *, per_page: int = 50, sort: str = "updated") -> list[dict]:
        # Search is limited to ~30 requests/minute and, separately, rejects rapid
        # bursts with a secondary-limit 403 even while quota remains. Pacing the
        # calls is cheaper than handling the rejection.
        async with _search_gate:
            wait = _SEARCH_MIN_INTERVAL - (time.monotonic() - _search_state["last"])
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                data = await self.get(
                    "/search/issues",
                    {"q": query, "per_page": min(per_page, 100), "sort": sort, "order": "desc"},
                    ttl=600,
                )
            finally:
                _search_state["last"] = time.monotonic()
        return (data or {}).get("items", [])

    async def searched_prs(self, username: str, *, merged: bool = True) -> list[dict]:
        state = "is:merged" if merged else "is:pr"
        return await self.search_issues(f"author:{username} is:pr {state}", per_page=50)

    async def repo(self, owner: str, name: str) -> dict | None:
        return await self.get(f"/repos/{owner}/{name}", ttl=3600)

    async def contributor_count(self, owner: str, name: str) -> int:
        """Total contributors, via the pagination Link header.

        Asking for one per page and reading `rel="last"` costs a single request
        instead of walking every page. Repos with a single contributor send no
        Link header at all, hence the fallback.
        """
        url = f"{API}/repos/{owner}/{name}/contributors"
        params = {"per_page": "1", "anon": "1"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
        if resp.status_code != 200:
            return 0
        link = resp.headers.get("link", "")
        match = re.search(r'[?&]page=(\d+)>;\s*rel="last"', link)
        if match:
            return int(match.group(1))
        try:
            return len(resp.json() or [])
        except ValueError:
            return 0

    async def community_profile(self, owner: str, name: str) -> dict:
        return await self.get(f"/repos/{owner}/{name}/community/profile", ttl=86400) or {}

    async def readme(self, owner: str, name: str) -> str:
        data = await self.get(f"/repos/{owner}/{name}/readme", ttl=86400)
        if not data or data.get("encoding") != "base64":
            return ""
        return base64.b64decode(data["content"]).decode("utf-8", "replace")

    async def tree(self, owner: str, name: str, branch: str = "HEAD") -> list[str]:
        data = await self.get(
            f"/repos/{owner}/{name}/git/trees/{branch}", {"recursive": "1"}, ttl=86400
        )
        if not data:
            return []
        # Truncated trees are still useful; we only need a directory sketch.
        return [item["path"] for item in data.get("tree", []) if item.get("type") == "blob"][:800]

    async def issue_comments(self, owner: str, name: str, number: int, limit: int = 5) -> list[dict]:
        data = await self.get(
            f"/repos/{owner}/{name}/issues/{number}/comments", {"per_page": limit}, ttl=1800
        )
        return data or []

    async def issue_timeline_has_pr(self, owner: str, name: str, number: int) -> bool:
        data = await self.get(
            f"/repos/{owner}/{name}/issues/{number}/timeline", {"per_page": 100}, ttl=1800
        )
        return any(
            e.get("event") in ("cross-referenced", "connected") for e in (data or [])
        )


async def exchange_oauth_code(code: str, state_ok: bool) -> str | None:
    if not state_ok:
        return None
    settings = get_settings()
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
        )
    resp.raise_for_status()
    return resp.json().get("access_token")
