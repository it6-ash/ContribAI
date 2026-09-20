from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SkillOut(BaseModel):
    name: str
    category: str
    confidence: float
    level: str
    evidence: list[str] = []
    source: str = "github"
    last_used_at: datetime | None = None


class UserOut(BaseModel):
    """Note: github_token_enc is deliberately absent. Tokens never leave the server."""

    id: int
    username: str
    avatar_url: str | None = None
    bio: str | None = None
    is_demo: bool = False
    experience_level: str
    mode: str
    interests: list[str] = []
    profile_analyzed_at: datetime | None = None


class ProfileOut(BaseModel):
    user: UserOut
    skills: list[SkillOut]
    skills_by_category: dict[str, list[SkillOut]]


class ProfileUpdate(BaseModel):
    experience_level: str | None = None
    mode: str | None = None
    interests: list[str] | None = None
    skills: list[str] | None = Field(
        default=None, description="Self-reported skill names; merged with GitHub evidence."
    )


class RepositoryOut(BaseModel):
    id: int
    full_name: str
    owner: str
    name: str
    description: str | None = None
    language: str | None = None
    topics: list[str] = []
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    contributors: int = 0
    url: str = ""
    health: dict


class IssueAnalysisOut(BaseModel):
    summary: str
    problem_description: str
    why_it_matters: str
    difficulty: str
    difficulty_basis: str
    estimated_hours_min: float
    estimated_hours_max: float
    required_skills: list[str] = []
    concepts: list[str] = []
    affected_files: list[str] = []
    investigation_order: list[str] = []
    open_questions: list[str] = []
    clarity: float
    learning_value: float
    risk: str
    confidence: str
    source: str


class IssueOut(BaseModel):
    id: int
    number: int
    title: str
    body: str | None = None
    labels: list[str] = []
    comments: int = 0
    state: str
    url: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    repository: RepositoryOut
    analysis: IssueAnalysisOut | None = None


class RecommendationOut(BaseModel):
    id: int | None = None
    issue: IssueOut
    fit_score: float
    dimensions: dict[str, float]
    matched_skills: list[dict]
    skill_gaps: list[dict]
    readiness: dict[str, float]
    reasoning: list[str]
    bucket: str
    skill_gap_narrative: str = ""


class RecommendationsResponse(BaseModel):
    stats: dict
    recommendations: list[RecommendationOut]
    generated_at: datetime


class PlanStep(BaseModel):
    title: str
    objective: str = ""
    command: str = ""
    expected: str = ""
    common_failure: str = ""


class PlanOut(BaseModel):
    issue_id: int
    prerequisites: list[str] = []
    steps: list[PlanStep] = []
    source: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    source: str


class IngestIssue(BaseModel):
    """Payload accepted by POST /api/ingest/issues.

    For loading a curated corpus from a script. The periodic refresh does not use
    this path; it goes straight through services.run_search_ingest."""

    repo_full_name: str
    number: int
    github_id: int
    title: str
    body: str | None = None
    labels: list[str] = []
    state: str = "open"
    assignee: str | None = None
    comments: int = 0
    url: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Repository facts, so the ingest does not need a second GitHub round trip.
    repo_github_id: int | None = None
    repo_description: str | None = None
    repo_language: str | None = None
    repo_topics: list[str] = []
    repo_stars: int = 0
    repo_forks: int = 0
    repo_open_issues: int = 0
    repo_pushed_at: datetime | None = None
    repo_license: str | None = None
    repo_url: str = ""


class IngestRequest(BaseModel):
    issues: list[IngestIssue] = Field(max_length=500)
    analyze: bool = True


class IngestResponse(BaseModel):
    received: int
    repositories_upserted: int
    issues_created: int
    issues_updated: int
    analyzed: int
