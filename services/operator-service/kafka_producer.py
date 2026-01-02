"""Kafka producer for operator_actions topic.

Thin wrapper for publishing OperatorActionEvent messages to the operator_actions topic.
"""

import json
import logging
from typing import Optional

from services.schemas.events import OperatorActionEvent

from .config import OperatorConfig

logger = logging.getLogger(__name__)

# TODO: Implement action_id-based deduplication here
# This will prevent duplicate actions from being published if the producer retries


class KafkaProducer:
    """Thin Kafka producer wrapper for operator_actions topic."""

    def __init__(self, config: OperatorConfig):
        """Initialize producer with configuration.

        Args:
            config: Operator service configuration
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

    def produce(self, event: OperatorActionEvent) -> None:
        """Publish an operator action event to Kafka.

        Args:
            event: OperatorActionEvent to publish

        This is a safe no-op if Kafka is unavailable.
        """
        if not self._ensure_initialized():
            logger.warning("Kafka producer not available, skipping event")
            return

        try:
            # Partition key: vehicle_id (for per-vehicle ordering)
            self._producer.send(
                topic="operator_actions",
                key=event.vehicle_id,
                value=event.model_dump(),
            )
            logger.debug(f"Published action {event.action_id} for vehicle {event.vehicle_id}")
        except Exception as e:
            logger.warning(f"Failed to publish action {event.action_id}: {e}")
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

