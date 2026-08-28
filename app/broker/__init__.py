from app.core.config import settings

from .kafka_client import KafkaClient
from .kafka_producer import KafkaProducer

kafka_client = KafkaClient(settings.kafka)
kafka_producer = KafkaProducer(kafka_client, settings.kafka)

__all__ = ["KafkaClient", "KafkaProducer", "kafka_client", "kafka_producer"]
