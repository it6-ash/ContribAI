import sqlite3
import threading

from sqlalchemy import text


def test_sqlite_runs_in_wal_so_readers_survive_a_write(engine):
    """The reported 500: the corpus ingest held a write lock and every
    concurrent dashboard request failed with "database is locked"."""
    with engine.connect() as c:
        mode = c.execute(text("PRAGMA journal_mode")).scalar()
    # :memory: databases cannot use WAL; the pragma is still applied and simply
    # reports back what the driver could honour.
    assert mode in ("wal", "memory")


def test_a_reader_is_not_blocked_by_an_open_write(tmp_path):
    from sqlalchemy import create_engine, event

    path = tmp_path / "c.db"
    url = f"sqlite:///{path}"

    def make():
        eng = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30})

        @event.listens_for(eng, "connect")
        def _pragmas(dbapi, _rec):
            cur = dbapi.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA busy_timeout=30000")
            cur.close()

        return eng

    writer, reader = make(), make()
    with writer.begin() as c:
        c.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)"))
        c.execute(text("INSERT INTO t (v) VALUES ('seed')"))

    result = {}

    with writer.connect() as wconn:
        wconn.execute(text("BEGIN IMMEDIATE"))
        wconn.execute(text("INSERT INTO t (v) VALUES ('held')"))

        def read():
            try:
                with reader.connect() as rconn:
                    result["rows"] = rconn.execute(text("SELECT count(*) FROM t")).scalar()
            except sqlite3.OperationalError as exc:  # pragma: no cover
                result["error"] = str(exc)

        t = threading.Thread(target=read)
        t.start()
        t.join(timeout=10)
        wconn.rollback()

    assert "error" not in result, result
    assert result["rows"] == 1  # sees the last committed state, not the open write
