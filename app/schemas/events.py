from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    producer: str = "school-service"
    aggregate_type: str
    aggregate_id: UUID
    actor_telegram_id: int
    class_id: UUID
    correlation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


def build_domain_event(
    *, event_type: str, aggregate_type: str, aggregate_id: UUID,
    actor_telegram_id: int, class_id: UUID, correlation_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> DomainEvent:
    """Build an event payload. Publishing is intentionally outside this service."""
    return DomainEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        actor_telegram_id=actor_telegram_id,
        class_id=class_id,
        correlation_id=correlation_id,
        payload=payload or {},
    )
