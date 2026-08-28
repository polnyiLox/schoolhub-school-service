from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OutboxEventORM
from app.schemas import DomainEvent


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def enqueue(self, event: DomainEvent, topic: str) -> OutboxEventORM:
        entity = OutboxEventORM(
            id=event.event_id,
            topic=topic,
            payload=event.model_dump(mode="json"),
        )
        self.session.add(entity)
        return entity

    async def claim_pending(
        self,
        *,
        available_at: datetime,
        batch_size: int,
    ) -> list[OutboxEventORM]:
        query = (
            select(OutboxEventORM)
            .where(
                OutboxEventORM.status == "pending",
                OutboxEventORM.available_at <= available_at,
            )
            .order_by(OutboxEventORM.created_at)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.scalars(query)
        return list(result.all())

    async def mark_published(self, event_id: UUID, published_at: datetime) -> None:
        statement = (
            update(OutboxEventORM)
            .where(OutboxEventORM.id == event_id)
            .values(
                status="published",
                published_at=published_at,
                last_error=None,
            )
        )
        await self.session.execute(statement)

    async def mark_retry(
        self,
        event_id: UUID,
        *,
        attempts: int,
        available_at: datetime,
        last_error: str,
        terminal: bool,
    ) -> None:
        statement = (
            update(OutboxEventORM)
            .where(OutboxEventORM.id == event_id)
            .values(
                status="failed" if terminal else "pending",
                attempts=attempts,
                available_at=available_at,
                last_error=last_error,
            )
        )
        await self.session.execute(statement)

    async def delete_published_before(self, cutoff: datetime) -> None:
        statement = delete(OutboxEventORM).where(
            OutboxEventORM.status == "published",
            OutboxEventORM.published_at < cutoff,
        )
        await self.session.execute(statement)
