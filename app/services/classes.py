import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ClassMemberORM, SchoolClassORM, SubjectORM
from app.enums import GlobalRole
from app.exceptions import (
    ClassMemberAlreadyExistsError,
    ClassMemberNotFoundError,
    ClassNotFoundError,
    SubjectDoesNotBelongToClassError,
    SubjectNotFoundError,
)
from app.repositories import ClassMemberRepository, SchoolClassRepository, SubjectRepository
from app.schemas import (
    ClassMemberCreate,
    ClassMemberUpdate,
    CurrentUser,
    SchoolClassCreate,
    SchoolClassUpdate,
    SubjectCreate,
    SubjectUpdate,
    build_domain_event,
)
from app.services.access import ClassAccessService
from app.services.base import EventCollectingService

logger = logging.getLogger(__name__)


class SchoolClassService(EventCollectingService):
    def __init__(
        self, session: AsyncSession, repository: SchoolClassRepository, access: ClassAccessService
    ) -> None:
        super().__init__()
        self.session = session
        self.repository = repository
        self.access = access

    async def create(self, data: SchoolClassCreate, actor: CurrentUser, correlation_id: str | None = None) -> SchoolClassORM:
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self.repository.create(**data.model_dump())
        self.pending_events.append(build_domain_event(
            event_type="class.created", aggregate_type="class", aggregate_id=entity.id,
            actor_telegram_id=actor.telegram_id, class_id=entity.id, correlation_id=correlation_id,
            payload={"name": entity.name, "academic_year": entity.academic_year},
        ))
        logger.info("class created", extra={"class_id": str(entity.id), "telegram_id": actor.telegram_id, "correlation_id": correlation_id})
        return entity

    async def list(self, actor: CurrentUser) -> list[SchoolClassORM]:
        if actor.global_role == GlobalRole.ADMIN:
            return await self.repository.list()
        return await self.repository.list_for_telegram_id(actor.telegram_id)

    async def get(self, class_id: UUID, actor: CurrentUser) -> SchoolClassORM:
        await self.access.require_member(class_id, actor)
        entity = await self.repository.get_by_id(class_id)
        if entity is None:
            raise ClassNotFoundError()
        return entity

    async def update(self, class_id: UUID, data: SchoolClassUpdate, actor: CurrentUser) -> SchoolClassORM:
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self.repository.get_by_id(class_id)
            if entity is None:
                raise ClassNotFoundError()
            await self.repository.update(entity, data.model_dump(exclude_unset=True))
        logger.info("class updated", extra={"class_id": str(class_id), "telegram_id": actor.telegram_id})
        return entity


class ClassMemberService(EventCollectingService):
    def __init__(
        self, session: AsyncSession, repository: ClassMemberRepository,
        class_repository: SchoolClassRepository, access: ClassAccessService,
    ) -> None:
        super().__init__()
        self.session = session
        self.repository = repository
        self.class_repository = class_repository
        self.access = access

    async def list(self, class_id: UUID, actor: CurrentUser) -> list[ClassMemberORM]:
        await self.access.require_member(class_id, actor)
        return await self.repository.list(class_id)

    async def add(self, class_id: UUID, data: ClassMemberCreate, actor: CurrentUser, correlation_id: str | None = None) -> ClassMemberORM:
        self.access.require_admin(actor)
        async with self.session.begin():
            if await self.class_repository.get_by_id(class_id) is None:
                raise ClassNotFoundError()
            if await self.repository.get(class_id, data.telegram_id) is not None:
                raise ClassMemberAlreadyExistsError()
            entity = await self.repository.create(class_id=class_id, **data.model_dump())
        self.pending_events.append(build_domain_event(
            event_type="class.member_added", aggregate_type="class_member", aggregate_id=entity.id,
            actor_telegram_id=actor.telegram_id, class_id=class_id, correlation_id=correlation_id,
            payload={"telegram_id": entity.telegram_id, "role": entity.role.value},
        ))
        logger.info("member added", extra={"class_id": str(class_id), "telegram_id": data.telegram_id})
        return entity

    async def update(self, class_id: UUID, telegram_id: int, data: ClassMemberUpdate, actor: CurrentUser) -> ClassMemberORM:
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self.repository.get(class_id, telegram_id)
            if entity is None:
                raise ClassMemberNotFoundError()
            await self.repository.update(entity, data.model_dump())
        self.pending_events.append(build_domain_event(
            event_type="class.member_role_changed", aggregate_type="class_member", aggregate_id=entity.id,
            actor_telegram_id=actor.telegram_id, class_id=class_id,
            payload={"telegram_id": telegram_id, "role": entity.role.value},
        ))
        logger.info("member role changed", extra={"class_id": str(class_id), "telegram_id": telegram_id})
        return entity

    async def delete(self, class_id: UUID, telegram_id: int, actor: CurrentUser) -> None:
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self.repository.get(class_id, telegram_id)
            if entity is None:
                raise ClassMemberNotFoundError()
            entity_id = entity.id
            await self.repository.delete(entity)
        self.pending_events.append(build_domain_event(
            event_type="class.member_removed", aggregate_type="class_member", aggregate_id=entity_id,
            actor_telegram_id=actor.telegram_id, class_id=class_id, payload={"telegram_id": telegram_id},
        ))
        logger.info("member removed", extra={"class_id": str(class_id), "telegram_id": telegram_id})


class SubjectService(EventCollectingService):
    def __init__(self, session: AsyncSession, repository: SubjectRepository, access: ClassAccessService) -> None:
        super().__init__()
        self.session = session
        self.repository = repository
        self.access = access

    async def list(self, class_id: UUID, actor: CurrentUser) -> list[SubjectORM]:
        await self.access.require_member(class_id, actor)
        return await self.repository.list(class_id)

    async def create(self, class_id: UUID, data: SubjectCreate, actor: CurrentUser) -> SubjectORM:
        self.access.require_admin(actor)
        async with self.session.begin():
            if await self.access.class_repository.get_by_id(class_id) is None:
                raise ClassNotFoundError()
            entity = await self.repository.create(class_id=class_id, **data.model_dump())
        self._add_event("subject.created", entity, actor)
        logger.info("subject created", extra={"class_id": str(class_id), "subject_id": str(entity.id)})
        return entity

    async def update(self, class_id: UUID, subject_id: UUID, data: SubjectUpdate, actor: CurrentUser) -> SubjectORM:
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self._get_for_class(class_id, subject_id)
            await self.repository.update(entity, data.model_dump(exclude_unset=True))
        self._add_event("subject.updated", entity, actor)
        logger.info("subject updated", extra={"class_id": str(class_id), "subject_id": str(subject_id)})
        return entity

    async def delete(self, class_id: UUID, subject_id: UUID, actor: CurrentUser) -> None:
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self._get_for_class(class_id, subject_id)
            await self.repository.delete(entity)
        self._add_event("subject.deleted", entity, actor)
        logger.info("subject deleted", extra={"class_id": str(class_id), "subject_id": str(subject_id)})

    async def _get_for_class(self, class_id: UUID, subject_id: UUID) -> SubjectORM:
        entity = await self.repository.get_by_id(subject_id)
        if entity is None:
            raise SubjectNotFoundError()
        if entity.class_id != class_id:
            raise SubjectDoesNotBelongToClassError()
        return entity

    def _add_event(self, event_type: str, entity: SubjectORM, actor: CurrentUser) -> None:
        self.pending_events.append(build_domain_event(
            event_type=event_type, aggregate_type="subject", aggregate_id=entity.id,
            actor_telegram_id=actor.telegram_id, class_id=entity.class_id,
            payload={"subject_id": str(entity.id), "name": entity.name},
        ))
