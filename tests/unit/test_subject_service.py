from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models import SubjectORM
from app.exceptions import ClassNotFoundError, SubjectInUseError, SubjectNotFoundError
from app.schemas import SubjectCreate, SubjectUpdate
from app.services import SubjectService


class ConstraintViolation(Exception):
    def __init__(self, constraint_name: str) -> None:
        self.constraint_name = constraint_name


def integrity_error(constraint_name: str) -> IntegrityError:
    return IntegrityError(None, None, ConstraintViolation(constraint_name))


@pytest.mark.asyncio
async def test_subject_update_invalidates_schedule_cache(transaction_session, admin):
    class_id, subject_id = uuid4(), uuid4()
    repository = AsyncMock()
    entity = SubjectORM(id=subject_id, class_id=class_id, name="Math")
    repository.get_by_id.return_value = entity
    repository.update.return_value = entity
    cache = AsyncMock()
    service = SubjectService(transaction_session, repository, MagicMock(), cache)

    await service.update(class_id, subject_id, SubjectUpdate(name="Physics"), admin)

    assert cache.invalidate_pattern.await_count == 2


@pytest.mark.asyncio
async def test_subject_create_requires_existing_class(transaction_session, admin):
    repository = AsyncMock()
    access = MagicMock()
    access.require_member = AsyncMock(side_effect=ClassNotFoundError())
    service = SubjectService(transaction_session, repository, access)

    with pytest.raises(ClassNotFoundError):
        await service.create(uuid4(), SubjectCreate(name="Math"), admin)

    repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_subject_is_not_found(transaction_session, admin):
    repository = AsyncMock()
    repository.get_by_id.return_value = None
    service = SubjectService(transaction_session, repository, MagicMock())

    with pytest.raises(SubjectNotFoundError):
        await service.update(uuid4(), uuid4(), SubjectUpdate(name="Physics"), admin)


@pytest.mark.asyncio
async def test_subject_in_use_cannot_be_deleted(transaction_session, admin):
    class_id, subject_id = uuid4(), uuid4()
    repository = AsyncMock()
    entity = SubjectORM(id=subject_id, class_id=class_id, name="Math")
    repository.get_by_id.return_value = entity
    repository.delete.side_effect = integrity_error("homeworks_subject_id_fkey")
    service = SubjectService(transaction_session, repository, MagicMock())

    with pytest.raises(SubjectInUseError):
        await service.delete(class_id, subject_id, admin)
