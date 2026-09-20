"""The matching engine is the product. These tests are the ones that matter."""

from sqlalchemy import select

from app import matching, services
from app.models import Issue, User
from conftest import user_named


def _ctx(db, username):
    user = user_named(db, username)
    return user, services.load_user_skills(db, user)


def _top(db, username, limit=5):
    user, skills = _ctx(db, username)
    issues = services.all_candidate_issues(db, demo_only=True)
    matches, stats = matching.recommend(issues, user, skills, limit=limit)
    return matches, stats


def test_weights_sum_to_one():
    assert abs(sum(matching.WEIGHTS.values()) - 1.0) < 1e-9


def test_different_profiles_get_different_top_issues(db):
    """If this ever fails, the engine has stopped discriminating and is just a search box."""
    alex = {m.issue.number for m in _top(db, "alex")[0]}
    priya = {m.issue.number for m in _top(db, "priya")[0]}
    rahul = {m.issue.number for m in _top(db, "rahul")[0]}
    assert alex != priya != rahul
    assert not (alex & priya), "Python backend dev and frontend dev should not share top issues"


def test_recommendations_match_the_profile_stack(db):
    """Top pick must land in the contributor's own stack, and never in a foreign one."""
    for username, expected_top, forbidden in [
        ("alex", "ledgerly-api", {"vela", "orbit"}),
        ("priya", "vela", {"orbit", "pipeforge", "ledgerly-api"}),
        ("rahul", "orbit", {"vela", "docsmith"}),
    ]:
        matches, _ = _top(db, username, limit=3)
        repos = [m.issue.repository.name for m in matches]
        assert repos[0] == expected_top, f"{username} top pick was {repos[0]}"
        assert not (set(repos) & forbidden), f"{username} got {repos}"


def test_assigned_and_linked_issues_are_filtered_out(db):
    issues = services.all_candidate_issues(db, demo_only=True)
    issues[0].assignee = "someone"
    issues[1].has_linked_pr = True
    result = matching.hard_filter(issues)
    kept = {i.id for i in result.kept}
    assert issues[0].id not in kept
    assert issues[1].id not in kept
    assert result.drop_reasons["already assigned"] == 1
    assert result.drop_reasons["pull request already open"] == 1


def test_security_labelled_issues_are_excluded(db):
    """#1856 is labelled security — not a first contribution, often embargoed."""
    issues = services.all_candidate_issues(db, demo_only=True)
    result = matching.hard_filter(issues)
    assert 1856 not in {i.number for i in result.kept}


def test_every_recommendation_carries_its_reasoning(db):
    matches, _ = _top(db, "alex")
    assert matches
    for match in matches:
        assert match.reasoning, "a recommendation with no explanation is not shippable"
        assert 0.0 <= match.fit_score <= 1.0
        assert set(matching.WEIGHTS) <= set(match.dimensions)
        assert 0.0 <= match.readiness["overall"] <= 1.0


def test_skill_gaps_name_what_is_missing(db):
    user, skills = _ctx(db, "alex")
    # Alex has no Go; an Orbit issue must surface Go as a core gap.
    issue = db.scalar(select(Issue).where(Issue.number == 791))
    match = matching.score_issue(issue, user, skills)
    gap_names = {g["skill"] for g in match.skill_gaps}
    assert "Go" in gap_names
    assert next(g for g in match.skill_gaps if g["skill"] == "Go")["severity"] == "core"


def test_matched_skills_only_include_skills_the_user_has(db):
    user, skills = _ctx(db, "priya")
    have = {us.skill.name for us in skills}
    issue = db.scalar(select(Issue).where(Issue.number == 2310))
    match = matching.score_issue(issue, user, skills)
    assert {m["skill"] for m in match.matched_skills} <= have


def test_mode_changes_what_gets_recommended(db):
    user = user_named(db, "alex")
    skills = services.load_user_skills(db, user)
    issues = services.all_candidate_issues(db, demo_only=True)

    user.mode = "first_contribution"
    user.experience_level = "never_contributed"
    beginner_first = matching.recommend(issues, user, skills, limit=3)[0]

    user.mode = "high_impact"
    user.experience_level = "experienced"
    impact_first = matching.recommend(issues, user, skills, limit=3)[0]

    beginner_difficulties = [m.issue.analysis.difficulty for m in beginner_first]
    impact_difficulties = [m.issue.analysis.difficulty for m in impact_first]
    assert beginner_difficulties != impact_difficulties
    assert "beginner" in beginner_difficulties


def test_difficulty_fit_penalises_overreach():
    user = User(username="x", experience_level="never_contributed", mode="first_contribution")
    assert matching._difficulty_fit(user, "beginner") == 1.0
    assert matching._difficulty_fit(user, "advanced") < 0.4


def test_stats_report_what_was_dropped(db):
    _, stats = _top(db, "alex")
    assert stats["analyzed"] == 23  # the seeded corpus
    assert stats["passed_filters"] < stats["analyzed"]
    assert sum(stats["dropped"].values()) == stats["analyzed"] - stats["passed_filters"]


def test_tfidf_ranks_the_obvious_document_first():
    index = matching.TfIdfIndex(
        [
            "pagination offset filter transactions sqlalchemy",
            "react dialog focus trap accessibility",
            "kubernetes helm chart resource limits",
        ]
    )
    scores = index.similarity("fastapi pagination offset bug in transactions")
    assert scores[0] == max(scores)
    assert scores[0] > 0


def test_semantic_similarity_cannot_dominate_the_score(db):
    """Even a perfect text match should not outrank a structurally bad fit by itself."""
    user, skills = _ctx(db, "alex")
    issue = db.scalar(select(Issue).where(Issue.number == 774))  # hard Go issue
    low = matching.score_issue(issue, user, skills, semantic=0.0).fit_score
    high = matching.score_issue(issue, user, skills, semantic=1.0).fit_score
    assert high - low <= 0.1 + 1e-9
