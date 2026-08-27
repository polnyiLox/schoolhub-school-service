from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.subject import SubjectORM


class HomeworkORM(TimestampMixin, Base):
    __tablename__ = "homeworks"
    __table_args__ = (CheckConstraint("due_date >= assigned_date", name="ck_homework_date_order"),)

    class_id: Mapped[UUID] = mapped_column(
        ForeignKey("school_classes.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), index=True
    )
    assigned_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    text: Mapped[str] = mapped_column(Text)
    created_by_telegram_id: Mapped[int] = mapped_column(BigInteger)
    updated_by_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    subject: Mapped[SubjectORM] = relationship()
    revisions: Mapped[list[HomeworkRevisionORM]] = relationship(
        back_populates="homework", cascade="all, delete-orphan"
    )
    attachments: Mapped[list[HomeworkAttachmentORM]] = relationship(
        back_populates="homework", cascade="all, delete-orphan"
    )


class HomeworkRevisionORM(Base):
    __tablename__ = "homework_revisions"

    homework_id: Mapped[UUID] = mapped_column(
        ForeignKey("homeworks.id", ondelete="CASCADE"), index=True
    )
    old_text: Mapped[str] = mapped_column(Text)
    new_text: Mapped[str] = mapped_column(Text)
    changed_by_telegram_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    homework: Mapped[HomeworkORM] = relationship(back_populates="revisions")


class HomeworkAttachmentORM(Base):
    __tablename__ = "homework_attachments"
    __table_args__ = (CheckConstraint("size >= 0", name="ck_attachment_size"),)

    homework_id: Mapped[UUID] = mapped_column(
        ForeignKey("homeworks.id", ondelete="CASCADE"), index=True
    )
    object_key: Mapped[str] = mapped_column(String(500), unique=True)
    file_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(150))
    size: Mapped[int] = mapped_column(BigInteger)
    uploaded_by_telegram_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    homework: Mapped[HomeworkORM] = relationship(back_populates="attachments")
