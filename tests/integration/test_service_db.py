from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.db.models import OutboxEventORM
from app.enums import ClassMemberRole, GlobalRole
from app.exceptions import ClassAccessDeniedError, SubjectDoesNotBelongToClassError
from app.repositories import (
    ClassMemberRepository,
    HomeworkRepository,
    OutboxRepository,
    SchoolClassRepository,
    SubjectRepository,
)
from app.schemas import CurrentUser, HomeworkCreate, HomeworkUpdate
from app.services import ClassAccessService, HomeworkService
from tests.integration.helpers import create_class, create_member, create_subject


def actor(telegram_id: int, role=GlobalRole.USER):
    return CurrentUser(user_id=uuid4(), telegram_id=telegram_id, global_role=role)


def homework_service(session, outbox=None):
    classes = SchoolClassRepository(session)
    members = ClassMemberRepository(session)
    subjects = SubjectRepository(session)
    return HomeworkService(
        session,
        HomeworkRepository(session),
        subjects,
        ClassAccessService(classes, members),
        outbox_repository=outbox,
    )


@pytest.mark.asyncio
async def test_editor_creates_homework_with_real_repositories(session):
    async with session.begin():
        school_class = await create_class(session)
        subject = await create_subject(session, school_class.id)
        await create_member(session, school_class.id, 20, ClassMemberRole.EDITOR)
    entity = await homework_service(session).create(
        school_class.id,
        HomeworkCreate(
            subject_id=subject.id,
            assigned_date=date(2026, 9, 14),
            due_date=date(2026, 9, 15),
            text="Task",
        ),
        actor(20),
    )
    assert entity.id is not None
    assert (await HomeworkRepository(session).get_by_id(entity.id)).text == "Task"


@pytest.mark.asyncio
async def test_student_cannot_create_homework_with_real_membership(session):
    async with session.begin():
        school_class = await create_class(session)
        subject = await create_subject(session, school_class.id)
        await create_member(session, school_class.id, 30, ClassMemberRole.STUDENT)
    with pytest.raises(ClassAccessDeniedError):
        await homework_service(session).create(
            school_class.id,
            HomeworkCreate(
                subject_id=subject.id,
                assigned_date=date(2026, 9, 14),
                due_date=date(2026, 9, 15),
                text="Task",
            ),
            actor(30),
        )


@pytest.mark.asyncio
async def test_homework_update_and_revision_are_atomic(session):
    async with session.begin():
        school_class = await create_class(session)
        subject = await create_subject(session, school_class.id)
        await create_member(session, school_class.id, 20, ClassMemberRole.EDITOR)
    service = homework_service(session)
    entity = await service.create(
        school_class.id,
        HomeworkCreate(
            subject_id=subject.id,
            assigned_date=date(2026, 9, 14),
            due_date=date(2026, 9, 15),
            text="Old",
        ),
        actor(20),
    )
    await service.update(school_class.id, entity.id, HomeworkUpdate(text="New"), actor(20))
    revisions = await HomeworkRepository(session).list_revisions(entity.id)
    assert entity.text == "New"
    assert [(item.old_text, item.new_text) for item in revisions] == [("Old", "New")]


@pytest.mark.asyncio
async def test_other_class_subject_is_rejected_with_real_db(session):
    async with session.begin():
        first, second = await create_class(session, "10A"), await create_class(session, "10B")
        foreign_subject = await create_subject(session, second.id)
        await create_member(session, first.id, 20, ClassMemberRole.EDITOR)
    with pytest.raises(SubjectDoesNotBelongToClassError):
        await homework_service(session).create(
            first.id,
            HomeworkCreate(
                subject_id=foreign_subject.id,
                assigned_date=date(2026, 9, 14),
                due_date=date(2026, 9, 15),
                text="Task",
            ),
            actor(20),
        )


@pytest.mark.asyncio
async def test_homework_and_outbox_event_commit_atomically(session):
    async with session.begin():
        school_class = await create_class(session)
        subject = await create_subject(session, school_class.id)
        await create_member(session, school_class.id, 20, ClassMemberRole.EDITOR)
    service = homework_service(session, OutboxRepository(session))

    entity = await service.create(
        school_class.id,
        HomeworkCreate(
            subject_id=subject.id,
            assigned_date=date(2026, 9, 14),
            due_date=date(2026, 9, 15),
            text="Task",
        ),
        actor(20),
        correlation_id="request-42",
    )

    event = service.get_pending_events()[0]
    outbox_event = await session.get(OutboxEventORM, event.event_id)
    assert await HomeworkRepository(session).get_by_id(entity.id) is not None
    assert outbox_event is not None
    assert outbox_event.payload["correlation_id"] == "request-42"


@pytest.mark.asyncio
async def test_outbox_enqueue_failure_rolls_back_business_change(session):
    async with session.begin():
        school_class = await create_class(session)
        subject = await create_subject(session, school_class.id)
        await create_member(session, school_class.id, 20, ClassMemberRole.EDITOR)
    outbox = MagicMock(spec=OutboxRepository)
    outbox.enqueue.side_effect = RuntimeError("outbox write failed")

    with pytest.raises(RuntimeError, match="outbox write failed"):
        await homework_service(session, outbox).create(
            school_class.id,
            HomeworkCreate(
                subject_id=subject.id,
                assigned_date=date(2026, 9, 14),
                due_date=date(2026, 9, 15),
                text="Task",
            ),
            actor(20),
        )

    assert await HomeworkRepository(session).list(school_class.id) == []
