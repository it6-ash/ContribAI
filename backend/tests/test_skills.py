from app.skills import (
    _parse_dependencies,
    detect_skills_in_paths,
    detect_skills_in_text,
    extract_skills,
    skills_for_packages,
)


def test_keyword_match_respects_word_boundaries():
    # "C" must not fire on "docker", "Go" must not fire on "google".
    assert "C" not in detect_skills_in_text("we use docker heavily")
    assert "Go" not in detect_skills_in_text("hosted on google cloud")
    assert "Go" in detect_skills_in_text("written in golang")
    assert "C++" in detect_skills_in_text("a C++ parser")


def test_requirements_parsing():
    content = "fastapi>=0.110\n# comment\nsqlalchemy==2.0.1\npytest\n-r other.txt\nredis[hiredis]~=5.0\n"
    names = _parse_dependencies("requirements.txt", content)
    assert names == {"fastapi", "sqlalchemy", "pytest", "redis"}
    assert {"FastAPI", "SQLAlchemy", "Testing", "Redis"} <= skills_for_packages(names)


def test_package_json_parsing():
    content = '{"dependencies": {"react": "^18", "next": "14"}, "devDependencies": {"vitest": "1"}}'
    names = _parse_dependencies("package.json", content)
    assert names == {"react", "next", "vitest"}
    assert {"React", "Next.js", "Testing"} <= skills_for_packages(names)


def test_paths_detect_infrastructure_and_tests():
    found = detect_skills_in_paths(
        ["Dockerfile", ".github/workflows/ci.yml", "tests/test_api.py", "src/main.py"]
    )
    assert {"Docker", "CI/CD", "Testing", "Python"} <= found


def test_confidence_grows_with_evidence_and_saturates():
    one = extract_skills(repos=[{"name": "a", "language": "Python", "pushed_at": None}])
    many = extract_skills(
        repos=[{"name": f"r{i}", "language": "Python", "pushed_at": None} for i in range(6)],
        merged_pr_languages={"Python": 4},
        commit_languages={"Python": 30},
    )
    weak = next(s for s in one if s.name == "Python")
    strong = next(s for s in many if s.name == "Python")
    assert weak.confidence < strong.confidence < 1.0
    assert strong.level == "advanced"


def test_forks_are_not_evidence():
    skills = extract_skills(
        repos=[{"name": "someone-elses", "language": "Rust", "fork": True, "pushed_at": None}]
    )
    assert not any(s.name == "Rust" for s in skills)


def test_evidence_is_recorded_for_every_skill():
    skills = extract_skills(
        repos=[{"name": "api", "language": "Python", "topics": ["fastapi"], "pushed_at": None}],
        manifests=[("requirements.txt", "fastapi\nsqlalchemy\n")],
    )
    for skill in skills:
        assert skill.evidence, f"{skill.name} has no evidence"
    fastapi = next(s for s in skills if s.name == "FastAPI")
    assert any("requirements.txt" in e for e in fastapi.evidence)
