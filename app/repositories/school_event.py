from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SchoolEventORM
from app.enums import SchoolEventType


class SchoolEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, event_id: UUID) -> SchoolEventORM | None:
        query = select(SchoolEventORM).where(SchoolEventORM.id == event_id)
        return await self.session.scalar(query)

    async def list(self, class_id: UUID) -> list[SchoolEventORM]:
        query = (
            select(SchoolEventORM)
            .where(SchoolEventORM.class_id == class_id)
            .order_by(SchoolEventORM.starts_at)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_for_day(
        self,
        class_id: UUID,
        day_start: datetime,
        day_end: datetime,
    ) -> list[SchoolEventORM]:
        query = (
            select(SchoolEventORM)
            .where(
                SchoolEventORM.class_id == class_id,
                SchoolEventORM.starts_at >= day_start,
                SchoolEventORM.starts_at < day_end,
            )
            .order_by(SchoolEventORM.starts_at)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(
        self,
        class_id: UUID,
        title: str,
        description: str | None,
        event_type: SchoolEventType,
        starts_at: datetime,
        ends_at: datetime | None,
        created_by_telegram_id: int,
    ) -> SchoolEventORM:
        school_event = SchoolEventORM(
            class_id=class_id,
            title=title,
            description=description,
            event_type=event_type,
            starts_at=starts_at,
            ends_at=ends_at,
            created_by_telegram_id=created_by_telegram_id,
        )
        self.session.add(school_event)
        await self.session.flush()
        return school_event

    async def update(
        self,
        school_event: SchoolEventORM,
        changes: Mapping[str, object],
    ) -> SchoolEventORM:
        statement = (
            update(SchoolEventORM)
            .where(SchoolEventORM.id == school_event.id)
            .values(**changes)
            .returning(SchoolEventORM)
        )
        updated_event = await self.session.scalar(statement)
        if updated_event is None:
            raise RuntimeError("Updated school event was not returned by the database")
        await self.session.flush()
        return updated_event

    async def delete(self, school_event: SchoolEventORM) -> None:
        statement = delete(SchoolEventORM).where(SchoolEventORM.id == school_event.id)
        await self.session.execute(statement)
        await self.session.flush()
