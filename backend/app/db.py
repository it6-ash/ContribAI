from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

settings = get_settings()

_is_sqlite = settings.database_url.startswith("sqlite")
_connect_args = (
    # timeout: wait for a held write lock instead of failing instantly. The
    # default is 5s, which the corpus ingest can exceed while writing ~100
    # issues.
    {"check_same_thread": False, "timeout": 30}
    if _is_sqlite
    else {}
)
engine = create_engine(settings.database_url, connect_args=_connect_args, future=True)


if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - driver glue
        """Let readers work while the refresh is writing.

        In SQLite's default rollback-journal mode a writer blocks every reader,
        so the background corpus ingest made concurrent dashboard requests fail
        with "database is locked". WAL keeps readers going against the last
        committed state while a write is in flight, which is exactly the shape
        of this workload: one writer, several readers.

        Postgres does not need any of this, hence the dialect guard.
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401  (registers mappers before create_all)

    Base.metadata.create_all(engine)

    # create_all only creates missing tables; a column added to an existing
    # model is silently absent until something queries it and dies.
    from .schema_sync import sync_columns

    sync_columns(engine)
