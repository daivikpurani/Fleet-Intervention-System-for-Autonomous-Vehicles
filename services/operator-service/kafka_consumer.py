"""Kafka consumer for anomalies topic.

Thin wrapper for consuming AnomalyEvent messages from the anomalies topic.
"""

import json
import logging
from typing import Iterator, Optional

from services.schemas.events import AnomalyEvent

from .config import OperatorConfig

logger = logging.getLogger(__name__)

# TODO: Implement anomaly_id-based deduplication here
# This will prevent processing duplicate anomalies if the consumer receives them
# TODO: Implement per-vehicle ordering guarantees enforcement here
# This will ensure anomalies from the same vehicle are processed in order


class KafkaConsumer:
    """Thin Kafka consumer wrapper for anomalies topic."""

    def __init__(self, config: OperatorConfig):
        """Initialize consumer with configuration.

        Args:
            config: Operator service configuration
        """
        self.config = config
        self._consumer: Optional[object] = None
        self._initialized = False

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
        """Consume messages from Kafka.

        Yields:
            AnomalyEvent instances

        This is a safe no-op if Kafka is unavailable (yields nothing).
        """
        if not self._ensure_initialized():
            logger.warning("Kafka consumer not available, no messages will be consumed")
            return

        try:
            for message in self._consumer:
                try:
                    event = AnomalyEvent(**message.value)
                    logger.debug(f"Consumed anomaly {event.anomaly_id} for vehicle {event.vehicle_id}")
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

