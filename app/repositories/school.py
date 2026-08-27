from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    ClassMemberORM,
    HomeworkAttachmentORM,
    HomeworkORM,
    HomeworkRevisionORM,
    ScheduleEntryORM,
    ScheduleOverrideORM,
    SchoolClassORM,
    SchoolEventORM,
    SubjectORM,
)


def _apply_changes(entity: Any, changes: dict[str, Any]) -> None:
    for field, value in changes.items():
        setattr(entity, field, value)


class SchoolClassRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, class_id: UUID) -> SchoolClassORM | None:
        return await self.session.get(SchoolClassORM, class_id)

    async def list(self) -> list[SchoolClassORM]:
        result = await self.session.execute(select(SchoolClassORM).order_by(SchoolClassORM.name))
        return list(result.scalars().all())

    async def list_for_telegram_id(self, telegram_id: int) -> list[SchoolClassORM]:
        statement = (
            select(SchoolClassORM)
            .join(ClassMemberORM)
            .where(ClassMemberORM.telegram_id == telegram_id)
            .order_by(SchoolClassORM.name)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create(self, **values: Any) -> SchoolClassORM:
        entity = SchoolClassORM(**values)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: SchoolClassORM, changes: dict[str, Any]) -> SchoolClassORM:
        _apply_changes(entity, changes)
        await self.session.flush()
        return entity


class ClassMemberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, class_id: UUID, telegram_id: int) -> ClassMemberORM | None:
        result = await self.session.execute(
            select(ClassMemberORM).where(
                ClassMemberORM.class_id == class_id,
                ClassMemberORM.telegram_id == telegram_id,
            )
        )
        return result.scalar_one_or_none()

    async def list(self, class_id: UUID) -> list[ClassMemberORM]:
        result = await self.session.execute(
            select(ClassMemberORM)
            .where(ClassMemberORM.class_id == class_id)
            .order_by(ClassMemberORM.created_at)
        )
        return list(result.scalars().all())

    async def create(self, **values: Any) -> ClassMemberORM:
        entity = ClassMemberORM(**values)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: ClassMemberORM, changes: dict[str, Any]) -> ClassMemberORM:
        _apply_changes(entity, changes)
        await self.session.flush()
        return entity

    async def delete(self, entity: ClassMemberORM) -> None:
        await self.session.delete(entity)
        await self.session.flush()


class SubjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, subject_id: UUID) -> SubjectORM | None:
        return await self.session.get(SubjectORM, subject_id)

    async def list(self, class_id: UUID) -> list[SubjectORM]:
        result = await self.session.execute(
            select(SubjectORM).where(SubjectORM.class_id == class_id).order_by(SubjectORM.name)
        )
        return list(result.scalars().all())

    async def create(self, **values: Any) -> SubjectORM:
        entity = SubjectORM(**values)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: SubjectORM, changes: dict[str, Any]) -> SubjectORM:
        _apply_changes(entity, changes)
        await self.session.flush()
        return entity

    async def delete(self, entity: SubjectORM) -> None:
        await self.session.delete(entity)
        await self.session.flush()


class ScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_entry(self, entry_id: UUID) -> ScheduleEntryORM | None:
        return await self.session.get(ScheduleEntryORM, entry_id)

    async def get_slot(
        self, class_id: UUID, weekday: int, lesson_number: int
    ) -> ScheduleEntryORM | None:
        result = await self.session.execute(
            select(ScheduleEntryORM).where(
                ScheduleEntryORM.class_id == class_id,
                ScheduleEntryORM.weekday == weekday,
                ScheduleEntryORM.lesson_number == lesson_number,
            )
        )
        return result.scalar_one_or_none()

    async def list_week(self, class_id: UUID) -> list[ScheduleEntryORM]:
        result = await self.session.execute(
            select(ScheduleEntryORM)
            .options(selectinload(ScheduleEntryORM.subject))
            .where(ScheduleEntryORM.class_id == class_id)
            .order_by(ScheduleEntryORM.weekday, ScheduleEntryORM.lesson_number)
        )
        return list(result.scalars().all())

    async def list_for_weekday(self, class_id: UUID, weekday: int) -> list[ScheduleEntryORM]:
        result = await self.session.execute(
            select(ScheduleEntryORM)
            .options(selectinload(ScheduleEntryORM.subject))
            .where(ScheduleEntryORM.class_id == class_id, ScheduleEntryORM.weekday == weekday)
            .order_by(ScheduleEntryORM.lesson_number)
        )
        return list(result.scalars().all())

    async def create_entry(self, **values: Any) -> ScheduleEntryORM:
        entity = ScheduleEntryORM(**values)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update_entry(self, entity: ScheduleEntryORM, changes: dict[str, Any]) -> ScheduleEntryORM:
        _apply_changes(entity, changes)
        await self.session.flush()
        return entity

    async def delete_entry(self, entity: ScheduleEntryORM) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def get_override(self, override_id: UUID) -> ScheduleOverrideORM | None:
        statement = (
            select(ScheduleOverrideORM)
            .options(selectinload(ScheduleOverrideORM.subject))
            .where(ScheduleOverrideORM.id == override_id)
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_override_slot(
        self, class_id: UUID, target_date: date, lesson_number: int
    ) -> ScheduleOverrideORM | None:
        result = await self.session.execute(
            select(ScheduleOverrideORM).where(
                ScheduleOverrideORM.class_id == class_id,
                ScheduleOverrideORM.date == target_date,
                ScheduleOverrideORM.lesson_number == lesson_number,
            )
        )
        return result.scalar_one_or_none()

    async def list_overrides(self, class_id: UUID, target_date: date) -> list[ScheduleOverrideORM]:
        result = await self.session.execute(
            select(ScheduleOverrideORM)
            .options(selectinload(ScheduleOverrideORM.subject))
            .where(ScheduleOverrideORM.class_id == class_id, ScheduleOverrideORM.date == target_date)
            .order_by(ScheduleOverrideORM.lesson_number)
        )
        return list(result.scalars().all())

    async def create_override(self, **values: Any) -> ScheduleOverrideORM:
        entity = ScheduleOverrideORM(**values)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update_override(self, entity: ScheduleOverrideORM, changes: dict[str, Any]) -> ScheduleOverrideORM:
        _apply_changes(entity, changes)
        await self.session.flush()
        return entity

    async def delete_override(self, entity: ScheduleOverrideORM) -> None:
        await self.session.delete(entity)
        await self.session.flush()


class HomeworkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, homework_id: UUID) -> HomeworkORM | None:
        return await self.session.get(HomeworkORM, homework_id)

    async def list(self, class_id: UUID) -> list[HomeworkORM]:
        result = await self.session.execute(
            select(HomeworkORM)
            .where(HomeworkORM.class_id == class_id)
            .order_by(HomeworkORM.due_date, HomeworkORM.created_at)
        )
        return list(result.scalars().all())

    async def list_active_on(self, class_id: UUID, target_date: date) -> list[HomeworkORM]:
        result = await self.session.execute(
            select(HomeworkORM).where(
                HomeworkORM.class_id == class_id,
                HomeworkORM.assigned_date <= target_date,
                HomeworkORM.due_date >= target_date,
            )
        )
        return list(result.scalars().all())

    async def create(self, **values: Any) -> HomeworkORM:
        entity = HomeworkORM(**values)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: HomeworkORM, changes: dict[str, Any]) -> HomeworkORM:
        _apply_changes(entity, changes)
        await self.session.flush()
        return entity

    async def delete(self, entity: HomeworkORM) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def create_revision(self, **values: Any) -> HomeworkRevisionORM:
        entity = HomeworkRevisionORM(**values)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def list_revisions(self, homework_id: UUID) -> list[HomeworkRevisionORM]:
        result = await self.session.execute(
            select(HomeworkRevisionORM)
            .where(HomeworkRevisionORM.homework_id == homework_id)
            .order_by(HomeworkRevisionORM.created_at)
        )
        return list(result.scalars().all())

    async def create_attachment(self, **values: Any) -> HomeworkAttachmentORM:
        entity = HomeworkAttachmentORM(**values)
        self.session.add(entity)
        await self.session.flush()
        return entity


class SchoolEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, event_id: UUID) -> SchoolEventORM | None:
        return await self.session.get(SchoolEventORM, event_id)

    async def list(self, class_id: UUID) -> list[SchoolEventORM]:
        result = await self.session.execute(
            select(SchoolEventORM)
            .where(SchoolEventORM.class_id == class_id)
            .order_by(SchoolEventORM.starts_at)
        )
        return list(result.scalars().all())

    async def list_for_day(self, class_id: UUID, day_start: datetime, day_end: datetime) -> list[SchoolEventORM]:
        result = await self.session.execute(
            select(SchoolEventORM)
            .where(
                SchoolEventORM.class_id == class_id,
                SchoolEventORM.starts_at >= day_start,
                SchoolEventORM.starts_at < day_end,
            )
            .order_by(SchoolEventORM.starts_at)
        )
        return list(result.scalars().all())

    async def create(self, **values: Any) -> SchoolEventORM:
        entity = SchoolEventORM(**values)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: SchoolEventORM, changes: dict[str, Any]) -> SchoolEventORM:
        _apply_changes(entity, changes)
        await self.session.flush()
        return entity

    async def delete(self, entity: SchoolEventORM) -> None:
        await self.session.delete(entity)
        await self.session.flush()
