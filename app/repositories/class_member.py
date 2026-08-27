from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ClassMemberORM
from app.enums import ClassMemberRole


class ClassMemberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, class_id: UUID, telegram_id: int) -> ClassMemberORM | None:
        query = select(ClassMemberORM).where(
            ClassMemberORM.class_id == class_id,
            ClassMemberORM.telegram_id == telegram_id,
        )
        return await self.session.scalar(query)

    async def list(self, class_id: UUID) -> list[ClassMemberORM]:
        query = (
            select(ClassMemberORM)
            .where(ClassMemberORM.class_id == class_id)
            .order_by(ClassMemberORM.created_at)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(
        self,
        class_id: UUID,
        telegram_id: int,
        role: ClassMemberRole,
    ) -> ClassMemberORM:
        member = ClassMemberORM(
            class_id=class_id,
            telegram_id=telegram_id,
            role=role,
        )
        self.session.add(member)
        await self.session.flush()
        return member

    async def update(
        self,
        member: ClassMemberORM,
        changes: Mapping[str, object],
    ) -> ClassMemberORM:
        statement = (
            update(ClassMemberORM)
            .where(ClassMemberORM.id == member.id)
            .values(**changes)
            .returning(ClassMemberORM)
        )
        updated_member = await self.session.scalar(statement)
        if updated_member is None:
            raise RuntimeError("Updated member was not returned by the database")
        await self.session.flush()
        return updated_member

    async def delete(self, member: ClassMemberORM) -> None:
        statement = delete(ClassMemberORM).where(ClassMemberORM.id == member.id)
        await self.session.execute(statement)
        await self.session.flush()
