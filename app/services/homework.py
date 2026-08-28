from __future__ import annotations

import builtins
import logging
from datetime import date
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import CacheNamespace, JsonCache
from app.db.models import HomeworkORM
from app.exceptions import (
    HomeworkNotFoundError,
    InvalidHomeworkDatesError,
    SubjectDoesNotBelongToClassError,
    SubjectNotFoundError,
)
from app.repositories import HomeworkRepository, OutboxRepository, SubjectRepository
from app.schemas import (
    CurrentUser,
    HomeworkCreate,
    HomeworkRead,
    HomeworkRevisionRead,
    HomeworkUpdate,
    build_domain_event,
)
from app.services.access import ClassAccessService
from app.services.base import EventCollectingService

logger = logging.getLogger(__name__)
homework_adapter = TypeAdapter(HomeworkRead)
homework_list_adapter = TypeAdapter(list[HomeworkRead])
homework_history_adapter = TypeAdapter(list[HomeworkRevisionRead])


class HomeworkService(EventCollectingService):
    def __init__(
        self,
        session: AsyncSession,
        repository: HomeworkRepository,
        subject_repository: SubjectRepository,
        access: ClassAccessService,
        cache: JsonCache | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        super().__init__(outbox_repository)
        self.session = session
        self.repository = repository
        self.subject_repository = subject_repository
        self.access = access
        self.cache = cache

    async def list(self, class_id: UUID, actor: CurrentUser) -> list[HomeworkRead]:
        logger.info("Listing homework: class_id=%s", class_id)
        await self.access.require_member(class_id, actor)
        if self.cache is not None:
            cached = await self.cache.get(
                CacheNamespace.HOMEWORK_LIST,
                class_id,
                adapter=homework_list_adapter,
            )
            if cached is not None:
                logger.info("Homework listed: class_id=%s, count=%d", class_id, len(cached))
                return cached

        logger.debug("Loading homework list from database: class_id=%s", class_id)
        entities = await self.repository.list(class_id)
        result = [HomeworkRead.model_validate(entity) for entity in entities]
        if self.cache is not None:
            await self.cache.set(
                CacheNamespace.HOMEWORK_LIST,
                result,
                class_id,
                adapter=homework_list_adapter,
            )
        logger.info("Homework listed: class_id=%s, count=%d", class_id, len(result))
        return result

    async def get(self, class_id: UUID, homework_id: UUID, actor: CurrentUser) -> HomeworkRead:
        logger.info("Getting homework: class_id=%s, homework_id=%s", class_id, homework_id)
        await self.access.require_member(class_id, actor)
        if self.cache is not None:
            cached = await self.cache.get(
                CacheNamespace.HOMEWORK,
                class_id,
                homework_id,
                adapter=homework_adapter,
            )
            if cached is not None:
                logger.info(
                    "Homework retrieved: class_id=%s, homework_id=%s", class_id, homework_id
                )
                return cached

        logger.debug("Loading homework from database: homework_id=%s", homework_id)
        result = HomeworkRead.model_validate(await self._get_for_class(class_id, homework_id))
        if self.cache is not None:
            await self.cache.set(
                CacheNamespace.HOMEWORK,
                result,
                class_id,
                homework_id,
                adapter=homework_adapter,
            )
        logger.info("Homework retrieved: class_id=%s, homework_id=%s", class_id, homework_id)
        return result

    async def history(
        self,
        class_id: UUID,
        homework_id: UUID,
        actor: CurrentUser,
    ) -> builtins.list[HomeworkRevisionRead]:
        logger.info("Getting homework history: class_id=%s, homework_id=%s", class_id, homework_id)
        await self.access.require_member(class_id, actor)
        if self.cache is not None:
            cached = await self.cache.get(
                CacheNamespace.HOMEWORK_HISTORY,
                class_id,
                homework_id,
                adapter=homework_history_adapter,
            )
            if cached is not None:
                logger.info(
                    "Homework history retrieved: homework_id=%s, revisions=%d",
                    homework_id,
                    len(cached),
                )
                return cached

        logger.debug("Loading homework revisions from database: homework_id=%s", homework_id)
        await self._get_for_class(class_id, homework_id)
        revisions = await self.repository.list_revisions(homework_id)
        result = [HomeworkRevisionRead.model_validate(revision) for revision in revisions]
        if self.cache is not None:
            await self.cache.set(
                CacheNamespace.HOMEWORK_HISTORY,
                result,
                class_id,
                homework_id,
                adapter=homework_history_adapter,
            )
        logger.info(
            "Homework history retrieved: homework_id=%s, revisions=%d", homework_id, len(result)
        )
        return result

    async def create(
        self,
        class_id: UUID,
        data: HomeworkCreate,
        actor: CurrentUser,
        correlation_id: str | None = None,
    ) -> HomeworkORM:
        logger.info("Creating homework: class_id=%s, subject_id=%s", class_id, data.subject_id)
        async with self.session.begin():
            await self.access.require_editor(class_id, actor)
            self._validate_dates(data.assigned_date, data.due_date)
            await self._require_subject(class_id, data.subject_id)
            entity = await self.repository.create(
                class_id=class_id,
                subject_id=data.subject_id,
                assigned_date=data.assigned_date,
                due_date=data.due_date,
                text=data.text,
                created_by_telegram_id=actor.telegram_id,
            )
            self._add_event("homework.created", entity, actor, correlation_id)
        await self._invalidate_homework_list(class_id)
        logger.info("Homework created: class_id=%s, homework_id=%s", class_id, entity.id)
        return entity

    async def update(
        self,
        class_id: UUID,
        homework_id: UUID,
        data: HomeworkUpdate,
        actor: CurrentUser,
        correlation_id: str | None = None,
    ) -> HomeworkORM:
        logger.info("Updating homework: class_id=%s, homework_id=%s", class_id, homework_id)
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
            entity = await self.repository.update(entity, changes)
            self._add_event("homework.updated", entity, actor, correlation_id)
        await self._invalidate_homework(class_id, homework_id)
        logger.info("Homework updated: class_id=%s, homework_id=%s", class_id, homework_id)
        return entity

    async def delete(
        self,
        class_id: UUID,
        homework_id: UUID,
        actor: CurrentUser,
        correlation_id: str | None = None,
    ) -> None:
        logger.info("Deleting homework: class_id=%s, homework_id=%s", class_id, homework_id)
        self.access.require_admin(actor)
        async with self.session.begin():
            entity = await self._get_for_class(class_id, homework_id)
            await self.repository.delete(entity)
            self._add_event("homework.deleted", entity, actor, correlation_id)
        await self._invalidate_homework(class_id, homework_id)
        logger.info("Homework deleted: class_id=%s, homework_id=%s", class_id, homework_id)

    async def _get_for_class(self, class_id: UUID, homework_id: UUID) -> HomeworkORM:
        entity = await self.repository.get_by_id(homework_id)
        if entity is None or entity.class_id != class_id:
            logger.warning("Homework not found: class_id=%s, homework_id=%s", class_id, homework_id)
            raise HomeworkNotFoundError()
        return entity

    async def _require_subject(self, class_id: UUID, subject_id: UUID) -> None:
        subject = await self.subject_repository.get_by_id(subject_id)
        if subject is None:
            logger.warning(
                "Homework subject not found: class_id=%s, subject_id=%s", class_id, subject_id
            )
            raise SubjectNotFoundError()
        if subject.class_id != class_id:
            logger.warning(
                "Homework subject belongs to another class: class_id=%s, subject_id=%s",
                class_id,
                subject_id,
            )
            raise SubjectDoesNotBelongToClassError()

    @staticmethod
    def _validate_dates(assigned_date: date, due_date: date) -> None:
        if due_date < assigned_date:
            logger.warning(
                "Invalid homework dates: assigned_date=%s, due_date=%s", assigned_date, due_date
            )
            raise InvalidHomeworkDatesError()

    def _add_event(
        self,
        event_type: str,
        entity: HomeworkORM,
        actor: CurrentUser,
        correlation_id: str | None = None,
    ) -> None:
        self.record_event(
            build_domain_event(
                event_type=event_type,
                aggregate_type="homework",
                aggregate_id=entity.id,
                actor_telegram_id=actor.telegram_id,
                class_id=entity.class_id,
                correlation_id=correlation_id,
                payload={
                    "homework_id": str(entity.id),
                    "subject_id": str(entity.subject_id),
                    "assigned_date": entity.assigned_date.isoformat(),
                    "due_date": entity.due_date.isoformat(),
                },
            )
        )

    async def _invalidate_homework_list(self, class_id: UUID) -> None:
        if self.cache is not None:
            await self.cache.invalidate(CacheNamespace.HOMEWORK_LIST, class_id)

    async def _invalidate_homework(self, class_id: UUID, homework_id: UUID) -> None:
        if self.cache is None:
            return
        await self.cache.invalidate(CacheNamespace.HOMEWORK, class_id, homework_id)
        await self.cache.invalidate(CacheNamespace.HOMEWORK_HISTORY, class_id, homework_id)
        await self._invalidate_homework_list(class_id)
