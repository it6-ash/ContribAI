import pytest

from app import matching
from app.analysis import QUALITY_TIERS, quality_tier, repo_health
from app.skills import LEVELS, level_for


def test_five_skill_bands_are_ordered_and_cover_the_range():
    assert len(LEVELS) == 5
    seen = [level_for(c / 100) for c in range(0, 101)]
    # Every band must be reachable, or it is decoration.
    assert set(seen) == set(LEVELS)
    # And they must only ever move upward as confidence rises.
    order = {name: i for i, name in enumerate(LEVELS)}
    ranks = [order[name] for name in seen]
    assert ranks == sorted(ranks)


def test_self_reported_top_level_stays_under_demonstrated_advanced():
    """Claiming expert must not reach the confidence real evidence earns."""
    from app.services import SELF_REPORTED_CONFIDENCE

    assert set(SELF_REPORTED_CONFIDENCE) == set(LEVELS)
    assert max(SELF_REPORTED_CONFIDENCE.values()) < 0.78  # the "expert" floor


def test_five_quality_tiers_are_ordered_and_reachable():
    assert len(QUALITY_TIERS) == 5
    seen = [quality_tier(s / 100) for s in range(0, 101)]
    assert set(seen) == set(QUALITY_TIERS)
    order = {name: i for i, name in enumerate(QUALITY_TIERS)}
    ranks = [order[name] for name in seen]
    assert ranks == sorted(ranks)


def test_repo_health_reports_a_tier(db):
    from sqlalchemy import select

    from app.models import Repository

    repo = db.scalar(select(Repository).where(Repository.name == "ledgerly-api"))
    health = repo_health(repo)
    assert health.tier in QUALITY_TIERS
    assert health.tier in ("welcoming", "exemplary")  # active, tested, has a guide


def test_prior_contribution_ranks_the_four_cases(db):
    from sqlalchemy import select

    from app.models import Repository, User

    orbit = db.scalar(select(Repository).where(Repository.name == "orbit"))
    rahul = db.scalar(select(User).where(User.username == "rahul"))  # merged into orbit
    alex = db.scalar(select(User).where(User.username == "alex"))  # no merged PRs

    same_repo, why = matching._prior_contribution(rahul, orbit)
    assert same_repo == 1.0 and "orbit" in why

    none_yet, why_none = matching._prior_contribution(alex, orbit)
    # A newcomer must not score zero: a first contribution is the whole point,
    # and zeroing it would bury exactly the user this product is built for.
    assert 0 < none_yet < same_repo
    assert "No merged pull requests" in why_none


def test_prior_contribution_is_a_visible_reason(db):
    from sqlalchemy import select

    from app import services
    from app.models import Issue, User

    rahul = db.scalar(select(User).where(User.username == "rahul"))
    issue = db.scalar(select(Issue).where(Issue.number == 791))  # orbit
    match = matching.score_issue(issue, rahul, services.load_user_skills(db, rahul))

    assert "prior_contribution" in match.dimensions
    assert match.dimensions["prior_contribution"] == 1.0
    assert any("already had a pull request merged" in r for r in match.reasoning)


def test_weights_still_sum_to_one_after_adding_the_dimension():
    assert abs(sum(matching.WEIGHTS.values()) - 1.0) < 1e-9
    assert "prior_contribution" in matching.WEIGHTS
