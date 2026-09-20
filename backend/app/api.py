"""All HTTP routes.

ponytail: one router module instead of the eight in the original spec. Every route
here is thin — the work lives in services/matching/analysis — so splitting it buys
nothing but extra imports. Split it when a section grows its own middleware.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Query,
    Response,
)
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import agents, matching, schemas, security, services
from . import analysis as analysis_mod
from .analysis import repo_health
from .config import get_settings
from .db import get_db
from .github import RateLimited, exchange_oauth_code
from .limits import api_limiter, llm_limiter
from .llm import get_provider
from .scheduler import refresher
from .models import (
    ContributionPlan,
    Issue,
    Recommendation,
    Repository,
    User,
    UserSkill,
)
from .seed import PROFILES, seed_all
from .skills import ALL_SKILL_NAMES, BY_NAME, LEVELS as SKILL_LEVELS
from .skills import level_for as skills_level_for

log = logging.getLogger("contribai.api")
router = APIRouter(prefix="/api")
settings = get_settings()


# --------------------------------------------------------------------------
# Auth helpers
# --------------------------------------------------------------------------
def current_user(
    db: Session = Depends(get_db),
    contribai_session: str | None = Cookie(default=None),
) -> User:
    uid = security.read_session(contribai_session)
    user = db.get(User, uid) if uid else None
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    return user


def _set_session(response: Response, user: User) -> None:
    response.set_cookie(
        security.SESSION_COOKIE,
        security.make_session(user.id),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        secure=settings.backend_url.startswith("https"),
    )


def _rate_limit(user: User, limiter, *, units: float = 0.0) -> None:
    """One choke point for abuse control.

    Keyed on the user, not the IP: IP alone is defeated by anyone signed in,
    and this product's expensive endpoints all require a session.
    """
    ok, retry = limiter.check(f"user:{user.id}", units=units)
    if not ok:
        log.warning("rate limited user=%s", user.username)
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Try again in {retry}s.",
            headers={"Retry-After": str(retry)},
        )


def llm_guard(user: User = Depends(current_user)) -> User:
    """Attach to every route that can reach the model provider.

    Bounds requests AND estimated tokens: request count alone does not bound
    cost, and the bill is the actual failure mode here.
    """
    _rate_limit(user, llm_limiter, units=get_settings().llm_units_per_call)
    return user


def _user_token(user: User) -> str | None:
    return security.decrypt_token(user.github_token_enc) or settings.github_token or None


# --------------------------------------------------------------------------
# Serialisation
# --------------------------------------------------------------------------
def _skill_out(row: UserSkill) -> schemas.SkillOut:
    confidence = row.confidence
    # Shared with skills.level_for so the bands cannot drift apart.
    level = skills_level_for(confidence)
    return schemas.SkillOut(
        name=row.skill.name,
        category=row.skill.category,
        confidence=round(confidence, 3),
        level=level,
        evidence=list(row.evidence or []),
        source=row.source,
        last_used_at=row.last_used_at,
    )


def _repo_out(repo: Repository) -> schemas.RepositoryOut:
    return schemas.RepositoryOut(
        id=repo.id,
        full_name=repo.full_name,
        owner=repo.owner,
        name=repo.name,
        description=repo.description,
        language=repo.language,
        topics=list(repo.topics or []),
        stars=repo.stars,
        forks=repo.forks,
        open_issues=repo.open_issues,
        contributors=repo.contributors,
        url=repo.url,
        health=repo_health(repo).to_dict(),
    )


def _analysis_out(issue: Issue) -> schemas.IssueAnalysisOut | None:
    a = issue.analysis
    if not a:
        return None
    return schemas.IssueAnalysisOut(
        summary=a.summary,
        problem_description=a.problem_description,
        why_it_matters=a.why_it_matters,
        difficulty=a.difficulty,
        difficulty_basis=a.difficulty_basis,
        estimated_hours_min=a.estimated_hours_min,
        estimated_hours_max=a.estimated_hours_max,
        required_skills=list(a.required_skills or []),
        concepts=list(a.concepts or []),
        affected_files=list(a.affected_files or []),
        investigation_order=list(a.investigation_order or []),
        open_questions=list(a.open_questions or []),
        clarity=a.clarity,
        learning_value=a.learning_value,
        risk=a.risk,
        confidence=a.confidence,
        source=a.source,
    )


def _issue_out(issue: Issue, *, include_body: bool = True) -> schemas.IssueOut:
    return schemas.IssueOut(
        id=issue.id,
        number=issue.number,
        title=issue.title,
        body=issue.body if include_body else None,
        labels=list(issue.labels or []),
        comments=issue.comments,
        state=issue.state,
        url=issue.url,
        is_demo=issue.is_demo,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
        repository=_repo_out(issue.repository),
        analysis=_analysis_out(issue),
    )


def _user_out(user: User) -> schemas.UserOut:
    return schemas.UserOut(
        id=user.id,
        username=user.username,
        avatar_url=user.avatar_url,
        bio=user.bio,
        is_demo=user.is_demo,
        experience_level=user.experience_level,
        mode=user.mode,
        interests=list(user.interests or []),
        profile_analyzed_at=user.profile_analyzed_at,
    )


# --------------------------------------------------------------------------
# Meta
# --------------------------------------------------------------------------
@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    return {
        "status": "ok",
        "llm_provider": get_provider().name,
        "llm_available": get_provider().available(),
        "github_oauth_configured": bool(settings.github_client_id),
        "issues_in_corpus": db.scalar(select(func.count(Issue.id))) or 0,
        "demo_profiles": [p["username"] for p in PROFILES],
        "corpus_refresh": refresher.status(),
    }


@router.get("/taxonomy")
def taxonomy() -> dict:
    grouped: dict[str, list[str]] = {}
    for name in ALL_SKILL_NAMES:
        grouped.setdefault(BY_NAME[name].category, []).append(name)
    return {
        "skills": grouped,
        "modes": {k: v["label"] for k, v in matching.MODES.items()},
        "experience_levels": list(matching.EXPERIENCE_TARGET),
        "skill_levels": list(SKILL_LEVELS),
        "repo_quality_tiers": list(analysis_mod.QUALITY_TIERS),
        "weights": matching.WEIGHTS,
    }


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------
@router.get("/auth/github")
def auth_github() -> RedirectResponse:
    if not settings.github_client_id:
        raise HTTPException(
            status_code=503,
            detail="GitHub OAuth is not configured. Use demo mode or set GITHUB_CLIENT_ID.",
        )
    state = security.new_oauth_state()
    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&redirect_uri={settings.backend_url}/api/auth/github/callback"
        "&scope=read:user"  # minimum scope: public profile only, no repo access
        f"&state={state}"
    )
    response = RedirectResponse(url)
    response.set_cookie(
        security.STATE_COOKIE, state, httponly=True, samesite="lax", max_age=600
    )
    return response


@router.get("/auth/github/callback")
async def auth_github_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
    contribai_oauth_state: str | None = Cookie(default=None),
) -> RedirectResponse:
    if not security.states_match(contribai_oauth_state, state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    token = await exchange_oauth_code(code, state_ok=True)
    if not token:
        raise HTTPException(status_code=400, detail="GitHub did not return an access token")

    from .github import GitHubClient

    profile = await GitHubClient(token).user()
    if not profile:
        raise HTTPException(status_code=400, detail="Could not read GitHub profile")

    user = db.scalar(select(User).where(User.github_id == profile["id"]))
    if not user:
        user = User(github_id=profile["id"], username=profile["login"])
        db.add(user)
    user.username = profile["login"]
    user.avatar_url = profile.get("avatar_url")
    user.bio = profile.get("bio")
    user.github_token_enc = security.encrypt_token(token)
    db.commit()

    response = RedirectResponse(f"{settings.frontend_url}/onboarding")
    _set_session(response, user)
    response.delete_cookie(security.STATE_COOKIE)
    return response


@router.post("/auth/demo")
def auth_demo(
    response: Response,
    background: BackgroundTasks,
    username: str = "alex",
    db: Session = Depends(get_db),
) -> dict:
    """Sign in as one of the seeded profiles. No GitHub, no network, no key."""
    if settings.is_production:
        # Otherwise anyone who finds the deployed API signs in as 'alex'.
        raise HTTPException(status_code=404, detail="Not found")
    user = db.scalar(select(User).where(User.username == username, User.is_demo.is_(True)))
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown demo profile. Available: {[p['username'] for p in PROFILES]}",
        )
    _set_session(response, user)
    _refresh_on_login(background, db, user)
    return {"user": _user_out(user).model_dump(mode="json")}


def _refresh_on_login(background: BackgroundTasks, db: Session, user: User) -> None:
    """Start a search for this user's stack when they sign in.

    Waiting for the six-hourly tick meant a new account saw whatever the last
    unrelated run happened to leave behind. Skipped when a run is already in
    flight or their own results are recent, so repeated logins do not stack up
    GitHub calls.
    """
    settings = get_settings()
    if not settings.github_token or refresher.in_progress:
        return
    if user.last_discovery_at:
        age = (
            datetime.now(timezone.utc).replace(tzinfo=None) - user.last_discovery_at
        ).total_seconds() / 60
        if age < settings.login_refresh_after_minutes:
            return
    skills = services.load_user_skills(db, user)
    if not skills:
        return
    user.last_discovery_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    background.add_task(
        refresher.run_once, services.discovery_queries(user, skills, limit=6)
    )
    log.info("login refresh queued for %s", user.username)


@router.post("/auth/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(security.SESSION_COOKIE)
    return {"ok": True}


@router.get("/me", response_model=schemas.UserOut)
def me(user: User = Depends(current_user)) -> schemas.UserOut:
    return _user_out(user)


# --------------------------------------------------------------------------
# Profile & skills
# --------------------------------------------------------------------------
@router.get("/profile", response_model=schemas.ProfileOut)
def get_profile(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> schemas.ProfileOut:
    skills = [_skill_out(row) for row in services.load_user_skills(db, user)]
    grouped: dict[str, list[schemas.SkillOut]] = {}
    for skill in skills:
        grouped.setdefault(skill.category, []).append(skill)
    return schemas.ProfileOut(user=_user_out(user), skills=skills, skills_by_category=grouped)


@router.post("/profile/analyze", response_model=schemas.ProfileOut)
async def analyze_profile(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> schemas.ProfileOut:
    if user.is_demo:
        raise HTTPException(
            status_code=400,
            detail="Demo profiles have a fixed skill graph. Sign in with GitHub to analyse a real one.",
        )
    try:
        await services.analyze_github_profile(db, user, _user_token(user))
    except RateLimited as exc:
        raise HTTPException(
            status_code=429,
            detail=f"GitHub rate limit reached. Try again in {exc.seconds_remaining // 60 + 1} minutes.",
            headers={"Retry-After": str(exc.seconds_remaining)},
        ) from exc
    return get_profile(user=user, db=db)


@router.put("/profile", response_model=schemas.ProfileOut)
def update_profile(
    payload: schemas.ProfileUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> schemas.ProfileOut:
    if payload.experience_level:
        if payload.experience_level not in matching.EXPERIENCE_TARGET:
            raise HTTPException(status_code=422, detail="Unknown experience level")
        user.experience_level = payload.experience_level
    if payload.mode:
        if payload.mode not in matching.MODES:
            raise HTTPException(status_code=422, detail="Unknown mode")
        user.mode = payload.mode
    if payload.interests is not None:
        user.interests = [i.strip() for i in payload.interests if i.strip()][:12]
    rejected: list[str] = []
    if payload.skills:
        entries = [
            (s, "intermediate") if isinstance(s, str) else (s.name, s.level)
            for s in payload.skills
        ]
        rejected = services.add_self_reported(db, user, entries)["rejected"]
    db.commit()
    out = get_profile(user=user, db=db)
    out.rejected_skills = rejected
    return out


# --------------------------------------------------------------------------
# Repositories & issues
# --------------------------------------------------------------------------
@router.get("/repositories")
def list_repositories(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    limit: int = 50,
) -> list[dict]:
    repos = db.scalars(select(Repository).order_by(Repository.stars.desc()).limit(limit))
    return [_repo_out(r).model_dump(mode="json") for r in repos]


@router.get("/repositories/{repo_id}")
def get_repository(
    repo_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> dict:
    repo = db.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    data = _repo_out(repo).model_dump(mode="json")
    data["readme"] = repo.readme
    data["setup_commands"] = list(repo.setup_commands or [])
    data["tree"] = list(repo.tree or [])[:200]
    return data


@router.get("/issues/{issue_id}", response_model=schemas.IssueOut)
def get_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> schemas.IssueOut:
    # Was unauthenticated, and it writes: ensure_analysis persists an analysis
    # row, so anyone could drive database work by walking sequential ids.
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    services.ensure_analysis(db, issue, use_llm=False)
    return _issue_out(issue)


@router.post("/issues/{issue_id}/analyze", response_model=schemas.IssueOut)
def analyze_issue_route(
    issue_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(llm_guard),
) -> schemas.IssueOut:
    """Deep 'Explain this issue' pass. Uses the LLM when configured, heuristics otherwise."""
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    services.ensure_analysis(db, issue, use_llm=True)
    return _issue_out(issue)


# --------------------------------------------------------------------------
# Recommendations
# --------------------------------------------------------------------------
@router.get("/recommendations", response_model=schemas.RecommendationsResponse)
async def recommendations(
    background: BackgroundTasks,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=5, ge=1, le=20),
    refresh: bool = Query(default=False, description="Pull fresh issues from GitHub first"),
) -> schemas.RecommendationsResponse:
    user_skills = services.load_user_skills(db, user)
    if not user_skills:
        raise HTTPException(
            status_code=409,
            detail="No skill graph yet. Run POST /api/profile/analyze or set skills first.",
        )

    stats: dict = {}
    if refresh and not user.is_demo:
        try:
            _, discovery_stats = await services.discover_issues(
                db, user, _user_token(user), user_skills, cap=settings.max_candidate_issues
            )
            stats["discovery"] = discovery_stats
        except RateLimited as exc:
            stats["discovery"] = {
                "rate_limited": True,
                "retry_after_seconds": exc.seconds_remaining,
            }

    # Live issues whenever we have any; the seeded corpus is a stand-in for an
    # empty database, not a parallel world to keep demo users inside.
    candidates = services.candidate_issues(db)
    for issue in candidates:
        if not issue.analysis:
            services.ensure_analysis(db, issue, use_llm=False)

    matches, match_stats = matching.recommend(candidates, user, user_skills, limit=limit)
    stats.update(match_stats)

    # A corpus entry is a snapshot, so the issues on screen get re-checked
    # against GitHub. That happens AFTER the response, never inside it.
    #
    # Doing it inline held this request's database connection open across
    # several seconds of network I/O. Under concurrency the pool emptied and
    # every request failed with QueuePool timeout — the endpoint took itself
    # down rather than being slow. The client polls /api/refresh/status and
    # reloads when the counter moves, so a correction lands seconds later
    # without any request waiting on GitHub.
    token = _user_token(user)
    if token and matches and not matches[0].issue.is_demo:
        stale_ids = [
            m.issue.id
            for m in matches
            if m.issue.fetched_at
            and (
                datetime.now(timezone.utc).replace(tzinfo=None) - m.issue.fetched_at
            ).total_seconds()
            > 1800
        ]
        if stale_ids:
            background.add_task(services.revalidate_ids, stale_ids, token)
            stats["revalidating"] = len(stale_ids)

    age = services.corpus_age_minutes(db)
    stats["corpus_age_minutes"] = round(age, 1) if age is not None else None
    stats["corpus"] = "demo" if (matches and matches[0].issue.is_demo) else "live"

    # Stale corpus and nobody has asked for a refresh: start one in the
    # background so the next visit is current. Never blocks this response.
    if (
        get_settings().github_token
        and age is not None
        and age > get_settings().refresh_interval_minutes
    ):
        background.add_task(refresher.run_once, None)
        stats["refresh_started"] = True

    out: list[schemas.RecommendationOut] = []
    for match in matches:
        row = db.scalar(
            select(Recommendation).where(
                Recommendation.user_id == user.id, Recommendation.issue_id == match.issue.id
            )
        )
        payload = match.to_dict()
        if row:
            for key, value in payload.items():
                setattr(row, key, value)
        else:
            row = Recommendation(user_id=user.id, issue_id=match.issue.id, **payload)
            db.add(row)
        db.flush()
        out.append(
            schemas.RecommendationOut(
                id=row.id,
                issue=_issue_out(match.issue),
                fit_score=match.fit_score,
                dimensions=match.dimensions,
                matched_skills=match.matched_skills,
                skill_gaps=match.skill_gaps,
                readiness=match.readiness,
                reasoning=match.reasoning,
                bucket=match.bucket,
                skill_gap_narrative=agents.skill_gap_narrative(
                    match.skill_gaps, match.matched_skills, match.readiness
                ),
            )
        )
    db.commit()
    return schemas.RecommendationsResponse(
        stats=stats, recommendations=out, generated_at=datetime.now(timezone.utc)
    )


@router.get("/recommendations/{rec_id}", response_model=schemas.RecommendationOut)
def get_recommendation(
    rec_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> schemas.RecommendationOut:
    row = db.get(Recommendation, rec_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return schemas.RecommendationOut(
        id=row.id,
        issue=_issue_out(row.issue),
        fit_score=row.fit_score,
        dimensions=row.dimensions or {},
        matched_skills=row.matched_skills or [],
        skill_gaps=row.skill_gaps or [],
        readiness=row.readiness or {},
        reasoning=row.reasoning or [],
        bucket=row.bucket,
        skill_gap_narrative=agents.skill_gap_narrative(
            row.skill_gaps or [], row.matched_skills or [], row.readiness or {}
        ),
    )


def _match_for(db: Session, user: User, issue: Issue) -> dict:
    row = db.scalar(
        select(Recommendation).where(
            Recommendation.user_id == user.id, Recommendation.issue_id == issue.id
        )
    )
    if row:
        return {"skill_gaps": row.skill_gaps or [], "readiness": row.readiness or {}}
    match = matching.score_issue(issue, user, services.load_user_skills(db, user))
    return {"skill_gaps": match.skill_gaps, "readiness": match.readiness}


# --------------------------------------------------------------------------
# Contribution workspace
# --------------------------------------------------------------------------
@router.post("/contribution/{issue_id}/plan", response_model=schemas.PlanOut)
def contribution_plan(
    issue_id: int,
    regenerate: bool = Query(default=False),
    user: User = Depends(llm_guard),
    db: Session = Depends(get_db),
) -> schemas.PlanOut:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    services.ensure_analysis(db, issue, use_llm=False)

    existing = db.scalar(
        select(ContributionPlan).where(
            ContributionPlan.user_id == user.id, ContributionPlan.issue_id == issue.id
        )
    )
    if existing and not regenerate:
        return schemas.PlanOut(
            issue_id=issue.id,
            prerequisites=list(existing.prerequisites or []),
            steps=[schemas.PlanStep(**s) for s in existing.steps or []],
            source=existing.source,
        )

    gaps = _match_for(db, user, issue)["skill_gaps"]
    steps, prerequisites, source = agents.contribution_plan(issue, user, gaps)
    if existing:
        existing.steps, existing.prerequisites, existing.source = steps, prerequisites, source
    else:
        db.add(
            ContributionPlan(
                user_id=user.id,
                issue_id=issue.id,
                steps=steps,
                prerequisites=prerequisites,
                source=source,
            )
        )
    db.commit()
    return schemas.PlanOut(
        issue_id=issue.id,
        prerequisites=prerequisites,
        steps=[schemas.PlanStep(**s) for s in steps],
        source=source,
    )


@router.post("/contribution/{issue_id}/chat", response_model=schemas.ChatResponse)
def contribution_chat(
    issue_id: int,
    payload: schemas.ChatRequest,
    user: User = Depends(llm_guard),
    db: Session = Depends(get_db),
) -> schemas.ChatResponse:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    services.ensure_analysis(db, issue, use_llm=False)
    answer, source = agents.workspace_chat(
        payload.question.strip(),
        issue,
        user,
        services.load_user_skills(db, user),
        _match_for(db, user, issue),
    )
    return schemas.ChatResponse(answer=answer, source=source)


# --------------------------------------------------------------------------
# Ingest (external bulk load)
# --------------------------------------------------------------------------
@router.post("/ingest/issues", response_model=schemas.IngestResponse)
def ingest_issues(
    payload: schemas.IngestRequest,
    db: Session = Depends(get_db),
    x_ingest_token: str | None = Header(default=None),
) -> schemas.IngestResponse:
    """Bulk upsert issues from an external scheduler.

    Exists so the issue corpus can be refreshed on a cron without the app process
    owning a scheduler. Authenticated by shared secret; disabled when INGEST_TOKEN
    is unset so an unconfigured deployment is not writable by the internet.
    """
    if not settings.ingest_token:
        raise HTTPException(status_code=503, detail="Ingest is disabled (INGEST_TOKEN unset)")
    if not x_ingest_token or not secrets.compare_digest(x_ingest_token, settings.ingest_token):
        raise HTTPException(status_code=401, detail="Invalid ingest token")

    repos_touched: set[int] = set()
    created = updated = analyzed = rejected = 0

    for item in payload.issues:
        parts = services.safe_slug(item.repo_full_name)
        if not parts:
            # Reject rather than store: a name that is not a real slug will be
            # interpolated into a GitHub API path later.
            rejected += 1
            continue
        owner, name = parts
        repo = db.scalar(
            select(Repository).where(Repository.owner == owner, Repository.name == name)
        )
        if repo is None:
            repo = Repository(
                github_id=item.repo_github_id or abs(hash(item.repo_full_name)) % (2**31),
                owner=owner,
                name=name,
                url=item.repo_url or f"https://github.com/{item.repo_full_name}",
            )
            db.add(repo)
        repo.description = item.repo_description or repo.description
        repo.language = item.repo_language or repo.language
        repo.topics = item.repo_topics or repo.topics
        repo.stars = item.repo_stars or repo.stars
        repo.forks = item.repo_forks or repo.forks
        repo.open_issues = item.repo_open_issues or repo.open_issues
        repo.license = item.repo_license or repo.license
        if item.repo_pushed_at:
            repo.last_commit_at = services._naive(item.repo_pushed_at)
        repo.health_score = repo_health(repo).score
        db.flush()
        repos_touched.add(repo.id)

        issue = db.scalar(select(Issue).where(Issue.github_id == item.github_id))
        fields = {
            "number": item.number,
            "repository_id": repo.id,
            "title": item.title,
            "body": item.body,
            "state": item.state,
            "labels": item.labels,
            "assignee": item.assignee,
            "comments": item.comments,
            "url": item.url,
            "created_at": services._naive(item.created_at),
            "updated_at": services._naive(item.updated_at),
            "fetched_at": datetime.now(timezone.utc).replace(tzinfo=None),
        }
        if issue is None:
            issue = Issue(github_id=item.github_id, **fields)
            db.add(issue)
            created += 1
        else:
            for key, value in fields.items():
                setattr(issue, key, value)
            updated += 1
        db.flush()

        if payload.analyze:
            services.ensure_analysis(db, issue, use_llm=False)
            analyzed += 1

    db.commit()
    return schemas.IngestResponse(
        received=len(payload.issues),
        rejected=rejected,
        repositories_upserted=len(repos_touched),
        issues_created=created,
        issues_updated=updated,
        analyzed=analyzed,
    )


@router.get("/refresh/status")
def refresh_status(
    db: Session = Depends(get_db),
    contribai_session: str | None = Cookie(default=None),
) -> dict:
    """Live refresh state. The dashboard polls this.

    Deliberately cheap and unauthenticated-tolerant: it runs every few seconds
    while a refresh is in flight, so it must not do real work.
    """
    out = refresher.status()
    out["corpus_age_minutes"] = services.corpus_age_minutes(db)
    out["can_refresh"] = bool(get_settings().github_token)

    uid = security.read_session(contribai_session)
    user = db.get(User, uid) if uid else None
    if user:
        out["last_discovery_at"] = (
            user.last_discovery_at.isoformat() if user.last_discovery_at else None
        )
    return out


@router.post("/refresh/corpus")
async def refresh_corpus(
    background: BackgroundTasks,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Widen the issue corpus for this contributor's stack, now.

    Returns immediately and runs in the background: search plus analysis takes
    far longer than a request should block for. Poll /api/refresh/status.
    """
    # get_settings() rather than the module-level `settings`: that one is bound at
    # import, so it cannot see an environment change without a process restart.
    if not get_settings().github_token:
        raise HTTPException(
            status_code=503,
            detail="Corpus refresh needs GITHUB_TOKEN. Without it the anonymous "
            "GitHub budget is exhausted by a single run.",
        )
    user_skills = services.load_user_skills(db, user)
    if not user_skills:
        raise HTTPException(
            status_code=409, detail="No skill graph yet, so there is nothing to search for."
        )
    if refresher.in_progress:
        return {"started": False, "reason": "already running", "queries": []}

    queries = services.discovery_queries(user, user_skills, limit=6)
    user.last_discovery_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    background.add_task(refresher.run_once, queries)
    return {"started": True, "queries": queries}


@router.post("/admin/seed")
def reseed(db: Session = Depends(get_db)) -> dict:
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not found")
    return seed_all(db)
