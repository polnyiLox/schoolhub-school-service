from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models import SubjectORM
from app.schemas import SubjectUpdate
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
