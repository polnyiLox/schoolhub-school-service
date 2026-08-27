from .access import ClassAccessService
from .classes import ClassMemberService, SchoolClassService, SubjectService
from .schedule import ScheduleService, merge_schedule
from .events import SchoolEventService
from .homework import HomeworkService
from .day import ClassDayService

__all__ = [name for name in globals() if name.endswith("Service")]
