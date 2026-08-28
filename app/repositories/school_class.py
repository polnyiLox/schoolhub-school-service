from __future__ import annotations

import builtins
from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ClassMemberORM, SchoolClassORM


class SchoolClassRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, class_id: UUID) -> SchoolClassORM | None:
        query = select(SchoolClassORM).where(SchoolClassORM.id == class_id)
        return await self.session.scalar(query)

    async def list(self) -> list[SchoolClassORM]:
        query = select(SchoolClassORM).order_by(SchoolClassORM.name)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_for_telegram_id(self, telegram_id: int) -> builtins.list[SchoolClassORM]:
        query = (
            select(SchoolClassORM)
            .join(ClassMemberORM)
            .where(ClassMemberORM.telegram_id == telegram_id)
            .order_by(SchoolClassORM.name)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(
        self,
        name: str,
        academic_year: str,
        is_archived: bool = False,
    ) -> SchoolClassORM:
        school_class = SchoolClassORM(
            name=name,
            academic_year=academic_year,
            is_archived=is_archived,
        )
        self.session.add(school_class)
        await self.session.flush()
        return school_class

    async def update(
        self,
        school_class: SchoolClassORM,
        changes: Mapping[str, object],
    ) -> SchoolClassORM:
        statement = (
            update(SchoolClassORM)
            .where(SchoolClassORM.id == school_class.id)
            .values(**changes)
            .returning(SchoolClassORM)
        )
        updated_class = await self.session.scalar(statement)
        if updated_class is None:
            raise RuntimeError("Updated class was not returned by the database")
        await self.session.flush()
        return updated_class
