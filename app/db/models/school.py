from datetime import UTC, date, datetime, time
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin
from app.enums import ClassMemberRole, ScheduleOverrideType, SchoolEventType


class SchoolClassORM(TimestampMixin, Base):
    __tablename__ = "school_classes"

    name: Mapped[str] = mapped_column(String(100))
    academic_year: Mapped[str] = mapped_column(String(9))
    is_archived: Mapped[bool] = mapped_column(default=False)

    members: Mapped[list["ClassMemberORM"]] = relationship(
        back_populates="school_class", cascade="all, delete-orphan"
    )
    subjects: Mapped[list["SubjectORM"]] = relationship(
        back_populates="school_class", cascade="all, delete-orphan"
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
        Enum(ClassMemberRole, name="class_member_role", values_callable=lambda e: [v.value for v in e])
    )

    school_class: Mapped[SchoolClassORM] = relationship(back_populates="members")


class SubjectORM(TimestampMixin, Base):
    __tablename__ = "subjects"

    class_id: Mapped[UUID] = mapped_column(
        ForeignKey("school_classes.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(150))
    teacher_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    school_class: Mapped[SchoolClassORM] = relationship(back_populates="subjects")


class ScheduleEntryORM(TimestampMixin, Base):
    __tablename__ = "schedule_entries"
    __table_args__ = (
        UniqueConstraint(
            "class_id", "weekday", "lesson_number", name="uq_schedule_class_slot"
        ),
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
            values_callable=lambda e: [v.value for v in e],
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


class HomeworkORM(TimestampMixin, Base):
    __tablename__ = "homeworks"
    __table_args__ = (
        CheckConstraint("due_date >= assigned_date", name="ck_homework_date_order"),
    )

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
    revisions: Mapped[list["HomeworkRevisionORM"]] = relationship(
        back_populates="homework", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["HomeworkAttachmentORM"]] = relationship(
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


class SchoolEventORM(TimestampMixin, Base):
    __tablename__ = "school_events"
    __table_args__ = (
        CheckConstraint(
            "ends_at IS NULL OR ends_at >= starts_at", name="ck_school_event_date_order"
        ),
    )

    class_id: Mapped[UUID] = mapped_column(
        ForeignKey("school_classes.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[SchoolEventType] = mapped_column(
        Enum(SchoolEventType, name="school_event_type", values_callable=lambda e: [v.value for v in e])
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_telegram_id: Mapped[int] = mapped_column(BigInteger)
