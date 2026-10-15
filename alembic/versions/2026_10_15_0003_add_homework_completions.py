"""Add per-user homework completions.

Revision ID: 0003_homework_completions
Revises: 0002_add_outbox
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_homework_completions"
down_revision: str | None = "0002_add_outbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "homework_completions",
        sa.Column("homework_id", sa.Uuid(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["homework_id"], ["homeworks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "homework_id",
            "telegram_id",
            name="uq_homework_completion_user",
        ),
    )
    op.create_index(
        "ix_homework_completions_homework_id",
        "homework_completions",
        ["homework_id"],
    )
    op.create_index(
        "ix_homework_completions_telegram_id",
        "homework_completions",
        ["telegram_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_homework_completions_telegram_id", table_name="homework_completions")
    op.drop_index("ix_homework_completions_homework_id", table_name="homework_completions")
    op.drop_table("homework_completions")
