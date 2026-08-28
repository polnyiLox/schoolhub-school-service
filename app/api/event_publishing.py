from collections.abc import Awaitable
from typing import TypeVar

from app.broker import KafkaProducer
from app.services.base import EventCollectingService

ResultT = TypeVar("ResultT")


async def execute_and_publish(
    operation: Awaitable[ResultT],
    service: EventCollectingService,
    producer: KafkaProducer,
) -> ResultT:
    """Execute a service operation and publish events created by that operation."""
    result = await operation

    for event in service.drain_events():
        await producer.publish(event)

    return result
