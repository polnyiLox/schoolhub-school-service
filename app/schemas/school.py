from datetime import date as date_type
from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.enums import ClassMemberRole, GlobalRole, ScheduleLessonStatus, ScheduleOverrideType, SchoolEventType


class ORMReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CurrentUser(BaseModel):
    user_id: UUID
    telegram_id: int
    global_role: GlobalRole


class SchoolClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    academic_year: str = Field(pattern=r"^\d{4}/\d{4}$")


class SchoolClassUpdate(BaseModel):
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


class SchoolEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    event_type: SchoolEventType
    starts_at: datetime
    ends_at: datetime | None = None


class SchoolEventUpdate(BaseModel):
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


class DayHomework(BaseModel):
    id: UUID
    text: str
    due_date: date_type


class DayLesson(ScheduleLesson):
    homeworks: list[DayHomework] = Field(default_factory=list)


class ClassDayRead(BaseModel):
    date: date_type
    lessons: list[DayLesson]
    events: list[SchoolEventRead]
