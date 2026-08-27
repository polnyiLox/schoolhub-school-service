from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMReadModel


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    teacher_name: str | None = Field(default=None, max_length=200)


class SubjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    teacher_name: str | None = Field(default=None, max_length=200)


class SubjectRead(ORMReadModel):
    id: UUID
    class_id: UUID
    name: str
    teacher_name: str | None
    created_at: datetime
    updated_at: datetime
