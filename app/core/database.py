"""SQLAlchemy engine, session factory, declarative base, and UTC datetime type."""

from datetime import datetime, timezone
from typing import Optional
from collections.abc import Iterator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.core.config import get_settings

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


class UTCDateTime(TypeDecorator):
    """Custom SQLAlchemy type for storing timezone-aware datetimes as naive UTC datetimes in MySQL."""

    impl = DATETIME(fsp=6)
    cache_ok = True

    def process_bind_param(
        self, value: Optional[datetime], dialect
    ) -> Optional[datetime]:
        """Converts incoming timezone-aware datetime to naive UTC before saving to DB.

        Rejects naive datetime objects with ValueError. Passes None through untouched.
        """
        if value is None:
            return None

        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError(
                "Cannot store naive datetime. Datetime object must be timezone-aware."
            )

        # Convert to UTC timezone, then strip tzinfo to make it a naive UTC object for MySQL
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(
        self, value: Optional[datetime], dialect
    ) -> Optional[datetime]:
        """Reads naive UTC datetime from MySQL and attaches timezone.utc."""
        if value is None:
            return None

        # Re-attach UTC timezone info when loading from DB
        return value.replace(tzinfo=timezone.utc)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)


def utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def get_db() -> Iterator[Session]:
    """Yield a database session and close it when the request is done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
