"""Configuration settings for anomaly service."""

import os
from dataclasses import dataclass
from typing import Dict

from .thresholds import load_thresholds


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

    kafka_consumer: KafkaConsumerConfig = None
    kafka_producer: KafkaProducerConfig = None
    thresholds: Dict = None

    def __post_init__(self):
        """Load thresholds after initialization."""
        if self.kafka_consumer is None:
            self.kafka_consumer = KafkaConsumerConfig()
        if self.kafka_producer is None:
            self.kafka_producer = KafkaProducerConfig()
        if self.thresholds is None:
            threshold_data = load_thresholds()
            self.thresholds = threshold_data.get("thresholds", {})
