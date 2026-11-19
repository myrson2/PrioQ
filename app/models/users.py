"""User account model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Double, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utcnow

if TYPE_CHECKING:
    from app.models.courses import Course
    from app.models.tasks import Task


class User(Base):
    """A student account that owns courses and tasks."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    email: Mapped[str] = mapped_column(
        String(320), nullable=False, unique=True, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    daily_study_hours: Mapped[float] = mapped_column(Double, nullable=False, default=3.0)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow
    )

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    courses: Mapped[list["Course"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
