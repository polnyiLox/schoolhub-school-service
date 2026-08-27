from app.exceptions.base import AccessDeniedError, ConflictError, NotFoundError, ValidationError


class ClassNotFoundError(NotFoundError):
    default_detail = "Class not found"


class ClassMemberNotFoundError(NotFoundError):
    default_detail = "Class member not found"


class ClassAccessDeniedError(AccessDeniedError):
    default_detail = "Access to the class is denied"


class ClassMemberAlreadyExistsError(ConflictError):
    default_detail = "Class member already exists"


class SubjectNotFoundError(NotFoundError):
    default_detail = "Subject not found"


class SubjectDoesNotBelongToClassError(ValidationError):
    default_detail = "Subject does not belong to the class"


class ScheduleEntryNotFoundError(NotFoundError):
    default_detail = "Schedule entry not found"


class ScheduleConflictError(ConflictError):
    default_detail = "The schedule slot is already occupied"


class ScheduleOverrideNotFoundError(NotFoundError):
    default_detail = "Schedule override not found"


class InvalidScheduleOverrideError(ValidationError):
    default_detail = "Invalid schedule override"


class InvalidScheduleTimeError(ValidationError):
    default_detail = "Lesson start time must be earlier than end time"


class HomeworkNotFoundError(NotFoundError):
    default_detail = "Homework not found"


class InvalidHomeworkDatesError(ValidationError):
    default_detail = "Homework due date cannot be earlier than assigned date"


class SchoolEventNotFoundError(NotFoundError):
    default_detail = "School event not found"


class InvalidSchoolEventDatesError(ValidationError):
    default_detail = "Event end cannot be earlier than its start"
