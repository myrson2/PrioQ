"""Tests for typed settings and the MySQL database harness."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.database import (
    SessionLocal,
    UTCDateTime,
    engine,
    get_db,
    utcnow,
)


def test_settings_requires_secret_key() -> None:
    """Missing SECRET_KEY must be rejected by Pydantic."""
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="mysql+pymysql://user:pass@localhost:3306/taskqueue",
        )


def test_settings_defaults_to_seven_days() -> None:
    """ACCESS_TOKEN_EXPIRE_DAYS defaults to exactly 7."""
    settings = Settings(
        _env_file=None,
        secret_key="test-secret",
        database_url="mysql+pymysql://user:pass@localhost:3306/taskqueue",
    )
    assert settings.access_token_expire_days == 7


def test_get_settings_is_cached() -> None:
    """The settings accessor returns the same instance within a process."""
    assert get_settings() is get_settings()


@pytest.fixture
def utc_type() -> UTCDateTime:
    """Return a fresh UTCDateTime type decorator."""
    return UTCDateTime()


def test_bind_normalizes_offset_to_naive_utc(utc_type: UTCDateTime) -> None:
    """:00 offsets must be converted to naive UTC."""
    value = datetime(2026, 1, 1, 8, 0, tzinfo=timezone(timedelta(hours=8)))
    assert utc_type.process_bind_param(value, None) == datetime(2026, 1, 1, 0, 0)


def test_bind_rejects_naive_datetime(utc_type: UTCDateTime) -> None:
    """Naive datetimes must never be silently assumed to be local time."""
    with pytest.raises(ValueError):
        utc_type.process_bind_param(datetime(2026, 1, 1, 8, 0), None)


def test_bind_preserves_none(utc_type: UTCDateTime) -> None:
    """Binding None must pass through untouched."""
    assert utc_type.process_bind_param(None, None) is None


def test_result_attaches_aware_utc(utc_type: UTCDateTime) -> None:
    """Values read from MySQL must be tagged with timezone.utc."""
    result = utc_type.process_result_value(datetime(2026, 1, 1, 0, 0), None)
    assert result == datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    assert result.tzinfo is timezone.utc


def test_result_preserves_none(utc_type: UTCDateTime) -> None:
    """Reading NULL must return None without raising."""
    assert utc_type.process_result_value(None, None) is None


def test_utcnow_is_aware_utc() -> None:
    """The utcnow helper returns a timezone-aware UTC timestamp."""
    assert utcnow().tzinfo is timezone.utc


def test_engine_uses_pre_ping() -> None:
    """Idle MySQL connections must be checked before use."""
    assert engine.pool._pre_ping is True


def test_session_factory_disables_expire_on_commit() -> None:
    """Sessions must not expire objects after commit."""
    assert SessionLocal.kw["expire_on_commit"] is False


def test_get_db_closes_session() -> None:
    """The FastAPI dependency yields a session and closes it on exit."""
    generator = get_db()
    session = next(generator)
    assert session is not None
    with pytest.raises(StopIteration):
        next(generator)
