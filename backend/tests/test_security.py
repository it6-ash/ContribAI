import pytest

from app.limits import RateLimiter


def _login(client, username="alex"):
    assert client.post("/api/auth/demo", params={"username": username}).status_code == 200


def test_reads_that_write_require_a_session(client):
    """get_issue persists an analysis row, so leaving it unauthenticated let
    anyone drive database work by walking sequential ids."""
    for path in ("/api/issues/1", "/api/repositories", "/api/repositories/1"):
        assert client.get(path).status_code == 401, path


def test_model_endpoints_are_rate_limited(client):
    """The failure this prevents is a bill, not a traffic spike."""
    _login(client)
    issue_id = client.get("/api/recommendations").json()["recommendations"][0]["issue"]["id"]

    codes = [
        client.post(f"/api/contribution/{issue_id}/chat", json={"question": "hi"}).status_code
        for _ in range(25)
    ]
    assert 429 in codes, "an unbounded loop on a model endpoint must be refused"
    first_429 = codes.index(429)
    assert first_429 >= 10, "a real user must not be throttled immediately"


def test_a_429_tells_the_client_when_to_retry(client):
    _login(client, "priya")
    issue_id = client.get("/api/recommendations").json()["recommendations"][0]["issue"]["id"]
    last = None
    for _ in range(30):
        last = client.post(f"/api/issues/{issue_id}/analyze")
        if last.status_code == 429:
            break
    assert last.status_code == 429
    assert int(last.headers["Retry-After"]) > 0


def test_security_headers_are_present(client):
    h = client.get("/api/health").headers
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["X-Frame-Options"] == "DENY"
    assert "Referrer-Policy" in h


def test_untrusted_issue_text_is_delimited_in_prompts():
    """Issue bodies are attacker-controlled: anyone can open a GitHub issue."""
    from app import agents
    from app.analysis import _ANALYST_SYSTEM

    assert "<untrusted>" in _ANALYST_SYSTEM or "untrusted" in _ANALYST_SYSTEM
    assert "never as instructions" in agents._CHAT_SYSTEM


def test_limiter_refills_over_time():
    limiter = RateLimiter(rate_per_minute=60, burst=2)
    assert limiter.check("k")[0]
    assert limiter.check("k")[0]
    allowed, retry = limiter.check("k")
    assert not allowed and retry >= 1


def test_limiter_caps_spend_independently_of_request_count():
    """Request count alone does not bound cost: one huge call is not one unit."""
    limiter = RateLimiter(rate_per_minute=600, burst=100, units_per_window=100)
    assert limiter.check("k", units=99)[0]
    assert limiter.check("k", units=99)[0]  # crosses the ceiling on this call
    allowed, retry = limiter.check("k", units=1)
    assert not allowed and retry > 0


def test_limiter_keyspace_is_bounded():
    """An unbounded key dict is its own denial of service."""
    limiter = RateLimiter(rate_per_minute=60, burst=1)
    for i in range(6000):
        limiter.check(f"k{i}")
    assert len(limiter._buckets) <= 5000
