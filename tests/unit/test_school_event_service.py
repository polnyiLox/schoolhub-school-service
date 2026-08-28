from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models import SchoolEventORM
from app.enums import SchoolEventType
from app.exceptions import InvalidSchoolEventDatesError, SchoolEventNotFoundError
from app.schemas import SchoolEventCreate, SchoolEventUpdate
from app.services import SchoolEventService


@pytest.mark.asyncio
async def test_event_end_before_start_is_rejected(transaction_session, user):
    repository, access = AsyncMock(), MagicMock()
    access.require_editor = AsyncMock()
    now = datetime.now(UTC)
    with pytest.raises(InvalidSchoolEventDatesError):
        await SchoolEventService(transaction_session, repository, access).create(
            uuid4(), SchoolEventCreate(title="Exam", event_type=SchoolEventType.EXAM, starts_at=now, ends_at=now - timedelta(hours=1)), user
        )
    repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_valid_event_is_created_by_actor(transaction_session, user):
    repository, access = AsyncMock(), MagicMock()
    access.require_editor = AsyncMock()
    class_id, event_id, now = uuid4(), uuid4(), datetime.now(UTC)
    entity = SchoolEventORM(id=event_id, class_id=class_id, title="Exam", event_type=SchoolEventType.EXAM, starts_at=now, ends_at=None, created_by_telegram_id=user.telegram_id)
    repository.create.return_value = entity
    service = SchoolEventService(transaction_session, repository, access)
    assert await service.create(class_id, SchoolEventCreate(title="Exam", event_type=SchoolEventType.EXAM, starts_at=now), user) is entity
    assert service.pending_events[0].event_type == "school_event.created"


@pytest.mark.asyncio
async def test_event_update_validates_effective_dates(transaction_session, user):
    repository, access = AsyncMock(), MagicMock()
    access.require_editor = AsyncMock()
    class_id, now = uuid4(), datetime.now(UTC)
    entity = SchoolEventORM(id=uuid4(), class_id=class_id, title="Exam", event_type=SchoolEventType.EXAM, starts_at=now, ends_at=None, created_by_telegram_id=user.telegram_id)
    repository.get_by_id.return_value = entity
    with pytest.raises(InvalidSchoolEventDatesError):
        await SchoolEventService(transaction_session, repository, access).update(class_id, entity.id, SchoolEventUpdate(ends_at=now - timedelta(minutes=1)), user)


@pytest.mark.asyncio
async def test_missing_school_event_is_not_found(transaction_session, user):
    repository, access = AsyncMock(), MagicMock()
    access.require_member = AsyncMock()
    repository.get_by_id.return_value = None

    with pytest.raises(SchoolEventNotFoundError):
        await SchoolEventService(transaction_session, repository, access).get(
            uuid4(), uuid4(), user,
        )
