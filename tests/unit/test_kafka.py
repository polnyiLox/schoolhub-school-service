import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.api.event_publishing import execute_and_publish
from app.broker import KafkaClient, KafkaProducer
from app.core.config import KafkaSettings
from app.schemas import build_domain_event
from app.services.base import EventCollectingService


def event(event_type: str = "homework.created"):
    return build_domain_event(
        event_type=event_type,
        aggregate_type="homework",
        aggregate_id=uuid4(),
        actor_telegram_id=42,
        class_id=uuid4(),
        payload={"homework_id": "homework-1"},
    )


@pytest.mark.asyncio
async def test_kafka_client_connects_only_once():
    raw_producer = MagicMock()
    raw_producer.start = AsyncMock()
    raw_producer.stop = AsyncMock()

    with patch("app.broker.kafka_client.AIOKafkaProducer", return_value=raw_producer) as producer_class:
        client = KafkaClient(KafkaSettings())
        await client.connect_producer()
        await client.connect_producer()

    producer_class.assert_called_once()
    assert producer_class.call_args.kwargs["acks"] == "all"
    assert producer_class.call_args.kwargs["enable_idempotence"] is True
    assert producer_class.call_args.kwargs["compression_type"] == "gzip"
    raw_producer.start.assert_awaited_once()


@pytest.mark.asyncio
async def test_kafka_client_cleans_up_after_connection_failure():
    raw_producer = MagicMock()
    raw_producer.start = AsyncMock(side_effect=ConnectionError("Kafka unavailable"))
    raw_producer.stop = AsyncMock()

    with patch("app.broker.kafka_client.AIOKafkaProducer", return_value=raw_producer):
        client = KafkaClient(KafkaSettings())
        with pytest.raises(ConnectionError, match="Kafka unavailable"):
            await client.connect_producer()

    raw_producer.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_kafka_client_closes_connected_producer():
    raw_producer = MagicMock()
    raw_producer.start = AsyncMock()
    raw_producer.stop = AsyncMock()

    with patch("app.broker.kafka_client.AIOKafkaProducer", return_value=raw_producer):
        client = KafkaClient(KafkaSettings())
        await client.connect_producer()
        await client.close_producer()
        await client.close_producer()

    raw_producer.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_serializes_event_and_uses_aggregate_as_key():
    raw_producer = AsyncMock()
    client = AsyncMock()
    client.get_producer.return_value = raw_producer
    domain_event = event()

    await KafkaProducer(client, KafkaSettings()).publish(domain_event)

    call = raw_producer.send_and_wait.await_args
    assert call.kwargs["topic"] == "school.events"
    assert call.kwargs["key"] == str(domain_event.aggregate_id).encode("utf-8")
    payload = json.loads(call.kwargs["value"])
    assert payload["event_id"] == str(domain_event.event_id)
    assert payload["event_type"] == "homework.created"


@pytest.mark.asyncio
async def test_publish_can_override_default_topic():
    raw_producer = AsyncMock()
    client = AsyncMock()
    client.get_producer.return_value = raw_producer

    await KafkaProducer(client, KafkaSettings()).publish(event(), topic="school.audit")

    assert raw_producer.send_and_wait.await_args.kwargs["topic"] == "school.audit"


@pytest.mark.asyncio
async def test_execute_and_publish_returns_operation_result():
    service = EventCollectingService()
    domain_event = event()
    service.pending_events.append(domain_event)
    producer = AsyncMock(spec=KafkaProducer)

    async def operation() -> str:
        return "created"

    result = await execute_and_publish(operation(), service, producer)

    assert result == "created"
    producer.publish.assert_awaited_once_with(domain_event)
    assert service.pending_events == []


@pytest.mark.asyncio
async def test_execute_and_publish_adds_request_correlation_id():
    service = EventCollectingService()
    domain_event = event()
    service.pending_events.append(domain_event)
    producer = AsyncMock(spec=KafkaProducer)

    async def operation() -> None:
        return None

    await execute_and_publish(
        operation(),
        service,
        producer,
        correlation_id="request-42",
    )

    published_event = producer.publish.await_args.args[0]
    assert published_event.correlation_id == "request-42"


@pytest.mark.asyncio
async def test_failed_service_operation_does_not_publish():
    service = EventCollectingService()
    producer = AsyncMock(spec=KafkaProducer)

    async def operation() -> None:
        raise ValueError("database error")

    with pytest.raises(ValueError, match="database error"):
        await execute_and_publish(operation(), service, producer)

    producer.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_publish_failure_keeps_pending_event():
    service = EventCollectingService()
    domain_event = event()
    service.pending_events.append(domain_event)
    producer = AsyncMock(spec=KafkaProducer)
    producer.publish.side_effect = RuntimeError("Kafka unavailable")

    async def operation() -> None:
        return None

    with pytest.raises(RuntimeError, match="Kafka unavailable"):
        await execute_and_publish(operation(), service, producer)

    assert service.get_pending_events() == (domain_event,)
