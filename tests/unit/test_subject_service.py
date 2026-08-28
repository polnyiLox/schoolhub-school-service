from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models import SubjectORM
from app.exceptions import ClassNotFoundError
from app.schemas import SubjectCreate, SubjectUpdate
from app.services import SubjectService


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
