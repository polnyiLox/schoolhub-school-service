from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin
from app.enums import ClassMemberRole

if TYPE_CHECKING:
    from app.db.models.subject import SubjectORM


class SchoolClassORM(TimestampMixin, Base):
    __tablename__ = "school_classes"

    name: Mapped[str] = mapped_column(String(100))
    academic_year: Mapped[str] = mapped_column(String(9))
    is_archived: Mapped[bool] = mapped_column(default=False)

    members: Mapped[list[ClassMemberORM]] = relationship(
        back_populates="school_class",
        cascade="all, delete-orphan",
    )
    subjects: Mapped[list[SubjectORM]] = relationship(
        back_populates="school_class",
        cascade="all, delete-orphan",
    )


class ClassMemberORM(TimestampMixin, Base):
    __tablename__ = "class_members"
    __table_args__ = (
        UniqueConstraint("class_id", "telegram_id", name="uq_class_member_telegram"),
        Index("ix_class_members_class_telegram", "class_id", "telegram_id"),
    )

    class_id: Mapped[UUID] = mapped_column(
        ForeignKey("school_classes.id", ondelete="CASCADE")
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    role: Mapped[ClassMemberRole] = mapped_column(
        Enum(
            ClassMemberRole,
            name="class_member_role",
            values_callable=lambda enum: [item.value for item in enum],
        )
    )

    school_class: Mapped[SchoolClassORM] = relationship(back_populates="members")
