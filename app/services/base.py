from app.schemas import DomainEvent


class EventCollectingService:
    """Keeps domain events until the API layer publishes them to Kafka."""

    def __init__(self) -> None:
        self.pending_events: list[DomainEvent] = []

    def drain_events(self) -> list[DomainEvent]:
        events = self.pending_events.copy()
        self.pending_events.clear()
        return events

    def get_pending_events(self) -> tuple[DomainEvent, ...]:
        return tuple(self.pending_events)
