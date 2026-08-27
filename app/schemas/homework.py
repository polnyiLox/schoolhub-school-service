from datetime import date as date_type
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMReadModel


class HomeworkCreate(BaseModel):
    subject_id: UUID
    assigned_date: date_type
    due_date: date_type
    text: str = Field(min_length=1)


class HomeworkUpdate(BaseModel):
    subject_id: UUID | None = None
    assigned_date: date_type | None = None
    due_date: date_type | None = None
    text: str | None = Field(default=None, min_length=1)


class HomeworkRead(ORMReadModel):
    id: UUID
    class_id: UUID
    subject_id: UUID
    assigned_date: date_type
    due_date: date_type
    text: str
    created_by_telegram_id: int
    updated_by_telegram_id: int | None
    created_at: datetime
    updated_at: datetime


class HomeworkRevisionRead(ORMReadModel):
    id: UUID
    homework_id: UUID
    old_text: str
    new_text: str
    changed_by_telegram_id: int
    created_at: datetime


class HomeworkAttachmentCreate(BaseModel):
    object_key: str = Field(min_length=1, max_length=500)
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=150)
    size: int = Field(ge=0)


class HomeworkAttachmentRead(ORMReadModel):
    id: UUID
    homework_id: UUID
    object_key: str
    file_name: str
    content_type: str
    size: int
    uploaded_by_telegram_id: int
    created_at: datetime
