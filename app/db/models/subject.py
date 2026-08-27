from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.school_class import SchoolClassORM


class SubjectORM(TimestampMixin, Base):
    __tablename__ = "subjects"

    class_id: Mapped[UUID] = mapped_column(
        ForeignKey("school_classes.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150))
    teacher_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    school_class: Mapped[SchoolClassORM] = relationship(back_populates="subjects")
