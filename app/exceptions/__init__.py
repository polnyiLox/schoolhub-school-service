from .base import AccessDeniedError, AppError, ConflictError, NotFoundError, ValidationError
from .domain import (
    AttachmentTooLargeError,
    ClassAccessDeniedError,
    ClassMemberAlreadyExistsError,
    ClassMemberNotFoundError,
    ClassNotFoundError,
    HomeworkAttachmentNotFoundError,
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
    UnsupportedAttachmentTypeError,
)

__all__ = [name for name in globals() if name.endswith("Error")]
