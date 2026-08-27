from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models import ClassMemberORM, HomeworkORM, SchoolClassORM, SubjectORM
from app.enums import ClassMemberRole
from app.repositories import ClassMemberRepository, HomeworkRepository, SchoolClassRepository, SubjectRepository


def mock_session() -> MagicMock:
    session = MagicMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.get = AsyncMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_class_repository_get_uses_scalar_query():
    session, class_id = mock_session(), uuid4()
    entity = SchoolClassORM(id=class_id, name="10A", academic_year="2026/2027")
    session.scalar.return_value = entity
    assert await SchoolClassRepository(session).get_by_id(class_id) is entity
    query = session.scalar.await_args.args[0]
    assert class_id in query.compile().params.values()


@pytest.mark.asyncio
async def test_class_repository_create_adds_and_flushes_without_commit():
    session = mock_session()
    entity = await SchoolClassRepository(session).create(name="10A", academic_year="2026/2027")
    assert entity.name == "10A"
    session.add.assert_called_once_with(entity)
    session.flush.assert_awaited_once()
    assert not session.commit.called


@pytest.mark.asyncio
async def test_class_repository_list_returns_scalars():
    session = mock_session()
    expected = [SchoolClassORM(name="10A", academic_year="2026/2027")]
    result = MagicMock()
    result.scalars.return_value.all.return_value = expected
    session.execute.return_value = result
    assert await SchoolClassRepository(session).list() == expected


@pytest.mark.asyncio
async def test_member_repository_get_returns_none():
    session = mock_session()
    session.scalar.return_value = None
    assert await ClassMemberRepository(session).get(uuid4(), 123) is None


@pytest.mark.asyncio
async def test_member_repository_delete_executes_delete_statement():
    session = mock_session()
    member = ClassMemberORM(class_id=uuid4(), telegram_id=1, role=ClassMemberRole.STUDENT)
    await ClassMemberRepository(session).delete(member)
    statement = session.execute.await_args.args[0]
    assert statement.is_delete
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_subject_repository_update_uses_update_statement():
    session = mock_session()
    subject = SubjectORM(class_id=uuid4(), name="Math", teacher_name=None)
    session.scalar.return_value = subject
    result = await SubjectRepository(session).update(
        subject,
        {"teacher_name": "Mrs Smith"},
    )
    assert result is subject
    statement = session.scalar.await_args.args[0]
    assert statement.is_update
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_homework_repository_get_filters_by_id():
    session, homework_id = mock_session(), uuid4()
    homework = MagicMock(spec=HomeworkORM)
    session.scalar.return_value = homework
    assert await HomeworkRepository(session).get_by_id(homework_id) is homework
    query = session.scalar.await_args.args[0]
    assert homework_id in query.compile().params.values()


@pytest.mark.asyncio
async def test_revision_repository_adds_revision_to_same_session():
    session = mock_session()
    revision = await HomeworkRepository(session).create_revision(
        homework_id=uuid4(), old_text="old", new_text="new", changed_by_telegram_id=1
    )
    assert revision.old_text == "old"
    session.add.assert_called_once_with(revision)
    session.flush.assert_awaited_once()
