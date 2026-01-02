"""Configuration settings for replay service."""

import os
from dataclasses import dataclass, field


@dataclass
class KafkaConfig:
    """Kafka producer configuration."""

    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    # Key serializer: vehicle_id (string)
    # Value serializer: JSON (RawTelemetryEvent)


@dataclass
class ReplayConfig:
    """Replay service configuration."""

    kafka: KafkaConfig = field(default_factory=KafkaConfig)
    dataset_path: str = os.getenv("L5KIT_DATASET_PATH", "dataset/sample.zarr")
    replay_rate_hz: float = float(os.getenv("REPLAY_RATE_HZ", "10.0"))

