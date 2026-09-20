"""Contributor <-> issue matching.

Four stages, in this order:
  1. hard filters      — deterministic, removes anything disqualifying
  2. semantic retrieval — TF-IDF cosine over issue/repo text vs the user's profile
  3. structured scoring — weighted, explainable dimensions
  4. LLM reasoning      — prose only, layered on top of 1-3 (see agents.py)

Stage 3 is the product. The score is reproducible without any model call, which is
why every recommendation can show its work.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import asdict, dataclass, field

from . import skills as skills_mod
from .analysis import DIFFICULTY_RANK, repo_health
from .models import Issue, User, UserSkill

# Mode -> difficulty the contributor should be aimed at, and how much stretch is allowed.
MODES = {
    "first_contribution": {"target": "beginner", "stretch": 1, "label": "First contribution"},
    "developer_match": {"target": "intermediate", "stretch": 1, "label": "Developer match"},
    "skill_stretch": {"target": "intermediate", "stretch": 2, "label": "Skill stretch"},
    "high_impact": {"target": "advanced", "stretch": 2, "label": "High impact"},
}

EXPERIENCE_TARGET = {
    "never_contributed": "beginner",
    "developer": "intermediate",
    "some_oss": "intermediate",
    "experienced": "advanced",
}

WEIGHTS = {
    "skill_match": 0.30,
    "difficulty_match": 0.20,
    "technology_match": 0.15,
    "repository_accessibility": 0.10,
    "issue_clarity": 0.10,
    "effort_fit": 0.05,
    "learning_value": 0.05,
    "repository_activity": 0.05,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "scoring weights must sum to 1"

_STOP = {
    "the", "and", "for", "with", "when", "that", "this", "from", "into", "are", "not",
    "but", "you", "your", "should", "would", "have", "has", "was", "were", "can", "use",
    "using", "issue", "bug", "add", "fix", "does", "doesn", "its", "our", "all", "any",
}


# --------------------------------------------------------------------------
# Stage 1 — hard filters
# --------------------------------------------------------------------------
@dataclass
class FilterResult:
    kept: list[Issue]
    dropped: list[tuple[Issue, str]]

    @property
    def drop_reasons(self) -> dict[str, int]:
        return dict(Counter(reason for _, reason in self.dropped))


def hard_filter(
    issues: list[Issue],
    *,
    user_skills: set[str] | None = None,
    allow_unknown_tech: bool = True,
    max_days_stale: int = 365,
) -> FilterResult:
    kept, dropped = [], []
    for issue in issues:
        reason = _disqualify(issue, user_skills, allow_unknown_tech, max_days_stale)
        (dropped.append((issue, reason)) if reason else kept.append(issue))
    return FilterResult(kept=kept, dropped=dropped)


def _disqualify(
    issue: Issue, user_skills: set[str] | None, allow_unknown_tech: bool, max_days_stale: int
) -> str | None:
    if issue.state != "open":
        return "closed"
    if issue.assignee:
        return "already assigned"
    if issue.has_linked_pr:
        return "pull request already open"
    labels = {str(label).lower() for label in (issue.labels or [])}
    if labels & {"wontfix", "invalid", "duplicate", "stale", "blocked", "needs-triage"}:
        return "labelled wontfix/duplicate/stale"
    if "security" in labels:
        return "security-sensitive"  # not a first contribution, and often embargoed

    repo = issue.repository
    if repo:
        days = _days_since(repo.last_commit_at)
        if days is not None and days > max_days_stale:
            return "repository inactive"
        if repo.contributors is not None and 0 < repo.contributors < 2 and not repo.has_contributing:
            return "single-maintainer repo with no contribution guide"

    if not allow_unknown_tech and user_skills is not None:
        required = _required_skills(issue)
        core = {
            s for s in required
            if skills_mod.BY_NAME[s].category
            in (skills_mod.CATEGORY_LANGUAGE, skills_mod.CATEGORY_FRAMEWORK)
        }
        if core and not (core & user_skills):
            return "outside selected technologies"
    return None


def _days_since(value) -> int | None:
    from datetime import datetime, timezone

    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - value).days)


# --------------------------------------------------------------------------
# Stage 2 — semantic retrieval
# --------------------------------------------------------------------------
def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z][a-z0-9+#.]{2,}", (text or "").lower()) if t not in _STOP]


class TfIdfIndex:
    """ponytail: 40 lines of TF-IDF instead of pgvector + an embedding API.

    At a few hundred candidate issues this is exact, instant, offline and
    debuggable. Swap in embeddings when the corpus is large enough that lexical
    overlap actually misses matches — not before.
    """

    def __init__(self, documents: list[str]):
        self.docs = [Counter(_tokens(d)) for d in documents]
        df = Counter()
        for doc in self.docs:
            df.update(doc.keys())
        n = max(len(self.docs), 1)
        self.idf = {term: math.log((n + 1) / (count + 1)) + 1.0 for term, count in df.items()}
        self.vectors = [self._vector(doc) for doc in self.docs]

    def _vector(self, counts: Counter) -> dict[str, float]:
        vec = {t: (1 + math.log(c)) * self.idf.get(t, 1.0) for t, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def similarity(self, query: str) -> list[float]:
        qvec = self._vector(Counter(_tokens(query)))
        out = []
        for vec in self.vectors:
            small, large = (qvec, vec) if len(qvec) < len(vec) else (vec, qvec)
            out.append(round(sum(v * large.get(t, 0.0) for t, v in small.items()), 4))
        return out


def profile_query(user: User, user_skills: list[UserSkill]) -> str:
    parts = [user.bio or ""]
    parts += list(user.interests or [])
    for us in user_skills:
        # Repeat by confidence so strong skills dominate the query vector.
        parts += [us.skill.name] * (1 + int(us.confidence * 3))
        parts += [str(e) for e in (us.evidence or [])[:2]]
    return " ".join(parts)


def issue_document(issue: Issue) -> str:
    repo = issue.repository
    parts = [issue.title, issue.body or "", " ".join(str(label) for label in issue.labels or [])]
    if repo:
        parts += [repo.full_name.replace("/", " "), repo.description or "", repo.language or ""]
        parts += list(repo.topics or [])
    if issue.analysis:
        parts += list(issue.analysis.required_skills or []) + list(issue.analysis.concepts or [])
    return " ".join(p for p in parts if p)


# --------------------------------------------------------------------------
# Stage 3 — structured scoring
# --------------------------------------------------------------------------
@dataclass
class Match:
    issue: Issue
    fit_score: float
    dimensions: dict[str, float]
    matched_skills: list[dict]
    skill_gaps: list[dict]
    readiness: dict[str, float]
    reasoning: list[str] = field(default_factory=list)
    bucket: str = "best_fit"

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("issue")
        return data


def _required_skills(issue: Issue) -> list[str]:
    if issue.analysis and issue.analysis.required_skills:
        return list(issue.analysis.required_skills)
    from .analysis import required_skills_for

    return required_skills_for(issue)


def _skill_map(user_skills: list[UserSkill]) -> dict[str, float]:
    return {us.skill.name: us.confidence for us in user_skills}


def score_issue(
    issue: Issue,
    user: User,
    user_skills: list[UserSkill],
    *,
    semantic: float = 0.0,
) -> Match:
    have = _skill_map(user_skills)
    required = _required_skills(issue)
    analysis = issue.analysis
    repo = issue.repository

    matched, gaps = [], []
    weighted_have, weighted_total = 0.0, 0.0
    for name in required:
        sd = skills_mod.BY_NAME.get(name)
        # Core technologies count double; "Git" shouldn't weigh as much as "Django".
        weight = 2.0 if sd and sd.category in (
            skills_mod.CATEGORY_LANGUAGE, skills_mod.CATEGORY_FRAMEWORK
        ) else 1.0
        weighted_total += weight
        confidence = have.get(name, 0.0)
        if confidence >= 0.25:
            weighted_have += weight * min(confidence / 0.75, 1.0)
            matched.append({"skill": name, "confidence": round(confidence, 3)})
        else:
            gaps.append(
                {
                    "skill": name,
                    "category": sd.category if sd else "engineering",
                    "severity": "core" if weight == 2.0 else "supporting",
                    "learning_hours": 2.0 if weight == 2.0 else 1.0,
                }
            )
    skill_match = weighted_have / weighted_total if weighted_total else 0.5

    tech_required = {
        s for s in required
        if skills_mod.BY_NAME.get(s)
        and skills_mod.BY_NAME[s].category
        in (skills_mod.CATEGORY_LANGUAGE, skills_mod.CATEGORY_FRAMEWORK, skills_mod.CATEGORY_DATA)
    }
    tech_have = {s for s in tech_required if have.get(s, 0) >= 0.25}
    technology_match = len(tech_have) / len(tech_required) if tech_required else 0.6

    difficulty = analysis.difficulty if analysis else "intermediate"
    difficulty_match = _difficulty_fit(user, difficulty)

    health = repo_health(repo) if repo else None
    accessibility = _accessibility(repo, health)
    activity = {"high": 1.0, "medium": 0.6, "low": 0.2, "unknown": 0.4}[
        health.activity if health else "unknown"
    ]

    clarity = analysis.clarity if analysis else 0.5
    learning_value = analysis.learning_value if analysis else 0.5
    effort_fit = _effort_fit(user, analysis)

    dimensions = {
        "skill_match": round(skill_match, 3),
        "difficulty_match": round(difficulty_match, 3),
        "technology_match": round(technology_match, 3),
        "repository_accessibility": round(accessibility, 3),
        "issue_clarity": round(clarity, 3),
        "effort_fit": round(effort_fit, 3),
        "learning_value": round(learning_value, 3),
        "repository_activity": round(activity, 3),
    }
    base = sum(WEIGHTS[k] * v for k, v in dimensions.items())
    # Semantic similarity nudges ordering within a tier; it never drives the score.
    fit = base * 0.9 + min(semantic * 2.5, 1.0) * 0.1
    dimensions["semantic_similarity"] = round(semantic, 4)

    readiness = {
        "skills": round(skill_match, 3),
        "repository_familiarity": round(_repo_familiarity(user, repo, have), 3),
        "difficulty_fit": round(difficulty_match, 3),
        "testing_readiness": round(min(have.get("Testing", 0.0) + (0.3 if repo and repo.has_tests else 0.0), 1.0), 3),
        "setup_readiness": round(_setup_readiness(repo, have), 3),
    }
    readiness["overall"] = round(sum(readiness.values()) / len(readiness), 3)

    match = Match(
        issue=issue,
        fit_score=round(min(fit, 1.0), 4),
        dimensions=dimensions,
        matched_skills=sorted(matched, key=lambda m: -m["confidence"]),
        skill_gaps=sorted(gaps, key=lambda g: (g["severity"] != "core", g["skill"])),
        readiness=readiness,
    )
    match.reasoning = explain(match, user, difficulty, health)
    return match


def _difficulty_fit(user: User, difficulty: str) -> float:
    mode = MODES.get(user.mode, MODES["developer_match"])
    target = mode["target"]
    if user.mode in ("developer_match", "skill_stretch"):
        target = EXPERIENCE_TARGET.get(user.experience_level, target)
    delta = DIFFICULTY_RANK[difficulty] - DIFFICULTY_RANK[target]
    if delta == 0:
        return 1.0
    if delta > 0:
        # Harder than target: allowed up to the mode's stretch, penalised beyond.
        return 0.7 if delta <= mode["stretch"] - 1 else 0.35 if delta <= mode["stretch"] else 0.1
    return 0.75 if delta == -1 else 0.45  # easier is fine, just less interesting


def _accessibility(repo, health) -> float:
    if not repo or not health:
        return 0.4
    score = 0.25
    if repo.has_contributing:
        score += 0.3
    if repo.has_tests:
        score += 0.15
    if repo.has_code_of_conduct:
        score += 0.05
    if repo.readme:
        score += 0.1
    if repo.setup_commands:
        score += 0.1
    if health.median_pr_response_hours is not None and health.median_pr_response_hours <= 72:
        score += 0.15
    return min(score, 1.0)


def _effort_fit(user: User, analysis) -> float:
    if not analysis:
        return 0.5
    hours = (analysis.estimated_hours_min + analysis.estimated_hours_max) / 2
    ceiling = {"never_contributed": 5.0, "developer": 8.0, "some_oss": 14.0, "experienced": 25.0}
    cap = ceiling.get(user.experience_level, 8.0)
    if hours <= cap * 0.5:
        return 1.0
    if hours <= cap:
        return 0.8
    return max(0.15, cap / hours)


def _repo_familiarity(user: User, repo, have: dict[str, float]) -> float:
    if not repo:
        return 0.3
    score = 0.25
    lang_skills = skills_mod.detect_skills_in_text(repo.language)
    if lang_skills and max((have.get(s, 0.0) for s in lang_skills), default=0.0) >= 0.5:
        score += 0.35
    interests = {i.lower() for i in (user.interests or [])}
    if interests & {t.lower() for t in (repo.topics or [])}:
        score += 0.2
    if repo.readme:
        score += 0.1
    if (repo.stars or 0) < 5000:
        score += 0.1  # smaller codebase is faster to hold in your head
    return min(score, 1.0)


def _setup_readiness(repo, have: dict[str, float]) -> float:
    if not repo:
        return 0.4
    score = 0.4
    if repo.setup_commands:
        score += 0.25
    if repo.has_contributing:
        score += 0.15
    if have.get("Docker", 0) >= 0.4 and any(
        "docker" in str(c).lower() for c in (repo.setup_commands or [])
    ):
        score += 0.2
    elif have.get("Git", 0) >= 0.3:
        score += 0.1
    return min(score, 1.0)


def explain(match: Match, user: User, difficulty: str, health) -> list[str]:
    """Deterministic 'why', always present even when the LLM is unavailable."""
    out: list[str] = []
    for m in match.matched_skills[:4]:
        level = "strong" if m["confidence"] >= 0.7 else "working"
        out.append(f"✓ {m['skill']}: {level} evidence in your GitHub history")
    if not match.matched_skills:
        out.append("△ None of the required skills appear in your GitHub evidence yet")
    d = match.dimensions
    if d["difficulty_match"] >= 0.7:
        out.append(f"✓ {difficulty.capitalize()} difficulty fits your current level")
    elif d["difficulty_match"] >= 0.35:
        out.append(f"△ {difficulty.capitalize()} is a stretch from your current level")
    else:
        out.append(f"△ {difficulty.capitalize()} is well beyond your stated level")
    if d["issue_clarity"] >= 0.6:
        out.append("✓ Issue is clearly specified")
    else:
        out.append("△ Issue is thin on detail, expect discovery work")
    if health:
        if health.activity == "high":
            out.append(f"✓ Repository is active (last commit {health.days_since_commit}d ago)")
        elif health.activity == "low":
            out.append("△ Repository has been quiet recently")
        if health.has_contributing:
            out.append("✓ CONTRIBUTING.md present")
    for gap in match.skill_gaps[:2]:
        out.append(f"△ Skill gap: {gap['skill']} (~{gap['learning_hours']:.0f}h to get started)")
    return out


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def recommend(
    issues: list[Issue],
    user: User,
    user_skills: list[UserSkill],
    *,
    limit: int = 5,
    allow_unknown_tech: bool | None = None,
) -> tuple[list[Match], dict]:
    """Returns (ranked matches, stats). Stats feed the 'N issues analysed' UI line."""
    have = set(_skill_map(user_skills))
    if allow_unknown_tech is None:
        allow_unknown_tech = user.mode == "skill_stretch"

    filtered = hard_filter(issues, user_skills=have, allow_unknown_tech=allow_unknown_tech)
    stats = {
        "analyzed": len(issues),
        "passed_filters": len(filtered.kept),
        "dropped": filtered.drop_reasons,
    }
    if not filtered.kept:
        return [], stats

    index = TfIdfIndex([issue_document(i) for i in filtered.kept])
    sims = index.similarity(profile_query(user, user_skills))

    matches = [
        score_issue(issue, user, user_skills, semantic=sim)
        for issue, sim in zip(filtered.kept, sims)
    ]
    matches.sort(key=lambda m: -m.fit_score)
    _bucket(matches, user)
    stats["strong_matches"] = sum(1 for m in matches if m.fit_score >= 0.7)
    return matches[:limit], stats


def _bucket(matches: list[Match], user: User) -> None:
    """Label the shelves the dashboard renders: best fit / stretch / gentle start."""
    for i, m in enumerate(matches):
        difficulty = m.issue.analysis.difficulty if m.issue.analysis else "intermediate"
        if m.skill_gaps and any(g["severity"] == "core" for g in m.skill_gaps):
            m.bucket = "skill_stretch"
        elif difficulty == "beginner" and m.dimensions["skill_match"] >= 0.6:
            m.bucket = "gentle_start"
        elif i == 0:
            m.bucket = "best_fit"
        else:
            m.bucket = "best_fit" if m.fit_score >= 0.65 else "worth_a_look"
