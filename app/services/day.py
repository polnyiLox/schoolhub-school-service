import logging
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from app.repositories import HomeworkRepository, SchoolEventRepository
from app.schemas import ClassDayRead, CurrentUser, DayHomework, DayLesson, SchoolEventRead
from app.services.access import ClassAccessService
from app.services.schedule import ScheduleService


logger = logging.getLogger(__name__)


class ClassDayService:
    def __init__(
        self, schedule_service: ScheduleService, homework_repository: HomeworkRepository,
        event_repository: SchoolEventRepository, access: ClassAccessService,
    ) -> None:
        self.schedule_service = schedule_service
        self.homework_repository = homework_repository
        self.event_repository = event_repository
        self.access = access

    async def get(self, class_id: UUID, target_date: date, actor: CurrentUser) -> ClassDayRead:
        logger.info("Building class day: class_id=%s, date=%s", class_id, target_date)
        await self.access.require_member(class_id, actor)
        schedule = await self.schedule_service.get_day(class_id, target_date, actor)
        logger.debug("Loading active homework from database: class_id=%s, date=%s", class_id, target_date)
        homeworks = await self.homework_repository.list_active_on(class_id, target_date)
        by_subject: dict[UUID, list[DayHomework]] = {}
        for homework in homeworks:
            by_subject.setdefault(homework.subject_id, []).append(
                DayHomework(id=homework.id, text=homework.text, due_date=homework.due_date)
            )
        lessons = [
            DayLesson(
                **lesson.model_dump(),
                homeworks=by_subject.get(lesson.subject.id, []) if lesson.subject else [],
            )
            for lesson in schedule.lessons
        ]
        day_start = datetime.combine(target_date, time.min, tzinfo=UTC)
        logger.debug("Loading school events from database: class_id=%s, date=%s", class_id, target_date)
        events = await self.event_repository.list_for_day(
            class_id, day_start, day_start + timedelta(days=1)
        )
        result = ClassDayRead(
            date=target_date,
            lessons=lessons,
            events=[SchoolEventRead.model_validate(event) for event in events],
        )
        logger.info(
            "Class day built: class_id=%s, date=%s, lessons=%d, events=%d",
            class_id, target_date, len(result.lessons), len(result.events),
        )
        return result
