from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SubjectORM


class SubjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, subject_id: UUID) -> SubjectORM | None:
        query = select(SubjectORM).where(SubjectORM.id == subject_id)
        return await self.session.scalar(query)

    async def list(self, class_id: UUID) -> list[SubjectORM]:
        query = select(SubjectORM).where(SubjectORM.class_id == class_id).order_by(SubjectORM.name)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(
        self,
        class_id: UUID,
        name: str,
        teacher_name: str | None,
    ) -> SubjectORM:
        subject = SubjectORM(
            class_id=class_id,
            name=name,
            teacher_name=teacher_name,
        )
        self.session.add(subject)
        await self.session.flush()
        return subject

    async def update(
        self,
        subject: SubjectORM,
        changes: Mapping[str, object],
    ) -> SubjectORM:
        statement = (
            update(SubjectORM)
            .where(SubjectORM.id == subject.id)
            .values(**changes)
            .returning(SubjectORM)
        )
        updated_subject = await self.session.scalar(statement)
        if updated_subject is None:
            raise RuntimeError("Updated subject was not returned by the database")
        await self.session.flush()
        return updated_subject

    async def delete(self, subject: SubjectORM) -> None:
        statement = delete(SubjectORM).where(SubjectORM.id == subject.id)
        await self.session.execute(statement)
        await self.session.flush()
