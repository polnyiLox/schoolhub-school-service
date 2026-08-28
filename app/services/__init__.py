from .access import ClassAccessService
from .classes import ClassMemberService, SchoolClassService, SubjectService
from .day import ClassDayService
from .events import SchoolEventService
from .homework import HomeworkService
from .schedule import ScheduleService, merge_schedule

__all__ = [name for name in globals() if name.endswith("Service")]
