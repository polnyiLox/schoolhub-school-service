import logging
from datetime import date, time, timedelta
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import CacheNamespace, JsonCache
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
from app.repositories import ScheduleRepository, SubjectRepository
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
        self, session: AsyncSession, repository: ScheduleRepository,
        subject_repository: SubjectRepository, access: ClassAccessService,
        cache: JsonCache | None = None,
    ) -> None:
        super().__init__()
        self.session = session
        self.repository = repository
        self.subject_repository = subject_repository
        self.access = access
        self.cache = cache

    async def get_day(self, class_id: UUID, target_date: date, actor: CurrentUser) -> ScheduleDayRead:
        await self.access.require_member(class_id, actor)
        return await self._get_day(class_id, target_date)

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

    async def get_week(self, class_id: UUID, start_date: date, actor: CurrentUser) -> ScheduleWeekRead:
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
        return result

    async def create_entry(self, class_id: UUID, data: ScheduleEntryCreate, actor: CurrentUser) -> ScheduleEntryORM:
        self.access.require_admin(actor)
        async with self.session.begin():
            await self._require_subject(class_id, data.subject_id)
            if await self.repository.get_slot(class_id, data.weekday, data.lesson_number):
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
        await self._invalidate_schedule(class_id)
        logger.info("schedule changed", extra={"class_id": str(class_id), "schedule_entry_id": str(entity.id)})
        return entity

    async def update_entry(self, class_id: UUID, entry_id: UUID, data: ScheduleEntryUpdate, actor: CurrentUser) -> ScheduleEntryORM:
        self.access.require_admin(actor)
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
                raise ScheduleConflictError()
            entity = await self.repository.update_entry(entity, changes)
        self._add_event("schedule.updated", "schedule", entity.id, class_id, actor)
        await self._invalidate_schedule(class_id)
        logger.info("schedule changed", extra={"class_id": str(class_id), "schedule_entry_id": str(entry_id)})
        return entity

    async def delete_entry(self, class_id: UUID, entry_id: UUID, actor: CurrentUser) -> None:
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self._get_entry(class_id, entry_id)
            await self.repository.delete_entry(entity)
        self._add_event("schedule.deleted", "schedule", entry_id, class_id, actor)
        await self._invalidate_schedule(class_id)
        logger.info("schedule changed", extra={"class_id": str(class_id), "schedule_entry_id": str(entry_id)})

    async def create_override(self, class_id: UUID, data: ScheduleOverrideCreate, actor: CurrentUser) -> ScheduleOverrideORM:
        self.access.require_admin(actor)
        async with self.session.begin():
            await self._validate_override(class_id, data.override_type, data.subject_id, data.start_time, data.end_time)
            if await self.repository.get_override_slot(class_id, data.date, data.lesson_number):
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
        self._add_event("schedule.override_created", "schedule_override", entity.id, class_id, actor)
        await self._invalidate_schedule(class_id)
        logger.info("schedule override created", extra={"class_id": str(class_id), "override_id": str(entity.id)})
        return entity

    async def update_override(self, class_id: UUID, override_id: UUID, data: ScheduleOverrideUpdate, actor: CurrentUser) -> ScheduleOverrideORM:
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self._get_override(class_id, override_id)
            changes = data.model_dump(exclude_unset=True)
            effective_type = changes.get("override_type", entity.override_type)
            subject_id = changes.get("subject_id", entity.subject_id)
            start_time = changes.get("start_time", entity.start_time)
            end_time = changes.get("end_time", entity.end_time)
            await self._validate_override(class_id, effective_type, subject_id, start_time, end_time)
            target_date = changes.get("date", entity.date)
            lesson_number = changes.get("lesson_number", entity.lesson_number)
            conflict = await self.repository.get_override_slot(class_id, target_date, lesson_number)
            if conflict is not None and conflict.id != entity.id:
                raise ScheduleConflictError("An override already exists for this lesson")
            entity = await self.repository.update_override(entity, changes)
        self._add_event("schedule.override_updated", "schedule_override", entity.id, class_id, actor)
        await self._invalidate_schedule(class_id)
        logger.info("schedule override updated", extra={"class_id": str(class_id), "override_id": str(override_id)})
        return entity

    async def delete_override(self, class_id: UUID, override_id: UUID, actor: CurrentUser) -> None:
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self._get_override(class_id, override_id)
            await self.repository.delete_override(entity)
        self._add_event("schedule.override_deleted", "schedule_override", override_id, class_id, actor)
        await self._invalidate_schedule(class_id)
        logger.info("schedule override deleted", extra={"class_id": str(class_id), "override_id": str(override_id)})

    async def _get_entry(self, class_id: UUID, entry_id: UUID) -> ScheduleEntryORM:
        entity = await self.repository.get_entry(entry_id)
        if entity is None or entity.class_id != class_id:
            raise ScheduleEntryNotFoundError()
        return entity

    async def _get_override(self, class_id: UUID, override_id: UUID) -> ScheduleOverrideORM:
        entity = await self.repository.get_override(override_id)
        if entity is None or entity.class_id != class_id:
            raise ScheduleOverrideNotFoundError()
        return entity

    async def _require_subject(self, class_id: UUID, subject_id: UUID) -> SubjectORM:
        subject = await self.subject_repository.get_by_id(subject_id)
        if subject is None:
            raise SubjectNotFoundError()
        if subject.class_id != class_id:
            raise SubjectDoesNotBelongToClassError()
        return subject

    async def _validate_override(
        self, class_id: UUID, override_type: ScheduleOverrideType,
        subject_id: UUID | None, start_time: time | None, end_time: time | None,
    ) -> None:
        if override_type in {ScheduleOverrideType.ADDED, ScheduleOverrideType.REPLACED}:
            if subject_id is None:
                raise InvalidScheduleOverrideError("A subject is required for added or replaced lessons")
            await self._require_subject(class_id, subject_id)
        if (start_time is None) != (end_time is None):
            raise InvalidScheduleOverrideError("start_time and end_time must be provided together")
        if start_time is not None and end_time is not None:
            self._validate_times(start_time, end_time)

    @staticmethod
    def _validate_times(start_time: time, end_time: time) -> None:
        if start_time >= end_time:
            raise InvalidScheduleTimeError()

    def _add_event(self, event_type: str, aggregate_type: str, aggregate_id: UUID, class_id: UUID, actor: CurrentUser) -> None:
        self.pending_events.append(build_domain_event(
            event_type=event_type, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
            actor_telegram_id=actor.telegram_id, class_id=class_id,
            payload={"entity_id": str(aggregate_id)},
        ))

    async def _invalidate_schedule(self, class_id: UUID) -> None:
        if self.cache is None:
            return
        await self.cache.invalidate_pattern(CacheNamespace.SCHEDULE_DAY, class_id)
        await self.cache.invalidate_pattern(CacheNamespace.SCHEDULE_WEEK, class_id)
