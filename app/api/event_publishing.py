from collections.abc import Awaitable

from app.broker import KafkaProducer
from app.services.base import EventCollectingService


async def execute_and_publish[ResultT](
    operation: Awaitable[ResultT],
    service: EventCollectingService,
    producer: KafkaProducer,
    correlation_id: str | None = None,
) -> ResultT:
    """Execute a service operation and publish events created by that operation."""
    result = await operation

    for event in service.get_pending_events():
        if event.correlation_id is None:
            event.correlation_id = correlation_id
        await producer.publish(event)

    service.drain_events()
    return result
