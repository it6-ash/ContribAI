from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    username: Mapped[str] = mapped_column(String(120), unique=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Fernet ciphertext. Never serialised into any response schema.
    github_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False)
    experience_level: Mapped[str] = mapped_column(String(40), default="developer")
    mode: Mapped[str] = mapped_column(String(40), default="developer_match")
    interests: Mapped[list] = mapped_column(JSON, default=list)
    # Past open-source contribution, used as its own scoring dimension. Someone
    # who has already landed a PR in this repo, or in this language, is a
    # materially different candidate from someone who never has.
    merged_pr_count: Mapped[int] = mapped_column(default=0)
    contributed_repos: Mapped[list] = mapped_column(JSON, default=list)
    contributed_languages: Mapped[list] = mapped_column(JSON, default=list)
    profile_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    skills: Mapped[list["UserSkill"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    category: Mapped[str] = mapped_column(String(40))


class UserSkill(Base):
    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"))
    # 0.0 - 1.0 heuristic strength, not a claim of measured proficiency.
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(40), default="github")
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship(lazy="joined")


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[int] = mapped_column(Integer, unique=True)
    owner: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(60), nullable=True)
    topics: Mapped[list] = mapped_column(JSON, default=list)
    stars: Mapped[int] = mapped_column(default=0)
    forks: Mapped[int] = mapped_column(default=0)
    open_issues: Mapped[int] = mapped_column(default=0)
    contributors: Mapped[int] = mapped_column(default=0)
    last_commit_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    has_contributing: Mapped[bool] = mapped_column(default=False)
    has_code_of_conduct: Mapped[bool] = mapped_column(default=False)
    has_tests: Mapped[bool] = mapped_column(default=False)
    license: Mapped[str | None] = mapped_column(String(60), nullable=True)
    median_pr_response_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    readme: Mapped[str | None] = mapped_column(Text, nullable=True)
    setup_commands: Mapped[list] = mapped_column(JSON, default=list)
    tree: Mapped[list] = mapped_column(JSON, default=list)
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    url: Mapped[str] = mapped_column(String(400), default="")
    is_demo: Mapped[bool] = mapped_column(default=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[int] = mapped_column(Integer, unique=True)
    number: Mapped[int] = mapped_column(Integer, default=0)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="open")
    labels: Mapped[list] = mapped_column(JSON, default=list)
    assignee: Mapped[str | None] = mapped_column(String(120), nullable=True)
    comments: Mapped[int] = mapped_column(default=0)
    comment_samples: Mapped[list] = mapped_column(JSON, default=list)
    has_linked_pr: Mapped[bool] = mapped_column(default=False)
    url: Mapped[str] = mapped_column(String(400), default="")
    is_demo: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    repository: Mapped[Repository] = relationship(lazy="joined")
    analysis: Mapped["IssueAnalysis | None"] = relationship(
        back_populates="issue", uselist=False, cascade="all, delete-orphan", lazy="joined"
    )


class IssueAnalysis(Base):
    """AI/heuristic interpretation of an issue. Kept in its own table so it is never
    confused with the factual GitHub payload on `issues`."""

    __tablename__ = "issue_analysis"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), unique=True
    )
    summary: Mapped[str] = mapped_column(Text, default="")
    problem_description: Mapped[str] = mapped_column(Text, default="")
    why_it_matters: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(20), default="intermediate")
    difficulty_basis: Mapped[str] = mapped_column(Text, default="")
    estimated_hours_min: Mapped[float] = mapped_column(Float, default=2.0)
    estimated_hours_max: Mapped[float] = mapped_column(Float, default=5.0)
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    concepts: Mapped[list] = mapped_column(JSON, default=list)
    affected_files: Mapped[list] = mapped_column(JSON, default=list)
    investigation_order: Mapped[list] = mapped_column(JSON, default=list)
    open_questions: Mapped[list] = mapped_column(JSON, default=list)
    clarity: Mapped[float] = mapped_column(Float, default=0.5)
    learning_value: Mapped[float] = mapped_column(Float, default=0.5)
    risk: Mapped[str] = mapped_column(String(20), default="low")
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    source: Mapped[str] = mapped_column(String(20), default="heuristic")  # heuristic | llm
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    issue: Mapped[Issue] = relationship(back_populates="analysis")


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (UniqueConstraint("user_id", "issue_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"))
    fit_score: Mapped[float] = mapped_column(Float, default=0.0)
    dimensions: Mapped[dict] = mapped_column(JSON, default=dict)
    matched_skills: Mapped[list] = mapped_column(JSON, default=list)
    skill_gaps: Mapped[list] = mapped_column(JSON, default=list)
    readiness: Mapped[dict] = mapped_column(JSON, default=dict)
    reasoning: Mapped[list] = mapped_column(JSON, default=list)
    bucket: Mapped[str] = mapped_column(String(30), default="best_fit")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    issue: Mapped[Issue] = relationship(lazy="joined")


class ContributionPlan(Base):
    __tablename__ = "contribution_plans"
    __table_args__ = (UniqueConstraint("user_id", "issue_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"))
    steps: Mapped[list] = mapped_column(JSON, default=list)
    prerequisites: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(20), default="heuristic")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
