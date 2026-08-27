import logging
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HomeworkORM, HomeworkRevisionORM
from app.exceptions import (
    HomeworkNotFoundError,
    InvalidHomeworkDatesError,
    SubjectDoesNotBelongToClassError,
    SubjectNotFoundError,
)
from app.repositories import HomeworkRepository, SubjectRepository
from app.schemas import CurrentUser, HomeworkCreate, HomeworkUpdate, build_domain_event
from app.services.access import ClassAccessService
from app.services.base import EventCollectingService

logger = logging.getLogger(__name__)


class HomeworkService(EventCollectingService):
    def __init__(
        self, session: AsyncSession, repository: HomeworkRepository,
        subject_repository: SubjectRepository, access: ClassAccessService,
    ) -> None:
        super().__init__()
        self.session = session
        self.repository = repository
        self.subject_repository = subject_repository
        self.access = access

    async def list(self, class_id: UUID, actor: CurrentUser) -> list[HomeworkORM]:
        await self.access.require_member(class_id, actor)
        return await self.repository.list(class_id)

    async def get(self, class_id: UUID, homework_id: UUID, actor: CurrentUser) -> HomeworkORM:
        await self.access.require_member(class_id, actor)
        return await self._get_for_class(class_id, homework_id)

    async def history(self, class_id: UUID, homework_id: UUID, actor: CurrentUser) -> list[HomeworkRevisionORM]:
        await self.access.require_member(class_id, actor)
        await self._get_for_class(class_id, homework_id)
        return await self.repository.list_revisions(homework_id)

    async def create(self, class_id: UUID, data: HomeworkCreate, actor: CurrentUser, correlation_id: str | None = None) -> HomeworkORM:
        async with self.session.begin():
            await self.access.require_editor(class_id, actor)
            self._validate_dates(data.assigned_date, data.due_date)
            await self._require_subject(class_id, data.subject_id)
            entity = await self.repository.create(
                class_id=class_id, created_by_telegram_id=actor.telegram_id, **data.model_dump()
            )
        self._add_event("homework.created", entity, actor, correlation_id)
        logger.info("homework created", extra={"class_id": str(class_id), "homework_id": str(entity.id), "telegram_id": actor.telegram_id, "correlation_id": correlation_id})
        return entity

    async def update(self, class_id: UUID, homework_id: UUID, data: HomeworkUpdate, actor: CurrentUser) -> HomeworkORM:
        async with self.session.begin():
            await self.access.require_editor(class_id, actor)
            entity = await self._get_for_class(class_id, homework_id)
            changes = data.model_dump(exclude_unset=True)
            subject_id = changes.get("subject_id", entity.subject_id)
            await self._require_subject(class_id, subject_id)
            assigned_date = changes.get("assigned_date", entity.assigned_date)
            due_date = changes.get("due_date", entity.due_date)
            self._validate_dates(assigned_date, due_date)
            new_text = changes.get("text")
            if new_text is not None and new_text != entity.text:
                await self.repository.create_revision(
                    homework_id=entity.id,
                    old_text=entity.text,
                    new_text=new_text,
                    changed_by_telegram_id=actor.telegram_id,
                )
            changes["updated_by_telegram_id"] = actor.telegram_id
            await self.repository.update(entity, changes)
        self._add_event("homework.updated", entity, actor)
        logger.info("homework updated", extra={"class_id": str(class_id), "homework_id": str(homework_id), "telegram_id": actor.telegram_id})
        return entity

    async def delete(self, class_id: UUID, homework_id: UUID, actor: CurrentUser) -> None:
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self._get_for_class(class_id, homework_id)
            await self.repository.delete(entity)
        self._add_event("homework.deleted", entity, actor)
        logger.info("homework deleted", extra={"class_id": str(class_id), "homework_id": str(homework_id), "telegram_id": actor.telegram_id})

    async def _get_for_class(self, class_id: UUID, homework_id: UUID) -> HomeworkORM:
        entity = await self.repository.get_by_id(homework_id)
        if entity is None or entity.class_id != class_id:
            raise HomeworkNotFoundError()
        return entity

    async def _require_subject(self, class_id: UUID, subject_id: UUID) -> None:
        subject = await self.subject_repository.get_by_id(subject_id)
        if subject is None:
            raise SubjectNotFoundError()
        if subject.class_id != class_id:
            raise SubjectDoesNotBelongToClassError()

    @staticmethod
    def _validate_dates(assigned_date: date, due_date: date) -> None:
        if due_date < assigned_date:
            raise InvalidHomeworkDatesError()

    def _add_event(self, event_type: str, entity: HomeworkORM, actor: CurrentUser, correlation_id: str | None = None) -> None:
        self.pending_events.append(build_domain_event(
            event_type=event_type, aggregate_type="homework", aggregate_id=entity.id,
            actor_telegram_id=actor.telegram_id, class_id=entity.class_id, correlation_id=correlation_id,
            payload={
                "homework_id": str(entity.id), "subject_id": str(entity.subject_id),
                "assigned_date": entity.assigned_date.isoformat(), "due_date": entity.due_date.isoformat(),
            },
        ))
