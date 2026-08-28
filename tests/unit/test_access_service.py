from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.db.models import ClassMemberORM, SchoolClassORM
from app.enums import ClassMemberRole
from app.exceptions import ClassAccessDeniedError, ClassNotFoundError
from app.services import ClassAccessService


@pytest.mark.asyncio
async def test_admin_is_allowed_without_membership(admin):
    classes = AsyncMock()
    classes.get_by_id.return_value = SchoolClassORM(
        id=uuid4(), name="10A", academic_year="2026/2027"
    )
    members = AsyncMock()
    service = ClassAccessService(classes, members)
    assert await service.require_member(uuid4(), admin) is None
    members.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_existing_student_is_member(user):
    class_id = uuid4()
    member = ClassMemberORM(
        class_id=class_id, telegram_id=user.telegram_id, role=ClassMemberRole.STUDENT
    )
    classes = AsyncMock(
        get_by_id=AsyncMock(
            return_value=SchoolClassORM(id=class_id, name="10A", academic_year="2026/2027")
        )
    )
    members = AsyncMock(get=AsyncMock(return_value=member))
    assert await ClassAccessService(classes, members).require_member(class_id, user) is member


@pytest.mark.asyncio
async def test_user_from_another_class_is_denied(user):
    classes = AsyncMock(
        get_by_id=AsyncMock(
            return_value=SchoolClassORM(id=uuid4(), name="10A", academic_year="2026/2027")
        )
    )
    members = AsyncMock(get=AsyncMock(return_value=None))
    with pytest.raises(ClassAccessDeniedError):
        await ClassAccessService(classes, members).require_member(uuid4(), user)


@pytest.mark.asyncio
async def test_student_cannot_edit(user):
    class_id = uuid4()
    member = ClassMemberORM(
        class_id=class_id, telegram_id=user.telegram_id, role=ClassMemberRole.STUDENT
    )
    classes = AsyncMock(
        get_by_id=AsyncMock(
            return_value=SchoolClassORM(id=class_id, name="10A", academic_year="2026/2027")
        )
    )
    members = AsyncMock(get=AsyncMock(return_value=member))
    with pytest.raises(ClassAccessDeniedError):
        await ClassAccessService(classes, members).require_editor(class_id, user)


@pytest.mark.asyncio
async def test_missing_class_is_not_found(user):
    classes = AsyncMock(get_by_id=AsyncMock(return_value=None))
    with pytest.raises(ClassNotFoundError):
        await ClassAccessService(classes, AsyncMock()).require_member(uuid4(), user)
