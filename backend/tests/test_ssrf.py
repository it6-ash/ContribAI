import pytest

from app.services import safe_slug

HEADERS = {"X-Ingest-Token": "test-ingest-token"}


@pytest.mark.parametrize(
    "value",
    [
        "../../user/emails",          # walks off /repos onto another endpoint
        "owner/../../../user",
        "owner/name/extra",
        "/absolute/name",
        "owner/name?per_page=100",
        "owner/name#frag",
        "owner name",
        "owner/",
        "/name",
        "",
        "..",
        "own er/na me",
        "owner/name%2F..",
    ],
)
def test_slugs_that_could_redirect_a_github_call_are_rejected(value):
    assert safe_slug(value) is None, value


@pytest.mark.parametrize(
    "value",
    ["encode/httpx", "vela-ui/vela", "a/b", "Some.Org/repo_name-1", "microsoft/apm"],
)
def test_real_slugs_still_pass(value):
    assert safe_slug(value) is not None, value


def test_ingest_refuses_a_traversal_slug_instead_of_storing_it(client):
    """repo_full_name is split and interpolated into a GitHub API path, so a
    traversal value would later send a request somewhere else entirely."""
    body = {
        "analyze": False,
        "issues": [
            {
                "repo_full_name": "../../user",
                "github_id": 999001,
                "number": 1,
                "title": "x",
                "url": "https://example.invalid/1",
            }
        ],
    }
    out = client.post("/api/ingest/issues", json=body, headers=HEADERS).json()
    assert out["rejected"] == 1
    assert out["issues_created"] == 0
    assert out["repositories_upserted"] == 0


def test_ingest_rejects_unknown_fields(client):
    """extra=forbid: a typo'd field should fail loudly, not vanish."""
    body = {
        "analyze": False,
        "issues": [
            {
                "repo_full_name": "a/b",
                "github_id": 999002,
                "number": 1,
                "title": "x",
                "sneaky": "value",
            }
        ],
    }
    assert client.post("/api/ingest/issues", json=body, headers=HEADERS).status_code == 422


def test_ingest_caps_body_size(client):
    """An unbounded string on a write endpoint is a storage denial of service
    even behind a shared secret."""
    body = {
        "analyze": False,
        "issues": [
            {
                "repo_full_name": "a/b",
                "github_id": 999003,
                "number": 1,
                "title": "x",
                "body": "A" * 300_000,
            }
        ],
    }
    assert client.post("/api/ingest/issues", json=body, headers=HEADERS).status_code == 422


def test_profile_update_rejects_unknown_fields(client):
    client.post("/api/auth/demo", params={"username": "alex"})
    assert client.put("/api/profile", json={"is_admin": True}).status_code == 422
