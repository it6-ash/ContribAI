from sqlalchemy import Column, Integer, String, create_engine, inspect, text

from app.schema_sync import sync_columns


def test_adds_a_column_the_model_gained_after_the_table_existed():
    """The exact failure: users.merged_pr_count existed in the model and not
    in the database, so every query against users raised OperationalError."""
    engine = create_engine("sqlite://")
    with engine.begin() as c:
        c.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR)"))
        c.execute(text("INSERT INTO users (id, username) VALUES (1, 'existing')"))

    from app.db import Base
    from app.models import User  # noqa: F401

    added = sync_columns(engine)
    assert any(a.startswith("users.merged_pr_count") for a in added)

    cols = {c["name"] for c in inspect(engine).get_columns("users")}
    assert {"merged_pr_count", "contributed_repos", "contributed_languages"} <= cols

    # The existing row must survive, with the default applied.
    with engine.connect() as c:
        row = c.execute(text("SELECT username, merged_pr_count FROM users")).first()
    assert row[0] == "existing"
    assert row[1] == 0


def test_running_twice_is_a_no_op():
    engine = create_engine("sqlite://")
    from app.db import Base
    from app.models import User  # noqa: F401

    Base.metadata.create_all(engine)
    assert sync_columns(engine) == []
    assert sync_columns(engine) == []
