"""Create the initial School Service schema.

Revision ID: 0001_school_schema
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_school_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

member_role = postgresql.ENUM("student", "editor", name="class_member_role", create_type=False)
override_type = postgresql.ENUM(
    "replaced", "cancelled", "added", name="schedule_override_type", create_type=False
)
event_type = postgresql.ENUM(
    "exam", "meeting", "trip", "reminder", "other", name="school_event_type", create_type=False
)


def upgrade() -> None:
    member_role.create(op.get_bind(), checkfirst=True)
    override_type.create(op.get_bind(), checkfirst=True)
    event_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "school_classes",
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("academic_year", sa.String(9), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "class_members",
        sa.Column("class_id", sa.Uuid(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("role", member_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["class_id"], ["school_classes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("class_id", "telegram_id", name="uq_class_member_telegram"),
    )
    op.create_index("ix_class_members_class_telegram", "class_members", ["class_id", "telegram_id"])
    op.create_table(
        "subjects",
        sa.Column("class_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("teacher_name", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["class_id"], ["school_classes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subjects_class_id", "subjects", ["class_id"])
    op.create_table(
        "schedule_entries",
        sa.Column("class_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("lesson_number", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("room", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_schedule_weekday"),
        sa.CheckConstraint("lesson_number > 0", name="ck_schedule_lesson_number"),
        sa.CheckConstraint("start_time < end_time", name="ck_schedule_time_order"),
        sa.ForeignKeyConstraint(["class_id"], ["school_classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("class_id", "weekday", "lesson_number", name="uq_schedule_class_slot"),
    )
    op.create_index("ix_schedule_entries_class_id", "schedule_entries", ["class_id"])
    op.create_index("ix_schedule_entries_subject_id", "schedule_entries", ["subject_id"])
    op.create_table(
        "schedule_overrides",
        sa.Column("class_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("lesson_number", sa.Integer(), nullable=False),
        sa.Column("override_type", override_type, nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("room", sa.String(100), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("created_by_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("lesson_number > 0", name="ck_override_lesson_number"),
        sa.CheckConstraint("start_time IS NULL OR end_time IS NULL OR start_time < end_time", name="ck_override_time_order"),
        sa.ForeignKeyConstraint(["class_id"], ["school_classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("class_id", "date", "lesson_number", name="uq_override_class_slot"),
    )
    op.create_index("ix_schedule_overrides_class_id", "schedule_overrides", ["class_id"])
    op.create_index("ix_schedule_overrides_date", "schedule_overrides", ["date"])
    op.create_table(
        "homeworks",
        sa.Column("class_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_by_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("updated_by_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("due_date >= assigned_date", name="ck_homework_date_order"),
        sa.ForeignKeyConstraint(["class_id"], ["school_classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_homeworks_class_id", "homeworks", ["class_id"])
    op.create_index("ix_homeworks_due_date", "homeworks", ["due_date"])
    op.create_index("ix_homeworks_subject_id", "homeworks", ["subject_id"])
    op.create_table(
        "school_events",
        sa.Column("class_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("ends_at IS NULL OR ends_at >= starts_at", name="ck_school_event_date_order"),
        sa.ForeignKeyConstraint(["class_id"], ["school_classes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_school_events_class_id", "school_events", ["class_id"])
    op.create_index("ix_school_events_starts_at", "school_events", ["starts_at"])
    op.create_table(
        "homework_revisions",
        sa.Column("homework_id", sa.Uuid(), nullable=False),
        sa.Column("old_text", sa.Text(), nullable=False),
        sa.Column("new_text", sa.Text(), nullable=False),
        sa.Column("changed_by_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["homework_id"], ["homeworks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_homework_revisions_homework_id", "homework_revisions", ["homework_id"])
    op.create_table(
        "homework_attachments",
        sa.Column("homework_id", sa.Uuid(), nullable=False),
        sa.Column("object_key", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(150), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_by_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("size >= 0", name="ck_attachment_size"),
        sa.ForeignKeyConstraint(["homework_id"], ["homeworks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index("ix_homework_attachments_homework_id", "homework_attachments", ["homework_id"])


def downgrade() -> None:
    op.drop_table("homework_attachments")
    op.drop_table("homework_revisions")
    op.drop_table("school_events")
    op.drop_table("homeworks")
    op.drop_table("schedule_overrides")
    op.drop_table("schedule_entries")
    op.drop_table("subjects")
    op.drop_table("class_members")
    op.drop_table("school_classes")
    event_type.drop(op.get_bind(), checkfirst=True)
    override_type.drop(op.get_bind(), checkfirst=True)
    member_role.drop(op.get_bind(), checkfirst=True)
