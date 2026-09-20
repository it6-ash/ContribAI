"""Additive column reconciliation at startup.

`Base.metadata.create_all()` creates missing *tables* and silently ignores
columns added to an existing one. That is how `users.merged_pr_count` came to
exist in the models and not in the database, which fails every query against
that table with a bare OperationalError.

This closes that specific gap and nothing more. It is **additive only**:

  - adds columns the models declare and the table lacks
  - never drops, renames, retypes or reorders anything
  - never touches data

That ceiling is deliberate. Renames and type changes need a real migration
tool with a downgrade path; reach for Alembic the moment you need one, and
delete this. It exists so that adding a nullable column does not require
either manual SQL on every environment or dropping the database.
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from .db import Base

log = logging.getLogger("contribai.schema")


def _sql_type(column, dialect) -> str:
    return column.type.compile(dialect=dialect)


def sync_columns(engine: Engine) -> list[str]:
    """Add any declared-but-missing columns. Returns what it added."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    added: list[str] = []

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue  # create_all handles whole tables
        have = {col["name"] for col in inspector.get_columns(table.name)}

        for column in table.columns:
            if column.name in have:
                continue
            # A NOT NULL column with no server default cannot be added to a
            # table that already has rows; skip it loudly rather than raising
            # at startup on a database that was previously working.
            if not column.nullable and column.server_default is None:
                default = _python_default(column)
                if default is None:
                    log.error(
                        "cannot add %s.%s automatically: NOT NULL with no default. "
                        "Write a migration.",
                        table.name,
                        column.name,
                    )
                    continue
                clause = (
                    f"ALTER TABLE {table.name} ADD COLUMN {column.name} "
                    f"{_sql_type(column, engine.dialect)} NOT NULL DEFAULT {default}"
                )
            else:
                clause = (
                    f"ALTER TABLE {table.name} ADD COLUMN {column.name} "
                    f"{_sql_type(column, engine.dialect)}"
                )

            with engine.begin() as conn:
                conn.execute(text(clause))
            added.append(f"{table.name}.{column.name}")

    if added:
        log.info("schema sync added %s", ", ".join(added))
    return added


def _python_default(column) -> str | None:
    """A literal usable in DEFAULT, from the model's python-side default."""
    default = column.default
    if default is None:
        return None

    if default.is_scalar:
        value = default.arg
    elif default.is_callable:
        # JSON columns are declared `default=list` / `default=dict`, which is a
        # callable, not a scalar. Those are exactly the columns this needs to
        # add, so evaluate the zero-argument ones rather than giving up.
        try:
            value = default.arg(None)
        except Exception:  # noqa: BLE001 - anything non-trivial needs a migration
            return None
    else:
        return None

    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    if isinstance(value, (list, dict)):
        import json

        return "'" + json.dumps(value).replace("'", "''") + "'"
    return None
