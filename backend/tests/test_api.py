def _login(client, username="alex"):
    resp = client.post("/api/auth/demo", params={"username": username})
    assert resp.status_code == 200, resp.text
    return resp.json()["user"]


def test_health_reports_provider_and_corpus(client):
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert data["llm_provider"] == "heuristic"  # no key in tests
    assert data["issues_in_corpus"] == 23
    assert set(data["demo_profiles"]) == {"alex", "priya", "rahul"}


def test_demo_login_and_session(client):
    user = _login(client)
    assert user["username"] == "alex"
    assert user["is_demo"] is True
    assert "github_token_enc" not in user  # tokens never cross the wire
    assert client.get("/api/me").json()["username"] == "alex"


def test_unknown_demo_profile_is_rejected(client):
    assert client.post("/api/auth/demo", params={"username": "nobody"}).status_code == 404


def test_protected_routes_require_a_session(client):
    assert client.get("/api/profile").status_code == 401
    assert client.get("/api/recommendations").status_code == 401


def test_profile_returns_skills_with_evidence(client):
    _login(client)
    data = client.get("/api/profile").json()
    assert data["user"]["username"] == "alex"
    python = next(s for s in data["skills"] if s["name"] == "Python")
    assert python["level"] == "advanced"
    assert python["evidence"]
    assert "language" in data["skills_by_category"]


def test_full_recommendation_flow(client):
    """The demo path, end to end: login -> recommendations -> explain -> plan -> chat."""
    _login(client)

    recs = client.get("/api/recommendations", params={"limit": 5}).json()
    assert recs["stats"]["analyzed"] == 23
    assert len(recs["recommendations"]) == 5
    top = recs["recommendations"][0]
    assert top["fit_score"] > 0
    assert top["reasoning"]
    assert top["skill_gap_narrative"]
    assert top["issue"]["repository"]["health"]["activity"] in ("high", "medium", "low")

    issue_id = top["issue"]["id"]
    explained = client.post(f"/api/issues/{issue_id}/analyze").json()
    assert explained["analysis"]["summary"]
    assert explained["analysis"]["source"] == "heuristic"  # no LLM key in tests
    assert explained["analysis"]["investigation_order"]

    plan = client.post(f"/api/contribution/{issue_id}/plan").json()
    assert len(plan["steps"]) >= 8
    assert plan["steps"][0]["title"]
    assert any("git checkout -b" in s["command"] for s in plan["steps"])

    chat = client.post(
        f"/api/contribution/{issue_id}/chat", json={"question": "Which file should I read first?"}
    ).json()
    assert chat["source"] == "heuristic"
    assert chat["answer"]


def test_plan_is_cached_until_regenerate_is_asked_for(client):
    _login(client)
    issue_id = client.get("/api/recommendations").json()["recommendations"][0]["issue"]["id"]
    first = client.post(f"/api/contribution/{issue_id}/plan").json()
    second = client.post(f"/api/contribution/{issue_id}/plan").json()
    assert first == second


def test_updating_mode_changes_recommendations(client):
    _login(client)
    before = [r["issue"]["number"] for r in client.get("/api/recommendations").json()["recommendations"]]
    client.put("/api/profile", json={"mode": "first_contribution", "experience_level": "never_contributed"})
    after = [r["issue"]["number"] for r in client.get("/api/recommendations").json()["recommendations"]]
    assert before != after


def test_self_reported_skills_are_marked_as_such(client):
    _login(client, "priya")
    data = client.put("/api/profile", json={"skills": ["Docker"]}).json()
    docker = next(s for s in data["skills"] if s["name"] == "Docker")
    assert docker["source"] == "self_reported"
    assert any("self-reported" in e for e in docker["evidence"])


def test_invalid_mode_is_rejected(client):
    _login(client)
    assert client.put("/api/profile", json={"mode": "nonsense"}).status_code == 422


def test_demo_profile_cannot_trigger_github_analysis(client):
    _login(client)
    resp = client.post("/api/profile/analyze")
    assert resp.status_code == 400
    assert "Demo profiles" in resp.json()["detail"]


def test_ingest_requires_the_shared_secret(client):
    payload = {"issues": [], "analyze": False}
    assert client.post("/api/ingest/issues", json=payload).status_code == 401
    assert (
        client.post(
            "/api/ingest/issues", json=payload, headers={"X-Ingest-Token": "wrong"}
        ).status_code
        == 401
    )


def test_ingest_upserts_issues(client):
    payload = {
        "analyze": True,
        "issues": [
            {
                "repo_full_name": "acme/widget",
                "repo_github_id": 123,
                "repo_language": "Python",
                "repo_stars": 900,
                "repo_url": "https://github.com/acme/widget",
                "github_id": 555001,
                "number": 42,
                "title": "Retry logic ignores the configured timeout",
                "body": "Steps to reproduce: call fetch() with timeout=1 and watch it hang.",
                "labels": ["bug", "help wanted"],
                "url": "https://github.com/acme/widget/issues/42",
            }
        ],
    }
    headers = {"X-Ingest-Token": "test-ingest-token"}
    first = client.post("/api/ingest/issues", json=payload, headers=headers).json()
    assert first == {
        "received": 1,
        "repositories_upserted": 1,
        "issues_created": 1,
        "issues_updated": 0,
        "analyzed": 1,
    }
    second = client.post("/api/ingest/issues", json=payload, headers=headers).json()
    assert second["issues_created"] == 0 and second["issues_updated"] == 1

    # Ingested issues are live data, so a demo user must not see them.
    _login(client)
    numbers = [
        r["issue"]["number"] for r in client.get("/api/recommendations").json()["recommendations"]
    ]
    assert 42 not in numbers


def test_taxonomy_exposes_modes_and_weights(client):
    data = client.get("/api/taxonomy").json()
    assert "Python" in data["skills"]["language"]
    assert "first_contribution" in data["modes"]
    assert abs(sum(data["weights"].values()) - 1.0) < 1e-9
