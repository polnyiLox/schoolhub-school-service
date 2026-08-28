from app.repositories import OutboxRepository
from app.schemas import DomainEvent


class EventCollectingService:
    """Records domain events and, when configured, persists them in the outbox."""

    def __init__(
        self,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        self.pending_events: list[DomainEvent] = []
        self._outbox_repository = outbox_repository

    def record_event(self, event: DomainEvent) -> None:
        self.pending_events.append(event)
        if self._outbox_repository is not None:
            self._outbox_repository.enqueue(event)

    def drain_events(self) -> list[DomainEvent]:
        events = self.pending_events.copy()
        self.pending_events.clear()
        return events

    def get_pending_events(self) -> tuple[DomainEvent, ...]:
        return tuple(self.pending_events)
