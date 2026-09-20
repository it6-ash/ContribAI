import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Must be set before app.config is imported anywhere.
os.environ.setdefault("DATABASE_URL", "sqlite://")  # in-memory
os.environ.setdefault("SESSION_SECRET", "test-secret")
os.environ.setdefault("GROQ_API_KEY", "")  # force the heuristic path in tests
# Hard-set, not setdefault: backend/.env carries real credentials and
# pydantic-settings reads it, so without this the suite makes live GitHub calls
# on every sign-in and takes minutes instead of seconds.
os.environ["GITHUB_TOKEN"] = ""
os.environ["CORPUS_REFRESH_ENABLED"] = "false"
os.environ.setdefault("INGEST_TOKEN", "test-ingest-token")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import db as db_module  # noqa: E402
from app.db import Base  # noqa: E402
from app.seed import seed_all  # noqa: E402


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    import app.models  # noqa: F401

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    seed_all(session)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(engine, monkeypatch):
    """TestClient wired to the in-memory database."""
    from fastapi.testclient import TestClient

    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(db_module, "SessionLocal", Session)
    monkeypatch.setattr(db_module, "engine", engine)

    from app.main import app

    def _get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    from app.db import get_db

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def user_named(session, username):
    from sqlalchemy import select

    from app.models import User

    return session.scalar(select(User).where(User.username == username))
