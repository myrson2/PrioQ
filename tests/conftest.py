"""Guarded MySQL test harness: schema setup, cleanup, and Alembic helpers."""

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

from app.core.config import get_settings

REPO_ROOT = Path(__file__).resolve().parents[1]


class _RedactedUrl(str):
    """A URL string whose repr keeps credentials out of pytest tracebacks."""

    def __repr__(self) -> str:
        return "<database url redacted>"


def assert_test_database_url(url: str | None) -> str:
    """Return the URL only when it targets a MySQL database ending in ``_test``."""
    if not url:
        raise RuntimeError("TEST_DATABASE_URL is not configured")
    parsed = make_url(url)
    if not parsed.database or not parsed.database.endswith("_test"):
        raise RuntimeError(
            "Refusing to run destructive migration tests against "
            f"non-test database {parsed.database!r}"
        )
    return url


def run_alembic(config: Config, url: str, operation: str, revision: str) -> None:
    """Run an Alembic operation against ``url`` instead of the app's DATABASE_URL."""
    stub = SimpleNamespace(database_url=url)
    with patch("app.core.config.get_settings", return_value=stub):
        getattr(command, operation)(config, revision)


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Return the guarded test database URL with a redacted repr."""
    return _RedactedUrl(assert_test_database_url(get_settings().test_database_url))


@pytest.fixture(scope="session")
def alembic_config(test_database_url: str) -> Config:
    """Return an Alembic Config wired to the test database."""
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", test_database_url.replace("%", "%%"))
    return config


@pytest.fixture(scope="session")
def test_engine(test_database_url: str, alembic_config: Config) -> Iterator[Engine]:
    """Upgrade the test database once and yield an engine for inspection."""
    run_alembic(alembic_config, test_database_url, "upgrade", "head")
    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables(test_engine: Engine) -> Iterator[None]:
    """Delete all rows before each test so state never leaks between tests."""
    with test_engine.begin() as connection:
        connection.execute(text("DELETE FROM tasks"))
        connection.execute(text("DELETE FROM courses"))
        connection.execute(text("DELETE FROM users"))
    yield
