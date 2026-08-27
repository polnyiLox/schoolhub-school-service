from collections.abc import Mapping
from datetime import date
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HomeworkAttachmentORM, HomeworkORM, HomeworkRevisionORM


class HomeworkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, homework_id: UUID) -> HomeworkORM | None:
        query = select(HomeworkORM).where(HomeworkORM.id == homework_id)
        return await self.session.scalar(query)

    async def list(self, class_id: UUID) -> list[HomeworkORM]:
        query = (
            select(HomeworkORM)
            .where(HomeworkORM.class_id == class_id)
            .order_by(HomeworkORM.due_date, HomeworkORM.created_at)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_active_on(
        self,
        class_id: UUID,
        target_date: date,
    ) -> list[HomeworkORM]:
        query = select(HomeworkORM).where(
            HomeworkORM.class_id == class_id,
            HomeworkORM.assigned_date <= target_date,
            HomeworkORM.due_date >= target_date,
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(
        self,
        class_id: UUID,
        subject_id: UUID,
        assigned_date: date,
        due_date: date,
        text: str,
        created_by_telegram_id: int,
    ) -> HomeworkORM:
        homework = HomeworkORM(
            class_id=class_id,
            subject_id=subject_id,
            assigned_date=assigned_date,
            due_date=due_date,
            text=text,
            created_by_telegram_id=created_by_telegram_id,
        )
        self.session.add(homework)
        await self.session.flush()
        return homework

    async def update(
        self,
        homework: HomeworkORM,
        changes: Mapping[str, object],
    ) -> HomeworkORM:
        statement = (
            update(HomeworkORM)
            .where(HomeworkORM.id == homework.id)
            .values(**changes)
            .returning(HomeworkORM)
        )
        updated_homework = await self.session.scalar(statement)
        if updated_homework is None:
            raise RuntimeError("Updated homework was not returned by the database")
        await self.session.flush()
        return updated_homework

    async def delete(self, homework: HomeworkORM) -> None:
        statement = delete(HomeworkORM).where(HomeworkORM.id == homework.id)
        await self.session.execute(statement)
        await self.session.flush()

    async def create_revision(
        self,
        homework_id: UUID,
        old_text: str,
        new_text: str,
        changed_by_telegram_id: int,
    ) -> HomeworkRevisionORM:
        revision = HomeworkRevisionORM(
            homework_id=homework_id,
            old_text=old_text,
            new_text=new_text,
            changed_by_telegram_id=changed_by_telegram_id,
        )
        self.session.add(revision)
        await self.session.flush()
        return revision

    async def list_revisions(self, homework_id: UUID) -> list[HomeworkRevisionORM]:
        query = (
            select(HomeworkRevisionORM)
            .where(HomeworkRevisionORM.homework_id == homework_id)
            .order_by(HomeworkRevisionORM.created_at)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_attachment(
        self,
        homework_id: UUID,
        object_key: str,
        file_name: str,
        content_type: str,
        size: int,
        uploaded_by_telegram_id: int,
    ) -> HomeworkAttachmentORM:
        attachment = HomeworkAttachmentORM(
            homework_id=homework_id,
            object_key=object_key,
            file_name=file_name,
            content_type=content_type,
            size=size,
            uploaded_by_telegram_id=uploaded_by_telegram_id,
        )
        self.session.add(attachment)
        await self.session.flush()
        return attachment
