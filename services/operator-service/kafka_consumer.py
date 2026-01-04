"""Kafka consumer for anomalies and raw_telemetry topics.

Thin wrapper for consuming AnomalyEvent and RawTelemetryEvent messages.
"""

import json
import logging
import time
from collections import deque
from typing import Iterator, Optional, Union
from uuid import UUID

from services.schemas.events import AnomalyEvent, RawTelemetryEvent
from services.kafka_utils import wait_for_kafka

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
        self._retry_count = 0
        self._max_retries = 10
        self._base_retry_delay = 2
        self._max_retry_delay = 15
        self._deduplication_cache_size = deduplication_cache_size
        # In-memory deduplication cache: use deque for bounded size and set for O(1) lookups
        self._seen_anomaly_ids: deque = deque(maxlen=deduplication_cache_size)
        self._seen_anomaly_ids_set: set[UUID] = set()

    def _ensure_initialized(self) -> bool:
        """Initialize Kafka consumer if not already initialized.

        Returns:
            True if initialized successfully, False otherwise
        """
        if self._initialized and self._consumer is not None:
            return True

        # Wait for Kafka on first attempt
        if self._retry_count == 0:
            logger.info("Waiting for Kafka to be ready...")
            wait_for_kafka(
                self.config.kafka_consumer.bootstrap_servers,
                max_wait=30.0,
                check_interval=2.0
            )

        # Retry logic with exponential backoff
        while self._retry_count < self._max_retries:
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
                    request_timeout_ms=40000,  # FIXED: Must be > session_timeout_ms
                    session_timeout_ms=10000,
                    max_poll_interval_ms=300000,  # 5 minutes
                    api_version=(0, 10, 1),
                )
                self._initialized = True
                self._retry_count = 0
                logger.info("Kafka consumer initialized")
                return True
            except Exception as e:
                self._retry_count += 1
                if self._retry_count < self._max_retries:
                    delay = min(self._base_retry_delay * (2 ** (self._retry_count - 1)), self._max_retry_delay)
                    logger.warning(
                        f"Failed to initialize Kafka consumer (attempt {self._retry_count}/{self._max_retries}): {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to initialize Kafka consumer after {self._max_retries} attempts: {e}")
                    self._consumer = None
                    self._initialized = True
                    return False

        return False

    def consume(self) -> Iterator[AnomalyEvent]:
        """Consume messages from Kafka with deduplication.

        Yields:
            AnomalyEvent instances (deduplicated by anomaly_id)

        This will retry connection if Kafka becomes unavailable.
        """
        while True:
            if not self._ensure_initialized():
                logger.warning("Kafka consumer not available. Waiting before retrying...")
                time.sleep(5)
                self._initialized = False
                self._retry_count = 0
                continue

            try:
                for message in self._consumer:
                    try:
                        event = AnomalyEvent(**message.value)
                        anomaly_id = event.anomaly_id

                        # Deduplication: skip if we've seen this anomaly_id recently (O(1) lookup)
                        if anomaly_id in self._seen_anomaly_ids_set:
                            logger.debug(
                                f"Skipping duplicate anomaly {anomaly_id} for vehicle {event.vehicle_id}"
                            )
                            continue

                        # Evict oldest if cache is full (before deque auto-evicts)
                        if len(self._seen_anomaly_ids) >= self._deduplication_cache_size:
                            oldest_id = self._seen_anomaly_ids[0]
                            self._seen_anomaly_ids_set.discard(oldest_id)

                        # Add to cache (both structures)
                        self._seen_anomaly_ids.append(anomaly_id)
                        self._seen_anomaly_ids_set.add(anomaly_id)
                        logger.debug(f"Consumed anomaly {anomaly_id} for vehicle {event.vehicle_id}")
                        yield event
                    except Exception as e:
                        logger.warning(f"Failed to parse message: {e}")
                        # Continue processing other messages
            except Exception as e:
                logger.error(f"Error consuming messages: {e}. Will retry connection...")
                if self._consumer:
                    try:
                        self._consumer.close()
                    except Exception:
                        pass
                self._consumer = None
                self._initialized = False
                self._retry_count = 0
                time.sleep(5)

    def close(self) -> None:
        """Close the consumer.

        Safe no-op if consumer is not initialized.
        """
        if self._consumer:
            try:
                self._consumer.close()
            except Exception as e:
                logger.warning(f"Failed to close consumer: {e}")


class TelemetryConsumer:
    """Kafka consumer for raw_telemetry topic."""

    def __init__(self, config: OperatorConfig):
        """Initialize consumer with configuration.

        Args:
            config: Operator service configuration
        """
        self.config = config
        self._consumer: Optional[object] = None
        self._initialized = False
        self._retry_count = 0
        self._max_retries = 10
        self._base_retry_delay = 2
        self._max_retry_delay = 15

    def _ensure_initialized(self) -> bool:
        """Initialize Kafka consumer if not already initialized.

        Returns:
            True if initialized successfully, False otherwise
        """
        if self._initialized and self._consumer is not None:
            return True

        # Wait for Kafka on first attempt
        if self._retry_count == 0:
            logger.info("Waiting for Kafka to be ready (telemetry consumer)...")
            wait_for_kafka(
                self.config.kafka_consumer.bootstrap_servers,
                max_wait=30.0,
                check_interval=2.0
            )

        # Retry logic with exponential backoff
        while self._retry_count < self._max_retries:
            try:
                # Lazy import to avoid dependency if Kafka is not available
                from kafka import KafkaConsumer as _KafkaConsumer

                self._consumer = _KafkaConsumer(
                    "raw_telemetry",
                    bootstrap_servers=self.config.kafka_consumer.bootstrap_servers,
                    group_id=f"{self.config.kafka_consumer.group_id}_telemetry",
                    key_deserializer=lambda k: k.decode("utf-8") if k else None,
                    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                    auto_offset_reset="earliest",  # Consume from beginning to catch up on startup
                    enable_auto_commit=True,
                    request_timeout_ms=40000,  # FIXED: Must be > session_timeout_ms
                    session_timeout_ms=10000,
                    max_poll_interval_ms=300000,  # 5 minutes
                    api_version=(0, 10, 1),
                )
                self._initialized = True
                self._retry_count = 0
                logger.info("Telemetry Kafka consumer initialized")
                return True
            except Exception as e:
                self._retry_count += 1
                if self._retry_count < self._max_retries:
                    delay = min(self._base_retry_delay * (2 ** (self._retry_count - 1)), self._max_retry_delay)
                    logger.warning(
                        f"Failed to initialize telemetry Kafka consumer (attempt {self._retry_count}/{self._max_retries}): {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to initialize telemetry Kafka consumer after {self._max_retries} attempts: {e}")
                    self._consumer = None
                    self._initialized = True
                    return False

        return False

    def consume(self) -> Iterator[RawTelemetryEvent]:
        """Consume messages from raw_telemetry topic.

        Yields:
            RawTelemetryEvent instances

        This will retry connection if Kafka becomes unavailable.
        """
        while True:
            if not self._ensure_initialized():
                logger.warning("Telemetry Kafka consumer not available. Waiting before retrying...")
                time.sleep(5)
                self._initialized = False
                self._retry_count = 0
                continue

            try:
                for message in self._consumer:
                    try:
                        event = RawTelemetryEvent(**message.value)
                        logger.debug(f"Consumed telemetry for vehicle {event.vehicle_id}")
                        yield event
                    except Exception as e:
                        logger.warning(f"Failed to parse telemetry message: {e}")
                        # Continue processing other messages
            except Exception as e:
                logger.error(f"Error consuming telemetry messages: {e}. Will retry connection...")
                if self._consumer:
                    try:
                        self._consumer.close()
                    except Exception:
                        pass
                self._consumer = None
                self._initialized = False
                self._retry_count = 0
                time.sleep(5)

    def close(self) -> None:
        """Close the consumer.

        Safe no-op if consumer is not initialized.
        """
        if self._consumer:
            try:
                self._consumer.close()
            except Exception as e:
                logger.warning(f"Failed to close telemetry consumer: {e}")

