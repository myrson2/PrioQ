"""Task model and its category enum."""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Double, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utcnow

if TYPE_CHECKING:
    from app.models.users import User


class TaskCategory(StrEnum):
    """The five supported academic task categories."""

    quiz = "quiz"
    homework = "homework"
    project = "project"
    exam = "exam"
    other = "other"


class Task(Base):
    """A student-owned task, optionally linked to a course."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[TaskCategory] = mapped_column(
        Enum(TaskCategory, native_enum=False, create_constraint=True, length=20),
        nullable=False,
    )
    due_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    grade_weight: Mapped[float] = mapped_column(Double, nullable=False)
    estimated_hours: Mapped[float] = mapped_column(Double, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="tasks")
