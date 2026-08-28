from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, Field

from app.enums import ClassMemberRole
from app.schemas.common import NonEmptyUpdateModel, ORMReadModel


class SchoolClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    academic_year: str = Field(pattern=r"^\d{4}/\d{4}$")


class SchoolClassUpdate(NonEmptyUpdateModel):
    non_nullable_fields: ClassVar[frozenset[str]] = frozenset(
        {"name", "academic_year", "is_archived"}
    )
    name: str | None = Field(default=None, min_length=1, max_length=100)
    academic_year: str | None = Field(default=None, pattern=r"^\d{4}/\d{4}$")
    is_archived: bool | None = None


class SchoolClassRead(ORMReadModel):
    id: UUID
    name: str
    academic_year: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class ClassMemberCreate(BaseModel):
    telegram_id: int
    role: ClassMemberRole


class ClassMemberUpdate(BaseModel):
    role: ClassMemberRole


class ClassMemberRead(ORMReadModel):
    id: UUID
    class_id: UUID
    telegram_id: int
    role: ClassMemberRole
    created_at: datetime
    updated_at: datetime
