import logging
from datetime import date, time, timedelta
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import CacheNamespace, JsonCache
from app.db.integrity import get_constraint_name
from app.db.models import ScheduleEntryORM, ScheduleOverrideORM, SubjectORM
from app.enums import ScheduleLessonStatus, ScheduleOverrideType
from app.exceptions import (
    InvalidScheduleOverrideError,
    InvalidScheduleTimeError,
    ScheduleConflictError,
    ScheduleEntryNotFoundError,
    ScheduleOverrideNotFoundError,
    SubjectDoesNotBelongToClassError,
    SubjectNotFoundError,
)
from app.repositories import OutboxRepository, ScheduleRepository, SubjectRepository
from app.schemas import (
    CurrentUser,
    ScheduleDayRead,
    ScheduleEntryCreate,
    ScheduleEntryUpdate,
    ScheduleLesson,
    ScheduleOverrideCreate,
    ScheduleOverrideUpdate,
    ScheduleWeekRead,
    SubjectRead,
    build_domain_event,
)
from app.services.access import ClassAccessService
from app.services.base import EventCollectingService

logger = logging.getLogger(__name__)
schedule_day_adapter = TypeAdapter(ScheduleDayRead)
schedule_week_adapter = TypeAdapter(ScheduleWeekRead)


def merge_schedule(
    target_date: date,
    base_entries: list[ScheduleEntryORM],
    overrides: list[ScheduleOverrideORM],
) -> ScheduleDayRead:
    """Merge weekly entries with one-off changes, keeping cancelled lessons visible."""
    lessons: dict[int, ScheduleLesson] = {
        entry.lesson_number: ScheduleLesson(
            lesson_number=entry.lesson_number,
            subject=SubjectRead.model_validate(entry.subject),
            start_time=entry.start_time,
            end_time=entry.end_time,
            room=entry.room,
            status=ScheduleLessonStatus.NORMAL,
        )
        for entry in base_entries
    }
    for override in overrides:
        base = lessons.get(override.lesson_number)
        if override.override_type == ScheduleOverrideType.CANCELLED:
            if base is None:
                continue
            lessons[override.lesson_number] = base.model_copy(
                update={"status": ScheduleLessonStatus.CANCELLED, "reason": override.reason}
            )
            continue
        subject = SubjectRead.model_validate(override.subject) if override.subject else None
        lessons[override.lesson_number] = ScheduleLesson(
            lesson_number=override.lesson_number,
            subject=subject,
            start_time=override.start_time or (base.start_time if base else None),
            end_time=override.end_time or (base.end_time if base else None),
            room=override.room if override.room is not None else (base.room if base else None),
            status=ScheduleLessonStatus(override.override_type.value),
            reason=override.reason,
        )
    return ScheduleDayRead(date=target_date, lessons=[lessons[key] for key in sorted(lessons)])


class ScheduleService(EventCollectingService):
    def __init__(
        self,
        session: AsyncSession,
        repository: ScheduleRepository,
        subject_repository: SubjectRepository,
        access: ClassAccessService,
        cache: JsonCache | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        super().__init__(outbox_repository)
        self.session = session
        self.repository = repository
        self.subject_repository = subject_repository
        self.access = access
        self.cache = cache

    async def get_day(
        self, class_id: UUID, target_date: date, actor: CurrentUser
    ) -> ScheduleDayRead:
        logger.info("Getting daily schedule: class_id=%s, date=%s", class_id, target_date)
        await self.access.require_member(class_id, actor)
        result = await self._get_day(class_id, target_date)
        logger.info(
            "Daily schedule retrieved: class_id=%s, date=%s, lessons=%d",
            class_id,
            target_date,
            len(result.lessons),
        )
        return result

    async def _get_day(self, class_id: UUID, target_date: date) -> ScheduleDayRead:
        if self.cache is not None:
            cached = await self.cache.get(
                CacheNamespace.SCHEDULE_DAY,
                class_id,
                target_date.isoformat(),
                adapter=schedule_day_adapter,
            )
            if cached is not None:
                return cached

        logger.debug(
            "Loading daily schedule from database: class_id=%s, date=%s", class_id, target_date
        )
        base = await self.repository.list_for_weekday(class_id, target_date.weekday())
        overrides = await self.repository.list_overrides(class_id, target_date)
        result = merge_schedule(target_date, base, overrides)
        if self.cache is not None:
            await self.cache.set(
                CacheNamespace.SCHEDULE_DAY,
                result,
                class_id,
                target_date.isoformat(),
                adapter=schedule_day_adapter,
            )
        return result

    async def get_week(
        self, class_id: UUID, start_date: date, actor: CurrentUser
    ) -> ScheduleWeekRead:
        logger.info("Getting weekly schedule: class_id=%s, start_date=%s", class_id, start_date)
        await self.access.require_member(class_id, actor)
        monday = start_date - timedelta(days=start_date.weekday())
        if self.cache is not None:
            cached = await self.cache.get(
                CacheNamespace.SCHEDULE_WEEK,
                class_id,
                monday.isoformat(),
                adapter=schedule_week_adapter,
            )
            if cached is not None:
                logger.info(
                    "Weekly schedule retrieved: class_id=%s, days=%d", class_id, len(cached.days)
                )
                return cached

        days: list[ScheduleDayRead] = []
        for offset in range(7):
            days.append(await self._get_day(class_id, monday + timedelta(days=offset)))
        result = ScheduleWeekRead(days=days)
        if self.cache is not None:
            await self.cache.set(
                CacheNamespace.SCHEDULE_WEEK,
                result,
                class_id,
                monday.isoformat(),
                adapter=schedule_week_adapter,
            )
        logger.info("Weekly schedule retrieved: class_id=%s, days=%d", class_id, len(result.days))
        return result

    async def create_entry(
        self, class_id: UUID, data: ScheduleEntryCreate, actor: CurrentUser
    ) -> ScheduleEntryORM:
        logger.info(
            "Creating schedule entry: class_id=%s, weekday=%d, lesson=%d",
            class_id,
            data.weekday,
            data.lesson_number,
        )
        self.access.require_admin(actor)
        try:
            async with self.session.begin():
                await self.access.require_member(class_id, actor)
                await self._require_subject(class_id, data.subject_id)
                if await self.repository.get_slot(class_id, data.weekday, data.lesson_number):
                    logger.warning(
                        "Schedule slot conflict: class_id=%s, weekday=%d, lesson=%d",
                        class_id,
                        data.weekday,
                        data.lesson_number,
                    )
                    raise ScheduleConflictError()
                entity = await self.repository.create_entry(
                    class_id=class_id,
                    subject_id=data.subject_id,
                    weekday=data.weekday,
                    lesson_number=data.lesson_number,
                    start_time=data.start_time,
                    end_time=data.end_time,
                    room=data.room,
                )
                self._add_event("schedule.created", "schedule", entity.id, class_id, actor)
        except IntegrityError as error:
            self._raise_slot_conflict(
                error,
                expected_constraint="uq_schedule_class_slot",
                detail="The schedule slot is already occupied",
                class_id=class_id,
            )
        await self._invalidate_schedule(class_id)
        logger.info("Schedule entry created: class_id=%s, entry_id=%s", class_id, entity.id)
        return entity

    async def update_entry(
        self, class_id: UUID, entry_id: UUID, data: ScheduleEntryUpdate, actor: CurrentUser
    ) -> ScheduleEntryORM:
        logger.info("Updating schedule entry: class_id=%s, entry_id=%s", class_id, entry_id)
        self.access.require_admin(actor)
        try:
            async with self.session.begin():
                entity = await self._get_entry(class_id, entry_id)
                changes = data.model_dump(exclude_unset=True)
                subject_id = changes.get("subject_id", entity.subject_id)
                await self._require_subject(class_id, subject_id)
                start_time = changes.get("start_time", entity.start_time)
                end_time = changes.get("end_time", entity.end_time)
                self._validate_times(start_time, end_time)
                weekday = changes.get("weekday", entity.weekday)
                lesson_number = changes.get("lesson_number", entity.lesson_number)
                conflict = await self.repository.get_slot(class_id, weekday, lesson_number)
                if conflict is not None and conflict.id != entity.id:
                    logger.warning(
                        "Schedule slot conflict while updating: class_id=%s, entry_id=%s",
                        class_id,
                        entry_id,
                    )
                    raise ScheduleConflictError()
                entity = await self.repository.update_entry(entity, changes)
                self._add_event("schedule.updated", "schedule", entity.id, class_id, actor)
        except IntegrityError as error:
            self._raise_slot_conflict(
                error,
                expected_constraint="uq_schedule_class_slot",
                detail="The schedule slot is already occupied",
                class_id=class_id,
            )
        await self._invalidate_schedule(class_id)
        logger.info("Schedule entry updated: class_id=%s, entry_id=%s", class_id, entry_id)
        return entity

    async def delete_entry(self, class_id: UUID, entry_id: UUID, actor: CurrentUser) -> None:
        logger.info("Deleting schedule entry: class_id=%s, entry_id=%s", class_id, entry_id)
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self._get_entry(class_id, entry_id)
            await self.repository.delete_entry(entity)
            self._add_event("schedule.deleted", "schedule", entry_id, class_id, actor)
        await self._invalidate_schedule(class_id)
        logger.info("Schedule entry deleted: class_id=%s, entry_id=%s", class_id, entry_id)

    async def create_override(
        self, class_id: UUID, data: ScheduleOverrideCreate, actor: CurrentUser
    ) -> ScheduleOverrideORM:
        logger.info(
            "Creating schedule override: class_id=%s, date=%s, lesson=%d",
            class_id,
            data.date,
            data.lesson_number,
        )
        self.access.require_admin(actor)
        try:
            async with self.session.begin():
                await self.access.require_member(class_id, actor)
                await self._validate_override(
                    class_id, data.override_type, data.subject_id, data.start_time, data.end_time
                )
                if await self.repository.get_override_slot(class_id, data.date, data.lesson_number):
                    logger.warning(
                        "Schedule override conflict: class_id=%s, date=%s, lesson=%d",
                        class_id,
                        data.date,
                        data.lesson_number,
                    )
                    raise ScheduleConflictError("An override already exists for this lesson")
                entity = await self.repository.create_override(
                    class_id=class_id,
                    target_date=data.date,
                    lesson_number=data.lesson_number,
                    override_type=data.override_type,
                    subject_id=data.subject_id,
                    start_time=data.start_time,
                    end_time=data.end_time,
                    room=data.room,
                    reason=data.reason,
                    created_by_telegram_id=actor.telegram_id,
                )
                self._add_event(
                    "schedule.override_created",
                    "schedule_override",
                    entity.id,
                    class_id,
                    actor,
                )
        except IntegrityError as error:
            self._raise_slot_conflict(
                error,
                expected_constraint="uq_override_class_slot",
                detail="An override already exists for this lesson",
                class_id=class_id,
            )
        await self._invalidate_schedule(class_id)
        logger.info("Schedule override created: class_id=%s, override_id=%s", class_id, entity.id)
        return entity

    async def update_override(
        self, class_id: UUID, override_id: UUID, data: ScheduleOverrideUpdate, actor: CurrentUser
    ) -> ScheduleOverrideORM:
        logger.info(
            "Updating schedule override: class_id=%s, override_id=%s", class_id, override_id
        )
        self.access.require_admin(actor)
        try:
            async with self.session.begin():
                entity = await self._get_override(class_id, override_id)
                changes = data.model_dump(exclude_unset=True)
                effective_type = changes.get("override_type", entity.override_type)
                subject_id = changes.get("subject_id", entity.subject_id)
                start_time = changes.get("start_time", entity.start_time)
                end_time = changes.get("end_time", entity.end_time)
                await self._validate_override(
                    class_id, effective_type, subject_id, start_time, end_time
                )
                target_date = changes.get("date", entity.date)
                lesson_number = changes.get("lesson_number", entity.lesson_number)
                conflict = await self.repository.get_override_slot(
                    class_id, target_date, lesson_number
                )
                if conflict is not None and conflict.id != entity.id:
                    logger.warning(
                        "Schedule override conflict while updating: class_id=%s, override_id=%s",
                        class_id,
                        override_id,
                    )
                    raise ScheduleConflictError("An override already exists for this lesson")
                entity = await self.repository.update_override(entity, changes)
                self._add_event(
                    "schedule.override_updated",
                    "schedule_override",
                    entity.id,
                    class_id,
                    actor,
                )
        except IntegrityError as error:
            self._raise_slot_conflict(
                error,
                expected_constraint="uq_override_class_slot",
                detail="An override already exists for this lesson",
                class_id=class_id,
            )
        await self._invalidate_schedule(class_id)
        logger.info("Schedule override updated: class_id=%s, override_id=%s", class_id, override_id)
        return entity

    async def delete_override(self, class_id: UUID, override_id: UUID, actor: CurrentUser) -> None:
        logger.info(
            "Deleting schedule override: class_id=%s, override_id=%s", class_id, override_id
        )
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self._get_override(class_id, override_id)
            await self.repository.delete_override(entity)
            self._add_event(
                "schedule.override_deleted", "schedule_override", override_id, class_id, actor
            )
        await self._invalidate_schedule(class_id)
        logger.info("Schedule override deleted: class_id=%s, override_id=%s", class_id, override_id)

    async def _get_entry(self, class_id: UUID, entry_id: UUID) -> ScheduleEntryORM:
        entity = await self.repository.get_entry(entry_id)
        if entity is None or entity.class_id != class_id:
            logger.warning("Schedule entry not found: class_id=%s, entry_id=%s", class_id, entry_id)
            raise ScheduleEntryNotFoundError()
        return entity

    async def _get_override(self, class_id: UUID, override_id: UUID) -> ScheduleOverrideORM:
        entity = await self.repository.get_override(override_id)
        if entity is None or entity.class_id != class_id:
            logger.warning(
                "Schedule override not found: class_id=%s, override_id=%s", class_id, override_id
            )
            raise ScheduleOverrideNotFoundError()
        return entity

    async def _require_subject(self, class_id: UUID, subject_id: UUID) -> SubjectORM:
        subject = await self.subject_repository.get_by_id(subject_id)
        if subject is None:
            logger.warning(
                "Schedule subject not found: class_id=%s, subject_id=%s", class_id, subject_id
            )
            raise SubjectNotFoundError()
        if subject.class_id != class_id:
            logger.warning(
                "Schedule subject belongs to another class: class_id=%s, subject_id=%s",
                class_id,
                subject_id,
            )
            raise SubjectDoesNotBelongToClassError()
        return subject

    async def _validate_override(
        self,
        class_id: UUID,
        override_type: ScheduleOverrideType,
        subject_id: UUID | None,
        start_time: time | None,
        end_time: time | None,
    ) -> None:
        if override_type in {ScheduleOverrideType.ADDED, ScheduleOverrideType.REPLACED}:
            if subject_id is None:
                logger.warning(
                    "Subject is missing for schedule override: class_id=%s, type=%s",
                    class_id,
                    override_type,
                )
                raise InvalidScheduleOverrideError(
                    "A subject is required for added or replaced lessons"
                )
            await self._require_subject(class_id, subject_id)
        if (start_time is None) != (end_time is None):
            logger.warning("Incomplete time range for schedule override: class_id=%s", class_id)
            raise InvalidScheduleOverrideError("start_time and end_time must be provided together")
        if start_time is not None and end_time is not None:
            self._validate_times(start_time, end_time)

    @staticmethod
    def _validate_times(start_time: time, end_time: time) -> None:
        if start_time >= end_time:
            logger.warning("Invalid schedule time range: start=%s, end=%s", start_time, end_time)
            raise InvalidScheduleTimeError()

    def _add_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: UUID,
        class_id: UUID,
        actor: CurrentUser,
    ) -> None:
        self.record_event(
            build_domain_event(
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                actor_telegram_id=actor.telegram_id,
                class_id=class_id,
                payload={"entity_id": str(aggregate_id)},
            )
        )

    @staticmethod
    def _raise_slot_conflict(
        error: IntegrityError,
        *,
        expected_constraint: str,
        detail: str,
        class_id: UUID,
    ) -> None:
        constraint_name = get_constraint_name(error)
        if constraint_name != expected_constraint:
            raise error
        logger.warning(
            "Concurrent schedule conflict: class_id=%s, constraint=%s",
            class_id,
            constraint_name,
        )
        raise ScheduleConflictError(detail) from error

    async def _invalidate_schedule(self, class_id: UUID) -> None:
        if self.cache is None:
            return
        await self.cache.invalidate_pattern(CacheNamespace.SCHEDULE_DAY, class_id)
        await self.cache.invalidate_pattern(CacheNamespace.SCHEDULE_WEEK, class_id)
