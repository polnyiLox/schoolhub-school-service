from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, Field

from app.enums import SchoolEventType
from app.schemas.common import NonEmptyUpdateModel, ORMReadModel


class SchoolEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    event_type: SchoolEventType
    starts_at: datetime
    ends_at: datetime | None = None


class SchoolEventUpdate(NonEmptyUpdateModel):
    non_nullable_fields: ClassVar[frozenset[str]] = frozenset(
        {"title", "event_type", "starts_at"}
    )
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    event_type: SchoolEventType | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class SchoolEventRead(ORMReadModel):
    id: UUID
    class_id: UUID
    title: str
    description: str | None
    event_type: SchoolEventType
    starts_at: datetime
    ends_at: datetime | None
    created_by_telegram_id: int
    created_at: datetime
    updated_at: datetime
