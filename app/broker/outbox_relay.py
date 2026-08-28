import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import OutboxSettings
from app.db.models import OutboxEventORM
from app.repositories import OutboxRepository
from app.schemas import DomainEvent

from .kafka_producer import KafkaProducer

logger = logging.getLogger(__name__)


class OutboxRelay:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        producer: KafkaProducer,
        settings: OutboxSettings,
    ) -> None:
        self._session_factory = session_factory
        self._producer = producer
        self._settings = settings
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="school-service-outbox-relay")
        logger.info("Outbox relay started")

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is None:
            return

        self._stop_event.set()
        try:
            await asyncio.wait_for(task, timeout=self._settings.shutdown_timeout_seconds)
        except TimeoutError:
            logger.warning("Outbox relay did not stop in time; cancelling it")
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        logger.info("Outbox relay stopped")

    async def process_batch(self) -> int:
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            repository = OutboxRepository(session)
            records = await repository.claim_pending(
                available_at=now,
                batch_size=self._settings.batch_size,
            )
            for record in records:
                try:
                    event = DomainEvent.model_validate(record.payload)
                    await self._producer.publish(event, topic=record.topic)
                except Exception as error:
                    await self._schedule_retry(repository, record, error, now)
                    continue
                await repository.mark_published(record.id, now)
        return len(records)

    async def cleanup_published(self) -> None:
        cutoff = datetime.now(UTC) - timedelta(hours=self._settings.published_retention_hours)
        async with self._session_factory() as session, session.begin():
            await OutboxRepository(session).delete_published_before(cutoff)
        logger.info("Expired published outbox events removed", extra={"cutoff": cutoff.isoformat()})

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()
        next_cleanup_at = loop.time() + self._settings.cleanup_interval_seconds
        while not self._stop_event.is_set():
            try:
                processed = await self.process_batch()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Unexpected outbox relay failure")
                processed = 0

            if loop.time() >= next_cleanup_at:
                try:
                    await self.cleanup_published()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Outbox cleanup failed")
                next_cleanup_at = loop.time() + self._settings.cleanup_interval_seconds

            if processed >= self._settings.batch_size:
                continue
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._settings.poll_interval_seconds,
                )
            except TimeoutError:
                pass

    async def _schedule_retry(
        self,
        repository: OutboxRepository,
        record: OutboxEventORM,
        error: Exception,
        now: datetime,
    ) -> None:
        attempts = record.attempts + 1
        terminal = attempts >= self._settings.max_attempts
        delay_seconds = min(
            self._settings.retry_base_seconds * (2 ** (attempts - 1)),
            self._settings.retry_max_seconds,
        )
        error_message = f"{type(error).__name__}: {error}"[:2_000]
        await repository.mark_retry(
            record.id,
            attempts=attempts,
            available_at=now + timedelta(seconds=delay_seconds),
            last_error=error_message,
            terminal=terminal,
        )
        logger.warning(
            "Outbox event delivery failed",
            extra={
                "event_id": str(record.id),
                "attempts": attempts,
                "terminal": terminal,
            },
            exc_info=error,
        )
