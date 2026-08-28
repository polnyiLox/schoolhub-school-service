from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.enums import ClassMemberRole, SchoolEventType
from app.repositories import (
    ClassMemberRepository,
    ScheduleRepository,
    SchoolClassRepository,
    SchoolEventRepository,
    SubjectRepository,
)
from tests.integration.helpers import (
    EVENT_START,
    LESSON_END,
    LESSON_START,
    create_class,
    create_subject,
)


@pytest.mark.asyncio
async def test_class_repository_crud_with_postgres(session):
    repository = SchoolClassRepository(session)
    entity = await repository.create(name="10A", academic_year="2026/2027", is_archived=False)
    assert await repository.get_by_id(entity.id) is entity
    await repository.update(entity, {"is_archived": True})
    assert entity.is_archived is True


@pytest.mark.asyncio
async def test_duplicate_member_constraint(session):
    school_class = await create_class(session)
    repository = ClassMemberRepository(session)
    await repository.create(class_id=school_class.id, telegram_id=100, role=ClassMemberRole.STUDENT)
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await repository.create(
                class_id=school_class.id, telegram_id=100, role=ClassMemberRole.EDITOR
            )


@pytest.mark.asyncio
async def test_subject_list_is_isolated_by_class(session):
    first, second = await create_class(session, "10A"), await create_class(session, "10B")
    repository = SubjectRepository(session)
    await repository.create(class_id=first.id, name="Math", teacher_name=None)
    await repository.create(class_id=second.id, name="Physics", teacher_name=None)
    assert [item.name for item in await repository.list(first.id)] == ["Math"]


@pytest.mark.asyncio
async def test_duplicate_schedule_slot_constraint(session):
    school_class = await create_class(session)
    subject = await create_subject(session, school_class.id)
    repository = ScheduleRepository(session)
    values = dict(
        class_id=school_class.id,
        subject_id=subject.id,
        weekday=0,
        lesson_number=1,
        start_time=LESSON_START,
        end_time=LESSON_END,
        room=None,
    )
    await repository.create_entry(**values)
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await repository.create_entry(**values)


@pytest.mark.asyncio
async def test_invalid_schedule_time_constraint(session):
    school_class = await create_class(session)
    subject = await create_subject(session, school_class.id)
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await ScheduleRepository(session).create_entry(
                class_id=school_class.id,
                subject_id=subject.id,
                weekday=0,
                lesson_number=1,
                start_time=LESSON_END,
                end_time=LESSON_START,
                room=None,
            )


@pytest.mark.asyncio
async def test_invalid_event_dates_constraint(session):
    school_class = await create_class(session)
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await SchoolEventRepository(session).create(
                class_id=school_class.id,
                title="Exam",
                description=None,
                event_type=SchoolEventType.EXAM,
                starts_at=EVENT_START,
                ends_at=EVENT_START - timedelta(hours=1),
                created_by_telegram_id=1,
            )
