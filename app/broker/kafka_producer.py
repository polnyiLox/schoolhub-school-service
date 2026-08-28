import logging

from app.core.config import KafkaSettings
from app.schemas import DomainEvent

from .kafka_client import KafkaClient

logger = logging.getLogger(__name__)


class KafkaProducer:
    def __init__(self, kafka_client: KafkaClient, settings: KafkaSettings) -> None:
        self._kafka_client = kafka_client
        self._settings = settings

    async def publish(
        self,
        event: DomainEvent,
        topic: str | None = None,
    ) -> None:
        producer = await self._kafka_client.get_producer()
        target_topic = topic or self._settings.topic

        await producer.send_and_wait(
            topic=target_topic,
            key=str(event.aggregate_id).encode("utf-8"),
            value=event.model_dump_json().encode("utf-8"),
        )

        logger.info(
            "Kafka event published",
            extra={
                "event_id": str(event.event_id),
                "event_type": event.event_type,
                "topic": target_topic,
            },
        )
