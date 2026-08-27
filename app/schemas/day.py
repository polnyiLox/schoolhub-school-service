from datetime import date as date_type
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.schedule import ScheduleLesson
from app.schemas.school_event import SchoolEventRead


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
