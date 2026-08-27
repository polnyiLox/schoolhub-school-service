from .class_member import ClassMemberRepository
from .homework import HomeworkRepository
from .schedule import ScheduleRepository
from .school_class import SchoolClassRepository
from .school_event import SchoolEventRepository
from .subject import SubjectRepository

__all__ = [name for name in globals() if name.endswith("Repository")]
