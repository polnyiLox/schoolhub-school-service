from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.config import settings
from app.db.models import HomeworkAttachmentORM, HomeworkORM, SubjectORM
from app.exceptions import (
    AttachmentTooLargeError,
    ClassAccessDeniedError,
    HomeworkNotFoundError,
    InvalidHomeworkDatesError,
    SubjectDoesNotBelongToClassError,
    UnsupportedAttachmentTypeError,
)
from app.schemas import HomeworkCreate, HomeworkRead, HomeworkUpdate
from app.services import HomeworkService


def homework(class_id, subject_id, text="old"):
    return HomeworkORM(
        id=uuid4(),
        class_id=class_id,
        subject_id=subject_id,
        assigned_date=date(2026, 9, 14),
        due_date=date(2026, 9, 15),
        text=text,
        created_by_telegram_id=1,
        updated_by_telegram_id=None,
    )


def service(transaction_session, class_id, subject_id, cache=None, storage=None):
    repository = AsyncMock()
    repository.update.side_effect = lambda entity, _: entity
    subjects = AsyncMock()
    subjects.get_by_id.return_value = SubjectORM(
        id=subject_id, class_id=class_id, name="Math", teacher_name=None
    )
    access = MagicMock()
    access.require_editor = AsyncMock()
    access.require_member = AsyncMock()
    return (
        HomeworkService(transaction_session, repository, subjects, access, cache, None, storage),
        repository,
        subjects,
        access,
    )


@pytest.mark.asyncio
async def test_homework_cache_hit_skips_database(transaction_session, user):
    class_id, subject_id = uuid4(), uuid4()
    cache = AsyncMock()
    cached = HomeworkRead.model_construct(
        id=uuid4(),
        class_id=class_id,
        subject_id=subject_id,
        assigned_date=date(2026, 9, 14),
        due_date=date(2026, 9, 15),
        text="cached",
        created_by_telegram_id=1,
        updated_by_telegram_id=None,
    )
    cache.get.return_value = cached
    tested, repository, _, _ = service(transaction_session, class_id, subject_id, cache)

    result = await tested.get(class_id, cached.id, user)

    assert result is cached
    repository.get_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_homework_is_not_found(transaction_session, user):
    tested, repository, _, _ = service(transaction_session, uuid4(), uuid4())
    repository.get_by_id.return_value = None

    with pytest.raises(HomeworkNotFoundError):
        await tested.get(uuid4(), uuid4(), user)


@pytest.mark.asyncio
async def test_homework_update_invalidates_related_cache_entries(transaction_session, user):
    class_id, subject_id = uuid4(), uuid4()
    cache = AsyncMock()
    tested, repository, _, _ = service(transaction_session, class_id, subject_id, cache)
    entity = homework(class_id, subject_id)
    repository.get_by_id.return_value = entity

    await tested.update(class_id, entity.id, HomeworkUpdate(text="new"), user)

    assert cache.invalidate.await_count == 3


@pytest.mark.asyncio
async def test_editor_can_create_homework(transaction_session, user):
    class_id, subject_id = uuid4(), uuid4()
    tested, repository, _, access = service(transaction_session, class_id, subject_id)
    entity = homework(class_id, subject_id)
    repository.create.return_value = entity
    result = await tested.create(
        class_id,
        HomeworkCreate(
            subject_id=subject_id,
            assigned_date=date(2026, 9, 14),
            due_date=date(2026, 9, 15),
            text="old",
        ),
        user,
    )
    assert result is entity
    access.require_editor.assert_awaited_once()
    assert tested.pending_events[0].event_type == "homework.created"


@pytest.mark.asyncio
async def test_admin_can_create_homework(transaction_session, admin):
    class_id, subject_id = uuid4(), uuid4()
    tested, repository, _, _ = service(transaction_session, class_id, subject_id)
    repository.create.return_value = homework(class_id, subject_id)
    await tested.create(
        class_id,
        HomeworkCreate(
            subject_id=subject_id,
            assigned_date=date(2026, 9, 14),
            due_date=date(2026, 9, 15),
            text="task",
        ),
        admin,
    )
    repository.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_student_cannot_create_homework(transaction_session, user):
    tested, repository, _, access = service(transaction_session, uuid4(), uuid4())
    access.require_editor.side_effect = ClassAccessDeniedError()
    with pytest.raises(ClassAccessDeniedError):
        await tested.create(
            uuid4(),
            HomeworkCreate(
                subject_id=uuid4(),
                assigned_date=date(2026, 9, 14),
                due_date=date(2026, 9, 15),
                text="task",
            ),
            user,
        )
    repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_due_date_before_assigned_is_rejected(transaction_session, user):
    class_id, subject_id = uuid4(), uuid4()
    tested, repository, _, _ = service(transaction_session, class_id, subject_id)
    with pytest.raises(InvalidHomeworkDatesError):
        await tested.create(
            class_id,
            HomeworkCreate(
                subject_id=subject_id,
                assigned_date=date(2026, 9, 15),
                due_date=date(2026, 9, 14),
                text="task",
            ),
            user,
        )
    repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_subject_from_another_class_is_rejected(transaction_session, user):
    class_id, subject_id = uuid4(), uuid4()
    tested, _, subjects, _ = service(transaction_session, class_id, subject_id)
    subjects.get_by_id.return_value = SubjectORM(id=subject_id, class_id=uuid4(), name="Math")
    with pytest.raises(SubjectDoesNotBelongToClassError):
        await tested.create(
            class_id,
            HomeworkCreate(
                subject_id=subject_id,
                assigned_date=date(2026, 9, 14),
                due_date=date(2026, 9, 15),
                text="task",
            ),
            user,
        )


@pytest.mark.asyncio
async def test_text_update_creates_revision_in_transaction(transaction_session, user):
    class_id, subject_id = uuid4(), uuid4()
    tested, repository, _, _ = service(transaction_session, class_id, subject_id)
    entity = homework(class_id, subject_id)
    repository.get_by_id.return_value = entity
    await tested.update(class_id, entity.id, HomeworkUpdate(text="new"), user)
    repository.create_revision.assert_awaited_once_with(
        homework_id=entity.id,
        old_text="old",
        new_text="new",
        changed_by_telegram_id=user.telegram_id,
    )
    repository.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_unchanged_text_does_not_create_revision(transaction_session, user):
    class_id, subject_id = uuid4(), uuid4()
    tested, repository, _, _ = service(transaction_session, class_id, subject_id)
    entity = homework(class_id, subject_id)
    repository.get_by_id.return_value = entity
    await tested.update(class_id, entity.id, HomeworkUpdate(text="old"), user)
    repository.create_revision.assert_not_awaited()


@pytest.mark.asyncio
async def test_homework_event_contains_ids(transaction_session, user):
    class_id, subject_id = uuid4(), uuid4()
    tested, repository, _, _ = service(transaction_session, class_id, subject_id)
    entity = homework(class_id, subject_id)
    repository.create.return_value = entity
    await tested.create(
        class_id,
        HomeworkCreate(
            subject_id=subject_id,
            assigned_date=entity.assigned_date,
            due_date=entity.due_date,
            text=entity.text,
        ),
        user,
    )
    event = tested.pending_events[0]
    assert event.aggregate_id == entity.id
    assert event.class_id == class_id


@pytest.mark.asyncio
async def test_upload_attachment_persists_object_metadata(transaction_session, user):
    class_id, subject_id = uuid4(), uuid4()
    storage = AsyncMock()
    tested, repository, _, access = service(
        transaction_session, class_id, subject_id, storage=storage
    )
    entity = homework(class_id, subject_id)
    repository.get_by_id.return_value = entity
    attachment = HomeworkAttachmentORM(
        id=uuid4(),
        homework_id=entity.id,
        object_key="key",
        file_name="task.pdf",
        content_type="application/pdf",
        size=3,
        uploaded_by_telegram_id=user.telegram_id,
    )
    repository.create_attachment.return_value = attachment

    result = await tested.upload_attachment(
        class_id, entity.id, "../task.pdf", "application/pdf", b"pdf", user
    )

    assert result is attachment
    storage.upload.assert_awaited_once()
    assert repository.create_attachment.await_args.kwargs["file_name"] == "task.pdf"
    access.require_editor.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_attachment_rejects_unsupported_type(transaction_session, user):
    class_id, subject_id = uuid4(), uuid4()
    storage = AsyncMock()
    tested, repository, _, _ = service(
        transaction_session, class_id, subject_id, storage=storage
    )
    entity = homework(class_id, subject_id)
    repository.get_by_id.return_value = entity

    with pytest.raises(UnsupportedAttachmentTypeError):
        await tested.upload_attachment(
            class_id, entity.id, "payload.exe", "application/octet-stream", b"x", user
        )
    storage.upload.assert_not_awaited()


@pytest.mark.asyncio
async def test_upload_attachment_enforces_size_limit(transaction_session, user, monkeypatch):
    class_id, subject_id = uuid4(), uuid4()
    storage = AsyncMock()
    tested, repository, _, _ = service(
        transaction_session, class_id, subject_id, storage=storage
    )
    entity = homework(class_id, subject_id)
    repository.get_by_id.return_value = entity
    monkeypatch.setattr(settings.object_storage, "max_file_size_bytes", 2)

    with pytest.raises(AttachmentTooLargeError):
        await tested.upload_attachment(
            class_id, entity.id, "task.pdf", "application/pdf", b"pdf", user
        )
    storage.upload.assert_not_awaited()


@pytest.mark.asyncio
async def test_upload_attachment_compensates_failed_database_write(transaction_session, user):
    class_id, subject_id = uuid4(), uuid4()
    storage = AsyncMock()
    tested, repository, _, _ = service(
        transaction_session, class_id, subject_id, storage=storage
    )
    entity = homework(class_id, subject_id)
    repository.get_by_id.return_value = entity
    repository.create_attachment.side_effect = RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        await tested.upload_attachment(
            class_id, entity.id, "task.pdf", "application/pdf", b"pdf", user
        )
    storage.delete.assert_awaited_once()
