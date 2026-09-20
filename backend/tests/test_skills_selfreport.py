def _login(client, username="alex"):
    assert client.post("/api/auth/demo", params={"username": username}).status_code == 200


def _named(profile, name):
    return next((s for s in profile["skills"] if s["name"] == name), None)


def test_level_sets_confidence_and_is_labelled(client):
    _login(client)
    data = client.put(
        "/api/profile",
        json={"skills": [{"name": "Kubernetes", "level": "advanced"}]},
    ).json()
    k = _named(data, "Kubernetes")
    assert k["source"] == "self_reported"
    assert k["confidence"] == 0.70
    assert k["evidence"] == ["self-reported: advanced"]


def test_self_reported_never_outranks_demonstrated_skill(client):
    """Claiming advanced must not beat GitHub evidence, or the whole
    evidence-based premise is decorative."""
    _login(client)
    before = _named(client.get("/api/profile").json(), "Python")
    assert before["confidence"] > 0.70  # alex has strong Python evidence
    after = _named(
        client.put(
            "/api/profile", json={"skills": [{"name": "Python", "level": "beginner"}]}
        ).json(),
        "Python",
    )
    assert after["confidence"] == before["confidence"]
    assert after["source"] == "github"


def test_a_skill_outside_the_taxonomy_is_kept_not_dropped(client):
    _login(client)
    data = client.put(
        "/api/profile", json={"skills": [{"name": "Terraform", "level": "intermediate"}]}
    ).json()
    t = _named(data, "Terraform")
    assert t is not None, "typed skills used to be silently discarded"
    assert t["category"] == "other"
    assert t["confidence"] == 0.50


def test_custom_skill_counts_when_the_issue_mentions_it(db):
    from sqlalchemy import select

    from app import matching, services
    from app.models import Issue, User

    user = db.scalar(select(User).where(User.username == "alex"))
    issue = db.scalar(select(Issue).where(Issue.number == 1842))
    issue.body = (issue.body or "") + "\nThis will need a Terraform change too."

    services.add_self_reported(db, user, [("Terraform", "intermediate")])
    db.commit()
    skills = services.load_user_skills(db, user)

    assert "Terraform" in matching.custom_skills_in_issue(issue, skills)
    match = matching.score_issue(issue, user, skills)
    assert "Terraform" in {m["skill"] for m in match.matched_skills}
    # A self-declared skill must never manufacture a gap: we have no evidence
    # the issue truly requires it.
    assert "Terraform" not in {g["skill"] for g in match.skill_gaps}


def test_custom_skill_does_not_match_on_a_substring(db):
    from sqlalchemy import select

    from app import matching, services
    from app.models import Issue, User

    user = db.scalar(select(User).where(User.username == "alex"))
    issue = db.scalar(select(Issue).where(Issue.number == 1842))
    services.add_self_reported(db, user, [("Go", "advanced")])
    db.commit()
    skills = services.load_user_skills(db, user)
    # "Go" must not fire on "google", "going", "algorithm"...
    issue.body = "We are going to refactor this in Google Cloud."
    assert matching.custom_skills_in_issue(issue, skills) == []


def test_unusable_names_are_reported_back_not_silently_dropped(client):
    """The original bug in a new place: the API knew the name was unusable and
    threw that away, so the UI looked like it had accepted it."""
    _login(client)
    body = client.put(
        "/api/profile",
        json={"skills": [{"name": "   ", "level": "beginner"}, {"name": "<script>", "level": "beginner"}]},
    ).json()
    assert body["rejected_skills"] == ["   ", "<script>"]
    assert not any(s["name"].strip() in ("", "<script>") for s in body["skills"])


def test_custom_skill_count_is_capped(db):
    from sqlalchemy import select

    from app import services
    from app.models import User

    user = db.scalar(select(User).where(User.username == "priya"))
    result = services.add_self_reported(
        db, user, [(f"CustomTool{i}", "beginner") for i in range(services.MAX_CUSTOM_SKILLS + 5)]
    )
    assert len(result["added"]) == services.MAX_CUSTOM_SKILLS
    assert len(result["rejected"]) == 5
