from enum import StrEnum


class GlobalRole(StrEnum):
    ADMIN = "admin"
    USER = "user"


class ClassMemberRole(StrEnum):
    STUDENT = "student"
    EDITOR = "editor"


class ScheduleOverrideType(StrEnum):
    REPLACED = "replaced"
    CANCELLED = "cancelled"
    ADDED = "added"


class ScheduleLessonStatus(StrEnum):
    NORMAL = "normal"
    REPLACED = "replaced"
    CANCELLED = "cancelled"
    ADDED = "added"


class SchoolEventType(StrEnum):
    EXAM = "exam"
    MEETING = "meeting"
    TRIP = "trip"
    REMINDER = "reminder"
    OTHER = "other"


__all__ = [
    "ClassMemberRole",
    "GlobalRole",
    "ScheduleLessonStatus",
    "ScheduleOverrideType",
    "SchoolEventType",
]
