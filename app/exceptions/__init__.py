from .base import AccessDeniedError, AppError, ConflictError, NotFoundError, ValidationError
from .domain import (
    ClassAccessDeniedError,
    ClassMemberAlreadyExistsError,
    ClassMemberNotFoundError,
    ClassNotFoundError,
    HomeworkNotFoundError,
    InvalidHomeworkDatesError,
    InvalidScheduleOverrideError,
    InvalidScheduleTimeError,
    InvalidSchoolEventDatesError,
    ScheduleConflictError,
    ScheduleEntryNotFoundError,
    ScheduleOverrideNotFoundError,
    SchoolEventNotFoundError,
    SubjectDoesNotBelongToClassError,
    SubjectInUseError,
    SubjectNotFoundError,
)

__all__ = [name for name in globals() if name.endswith("Error")]
