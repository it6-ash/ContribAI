from app.analysis import SCALE_TIERS, difficulty_for, repo_scale
from app.models import Issue, Repository


def _repo(**kw):
    defaults = dict(github_id=1, owner="o", name="n", stars=0, contributors=0, tree=[])
    return Repository(**{**defaults, **kw})


def _issue(repo, labels):
    return Issue(github_id=1, number=1, title="Fix a small thing", body="x" * 300,
                 labels=labels, comments=1, repository=repo)


def test_scale_tiers_track_stars_and_contributors():
    assert repo_scale(_repo(stars=200)) == "small"
    assert repo_scale(_repo(stars=4_000)) == "medium"
    assert repo_scale(_repo(stars=20_000)) == "large"
    assert repo_scale(_repo(stars=90_000)) == "very_large"
    # Contributor count can carry it alone: a 2k-star repo with 600 people is
    # still a queue to stand in.
    assert repo_scale(_repo(stars=2_000, contributors=600)) == "very_large"
    assert set(SCALE_TIERS) == {"small", "medium", "large", "very_large"}


def test_good_first_issue_does_not_mean_the_same_thing_at_every_scale():
    """The reported problem: a 'good first issue' at Microsoft scale was being
    treated as equivalent to one in a 600-star project."""
    labels = ["good first issue"]
    small = _issue(_repo(stars=600), labels)
    huge = _issue(_repo(stars=90_000, contributors=800), labels)

    small_level, _ = difficulty_for(small, ["Python"], 0.8)
    huge_level, huge_why = difficulty_for(huge, ["Python"], 0.8)

    assert small_level == "beginner"
    assert huge_level != "beginner", "scale must not be cancelled by the label"
    assert "onboarding" in huge_why


def test_the_scale_cost_is_told_to_the_contributor(db):
    from sqlalchemy import select

    from app.analysis import analyze_issue
    from app.models import Repository as R

    repo = db.scalar(select(R).where(R.name == "vela"))
    repo.stars, repo.contributors = 90_000, 900
    issue = db.scalars(select(Issue).where(Issue.repository_id == repo.id)).first()
    insight = analyze_issue(issue, use_llm=False)
    assert any("Very large project" in q for q in insight.open_questions)


def test_paperwork_does_not_make_a_monorepo_approachable(db):
    from sqlalchemy import select

    from app import matching
    from app.analysis import repo_health
    from app.models import Repository as R

    repo = db.scalar(select(R).where(R.name == "ledgerly-api"))
    health = repo_health(repo)
    small = matching._accessibility(repo, health)

    repo.stars, repo.contributors = 95_000, 900
    huge = matching._accessibility(repo, repo_health(repo))
    assert huge < small, "CONTRIBUTING.md does not offset a 95k-star codebase"
