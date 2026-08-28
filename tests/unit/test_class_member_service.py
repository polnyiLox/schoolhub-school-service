from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models import ClassMemberORM, SchoolClassORM
from app.enums import ClassMemberRole
from app.exceptions import ClassAccessDeniedError, ClassMemberAlreadyExistsError
from app.schemas import ClassMemberCreate, ClassMemberUpdate, SchoolClassCreate
from app.services import ClassMemberService, SchoolClassService


@pytest.mark.asyncio
async def test_admin_can_create_class(transaction_session, admin):
    repository, access = AsyncMock(), MagicMock()
    entity = SchoolClassORM(id=uuid4(), name="10A", academic_year="2026/2027")
    repository.create.return_value = entity
    service = SchoolClassService(transaction_session, repository, access)
    assert await service.create(SchoolClassCreate(name="10A", academic_year="2026/2027"), admin) is entity
    access.require_admin.assert_called_once_with(admin)
    assert service.pending_events[0].event_type == "class.created"


@pytest.mark.asyncio
async def test_user_cannot_create_class(transaction_session, user):
    repository, access = AsyncMock(), MagicMock()
    access.require_admin.side_effect = ClassAccessDeniedError()
    with pytest.raises(ClassAccessDeniedError):
        await SchoolClassService(transaction_session, repository, access).create(SchoolClassCreate(name="10A", academic_year="2026/2027"), user)
    repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_can_add_member(transaction_session, admin):
    class_id = uuid4()
    repository, classes, access = AsyncMock(), AsyncMock(), MagicMock()
    classes.get_by_id.return_value = SchoolClassORM(id=class_id, name="10A", academic_year="2026/2027")
    repository.get.return_value = None
    entity = ClassMemberORM(id=uuid4(), class_id=class_id, telegram_id=20, role=ClassMemberRole.STUDENT)
    repository.create.return_value = entity
    service = ClassMemberService(transaction_session, repository, classes, access)
    assert await service.add(class_id, ClassMemberCreate(telegram_id=20, role=ClassMemberRole.STUDENT), admin) is entity
    assert service.pending_events[0].event_type == "class.member_added"


@pytest.mark.asyncio
async def test_duplicate_member_is_rejected(transaction_session, admin):
    class_id = uuid4()
    repository, classes, access = AsyncMock(), AsyncMock(), MagicMock()
    classes.get_by_id.return_value = SchoolClassORM(id=class_id, name="10A", academic_year="2026/2027")
    repository.get.return_value = ClassMemberORM(class_id=class_id, telegram_id=20, role=ClassMemberRole.STUDENT)
    with pytest.raises(ClassMemberAlreadyExistsError):
        await ClassMemberService(transaction_session, repository, classes, access).add(
            class_id, ClassMemberCreate(telegram_id=20, role=ClassMemberRole.STUDENT), admin
        )


@pytest.mark.asyncio
async def test_admin_can_promote_student_to_editor(transaction_session, admin):
    class_id = uuid4()
    repository, classes, access = AsyncMock(), AsyncMock(), MagicMock()
    member = ClassMemberORM(
        id=uuid4(), class_id=class_id, telegram_id=20, role=ClassMemberRole.STUDENT,
    )
    updated_member = ClassMemberORM(
        id=member.id, class_id=class_id, telegram_id=20, role=ClassMemberRole.EDITOR,
    )
    repository.get.return_value = member
    repository.update.return_value = updated_member
    service = ClassMemberService(transaction_session, repository, classes, access)

    await service.update(
        class_id,
        member.telegram_id,
        ClassMemberUpdate(role=ClassMemberRole.EDITOR),
        admin,
    )

    repository.update.assert_awaited_once_with(
        member,
        {"role": ClassMemberRole.EDITOR},
    )
    assert service.pending_events[0].event_type == "class.member_role_changed"
    assert service.pending_events[0].payload["role"] == "editor"
