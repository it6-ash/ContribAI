"""Skill taxonomy + evidence-based extraction from GitHub data.

Deliberately not an LLM call: the skill graph is the factual spine of every
recommendation, so it is derived from countable GitHub signals (languages,
topics, dependency manifests, commits, merged PRs) and every entry carries the
evidence that produced it. The LLM layer only *narrates* this, never invents it.
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

CATEGORY_LANGUAGE = "language"
CATEGORY_FRAMEWORK = "framework"
CATEGORY_INFRA = "infrastructure"
CATEGORY_DATA = "data"
CATEGORY_ENGINEERING = "engineering"
CATEGORY_AI = "ai"


@dataclass(frozen=True)
class SkillDef:
    name: str
    category: str
    languages: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    packages: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()


# ponytail: a hand-written taxonomy beats a learned one at this size and is
# debuggable at 3am. Add rows, not machinery, when coverage is short.
TAXONOMY: tuple[SkillDef, ...] = (
    SkillDef("Python", CATEGORY_LANGUAGE, languages=("python",), keywords=("python",)),
    SkillDef("JavaScript", CATEGORY_LANGUAGE, languages=("javascript",), keywords=("javascript", "node.js", "nodejs")),
    SkillDef("TypeScript", CATEGORY_LANGUAGE, languages=("typescript",), keywords=("typescript",)),
    SkillDef("Go", CATEGORY_LANGUAGE, languages=("go",), keywords=("golang",)),
    SkillDef("Rust", CATEGORY_LANGUAGE, languages=("rust",), keywords=("rust",)),
    SkillDef("Java", CATEGORY_LANGUAGE, languages=("java",), keywords=("java",)),
    SkillDef("C++", CATEGORY_LANGUAGE, languages=("c++",), keywords=("c++", "cpp")),
    SkillDef("C", CATEGORY_LANGUAGE, languages=("c",)),
    SkillDef("Shell", CATEGORY_LANGUAGE, languages=("shell", "powershell")),
    SkillDef("HTML/CSS", CATEGORY_LANGUAGE, languages=("html", "css", "scss")),

    SkillDef("FastAPI", CATEGORY_FRAMEWORK, keywords=("fastapi",), packages=("fastapi",)),
    SkillDef("Django", CATEGORY_FRAMEWORK, keywords=("django",), packages=("django",)),
    SkillDef("Flask", CATEGORY_FRAMEWORK, keywords=("flask",), packages=("flask",)),
    SkillDef("React", CATEGORY_FRAMEWORK, keywords=("react",), packages=("react",)),
    SkillDef("Next.js", CATEGORY_FRAMEWORK, keywords=("next.js", "nextjs"), packages=("next",)),
    SkillDef("Vue", CATEGORY_FRAMEWORK, keywords=("vue",), packages=("vue",)),
    SkillDef("Express", CATEGORY_FRAMEWORK, keywords=("express",), packages=("express",)),
    SkillDef("Tailwind CSS", CATEGORY_FRAMEWORK, keywords=("tailwind",), packages=("tailwindcss",)),

    SkillDef("Docker", CATEGORY_INFRA, keywords=("docker", "container"), paths=("dockerfile", "docker-compose")),
    SkillDef("Kubernetes", CATEGORY_INFRA, keywords=("kubernetes", "k8s", "helm"), paths=("k8s/", "charts/")),
    SkillDef("Redis", CATEGORY_INFRA, keywords=("redis",), packages=("redis", "celery")),
    SkillDef("AWS", CATEGORY_INFRA, keywords=("aws", "lambda", "s3"), packages=("boto3",)),
    SkillDef("CI/CD", CATEGORY_INFRA, keywords=("ci/cd", "github actions"), paths=(".github/workflows",)),
    SkillDef("Nginx", CATEGORY_INFRA, keywords=("nginx",), paths=("nginx.conf",)),

    SkillDef("PostgreSQL", CATEGORY_DATA, keywords=("postgres", "postgresql"), packages=("psycopg", "psycopg2", "asyncpg", "pg")),
    SkillDef("MySQL", CATEGORY_DATA, keywords=("mysql", "mariadb"), packages=("pymysql", "mysql2")),
    SkillDef("MongoDB", CATEGORY_DATA, keywords=("mongodb", "mongo"), packages=("pymongo", "mongoose")),
    SkillDef("SQL", CATEGORY_DATA, languages=("plpgsql", "sql"), keywords=("sql query", "sql")),
    SkillDef("SQLAlchemy", CATEGORY_DATA, keywords=("sqlalchemy", "orm"), packages=("sqlalchemy", "alembic")),
    SkillDef("Prisma", CATEGORY_DATA, keywords=("prisma",), packages=("prisma", "@prisma/client")),
    SkillDef("Pandas", CATEGORY_DATA, keywords=("pandas", "dataframe"), packages=("pandas", "numpy")),

    SkillDef("REST APIs", CATEGORY_ENGINEERING, keywords=("rest api", "rest", "api endpoint", "openapi", "swagger")),
    SkillDef("GraphQL", CATEGORY_ENGINEERING, keywords=("graphql",), packages=("graphql", "strawberry-graphql", "apollo-server")),
    SkillDef("Testing", CATEGORY_ENGINEERING, keywords=("pytest", "unit test", "jest", "vitest", "test coverage"),
             packages=("pytest", "jest", "vitest", "unittest"), paths=("tests/", "test/", "__tests__/")),
    SkillDef("Git", CATEGORY_ENGINEERING, keywords=("git",)),
    SkillDef("Documentation", CATEGORY_ENGINEERING, keywords=("documentation", "docs", "mkdocs", "sphinx"),
             packages=("mkdocs", "sphinx"), paths=("docs/",)),
    SkillDef("Async/Concurrency", CATEGORY_ENGINEERING, keywords=("asyncio", "async", "concurrency", "goroutine")),

    SkillDef("LLM Integration", CATEGORY_AI, keywords=("llm", "gpt", "claude", "openai"),
             packages=("anthropic", "openai", "litellm")),
    SkillDef("LangChain", CATEGORY_AI, keywords=("langchain",), packages=("langchain", "langgraph")),
    SkillDef("RAG", CATEGORY_AI, keywords=("rag", "retrieval augmented", "vector search", "embedding"),
             packages=("chromadb", "pinecone-client", "faiss-cpu", "pgvector")),
    SkillDef("Machine Learning", CATEGORY_AI, keywords=("machine learning", "pytorch", "tensorflow", "scikit"),
             packages=("torch", "tensorflow", "scikit-learn")),
)

BY_NAME = {s.name: s for s in TAXONOMY}
ALL_SKILL_NAMES = tuple(s.name for s in TAXONOMY)

# Five bands rather than three: at three, everything from a single hobby repo
# to years of merged work collapsed into "intermediate", which is the band that
# matters most for matching difficulty.
LEVELS = ("novice", "beginner", "intermediate", "advanced", "expert")
_LEVEL_FLOORS = ((0.78, "expert"), (0.60, "advanced"), (0.38, "intermediate"), (0.18, "beginner"))


def level_for(confidence: float) -> str:
    for floor, name in _LEVEL_FLOORS:
        if confidence >= floor:
            return name
    return "novice"


# Weight per kind of evidence. Merged PRs are the strongest signal available
# because they survived someone else's review.
EVIDENCE_WEIGHTS = {
    "primary_language": 1.0,
    "language_bytes": 0.6,
    "dependency": 0.9,
    "topic": 0.4,
    "description": 0.25,
    "path": 0.5,
    "commits": 0.5,
    "merged_pr": 1.2,
    "self_reported": 0.7,
}

# Sum of weights at which confidence is ~0.86. Above this, returns diminish.
_SATURATION = 2.0


@dataclass
class SkillEvidence:
    skill: str
    weight: float
    kind: str
    detail: str
    when: datetime | None = None


@dataclass
class ExtractedSkill:
    name: str
    category: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    source: str = "github"
    last_used_at: datetime | None = None

    @property
    def level(self) -> str:
        return level_for(self.confidence)


def _norm(text: str | None) -> str:
    return (text or "").lower()


def _keyword_hit(haystack: str, needle: str) -> bool:
    # Word-boundary match so "c" doesn't match "docker" and "go" doesn't match "google".
    return re.search(rf"(?<![a-z0-9+#]){re.escape(needle)}(?![a-z0-9])", haystack) is not None


def detect_skills_in_text(text: str | None, *, include_packages: bool = True) -> set[str]:
    """Skill names plausibly referenced by a blob of text (issue body, README...)."""
    hay = _norm(text)
    if not hay:
        return set()
    found: set[str] = set()
    for sd in TAXONOMY:
        probes = list(sd.keywords) + list(sd.languages)
        if include_packages:
            probes += list(sd.packages)
        if any(_keyword_hit(hay, p) for p in probes):
            found.add(sd.name)
    return found


def detect_skills_in_paths(paths: list[str]) -> set[str]:
    joined = "\n".join(p.lower() for p in paths)
    found: set[str] = set()
    for sd in TAXONOMY:
        if any(p in joined for p in sd.paths):
            found.add(sd.name)
    ext_map = {
        ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript",
        ".jsx": "JavaScript", ".go": "Go", ".rs": "Rust", ".java": "Java",
        ".cpp": "C++", ".cc": "C++", ".c": "C", ".sh": "Shell", ".sql": "SQL",
        ".css": "HTML/CSS", ".html": "HTML/CSS", ".md": "Documentation",
    }
    for path in paths:
        for ext, skill in ext_map.items():
            if path.lower().endswith(ext):
                found.add(skill)
    return found


def _parse_dependencies(filename: str, content: str) -> set[str]:
    """Package names declared by a manifest. Returns lowercase names."""
    names: set[str] = set()
    low = filename.lower()
    if low.endswith("package.json"):
        try:
            data = json.loads(content)
        except (ValueError, TypeError):
            return names
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            names.update(k.lower() for k in (data.get(key) or {}))
    elif low.endswith((".txt", ".in")):  # requirements.txt / .in
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "-")):
                continue
            names.add(re.split(r"[<>=!~\[; ]", line, maxsplit=1)[0].strip().lower())
    elif low.endswith((".toml", ".cfg")):  # pyproject / setup.cfg — loose scan
        for match in re.finditer(r"^\s*[\"']?([A-Za-z0-9_.\-]+)[\"']?\s*[<>=~^\"]", content, re.M):
            names.add(match.group(1).lower())
    elif low.endswith("go.mod"):
        for match in re.finditer(r"^\s*([\w.\-/]+)\s+v\d", content, re.M):
            names.add(match.group(1).rsplit("/", 1)[-1].lower())
    return {n for n in names if n}


def skills_for_packages(packages: set[str]) -> set[str]:
    found: set[str] = set()
    for sd in TAXONOMY:
        for pkg in sd.packages:
            base = pkg.lower()
            if base in packages or any(p == base or p.startswith(base + "-") for p in packages):
                found.add(sd.name)
                break
    return found


def extract_skills(
    *,
    repos: list[dict],
    commit_languages: dict[str, int] | None = None,
    merged_pr_languages: dict[str, int] | None = None,
    manifests: list[tuple[str, str]] | None = None,
    self_reported: list[str] | None = None,
    bio: str | None = None,
) -> list[ExtractedSkill]:
    """Build a skill graph from GitHub evidence.

    repos: [{name, description, language, languages:{Lang:bytes}, topics:[..],
             stargazers_count, pushed_at, fork:bool}]
    commit_languages / merged_pr_languages: {language: count}
    manifests: [(filename, content)] from the user's repos
    """
    buckets: dict[str, list[SkillEvidence]] = defaultdict(list)
    recency: dict[str, datetime] = {}

    def add(skill: str, kind: str, detail: str, when: datetime | None = None, scale: float = 1.0):
        if skill not in BY_NAME:
            return
        buckets[skill].append(
            SkillEvidence(skill, EVIDENCE_WEIGHTS[kind] * scale, kind, detail, when)
        )
        if when and (skill not in recency or when > recency[skill]):
            recency[skill] = when

    lang_to_skill = {}
    for sd in TAXONOMY:
        for lang in sd.languages:
            lang_to_skill[lang] = sd.name

    repo_count_by_skill: dict[str, int] = defaultdict(int)

    for repo in repos or []:
        if repo.get("fork"):
            continue  # forks are not evidence of authorship
        pushed = _parse_ts(repo.get("pushed_at"))
        rname = repo.get("name", "repo")

        primary = _norm(repo.get("language"))
        if primary in lang_to_skill:
            skill = lang_to_skill[primary]
            add(skill, "primary_language", f"primary language of {rname}", pushed)
            repo_count_by_skill[skill] += 1

        for lang, size in (repo.get("languages") or {}).items():
            key = _norm(lang)
            if key in lang_to_skill and key != primary and size >= 2000:
                skill = lang_to_skill[key]
                add(skill, "language_bytes", f"{size:,} bytes of {lang} in {rname}", pushed)
                repo_count_by_skill[skill] += 1

        for topic in repo.get("topics") or []:
            for skill in detect_skills_in_text(topic):
                add(skill, "topic", f"topic '{topic}' on {rname}", pushed)

        blurb = f"{repo.get('description') or ''} {repo.get('readme_excerpt') or ''}"
        for skill in detect_skills_in_text(blurb):
            add(skill, "description", f"referenced in {rname} description", pushed)

    for filename, content in manifests or []:
        packages = _parse_dependencies(filename, content)
        for skill in skills_for_packages(packages):
            add(skill, "dependency", f"declared in {filename}")

    for lang, count in (commit_languages or {}).items():
        skill = lang_to_skill.get(_norm(lang))
        if skill and count:
            add(skill, "commits", f"{count} recent commits", scale=min(count / 10, 1.5))

    for lang, count in (merged_pr_languages or {}).items():
        skill = lang_to_skill.get(_norm(lang))
        if skill and count:
            add(skill, "merged_pr", f"{count} merged pull request(s)", scale=min(count / 3, 1.5))

    for skill in detect_skills_in_text(bio):
        add(skill, "description", "mentioned in GitHub bio")

    for name in self_reported or []:
        canonical = _canonical(name)
        if canonical:
            add(canonical, "self_reported", "self-reported during onboarding")

    out: list[ExtractedSkill] = []
    for skill, items in buckets.items():
        total = sum(i.weight for i in items)
        confidence = round(1 - math.exp(-total / _SATURATION), 3)
        sources = {i.kind for i in items}
        source = "self_reported" if sources == {"self_reported"} else "github"
        details = []
        if repo_count_by_skill.get(skill):
            n = repo_count_by_skill[skill]
            details.append(f"{n} repositor{'y' if n == 1 else 'ies'}")
        details += [i.detail for i in items if i.kind != "language_bytes"][:4]
        out.append(
            ExtractedSkill(
                name=skill,
                category=BY_NAME[skill].category,
                confidence=confidence,
                evidence=_dedupe(details)[:5],
                source=source,
                last_used_at=recency.get(skill),
            )
        )
    out.sort(key=lambda s: (-s.confidence, s.name))
    return out


def _canonical(name: str) -> str | None:
    target = name.strip().lower()
    for sd in TAXONOMY:
        if sd.name.lower() == target or target in sd.keywords or target in sd.languages:
            return sd.name
    return None


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _parse_ts(value) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
    return None
