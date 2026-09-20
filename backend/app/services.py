"""Orchestration between GitHub, the analysers and the database."""

from __future__ import annotations

import asyncio
import logging
import re
from collections import Counter
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import analysis as analysis_mod
from . import skills as skills_mod
from .config import get_settings
from .github import GitHubClient, RateLimited
from .models import Issue, IssueAnalysis, Repository, Skill, User, UserSkill
from .seed import _get_or_create_skill

log = logging.getLogger("contribai.services")

# GitHub search qualifiers by skill, so discovery uses the user's actual stack.
_LANGUAGE_QUALIFIER = {
    "Python": "python", "JavaScript": "javascript", "TypeScript": "typescript",
    "Go": "go", "Rust": "rust", "Java": "java", "C++": "cpp", "C": "c",
    "HTML/CSS": "css", "Shell": "shell",
}


def _naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _parse_ts(value) -> datetime | None:
    if isinstance(value, datetime):
        return _naive(value)
    if isinstance(value, str) and value:
        try:
            return _naive(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError:
            return None
    return None


# --------------------------------------------------------------------------
# Profile ingestion
# --------------------------------------------------------------------------
async def analyze_github_profile(
    db: Session, user: User, token: str | None, *, repo_limit: int = 20
) -> list[UserSkill]:
    client = GitHubClient(token)
    profile = await client.user(None if token else user.username)
    if profile:
        user.avatar_url = profile.get("avatar_url") or user.avatar_url
        user.bio = profile.get("bio") or user.bio
        user.github_id = profile.get("id") or user.github_id

    repos = await client.user_repos(None if token else user.username, limit=repo_limit)
    own = [r for r in repos if not r.get("fork")]

    # Enrich the most recently pushed repos only — the long tail is noise and costs quota.
    enrich = own[:8]
    languages = await asyncio.gather(
        *(client.repo_languages(r["owner"]["login"], r["name"]) for r in enrich),
        return_exceptions=True,
    )
    manifests: list[tuple[str, str]] = []
    for repo, langs in zip(enrich, languages):
        if isinstance(langs, dict):
            repo["languages"] = langs
        try:
            manifests += await client.manifests(repo["owner"]["login"], repo["name"])
        except Exception as exc:  # noqa: BLE001 - manifests are optional
            log.info("manifest fetch skipped for %s: %s", repo.get("name"), exc)
            break

    merged_pr_languages: Counter[str] = Counter()
    contributed_repos: set[str] = set()
    try:
        prs = await client.searched_prs(user.username)
        repo_lang = {f"{r['owner']['login']}/{r['name']}": r.get("language") for r in own}
        for pr in prs:
            slug = _slug_from_url(pr.get("repository_url", ""))
            if not slug:
                continue
            # A merged PR into someone else's repository is the strongest
            # evidence of contribution there is; own repos do not count.
            if not slug.lower().startswith(f"{user.username.lower()}/"):
                contributed_repos.add(slug)
            lang = repo_lang.get(slug)
            if lang:
                merged_pr_languages[lang] += 1
        user.merged_pr_count = len(prs)
        user.contributed_repos = sorted(contributed_repos)[:200]
        user.contributed_languages = sorted(merged_pr_languages)
    except Exception as exc:  # noqa: BLE001 - PR search is a bonus signal
        log.info("merged PR search skipped: %s", exc)

    commit_languages = Counter()
    for repo in own:
        if repo.get("language") and _recent(repo.get("pushed_at")):
            commit_languages[repo["language"]] += 1

    extracted = skills_mod.extract_skills(
        repos=own,
        commit_languages=dict(commit_languages),
        merged_pr_languages=dict(merged_pr_languages),
        manifests=manifests,
        self_reported=None,
        bio=user.bio,
    )
    persist_skills(db, user, extracted)
    user.profile_analyzed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return load_user_skills(db, user)


def _slug_from_url(url: str) -> str:
    match = re.search(r"/repos/([^/]+/[^/]+)$", url or "")
    return match.group(1) if match else ""


def _recent(pushed_at) -> bool:
    ts = _parse_ts(pushed_at)
    return bool(ts and (datetime.now(timezone.utc).replace(tzinfo=None) - ts).days <= 180)


def persist_skills(
    db: Session, user: User, extracted: list[skills_mod.ExtractedSkill], *, replace: bool = True
) -> None:
    existing = {us.skill.name: us for us in load_user_skills(db, user)}
    seen = set()
    for item in extracted:
        seen.add(item.name)
        skill = _get_or_create_skill(db, item.name)
        row = existing.get(item.name)
        if row is None:
            db.add(
                UserSkill(
                    user_id=user.id,
                    skill_id=skill.id,
                    confidence=item.confidence,
                    evidence=item.evidence,
                    source=item.source,
                    last_used_at=item.last_used_at,
                )
            )
        else:
            # Self-reported skills keep whichever confidence is higher: GitHub evidence
            # should be able to raise a claim, never silently demote one the user made.
            row.confidence = max(row.confidence, item.confidence) if row.source == "self_reported" else item.confidence
            row.evidence = item.evidence
            row.source = item.source
            row.last_used_at = item.last_used_at or row.last_used_at
    if replace:
        for name, row in existing.items():
            if name not in seen and row.source != "self_reported":
                db.delete(row)
    db.flush()


# What a self-reported level is worth. Deliberately topped out below the 0.75
# that GitHub evidence needs to read as "advanced": a claimed skill must never
# outrank a demonstrated one, or the whole evidence-based premise is decorative.
SELF_REPORTED_CONFIDENCE = {
    "novice": 0.12,
    "beginner": 0.28,
    "intermediate": 0.45,
    "advanced": 0.60,
    "expert": 0.72,
}
MAX_CUSTOM_SKILLS = 20
_CUSTOM_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 +#._/-]{0,39}$")


def normalize_skill_name(raw: str) -> str | None:
    """Clean a user-typed skill name, or None if it is not usable.

    This is a trust boundary: the string reaches the database and later the
    LLM prompts, so it gets length-capped and character-restricted here rather
    than anywhere downstream.
    """
    name = re.sub(r"\s+", " ", (raw or "").strip())
    if not name or not _CUSTOM_NAME.match(name):
        return None
    return name


def add_self_reported(
    db: Session, user: User, entries: list[tuple[str, str]]
) -> dict[str, list[str]]:
    """Record skills the user claims, at the level they claim.

    Anything outside the built-in taxonomy is kept as a custom skill rather
    than dropped. Silently discarding what someone typed is worse than not
    offering the field: they think it registered.
    """
    added, rejected = [], []
    custom_count = sum(
        1 for us in load_user_skills(db, user) if us.skill.category == "other"
    )

    for raw, level in entries:
        name = normalize_skill_name(raw)
        if not name:
            rejected.append(raw)
            continue

        canonical = skills_mod._canonical(name)
        if canonical:
            skill = _get_or_create_skill(db, canonical)
        else:
            if custom_count >= MAX_CUSTOM_SKILLS:
                rejected.append(name)
                continue
            skill = db.scalar(select(Skill).where(func.lower(Skill.name) == name.lower()))
            if skill is None:
                skill = Skill(name=name, category="other")
                db.add(skill)
                db.flush()
                custom_count += 1

        confidence = SELF_REPORTED_CONFIDENCE.get(level, SELF_REPORTED_CONFIDENCE["intermediate"])
        row = db.scalar(
            select(UserSkill).where(
                UserSkill.user_id == user.id, UserSkill.skill_id == skill.id
            )
        )
        if row:
            # Never lower a confidence that GitHub evidence produced.
            if row.source == "self_reported" or confidence > row.confidence:
                row.confidence = confidence if row.source == "self_reported" else row.confidence
                row.evidence = [f"self-reported: {level}"]
                row.source = "self_reported" if row.source == "self_reported" else row.source
        else:
            db.add(
                UserSkill(
                    user_id=user.id,
                    skill_id=skill.id,
                    confidence=confidence,
                    evidence=[f"self-reported: {level}"],
                    source="self_reported",
                )
            )
        added.append(skill.name)

    db.flush()
    return {"added": added, "rejected": rejected}


def load_user_skills(db: Session, user: User) -> list[UserSkill]:
    rows = list(
        db.scalars(
            select(UserSkill).where(UserSkill.user_id == user.id).order_by(
                UserSkill.confidence.desc()
            )
        ).unique()
    )
    return rows


# --------------------------------------------------------------------------
# Issue discovery
# --------------------------------------------------------------------------
def discovery_queries(user: User, user_skills: list[UserSkill], *, limit: int = 4) -> list[str]:
    """Build GitHub search queries from the user's strongest languages + mode."""
    langs = [
        _LANGUAGE_QUALIFIER[us.skill.name]
        for us in user_skills
        if us.skill.name in _LANGUAGE_QUALIFIER and us.confidence >= 0.35
    ][:3] or ["python"]

    base = "is:issue is:open no:assignee archived:false"
    if user.mode == "first_contribution":
        label_sets = ['label:"good first issue"', 'label:"help wanted" label:documentation']
        extra = "comments:<8"
    elif user.mode == "skill_stretch":
        label_sets = ['label:"help wanted"', "label:enhancement"]
        extra = "comments:<25"
    elif user.mode == "high_impact":
        label_sets = ['label:"help wanted"', "label:bug"]
        extra = "stars:>2000 comments:<30"
    else:
        label_sets = ['label:"help wanted"', "label:bug", 'label:"good first issue"']
        extra = "comments:<15"

    queries = []
    for lang in langs:
        for labels in label_sets:
            queries.append(f"{base} language:{lang} {labels} {extra}")
            if len(queries) >= limit:
                return queries
    return queries


def background_queries(limit: int = 6) -> list[str]:
    """Queries for the unattended refresh, when there is no user to aim at.

    Driven by REFRESH_LANGUAGES so the corpus reflects what this deployment's
    contributors actually write, not a hardcoded guess.
    """
    settings = get_settings()
    langs = [
        lang.strip().lower()
        for lang in settings.refresh_languages.split(",")
        if lang.strip()
    ] or ["python"]

    base = "is:issue is:open no:assignee archived:false"
    label_sets = ['label:"good first issue"', 'label:"help wanted"', "label:bug"]
    queries = []
    for lang in langs:
        for labels in label_sets:
            queries.append(f"{base} language:{lang} {labels} comments:<15")
            if len(queries) >= limit:
                return queries
    return queries


async def run_search_ingest(
    db: Session, token: str | None, queries: list[str], *, cap: int, analyze: bool = False
) -> tuple[list[Issue], dict]:
    """Search GitHub for `queries` and upsert whatever comes back.

    The single ingestion path. Both the periodic refresh and a user-triggered
    discovery run go through here, so there is one place where GitHub pacing,
    rate-limit handling and deduplication live.
    """
    client = GitHubClient(token)
    per_query = max(10, cap // max(len(queries), 1))

    raw: list[dict] = []
    stats: dict = {"queries": queries, "fetched": 0, "rate_limited": False, "failed_queries": 0}
    for query in queries:
        try:
            items = await client.search_issues(query, per_page=min(per_query, 100))
        except RateLimited as exc:
            # Nothing else will succeed until the window resets, so stop early and
            # keep whatever earlier queries returned.
            stats["rate_limited"] = True
            stats["retry_after_seconds"] = exc.seconds_remaining
            break
        except Exception as exc:  # noqa: BLE001
            # One malformed or rejected query must not discard the other queries'
            # results, which is what an uncaught raise here used to do.
            stats["failed_queries"] += 1
            log.warning("search failed for %r: %s", query[:60], exc)
            continue
        raw += items
        if len(raw) >= cap:
            break
    stats["fetched"] = len(raw)

    seen: set[int] = set()
    issues: list[Issue] = []
    for item in raw[:cap]:
        if item.get("id") in seen or "pull_request" in item:
            continue
        seen.add(item["id"])
        issue = await _upsert_search_result(db, client, item)
        if issue:
            issues.append(issue)
    db.commit()

    if analyze:
        # Pre-compute the rule-derived analysis so the first user to see these
        # issues does not pay for it inside their request.
        for issue in issues:
            if not issue.analysis:
                ensure_analysis(db, issue, use_llm=False)
    stats["ingested"] = len(issues)
    return issues, stats


async def discover_issues(
    db: Session, user: User, token: str | None, user_skills: list[UserSkill], *, cap: int
) -> tuple[list[Issue], dict]:
    return await run_search_ingest(
        db, token, discovery_queries(user, user_skills), cap=cap
    )


async def _upsert_search_result(db: Session, client: GitHubClient, item: dict) -> Issue | None:
    slug = _slug_from_url(item.get("repository_url", ""))
    if "/" not in slug:
        return None
    owner, name = slug.split("/", 1)

    repo = db.scalar(select(Repository).where(Repository.owner == owner, Repository.name == name))
    if repo is None:
        try:
            data = await client.repo(owner, name)
        except RateLimited:
            return None
        if not data:
            return None
        repo = Repository(
            github_id=data["id"],
            owner=owner,
            name=name,
            description=data.get("description"),
            language=data.get("language"),
            topics=data.get("topics") or [],
            stars=data.get("stargazers_count") or 0,
            forks=data.get("forks_count") or 0,
            open_issues=data.get("open_issues_count") or 0,
            last_commit_at=_parse_ts(data.get("pushed_at")),
            license=(data.get("license") or {}).get("spdx_id"),
            url=data.get("html_url") or f"https://github.com/{slug}",
        )
        db.add(repo)
        db.flush()
        await _enrich_repository(client, repo)
        db.flush()

    issue = db.scalar(select(Issue).where(Issue.github_id == item["id"]))
    labels = [label["name"] for label in item.get("labels", []) if isinstance(label, dict)]
    assignee = (item.get("assignee") or {}).get("login")
    fields = {
        "number": item.get("number", 0),
        "repository_id": repo.id,
        "title": item.get("title", ""),
        "body": item.get("body"),
        "state": item.get("state", "open"),
        "labels": labels,
        "assignee": assignee,
        "comments": item.get("comments", 0),
        "has_linked_pr": bool(item.get("draft")) or "pull_request" in item,
        "url": item.get("html_url", ""),
        "created_at": _parse_ts(item.get("created_at")),
        "updated_at": _parse_ts(item.get("updated_at")),
        "fetched_at": datetime.now(timezone.utc).replace(tzinfo=None),
    }
    if issue is None:
        issue = Issue(github_id=item["id"], **fields)
        db.add(issue)
        db.flush()
    else:
        for key, value in fields.items():
            setattr(issue, key, value)
    return issue


async def _enrich_repository(client: GitHubClient, repo: Repository) -> None:
    """Community health + directory tree. Best-effort: a failure here degrades the
    recommendation's confidence, it does not break discovery."""
    try:
        # Never populated before this: 0 of 91 live repositories had a count,
        # so half the scale signal was dead and only stars were deciding.
        repo.contributors = await client.contributor_count(repo.owner, repo.name)
    except Exception as exc:  # noqa: BLE001
        log.info("contributor count unavailable for %s: %s", repo.full_name, exc)
    try:
        community = await client.community_profile(repo.owner, repo.name)
        files = community.get("files") or {}
        repo.has_contributing = bool(files.get("contributing"))
        repo.has_code_of_conduct = bool(files.get("code_of_conduct"))
    except Exception as exc:  # noqa: BLE001
        log.info("community profile unavailable for %s: %s", repo.full_name, exc)
    try:
        tree = await client.tree(repo.owner, repo.name)
        repo.tree = tree
        repo.has_tests = any(
            re.search(r"(^|/)(tests?|__tests__|spec)/", p) or p.endswith("_test.go")
            for p in tree
        )
        repo.setup_commands = _infer_setup(tree, repo.language)
    except Exception as exc:  # noqa: BLE001
        log.info("tree unavailable for %s: %s", repo.full_name, exc)
    try:
        repo.readme = (await client.readme(repo.owner, repo.name))[:8000] or None
    except Exception as exc:  # noqa: BLE001
        log.info("readme unavailable for %s: %s", repo.full_name, exc)
    repo.health_score = analysis_mod.repo_health(repo).score


def _infer_setup(tree: list[str], language: str | None) -> list[str]:
    """Only commands justified by files actually present in the repo."""
    files = {p.lower() for p in tree if "/" not in p}
    commands: list[str] = []
    if "package.json" in files:
        commands += ["npm install", "npm test"]
    if "pyproject.toml" in files or "setup.py" in files:
        commands.append("pip install -e '.[dev]'")
    elif "requirements.txt" in files:
        commands.append("pip install -r requirements.txt")
    if any(p.startswith("tests/") or p.startswith("test/") for p in tree) and (
        language or ""
    ).lower() == "python":
        commands.append("pytest")
    if "go.mod" in files:
        commands += ["go mod download", "go test ./..."]
    if "cargo.toml" in files:
        commands += ["cargo build", "cargo test"]
    if "docker-compose.yml" in files or "docker-compose.yaml" in files:
        commands.insert(0, "docker compose up -d")
    return commands


def ensure_analysis(db: Session, issue: Issue, *, use_llm: bool = False) -> IssueAnalysis:
    if issue.analysis and (issue.analysis.source == "llm" or not use_llm):
        return issue.analysis
    insight = analysis_mod.analyze_issue(issue, use_llm=use_llm)
    if issue.analysis:
        for key, value in insight.to_dict().items():
            setattr(issue.analysis, key, value)
    else:
        db.add(IssueAnalysis(issue_id=issue.id, **insight.to_dict()))
    db.commit()
    db.refresh(issue)
    return issue.analysis


def all_candidate_issues(db: Session, *, demo_only: bool | None = None) -> list[Issue]:
    """demo_only=True returns only seeded issues, False only live ones, None both."""
    stmt = select(Issue).where(Issue.state == "open")
    if demo_only is not None:
        stmt = stmt.where(Issue.is_demo.is_(demo_only))
    return list(db.scalars(stmt).unique())


def candidate_issues(db: Session) -> list[Issue]:
    """What to rank for a real session: live issues, falling back to the seed.

    The seeded corpus is a stand-in for an empty database, not a parallel world.
    Pinning demo profiles to it meant recommending fabricated issue numbers in
    repositories that actually exist, so "View on GitHub" led to a 404.
    """
    live = all_candidate_issues(db, demo_only=False)
    return live if live else all_candidate_issues(db, demo_only=True)


def corpus_age_minutes(db: Session) -> float | None:
    """Minutes since the newest live issue was fetched. None if there are none."""
    newest = db.scalar(select(func.max(Issue.fetched_at)).where(Issue.is_demo.is_(False)))
    if not newest:
        return None
    return (datetime.now(timezone.utc).replace(tzinfo=None) - newest).total_seconds() / 60


async def revalidate(db: Session, issues: list[Issue], token: str | None, *, cap: int = 8) -> int:
    """Re-check the issues we are about to recommend against GitHub.

    A corpus entry is a snapshot. By the time it reaches the top of someone's
    list the issue may have been closed, assigned or picked up by a pull
    request, and recommending it wastes the contributor's time. Only the few
    that are actually about to be shown are checked, and only when stale.
    """
    client = GitHubClient(token)
    changed = 0
    for issue in issues[:cap]:
        if issue.is_demo or not issue.repository:
            continue
        try:
            data = await client.get(
                f"/repos/{issue.repository.full_name}/issues/{issue.number}", ttl=600
            )
        except RateLimited:
            break  # nothing further will succeed this window
        except Exception as exc:  # noqa: BLE001
            log.info("revalidate skipped %s: %s", issue.url, exc)
            continue
        if not data:
            # 404: the issue was deleted or transferred. Do not keep offering it.
            issue.state = "closed"
            changed += 1
            continue
        state = data.get("state", issue.state)
        assignee = (data.get("assignee") or {}).get("login")
        if state != issue.state or assignee != issue.assignee:
            issue.state, issue.assignee = state, assignee
            changed += 1
        issue.fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if changed:
        db.commit()
        log.info("revalidate updated %s issue(s)", changed)
    return changed
