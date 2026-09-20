import time

import httpx
import pytest

from app.github import GitHubClient, RateLimited


class _Resp:
    def __init__(self, status, headers, text=""):
        self.status_code = status
        self.headers = headers
        self.text = text

    def json(self):
        return {}

    def raise_for_status(self):
        raise httpx.HTTPStatusError("boom", request=None, response=None)


def _patch(monkeypatch, resp):
    class _Client:
        def __init__(self, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, headers=None, params=None):
            return resp

    monkeypatch.setattr(httpx, "AsyncClient", _Client)


@pytest.mark.asyncio_compat
def test_secondary_rate_limit_is_recognised_while_quota_remains(monkeypatch):
    """The bug that crashed the first live refresh: 403 with remaining > 0."""
    import asyncio

    _patch(
        monkeypatch,
        _Resp(
            403,
            {"x-ratelimit-remaining": "27", "retry-after": "45"},
            text="You have exceeded a secondary rate limit",
        ),
    )
    with pytest.raises(RateLimited) as err:
        asyncio.run(GitHubClient("t").get("/search/issues", {"q": "x"}))
    assert 0 < err.value.seconds_remaining <= 46


def test_primary_rate_limit_still_recognised(monkeypatch):
    import asyncio

    _patch(
        monkeypatch,
        _Resp(403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": str(int(time.time()) + 90)}),
    )
    with pytest.raises(RateLimited) as err:
        asyncio.run(GitHubClient("t").get("/x", {"a": 1}))
    assert err.value.seconds_remaining > 60


def test_a_plain_403_is_not_swallowed_as_a_rate_limit(monkeypatch):
    """A genuine permission error must stay an error, not a silent retry-later."""
    import asyncio

    _patch(monkeypatch, _Resp(403, {"x-ratelimit-remaining": "42"}, text="Must have admin rights"))
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(GitHubClient("t").get("/y", {"b": 2}))
