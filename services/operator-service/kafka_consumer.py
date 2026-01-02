"""Kafka consumer for anomalies topic.

Thin wrapper for consuming AnomalyEvent messages from the anomalies topic.
"""

import json
import logging
from collections import deque
from typing import Iterator, Optional
from uuid import UUID

from services.schemas.events import AnomalyEvent

from .config import OperatorConfig

logger = logging.getLogger(__name__)


class KafkaConsumer:
    """Thin Kafka consumer wrapper for anomalies topic."""

    def __init__(self, config: OperatorConfig, deduplication_cache_size: int = 1000):
        """Initialize consumer with configuration.

        Args:
            config: Operator service configuration
            deduplication_cache_size: Maximum number of anomaly_ids to keep in cache
        """
        self.config = config
        self._consumer: Optional[object] = None
        self._initialized = False
        # In-memory deduplication cache: use deque for bounded size
        self._seen_anomaly_ids: deque = deque(maxlen=deduplication_cache_size)

    def _ensure_initialized(self) -> bool:
        """Initialize Kafka consumer if not already initialized.

        Returns:
            True if initialized successfully, False otherwise
        """
        if self._initialized:
            return self._consumer is not None

        try:
            # Lazy import to avoid dependency if Kafka is not available
            from kafka import KafkaConsumer as _KafkaConsumer

            self._consumer = _KafkaConsumer(
                "anomalies",
                bootstrap_servers=self.config.kafka_consumer.bootstrap_servers,
                group_id=self.config.kafka_consumer.group_id,
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
            )
            self._initialized = True
            logger.info("Kafka consumer initialized")
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize Kafka consumer: {e}")
            self._consumer = None
            self._initialized = True  # Mark as attempted to avoid retry loops
            return False

    def consume(self) -> Iterator[AnomalyEvent]:
        """Consume messages from Kafka with deduplication.

        Yields:
            AnomalyEvent instances (deduplicated by anomaly_id)

        This is a safe no-op if Kafka is unavailable (yields nothing).
        """
        if not self._ensure_initialized():
            logger.warning("Kafka consumer not available, no messages will be consumed")
            return

        try:
            for message in self._consumer:
                try:
                    event = AnomalyEvent(**message.value)
                    anomaly_id = event.anomaly_id

                    # Deduplication: skip if we've seen this anomaly_id recently
                    if anomaly_id in self._seen_anomaly_ids:
                        logger.debug(
                            f"Skipping duplicate anomaly {anomaly_id} for vehicle {event.vehicle_id}"
                        )
                        continue

                    # Add to cache
                    self._seen_anomaly_ids.append(anomaly_id)
                    logger.debug(f"Consumed anomaly {anomaly_id} for vehicle {event.vehicle_id}")
                    yield event
                except Exception as e:
                    logger.warning(f"Failed to parse message: {e}")
                    # Continue processing other messages
        except Exception as e:
            logger.warning(f"Error consuming messages: {e}")
            # Safe no-op: yield nothing

    def close(self) -> None:
        """Close the consumer.

        Safe no-op if consumer is not initialized.
        """
        if self._consumer:
            try:
                self._consumer.close()
            except Exception as e:
                logger.warning(f"Failed to close consumer: {e}")

