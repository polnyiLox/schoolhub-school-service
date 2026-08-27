from collections.abc import Mapping
from datetime import date, time
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ScheduleEntryORM, ScheduleOverrideORM
from app.enums import ScheduleOverrideType


class ScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_entry(self, entry_id: UUID) -> ScheduleEntryORM | None:
        query = select(ScheduleEntryORM).where(ScheduleEntryORM.id == entry_id)
        return await self.session.scalar(query)

    async def get_slot(
        self,
        class_id: UUID,
        weekday: int,
        lesson_number: int,
    ) -> ScheduleEntryORM | None:
        query = select(ScheduleEntryORM).where(
            ScheduleEntryORM.class_id == class_id,
            ScheduleEntryORM.weekday == weekday,
            ScheduleEntryORM.lesson_number == lesson_number,
        )
        return await self.session.scalar(query)

    async def list_week(self, class_id: UUID) -> list[ScheduleEntryORM]:
        query = (
            select(ScheduleEntryORM)
            .options(selectinload(ScheduleEntryORM.subject))
            .where(ScheduleEntryORM.class_id == class_id)
            .order_by(ScheduleEntryORM.weekday, ScheduleEntryORM.lesson_number)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_for_weekday(
        self,
        class_id: UUID,
        weekday: int,
    ) -> list[ScheduleEntryORM]:
        query = (
            select(ScheduleEntryORM)
            .options(selectinload(ScheduleEntryORM.subject))
            .where(
                ScheduleEntryORM.class_id == class_id,
                ScheduleEntryORM.weekday == weekday,
            )
            .order_by(ScheduleEntryORM.lesson_number)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_entry(
        self,
        class_id: UUID,
        subject_id: UUID,
        weekday: int,
        lesson_number: int,
        start_time: time,
        end_time: time,
        room: str | None,
    ) -> ScheduleEntryORM:
        entry = ScheduleEntryORM(
            class_id=class_id,
            subject_id=subject_id,
            weekday=weekday,
            lesson_number=lesson_number,
            start_time=start_time,
            end_time=end_time,
            room=room,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def update_entry(
        self,
        entry: ScheduleEntryORM,
        changes: Mapping[str, object],
    ) -> ScheduleEntryORM:
        statement = (
            update(ScheduleEntryORM)
            .where(ScheduleEntryORM.id == entry.id)
            .values(**changes)
            .returning(ScheduleEntryORM)
        )
        updated_entry = await self.session.scalar(statement)
        if updated_entry is None:
            raise RuntimeError("Updated schedule entry was not returned by the database")
        await self.session.flush()
        return updated_entry

    async def delete_entry(self, entry: ScheduleEntryORM) -> None:
        statement = delete(ScheduleEntryORM).where(ScheduleEntryORM.id == entry.id)
        await self.session.execute(statement)
        await self.session.flush()

    async def get_override(self, override_id: UUID) -> ScheduleOverrideORM | None:
        query = (
            select(ScheduleOverrideORM)
            .options(selectinload(ScheduleOverrideORM.subject))
            .where(ScheduleOverrideORM.id == override_id)
        )
        return await self.session.scalar(query)

    async def get_override_slot(
        self,
        class_id: UUID,
        target_date: date,
        lesson_number: int,
    ) -> ScheduleOverrideORM | None:
        query = select(ScheduleOverrideORM).where(
            ScheduleOverrideORM.class_id == class_id,
            ScheduleOverrideORM.date == target_date,
            ScheduleOverrideORM.lesson_number == lesson_number,
        )
        return await self.session.scalar(query)

    async def list_overrides(
        self,
        class_id: UUID,
        target_date: date,
    ) -> list[ScheduleOverrideORM]:
        query = (
            select(ScheduleOverrideORM)
            .options(selectinload(ScheduleOverrideORM.subject))
            .where(
                ScheduleOverrideORM.class_id == class_id,
                ScheduleOverrideORM.date == target_date,
            )
            .order_by(ScheduleOverrideORM.lesson_number)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_override(
        self,
        class_id: UUID,
        target_date: date,
        lesson_number: int,
        override_type: ScheduleOverrideType,
        subject_id: UUID | None,
        start_time: time | None,
        end_time: time | None,
        room: str | None,
        reason: str | None,
        created_by_telegram_id: int,
    ) -> ScheduleOverrideORM:
        schedule_override = ScheduleOverrideORM(
            class_id=class_id,
            date=target_date,
            lesson_number=lesson_number,
            override_type=override_type,
            subject_id=subject_id,
            start_time=start_time,
            end_time=end_time,
            room=room,
            reason=reason,
            created_by_telegram_id=created_by_telegram_id,
        )
        self.session.add(schedule_override)
        await self.session.flush()
        return schedule_override

    async def update_override(
        self,
        schedule_override: ScheduleOverrideORM,
        changes: Mapping[str, object],
    ) -> ScheduleOverrideORM:
        statement = (
            update(ScheduleOverrideORM)
            .where(ScheduleOverrideORM.id == schedule_override.id)
            .values(**changes)
            .returning(ScheduleOverrideORM)
        )
        updated_override = await self.session.scalar(statement)
        if updated_override is None:
            raise RuntimeError("Updated schedule override was not returned by the database")
        await self.session.flush()
        return updated_override

    async def delete_override(self, schedule_override: ScheduleOverrideORM) -> None:
        statement = delete(ScheduleOverrideORM).where(
            ScheduleOverrideORM.id == schedule_override.id
        )
        await self.session.execute(statement)
        await self.session.flush()
