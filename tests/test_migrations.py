"""Schema and migration tests against the guarded MySQL test database."""

import pytest
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.dialects.mysql import DATETIME, DOUBLE
from sqlalchemy.engine import Engine

from tests.conftest import assert_test_database_url, run_alembic


def test_upgrade_creates_expected_tables(test_engine: Engine) -> None:
    """A fresh upgrade creates the three domain tables plus Alembic's version table."""
    with test_engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
    assert {"users", "courses", "tasks", "alembic_version"} <= tables


def test_foreign_keys_use_cascade_and_set_null(test_engine: Engine) -> None:
    """Owner FKs cascade on user delete; the course FK nulls on course delete."""
    with test_engine.connect() as connection:
        inspector = inspect(connection)
        course_fks = {
            fk["constrained_columns"][0]: fk
            for fk in inspector.get_foreign_keys("courses")
        }
        task_fks = {
            fk["constrained_columns"][0]: fk
            for fk in inspector.get_foreign_keys("tasks")
        }

    assert course_fks["owner_id"]["referred_table"] == "users"
    assert course_fks["owner_id"]["options"]["ondelete"] == "CASCADE"
    assert task_fks["owner_id"]["referred_table"] == "users"
    assert task_fks["owner_id"]["options"]["ondelete"] == "CASCADE"
    assert task_fks["course_id"]["referred_table"] == "courses"
    assert task_fks["course_id"]["options"]["ondelete"] == "SET NULL"


def test_double_and_datetime_columns(test_engine: Engine) -> None:
    """Floats are DOUBLE and every timestamp is DATETIME(6)."""
    with test_engine.connect() as connection:
        inspector = inspect(connection)
        columns = {
            table: {
                column["name"]: column["type"]
                for column in inspector.get_columns(table)
            }
            for table in ("users", "courses", "tasks")
        }

    float_columns = (
        ("users", "daily_study_hours"),
        ("tasks", "grade_weight"),
        ("tasks", "estimated_hours"),
    )
    for table, name in float_columns:
        assert isinstance(columns[table][name], DOUBLE), f"{table}.{name} must be DOUBLE"

    datetime_columns = (
        ("users", "created_at"),
        ("courses", "created_at"),
        ("courses", "updated_at"),
        ("tasks", "due_at"),
        ("tasks", "completed_at"),
        ("tasks", "created_at"),
        ("tasks", "updated_at"),
    )
    for table, name in datetime_columns:
        column_type = columns[table][name]
        assert isinstance(column_type, DATETIME), f"{table}.{name} must be DATETIME"
        assert column_type.fsp == 6, f"{table}.{name} must have fsp=6"


def test_test_database_name_is_guarded() -> None:
    """A non-*_test URL is rejected before any destructive SQL can run."""
    unsafe = "mysql+pymysql://user:pass@localhost:3306/taskqueue"
    with pytest.raises(RuntimeError, match="non-test database"):
        assert_test_database_url(unsafe)

    safe = "mysql+pymysql://user:pass@localhost:3306/taskqueue_test"
    assert assert_test_database_url(safe) == safe


def test_upgrade_downgrade_cycle(
    test_engine: Engine,
    alembic_config: Config,
    test_database_url: str,
) -> None:
    """The initial revision can be rolled back to base and re-applied."""
    run_alembic(alembic_config, test_database_url, "downgrade", "base")
    with test_engine.connect() as connection:
        assert "tasks" not in inspect(connection).get_table_names()

    run_alembic(alembic_config, test_database_url, "upgrade", "head")
    with test_engine.connect() as connection:
        inspector = inspect(connection)
        assert {"users", "courses", "tasks", "alembic_version"} <= set(
            inspector.get_table_names()
        )
