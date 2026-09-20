from sqlalchemy import select

from app.analysis import affected_files_for, analyze_issue, clarity_of, repo_health
from app.models import Issue, Repository


def _issue(db, number):
    return db.scalar(select(Issue).where(Issue.number == number))


def test_repo_health_reflects_real_signals(db):
    active = db.scalar(select(Repository).where(Repository.name == "ledgerly-api"))
    quiet = db.scalar(select(Repository).where(Repository.name == "docsmith"))
    assert repo_health(active).activity == "high"
    assert repo_health(active).score > repo_health(quiet).score
    assert "CONTRIBUTING.md present" in repo_health(active).signals


def test_missing_contributing_is_reported_as_absent(db):
    repo = db.scalar(select(Repository).where(Repository.name == "orbit"))
    repo.has_contributing = False
    health = repo_health(repo)
    assert "No CONTRIBUTING.md found" in health.signals


def test_clarity_rewards_reproduction_steps(db):
    detailed = _issue(db, 1842)  # has steps to reproduce + expected
    thin = _issue(db, 2355)  # short docs request
    assert clarity_of(detailed)[0] > clarity_of(thin)[0]


def test_affected_files_prefers_source_over_tests(db):
    issue = _issue(db, 1842)
    files = affected_files_for(issue)
    assert any("transaction_service.py" in f for f in files)
    # The issue names the service module explicitly; it should not lead with a test file.
    assert "tests/" not in files[0]


def test_explicit_file_mentions_are_resolved_against_the_tree(db):
    issue = _issue(db, 2288)  # mentions useCombobox.ts
    files = affected_files_for(issue)
    assert "packages/core/src/Select/useCombobox.ts" in files


def test_difficulty_spread_across_the_corpus(db):
    good_first = analyze_issue(_issue(db, 1871), use_llm=False)  # labelled good first issue
    hard = analyze_issue(_issue(db, 1802), use_llm=False)  # labelled hard, 17 comments
    assert good_first.difficulty == "beginner"
    assert hard.difficulty == "advanced"
    assert hard.estimated_hours_max > good_first.estimated_hours_max


def test_required_skills_come_from_issue_and_repo(db):
    insight = analyze_issue(_issue(db, 1842), use_llm=False)
    assert "Python" in insight.required_skills  # repo language
    assert "Testing" in insight.required_skills  # issue mentions a count query / regression


def test_analysis_is_deterministic_without_llm(db):
    issue = _issue(db, 910021 and 418)
    first = analyze_issue(issue, use_llm=False).to_dict()
    second = analyze_issue(issue, use_llm=False).to_dict()
    assert first == second
    assert first["source"] == "heuristic"


def test_open_questions_flag_missing_information(db):
    issue = _issue(db, 2355)  # zero comments, short body, no repro
    insight = analyze_issue(issue, use_llm=False)
    assert insight.open_questions
    assert insight.confidence in ("low", "medium")
