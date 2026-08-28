from uuid import uuid4

from app.schemas import build_domain_event


def build(event_type: str = "homework.created"):
    return build_domain_event(
        event_type=event_type,
        aggregate_type="homework",
        aggregate_id=uuid4(),
        actor_telegram_id=42,
        class_id=uuid4(),
        correlation_id="request-1",
        payload={"subject_id": "subject"},
    )


def test_event_has_requested_type():
    assert build().event_type == "homework.created"


def test_event_has_aggregate_id():
    assert build().aggregate_id is not None


def test_event_has_class_id_and_actor():
    event = build()
    assert event.class_id is not None
    assert event.actor_telegram_id == 42


def test_event_uses_school_service_producer_and_correlation():
    event = build("schedule.updated")
    assert event.producer == "school-service"
    assert event.correlation_id == "request-1"
