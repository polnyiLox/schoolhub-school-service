from __future__ import annotations

import builtins
import logging
from datetime import date
from uuid import UUID, uuid4

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import CacheNamespace, JsonCache
from app.core.config import settings
from app.db.models import HomeworkAttachmentORM, HomeworkORM
from app.exceptions import (
    AttachmentTooLargeError,
    HomeworkAttachmentNotFoundError,
    HomeworkNotFoundError,
    InvalidHomeworkDatesError,
    SubjectDoesNotBelongToClassError,
    SubjectNotFoundError,
    UnsupportedAttachmentTypeError,
)
from app.repositories import HomeworkRepository, OutboxRepository, SubjectRepository
from app.schemas import (
    CurrentUser,
    HomeworkAttachmentRead,
    HomeworkCreate,
    HomeworkRead,
    HomeworkRevisionRead,
    HomeworkUpdate,
    build_domain_event,
)
from app.services.access import ClassAccessService
from app.services.base import EventCollectingService
from app.storage import S3ObjectStorage

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
        object_storage: S3ObjectStorage | None = None,
    ) -> None:
        super().__init__(outbox_repository)
        self.session = session
        self.repository = repository
        self.subject_repository = subject_repository
        self.access = access
        self.cache = cache
        self.object_storage = object_storage

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
        attachment_keys: builtins.list[str] = []
        async with self.session.begin():
            entity = await self._get_for_class(class_id, homework_id)
            if self.object_storage is not None:
                attachment_keys = [
                    item.object_key for item in await self.repository.list_attachments(homework_id)
                ]
            await self.repository.delete(entity)
            self._add_event("homework.deleted", entity, actor, correlation_id)
        await self._invalidate_homework(class_id, homework_id)
        for object_key in attachment_keys:
            await self._delete_object_best_effort(object_key)
        logger.info("Homework deleted: class_id=%s, homework_id=%s", class_id, homework_id)

    async def upload_attachment(
        self,
        class_id: UUID,
        homework_id: UUID,
        file_name: str,
        content_type: str,
        content: bytes,
        actor: CurrentUser,
    ) -> HomeworkAttachmentORM:
        logger.info("Uploading homework attachment: homework_id=%s", homework_id)
        async with self.session.begin():
            await self.access.require_editor(class_id, actor)
            await self._get_for_class(class_id, homework_id)
        normalized_type = content_type.partition(";")[0].strip().lower()
        if normalized_type not in settings.object_storage.allowed_content_types:
            logger.warning("Unsupported attachment type: content_type=%s", normalized_type)
            raise UnsupportedAttachmentTypeError()
        if len(content) > settings.object_storage.max_file_size_bytes:
            logger.warning("Attachment is too large: size=%d", len(content))
            raise AttachmentTooLargeError()
        storage = self._require_object_storage()
        safe_name = file_name.replace("\\", "/").rsplit("/", 1)[-1].strip() or "attachment"
        safe_name = safe_name[:255]
        object_key = f"classes/{class_id}/homeworks/{homework_id}/{uuid4()}"
        await storage.upload(object_key, content, normalized_type)
        try:
            async with self.session.begin():
                attachment = await self.repository.create_attachment(
                    homework_id=homework_id,
                    object_key=object_key,
                    file_name=safe_name,
                    content_type=normalized_type,
                    size=len(content),
                    uploaded_by_telegram_id=actor.telegram_id,
                )
        except BaseException:
            await self._delete_object_best_effort(object_key)
            raise
        logger.info("Homework attachment uploaded: attachment_id=%s", attachment.id)
        return attachment

    async def list_attachments(
        self,
        class_id: UUID,
        homework_id: UUID,
        actor: CurrentUser,
    ) -> builtins.list[HomeworkAttachmentRead]:
        await self.access.require_member(class_id, actor)
        await self._get_for_class(class_id, homework_id)
        attachments = await self.repository.list_attachments(homework_id)
        return [HomeworkAttachmentRead.model_validate(item) for item in attachments]

    async def download_attachment(
        self,
        class_id: UUID,
        homework_id: UUID,
        attachment_id: UUID,
        actor: CurrentUser,
    ) -> tuple[HomeworkAttachmentRead, bytes]:
        await self.access.require_member(class_id, actor)
        await self._get_for_class(class_id, homework_id)
        attachment = await self._get_attachment(homework_id, attachment_id)
        content = await self._require_object_storage().download(attachment.object_key)
        return HomeworkAttachmentRead.model_validate(attachment), content

    async def delete_attachment(
        self,
        class_id: UUID,
        homework_id: UUID,
        attachment_id: UUID,
        actor: CurrentUser,
    ) -> None:
        async with self.session.begin():
            await self.access.require_editor(class_id, actor)
            await self._get_for_class(class_id, homework_id)
            attachment = await self._get_attachment(homework_id, attachment_id)
            await self.repository.delete_attachment(attachment.id)
        await self._delete_object_best_effort(attachment.object_key)

    async def _get_attachment(
        self,
        homework_id: UUID,
        attachment_id: UUID,
    ) -> HomeworkAttachmentORM:
        attachment = await self.repository.get_attachment(attachment_id)
        if attachment is None or attachment.homework_id != homework_id:
            raise HomeworkAttachmentNotFoundError()
        return attachment

    def _require_object_storage(self) -> S3ObjectStorage:
        if self.object_storage is None:
            raise RuntimeError("Object storage is not configured")
        return self.object_storage

    async def _delete_object_best_effort(self, object_key: str) -> None:
        if self.object_storage is None:
            return
        try:
            await self.object_storage.delete(object_key)
        except Exception:
            logger.exception("Failed to delete attachment object: key=%s", object_key)

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
