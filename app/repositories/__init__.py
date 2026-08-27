from .school import (
    ClassMemberRepository,
    HomeworkRepository,
    ScheduleRepository,
    SchoolClassRepository,
    SchoolEventRepository,
    SubjectRepository,
)

__all__ = [name for name in globals() if name.endswith("Repository")]
