from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.enums import SchoolEventType


class SchoolEventORM(TimestampMixin, Base):
    __tablename__ = "school_events"
    __table_args__ = (
        CheckConstraint(
            "ends_at IS NULL OR ends_at >= starts_at",
            name="ck_school_event_date_order",
        ),
    )

    class_id: Mapped[UUID] = mapped_column(
        ForeignKey("school_classes.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[SchoolEventType] = mapped_column(
        Enum(
            SchoolEventType,
            name="school_event_type",
            values_callable=lambda enum: [item.value for item in enum],
        )
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_telegram_id: Mapped[int] = mapped_column(BigInteger)
