import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SchoolEventORM
from app.exceptions import InvalidSchoolEventDatesError, SchoolEventNotFoundError
from app.repositories import SchoolEventRepository
from app.schemas import CurrentUser, SchoolEventCreate, SchoolEventUpdate, build_domain_event
from app.services.access import ClassAccessService
from app.services.base import EventCollectingService

logger = logging.getLogger(__name__)


class SchoolEventService(EventCollectingService):
    def __init__(self, session: AsyncSession, repository: SchoolEventRepository, access: ClassAccessService) -> None:
        super().__init__()
        self.session = session
        self.repository = repository
        self.access = access

    async def list(self, class_id: UUID, actor: CurrentUser) -> list[SchoolEventORM]:
        await self.access.require_member(class_id, actor)
        return await self.repository.list(class_id)

    async def get(self, class_id: UUID, event_id: UUID, actor: CurrentUser) -> SchoolEventORM:
        await self.access.require_member(class_id, actor)
        return await self._get_for_class(class_id, event_id)

    async def create(self, class_id: UUID, data: SchoolEventCreate, actor: CurrentUser) -> SchoolEventORM:
        async with self.session.begin():
            await self.access.require_editor(class_id, actor)
            self._validate_dates(data.starts_at, data.ends_at)
            entity = await self.repository.create(
                class_id=class_id,
                title=data.title,
                description=data.description,
                event_type=data.event_type,
                starts_at=data.starts_at,
                ends_at=data.ends_at,
                created_by_telegram_id=actor.telegram_id,
            )
        self._add_event("school_event.created", entity, actor)
        logger.info("school event created", extra={"class_id": str(class_id), "event_id": str(entity.id), "telegram_id": actor.telegram_id})
        return entity

    async def update(self, class_id: UUID, event_id: UUID, data: SchoolEventUpdate, actor: CurrentUser) -> SchoolEventORM:
        async with self.session.begin():
            await self.access.require_editor(class_id, actor)
            entity = await self._get_for_class(class_id, event_id)
            changes = data.model_dump(exclude_unset=True)
            starts_at = changes.get("starts_at", entity.starts_at)
            ends_at = changes.get("ends_at", entity.ends_at)
            self._validate_dates(starts_at, ends_at)
            entity = await self.repository.update(entity, changes)
        self._add_event("school_event.updated", entity, actor)
        logger.info("school event updated", extra={"class_id": str(class_id), "event_id": str(event_id), "telegram_id": actor.telegram_id})
        return entity

    async def delete(self, class_id: UUID, event_id: UUID, actor: CurrentUser) -> None:
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self._get_for_class(class_id, event_id)
            await self.repository.delete(entity)
        self._add_event("school_event.deleted", entity, actor)
        logger.info("school event deleted", extra={"class_id": str(class_id), "event_id": str(event_id), "telegram_id": actor.telegram_id})

    async def _get_for_class(self, class_id: UUID, event_id: UUID) -> SchoolEventORM:
        entity = await self.repository.get_by_id(event_id)
        if entity is None or entity.class_id != class_id:
            raise SchoolEventNotFoundError()
        return entity

    @staticmethod
    def _validate_dates(starts_at: datetime, ends_at: datetime | None) -> None:
        if ends_at is not None and ends_at < starts_at:
            raise InvalidSchoolEventDatesError()

    def _add_event(self, event_type: str, entity: SchoolEventORM, actor: CurrentUser) -> None:
        self.pending_events.append(build_domain_event(
            event_type=event_type, aggregate_type="school_event", aggregate_id=entity.id,
            actor_telegram_id=actor.telegram_id, class_id=entity.class_id,
            payload={"event_id": str(entity.id), "event_type": entity.event_type.value},
        ))
