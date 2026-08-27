from datetime import date as date_type
from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.enums import ScheduleLessonStatus, ScheduleOverrideType
from app.schemas.common import ORMReadModel
from app.schemas.subject import SubjectRead


class ScheduleEntryCreate(BaseModel):
    subject_id: UUID
    weekday: int = Field(ge=0, le=6)
    lesson_number: int = Field(gt=0)
    start_time: time
    end_time: time
    room: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_time_order(self) -> "ScheduleEntryCreate":
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be earlier than end_time")
        return self


class ScheduleEntryUpdate(BaseModel):
    subject_id: UUID | None = None
    weekday: int | None = Field(default=None, ge=0, le=6)
    lesson_number: int | None = Field(default=None, gt=0)
    start_time: time | None = None
    end_time: time | None = None
    room: str | None = Field(default=None, max_length=100)


class ScheduleEntryRead(ORMReadModel):
    id: UUID
    class_id: UUID
    subject_id: UUID
    weekday: int
    lesson_number: int
    start_time: time
    end_time: time
    room: str | None
    created_at: datetime
    updated_at: datetime


class ScheduleOverrideCreate(BaseModel):
    date: date_type
    lesson_number: int = Field(gt=0)
    override_type: ScheduleOverrideType
    subject_id: UUID | None = None
    start_time: time | None = None
    end_time: time | None = None
    room: str | None = Field(default=None, max_length=100)
    reason: str | None = Field(default=None, max_length=500)


class ScheduleOverrideUpdate(BaseModel):
    date: date_type | None = None
    lesson_number: int | None = Field(default=None, gt=0)
    override_type: ScheduleOverrideType | None = None
    subject_id: UUID | None = None
    start_time: time | None = None
    end_time: time | None = None
    room: str | None = Field(default=None, max_length=100)
    reason: str | None = Field(default=None, max_length=500)


class ScheduleOverrideRead(ORMReadModel):
    id: UUID
    class_id: UUID
    date: date_type
    lesson_number: int
    override_type: ScheduleOverrideType
    subject_id: UUID | None
    start_time: time | None
    end_time: time | None
    room: str | None
    reason: str | None
    created_by_telegram_id: int
    created_at: datetime
    updated_at: datetime


class ScheduleLesson(BaseModel):
    lesson_number: int
    subject: SubjectRead | None
    start_time: time | None
    end_time: time | None
    room: str | None
    status: ScheduleLessonStatus
    reason: str | None = None


class ScheduleDayRead(BaseModel):
    date: date_type
    lessons: list[ScheduleLesson]


class ScheduleWeekRead(BaseModel):
    days: list[ScheduleDayRead]
