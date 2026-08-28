from app.core.config import settings
from app.db.session import SessionLocal

from .kafka_client import KafkaClient
from .kafka_producer import KafkaProducer
from .outbox_relay import OutboxRelay

kafka_client = KafkaClient(settings.kafka)
kafka_producer = KafkaProducer(kafka_client, settings.kafka)
outbox_relay = OutboxRelay(SessionLocal, kafka_producer, settings.outbox)

__all__ = [
    "KafkaClient",
    "KafkaProducer",
    "OutboxRelay",
    "kafka_client",
    "kafka_producer",
    "outbox_relay",
]
