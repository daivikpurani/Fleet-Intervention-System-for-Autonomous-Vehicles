"""Configuration settings for anomaly service.

TODO: Implement settings for:
- Kafka consumer/producer configuration
- Feature extraction parameters
- Anomaly detection thresholds
"""

import os
from dataclasses import dataclass


@dataclass
class KafkaConsumerConfig:
    """Kafka consumer configuration."""

    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    group_id: str = "anomaly-service"
    # Key deserializer: string (vehicle_id)
    # Value deserializer: JSON (RawTelemetryEvent)


@dataclass
class KafkaProducerConfig:
    """Kafka producer configuration."""

    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    # Key serializer: vehicle_id (string)
    # Value serializer: JSON (AnomalyEvent)


@dataclass
class AnomalyConfig:
    """Anomaly service configuration."""

    kafka_consumer: KafkaConsumerConfig = KafkaConsumerConfig()
    kafka_producer: KafkaProducerConfig = KafkaProducerConfig()

