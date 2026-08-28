from datetime import date, time
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models import ScheduleEntryORM, ScheduleOverrideORM, SubjectORM
from app.enums import ScheduleOverrideType
from app.exceptions import InvalidScheduleOverrideError, InvalidScheduleTimeError, ScheduleConflictError
from app.schemas import ScheduleDayRead, ScheduleEntryCreate, ScheduleEntryUpdate, ScheduleOverrideCreate
from app.services import ScheduleService


def dependencies(transaction_session, class_id, subject_id, cache=None):
    repository, subjects, access = AsyncMock(), AsyncMock(), MagicMock()
    access.require_member = AsyncMock()
    subjects.get_by_id.return_value = SubjectORM(id=subject_id, class_id=class_id, name="Math")
    return ScheduleService(transaction_session, repository, subjects, access, cache), repository


@pytest.mark.asyncio
async def test_schedule_day_cache_hit_skips_database(transaction_session, user):
    class_id = uuid4()
    cache = AsyncMock()
    cached = ScheduleDayRead(date=date(2026, 9, 14), lessons=[])
    cache.get.return_value = cached
    tested, repository = dependencies(transaction_session, class_id, uuid4(), cache)

    result = await tested.get_day(class_id, cached.date, user)

    assert result is cached
    repository.list_for_weekday.assert_not_awaited()


@pytest.mark.asyncio
async def test_schedule_change_invalidates_class_cache(transaction_session, admin):
    class_id, subject_id = uuid4(), uuid4()
    cache = AsyncMock()
    tested, repository = dependencies(transaction_session, class_id, subject_id, cache)
    repository.get_slot.return_value = None
    repository.create_entry.return_value = ScheduleEntryORM(
        id=uuid4(), class_id=class_id, subject_id=subject_id, weekday=0,
        lesson_number=1, start_time=time(8), end_time=time(9),
    )

    await tested.create_entry(
        class_id,
        ScheduleEntryCreate(
            subject_id=subject_id, weekday=0, lesson_number=1,
            start_time=time(8), end_time=time(9),
        ),
        admin,
    )

    assert cache.invalidate_pattern.await_count == 2


@pytest.mark.asyncio
async def test_duplicate_schedule_slot_is_rejected(transaction_session, admin):
    class_id, subject_id = uuid4(), uuid4()
    service, repository = dependencies(transaction_session, class_id, subject_id)
    repository.get_slot.return_value = ScheduleEntryORM(class_id=class_id, subject_id=subject_id, weekday=0, lesson_number=1, start_time=time(8), end_time=time(9))
    with pytest.raises(ScheduleConflictError):
        await service.create_entry(class_id, ScheduleEntryCreate(subject_id=subject_id, weekday=0, lesson_number=1, start_time=time(8), end_time=time(9)), admin)


@pytest.mark.asyncio
async def test_schedule_entry_update_rejects_invalid_time(transaction_session, admin):
    class_id, subject_id, entry_id = uuid4(), uuid4(), uuid4()
    service, repository = dependencies(transaction_session, class_id, subject_id)
    repository.get_entry.return_value = ScheduleEntryORM(id=entry_id, class_id=class_id, subject_id=subject_id, weekday=0, lesson_number=1, start_time=time(8), end_time=time(9))
    with pytest.raises(InvalidScheduleTimeError):
        await service.update_entry(class_id, entry_id, ScheduleEntryUpdate(start_time=time(10)), admin)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", [ScheduleOverrideType.REPLACED, ScheduleOverrideType.ADDED])
async def test_replaced_and_added_require_subject(transaction_session, admin, kind):
    service, _ = dependencies(transaction_session, uuid4(), uuid4())
    with pytest.raises(InvalidScheduleOverrideError):
        await service.create_override(uuid4(), ScheduleOverrideCreate(date=date(2026, 9, 14), lesson_number=2, override_type=kind), admin)


@pytest.mark.asyncio
async def test_cancelled_override_does_not_require_subject(transaction_session, admin):
    class_id = uuid4()
    service, repository = dependencies(transaction_session, class_id, uuid4())
    repository.get_override_slot.return_value = None
    entity = ScheduleOverrideORM(id=uuid4(), class_id=class_id, date=date(2026, 9, 14), lesson_number=2, override_type=ScheduleOverrideType.CANCELLED, created_by_telegram_id=admin.telegram_id)
    repository.create_override.return_value = entity
    assert await service.create_override(class_id, ScheduleOverrideCreate(date=entity.date, lesson_number=2, override_type=ScheduleOverrideType.CANCELLED), admin) is entity


@pytest.mark.asyncio
async def test_override_time_requires_both_values(transaction_session, admin):
    class_id, subject_id = uuid4(), uuid4()
    service, _ = dependencies(transaction_session, class_id, subject_id)
    with pytest.raises(InvalidScheduleOverrideError):
        await service.create_override(class_id, ScheduleOverrideCreate(date=date(2026, 9, 14), lesson_number=2, override_type=ScheduleOverrideType.REPLACED, subject_id=subject_id, start_time=time(10)), admin)


@pytest.mark.asyncio
async def test_created_schedule_event_type_is_correct(transaction_session, admin):
    class_id, subject_id = uuid4(), uuid4()
    service, repository = dependencies(transaction_session, class_id, subject_id)
    repository.get_slot.return_value = None
    entity = ScheduleEntryORM(id=uuid4(), class_id=class_id, subject_id=subject_id, weekday=0, lesson_number=1, start_time=time(8), end_time=time(9))
    repository.create_entry.return_value = entity
    await service.create_entry(class_id, ScheduleEntryCreate(subject_id=subject_id, weekday=0, lesson_number=1, start_time=time(8), end_time=time(9)), admin)
    assert service.pending_events[0].event_type == "schedule.created"
