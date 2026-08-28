from app.schemas import DomainEvent


class EventCollectingService:
    """Keeps event payloads until Kafka publishing is implemented by the project owner."""

    def __init__(self) -> None:
        self.pending_events: list[DomainEvent] = []

    def drain_events(self) -> list[DomainEvent]:
        events = self.pending_events.copy()
        self.pending_events.clear()
        return events

    def get_pending_events(self) -> tuple[DomainEvent, ...]:
        return tuple(self.pending_events)
