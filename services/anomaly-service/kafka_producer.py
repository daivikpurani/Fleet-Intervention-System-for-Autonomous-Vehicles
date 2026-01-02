"""Kafka producer for anomalies topic.

Thin wrapper for publishing AnomalyEvent messages to the anomalies topic.
"""

import json
import logging
from typing import Optional

from services.schemas.events import AnomalyEvent

from .config import AnomalyConfig

logger = logging.getLogger(__name__)

# TODO: Implement anomaly_id-based deduplication here
# This will prevent duplicate anomalies from being published if the producer retries


class KafkaProducer:
    """Thin Kafka producer wrapper for anomalies topic."""

    def __init__(self, config: AnomalyConfig):
        """Initialize producer with configuration.

        Args:
            config: Anomaly service configuration
        """
        self.config = config
        self._producer: Optional[object] = None
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        """Initialize Kafka producer if not already initialized.

        Returns:
            True if initialized successfully, False otherwise
        """
        if self._initialized:
            return self._producer is not None

        try:
            # Lazy import to avoid dependency if Kafka is not available
            from kafka import KafkaProducer as _KafkaProducer

            self._producer = _KafkaProducer(
                bootstrap_servers=self.config.kafka_producer.bootstrap_servers,
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            )
            self._initialized = True
            logger.info("Kafka producer initialized")
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize Kafka producer: {e}")
            self._producer = None
            self._initialized = True  # Mark as attempted to avoid retry loops
            return False

    def produce(self, event: AnomalyEvent) -> None:
        """Publish an anomaly event to Kafka.

        Args:
            event: AnomalyEvent to publish

        This is a safe no-op if Kafka is unavailable.
        """
        if not self._ensure_initialized():
            logger.warning("Kafka producer not available, skipping event")
            return

        try:
            # Partition key: vehicle_id
            self._producer.send(
                topic="anomalies",
                key=event.vehicle_id,
                value=event.model_dump(),
            )
            logger.debug(f"Published anomaly {event.anomaly_id} for vehicle {event.vehicle_id}")
        except Exception as e:
            logger.warning(f"Failed to publish anomaly {event.anomaly_id}: {e}")
            # Safe no-op: do not raise, allow processing to continue

    def flush(self) -> None:
        """Flush any pending messages.

        Safe no-op if producer is not initialized.
        """
        if self._producer:
            try:
                self._producer.flush()
            except Exception as e:
                logger.warning(f"Failed to flush producer: {e}")

    def close(self) -> None:
        """Close the producer.

        Safe no-op if producer is not initialized.
        """
        if self._producer:
            try:
                self._producer.close()
            except Exception as e:
                logger.warning(f"Failed to close producer: {e}")

