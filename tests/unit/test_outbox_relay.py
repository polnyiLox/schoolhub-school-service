import asyncio
from contextlib import AbstractAsyncContextManager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.broker import KafkaProducer, OutboxRelay
from app.core.config import OutboxSettings
from app.db.models import OutboxEventORM
from app.schemas import build_domain_event


class TransactionContext(AbstractAsyncContextManager):
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


def session_factory() -> MagicMock:
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.begin.return_value = TransactionContext()
    return MagicMock(return_value=session)


def outbox_record(attempts: int = 0) -> OutboxEventORM:
    event = build_domain_event(
        event_type="homework.created",
        aggregate_type="homework",
        aggregate_id=uuid4(),
        actor_telegram_id=42,
        class_id=uuid4(),
    )
    return OutboxEventORM(
        id=event.event_id,
        topic="school.events",
        payload=event.model_dump(mode="json"),
        attempts=attempts,
    )


@pytest.mark.asyncio
async def test_relay_marks_successfully_published_event() -> None:
    record = outbox_record()
    repository = MagicMock()
    repository.claim_pending = AsyncMock(return_value=[record])
    repository.mark_published = AsyncMock()
    repository.mark_retry = AsyncMock()
    producer = AsyncMock(spec=KafkaProducer)
    relay = OutboxRelay(session_factory(), producer, OutboxSettings())

    with patch("app.broker.outbox_relay.OutboxRepository", return_value=repository):
        assert await relay.process_batch() == 1

    published_event = producer.publish.await_args.args[0]
    assert published_event.event_id == record.id
    producer.publish.assert_awaited_once_with(published_event, topic="school.events")
    repository.mark_published.assert_awaited_once()
    repository.mark_retry.assert_not_awaited()


@pytest.mark.asyncio
async def test_relay_schedules_exponential_retry() -> None:
    record = outbox_record(attempts=2)
    repository = MagicMock()
    repository.claim_pending = AsyncMock(return_value=[record])
    repository.mark_published = AsyncMock()
    repository.mark_retry = AsyncMock()
    producer = AsyncMock(spec=KafkaProducer)
    producer.publish.side_effect = ConnectionError("Kafka unavailable")
    relay = OutboxRelay(
        session_factory(),
        producer,
        OutboxSettings(max_attempts=5, retry_base_seconds=2, retry_max_seconds=60),
    )

    with patch("app.broker.outbox_relay.OutboxRepository", return_value=repository):
        assert await relay.process_batch() == 1

    retry = repository.mark_retry.await_args
    assert retry.kwargs["attempts"] == 3
    assert retry.kwargs["terminal"] is False
    assert retry.kwargs["last_error"] == "ConnectionError: Kafka unavailable"
    repository.mark_published.assert_not_awaited()


@pytest.mark.asyncio
async def test_relay_start_and_stop_are_idempotent() -> None:
    relay = OutboxRelay(
        session_factory(),
        AsyncMock(spec=KafkaProducer),
        OutboxSettings(poll_interval_seconds=60),
    )
    relay.process_batch = AsyncMock(return_value=0)

    await relay.start()
    await relay.start()
    await asyncio.sleep(0)
    assert relay.is_running is True

    await relay.stop()
    await relay.stop()
    assert relay.is_running is False
