"""Configuration settings for operator service."""

import os
from dataclasses import dataclass, field


@dataclass
class DatabaseConfig:
    """Database configuration."""

    database_url: str = os.getenv(
        "DATABASE_URL",
        f"postgresql://postgres:postgres@localhost:{os.getenv('POSTGRES_PORT', '5432')}/fleetops",
    )


@dataclass
class KafkaConsumerConfig:
    """Kafka consumer configuration."""

    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    group_id: str = "operator-service"
    # Key deserializer: string (vehicle_id)
    # Value deserializer: JSON (AnomalyEvent)


@dataclass
class KafkaProducerConfig:
    """Kafka producer configuration."""

    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    # Key serializer: action_id (string, UUID)
    # Value serializer: JSON (OperatorActionEvent)


@dataclass
class OperatorConfig:
    """Operator service configuration."""

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    kafka_consumer: KafkaConsumerConfig = field(default_factory=KafkaConsumerConfig)
    kafka_producer: KafkaProducerConfig = field(default_factory=KafkaProducerConfig)

