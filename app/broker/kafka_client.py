import asyncio
import logging

from aiokafka import AIOKafkaProducer

from app.core.config import KafkaSettings

logger = logging.getLogger(__name__)


class KafkaClient:
    def __init__(
        self,
        settings: KafkaSettings,
    ) -> None:
        self._producer: AIOKafkaProducer | None = None
        self._settings = settings
        self._connect_lock = asyncio.Lock()

    async def connect_producer(self) -> None:
        if self._producer is not None:
            return

        async with self._connect_lock:
            if self._producer is not None:
                return

            producer = AIOKafkaProducer(
                bootstrap_servers=self._settings.bootstrap_servers,
                client_id=self._settings.client_id,
                acks=self._settings.acks,
                request_timeout_ms=self._settings.request_timeout_ms,
                enable_idempotence=True,
                linger_ms=self._settings.linger_ms,
                compression_type=self._settings.compression_type,
            )

            try:
                await producer.start()
            except Exception:
                logger.exception(
                    "Kafka producer connection failed",
                    extra={"client_id": self._settings.client_id},
                )
                await producer.stop()
                raise
            self._producer = producer
            logger.info("Kafka producer connected", extra={"client_id": self._settings.client_id})

    async def get_producer(self) -> AIOKafkaProducer:
        await self.connect_producer()
        assert self._producer is not None
        return self._producer

    async def close_producer(self) -> None:
        producer = self._producer
        if producer is None:
            return

        self._producer = None
        await producer.stop()
        logger.info("Kafka producer closed", extra={"client_id": self._settings.client_id})
