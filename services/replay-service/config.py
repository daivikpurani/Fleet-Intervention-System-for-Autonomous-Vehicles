"""Configuration settings for replay service.

TODO: Implement settings for:
- Kafka broker configuration
- Dataset paths
- Replay rate configuration
"""

import os
from dataclasses import dataclass


@dataclass
class KafkaConfig:
    """Kafka producer configuration."""

    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    # Key serializer: vehicle_id (string)
    # Value serializer: JSON (RawTelemetryEvent)


@dataclass
class ReplayConfig:
    """Replay service configuration."""

    kafka: KafkaConfig = KafkaConfig()

