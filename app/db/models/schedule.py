from __future__ import annotations

from datetime import date, time
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, Date, Enum, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin
from app.enums import ScheduleOverrideType

if TYPE_CHECKING:
    from app.db.models.subject import SubjectORM


class ScheduleEntryORM(TimestampMixin, Base):
    __tablename__ = "schedule_entries"
    __table_args__ = (
        UniqueConstraint("class_id", "weekday", "lesson_number", name="uq_schedule_class_slot"),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_schedule_weekday"),
        CheckConstraint("lesson_number > 0", name="ck_schedule_lesson_number"),
        CheckConstraint("start_time < end_time", name="ck_schedule_time_order"),
    )

    class_id: Mapped[UUID] = mapped_column(
        ForeignKey("school_classes.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), index=True
    )
    weekday: Mapped[int] = mapped_column(Integer)
    lesson_number: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    room: Mapped[str | None] = mapped_column(String(100), nullable=True)

    subject: Mapped[SubjectORM] = relationship()


class ScheduleOverrideORM(TimestampMixin, Base):
    __tablename__ = "schedule_overrides"
    __table_args__ = (
        UniqueConstraint("class_id", "date", "lesson_number", name="uq_override_class_slot"),
        CheckConstraint("lesson_number > 0", name="ck_override_lesson_number"),
        CheckConstraint(
            "start_time IS NULL OR end_time IS NULL OR start_time < end_time",
            name="ck_override_time_order",
        ),
    )

    class_id: Mapped[UUID] = mapped_column(
        ForeignKey("school_classes.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    lesson_number: Mapped[int] = mapped_column(Integer)
    override_type: Mapped[ScheduleOverrideType] = mapped_column(
        Enum(
            ScheduleOverrideType,
            name="schedule_override_type",
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    subject_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=True
    )
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    room: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_telegram_id: Mapped[int] = mapped_column(BigInteger)

    subject: Mapped[SubjectORM | None] = relationship()
