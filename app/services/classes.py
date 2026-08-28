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
        logger.info("Creating class: academic_year=%s", data.academic_year)
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self.repository.create(
                name=data.name,
                academic_year=data.academic_year,
            )
        self.pending_events.append(build_domain_event(
            event_type="class.created", aggregate_type="class", aggregate_id=entity.id,
            actor_telegram_id=actor.telegram_id, class_id=entity.id, correlation_id=correlation_id,
            payload={"name": entity.name, "academic_year": entity.academic_year},
        ))
        logger.info("class created", extra={"class_id": str(entity.id), "telegram_id": actor.telegram_id, "correlation_id": correlation_id})
        return entity

    async def list(self, actor: CurrentUser) -> list[SchoolClassORM]:
        logger.info("Listing classes: telegram_id=%s", actor.telegram_id)
        if actor.global_role == GlobalRole.ADMIN:
            entities = await self.repository.list()
        else:
            entities = await self.repository.list_for_telegram_id(actor.telegram_id)
        logger.info("Classes listed: telegram_id=%s, count=%d", actor.telegram_id, len(entities))
        return entities

    async def get(self, class_id: UUID, actor: CurrentUser) -> SchoolClassORM:
        logger.info("Getting class: class_id=%s", class_id)
        await self.access.require_member(class_id, actor)
        entity = await self.repository.get_by_id(class_id)
        if entity is None:
            logger.warning("Class not found after access check: class_id=%s", class_id)
            raise ClassNotFoundError()
        logger.info("Class retrieved: class_id=%s", class_id)
        return entity

    async def update(self, class_id: UUID, data: SchoolClassUpdate, actor: CurrentUser) -> SchoolClassORM:
        logger.info("Updating class: class_id=%s", class_id)
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self.repository.get_by_id(class_id)
            if entity is None:
                logger.warning("Class update target not found: class_id=%s", class_id)
                raise ClassNotFoundError()
            entity = await self.repository.update(
                entity,
                data.model_dump(exclude_unset=True),
            )
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
        logger.info("Listing class members: class_id=%s", class_id)
        await self.access.require_member(class_id, actor)
        entities = await self.repository.list(class_id)
        logger.info("Class members listed: class_id=%s, count=%d", class_id, len(entities))
        return entities

    async def add(self, class_id: UUID, data: ClassMemberCreate, actor: CurrentUser, correlation_id: str | None = None) -> ClassMemberORM:
        logger.info("Adding class member: class_id=%s, telegram_id=%s", class_id, data.telegram_id)
        self.access.require_admin(actor)
        async with self.session.begin():
            if await self.class_repository.get_by_id(class_id) is None:
                logger.warning("Cannot add member because class was not found: class_id=%s", class_id)
                raise ClassNotFoundError()
            if await self.repository.get(class_id, data.telegram_id) is not None:
                logger.warning("Class member already exists: class_id=%s, telegram_id=%s", class_id, data.telegram_id)
                raise ClassMemberAlreadyExistsError()
            entity = await self.repository.create(
                class_id=class_id,
                telegram_id=data.telegram_id,
                role=data.role,
            )
        self.pending_events.append(build_domain_event(
            event_type="class.member_added", aggregate_type="class_member", aggregate_id=entity.id,
            actor_telegram_id=actor.telegram_id, class_id=class_id, correlation_id=correlation_id,
            payload={"telegram_id": entity.telegram_id, "role": entity.role.value},
        ))
        logger.info("member added", extra={"class_id": str(class_id), "telegram_id": data.telegram_id})
        return entity

    async def update(self, class_id: UUID, telegram_id: int, data: ClassMemberUpdate, actor: CurrentUser) -> ClassMemberORM:
        logger.info("Updating class member: class_id=%s, telegram_id=%s", class_id, telegram_id)
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self.repository.get(class_id, telegram_id)
            if entity is None:
                logger.warning("Class member not found: class_id=%s, telegram_id=%s", class_id, telegram_id)
                raise ClassMemberNotFoundError()
            entity = await self.repository.update(entity, data.model_dump())
        self.pending_events.append(build_domain_event(
            event_type="class.member_role_changed", aggregate_type="class_member", aggregate_id=entity.id,
            actor_telegram_id=actor.telegram_id, class_id=class_id,
            payload={"telegram_id": telegram_id, "role": entity.role.value},
        ))
        logger.info("member role changed", extra={"class_id": str(class_id), "telegram_id": telegram_id})
        return entity

    async def delete(self, class_id: UUID, telegram_id: int, actor: CurrentUser) -> None:
        logger.info("Deleting class member: class_id=%s, telegram_id=%s", class_id, telegram_id)
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self.repository.get(class_id, telegram_id)
            if entity is None:
                logger.warning("Class member not found: class_id=%s, telegram_id=%s", class_id, telegram_id)
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
        logger.info("Listing subjects: class_id=%s", class_id)
        await self.access.require_member(class_id, actor)
        entities = await self.repository.list(class_id)
        logger.info("Subjects listed: class_id=%s, count=%d", class_id, len(entities))
        return entities

    async def create(self, class_id: UUID, data: SubjectCreate, actor: CurrentUser) -> SubjectORM:
        logger.info("Creating subject: class_id=%s", class_id)
        self.access.require_admin(actor)
        async with self.session.begin():
            if await self.access.class_repository.get_by_id(class_id) is None:
                logger.warning("Cannot create subject because class was not found: class_id=%s", class_id)
                raise ClassNotFoundError()
            entity = await self.repository.create(
                class_id=class_id,
                name=data.name,
                teacher_name=data.teacher_name,
            )
        self._add_event("subject.created", entity, actor)
        logger.info("subject created", extra={"class_id": str(class_id), "subject_id": str(entity.id)})
        return entity

    async def update(self, class_id: UUID, subject_id: UUID, data: SubjectUpdate, actor: CurrentUser) -> SubjectORM:
        logger.info("Updating subject: class_id=%s, subject_id=%s", class_id, subject_id)
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self._get_for_class(class_id, subject_id)
            entity = await self.repository.update(
                entity,
                data.model_dump(exclude_unset=True),
            )
        self._add_event("subject.updated", entity, actor)
        logger.info("subject updated", extra={"class_id": str(class_id), "subject_id": str(subject_id)})
        return entity

    async def delete(self, class_id: UUID, subject_id: UUID, actor: CurrentUser) -> None:
        logger.info("Deleting subject: class_id=%s, subject_id=%s", class_id, subject_id)
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self._get_for_class(class_id, subject_id)
            await self.repository.delete(entity)
        self._add_event("subject.deleted", entity, actor)
        logger.info("subject deleted", extra={"class_id": str(class_id), "subject_id": str(subject_id)})

    async def _get_for_class(self, class_id: UUID, subject_id: UUID) -> SubjectORM:
        entity = await self.repository.get_by_id(subject_id)
        if entity is None:
            logger.warning("Subject not found: class_id=%s, subject_id=%s", class_id, subject_id)
            raise SubjectNotFoundError()
        if entity.class_id != class_id:
            logger.warning("Subject belongs to another class: class_id=%s, subject_id=%s", class_id, subject_id)
            raise SubjectDoesNotBelongToClassError()
        return entity

    def _add_event(self, event_type: str, entity: SubjectORM, actor: CurrentUser) -> None:
        self.pending_events.append(build_domain_event(
            event_type=event_type, aggregate_type="subject", aggregate_id=entity.id,
            actor_telegram_id=actor.telegram_id, class_id=entity.class_id,
            payload={"subject_id": str(entity.id), "name": entity.name},
        ))
