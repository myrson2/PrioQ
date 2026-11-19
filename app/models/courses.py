"""Course model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UTCDateTime, utcnow

if TYPE_CHECKING:
    from app.models.users import User


class Course(Base):
    """A student-owned academic course."""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#3B82F6")
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="courses")
