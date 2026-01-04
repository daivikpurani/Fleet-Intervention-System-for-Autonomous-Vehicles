"""Main processing loop for anomaly service.

Consumes raw_telemetry events, maintains per-vehicle state,
extracts features, detects anomalies, and emits AnomalyEvent messages.
"""

import logging
from datetime import datetime
from uuid import uuid4

from services.schemas.events import AnomalyEvent, RawTelemetryEvent
from services.id_generator import (
    generate_incident_id,
    generate_vehicle_display_id,
    generate_scene_display_id,
)

from .anomalies.detectors import AnomalyDetector
from .config import AnomalyConfig
from .features.extractors import FeatureExtractor
from .features.windows import StateManager
from .kafka_consumer import KafkaConsumer
from .kafka_producer import KafkaProducer

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class AnomalyService:
    """Main anomaly detection service."""

    def __init__(self, config: AnomalyConfig):
        """Initialize anomaly service.

        Args:
            config: Anomaly service configuration
        """
        self.config = config
        self.consumer = KafkaConsumer(config)
        self.producer = KafkaProducer(config)
        self.state_manager = StateManager()
        self.feature_extractor = FeatureExtractor()
        self.detector = AnomalyDetector(config.thresholds)

        # Track active agent count per (scene_id, frame_index) for dropout detection
        # Maps (scene_id, frame_index) -> set of vehicle_ids seen in that frame
        self.scene_frame_vehicles: dict[tuple[str, int], set[str]] = {}

    def process_event(self, event: RawTelemetryEvent) -> None:
        """Process a single telemetry event.

        Args:
            event: RawTelemetryEvent to process
        """
        # Update vehicle state (ring buffer)
        if not self.state_manager.update_vehicle(event):
            # Event was rejected (too far out of order)
            return

        # Get vehicle state
        vehicle_state = self.state_manager.get_vehicle_state(event.vehicle_id)
        if vehicle_state is None:
            logger.warning(
                f"Vehicle state not found for {event.vehicle_id} after update"
            )
            return

        # Get frames within event-time window
        frames = vehicle_state.get_frames_in_window()

        # Check if we have sufficient history within window
        if not vehicle_state.has_sufficient_history(min_frames=2):
            logger.debug(
                f"Insufficient history in window for vehicle {event.vehicle_id}, skipping detection"
            )
            return

        # Update active agent count tracking (scene-scoped)
        # Track unique vehicle_ids per (scene_id, frame_index)
        scene_frame_key = (event.scene_id, event.frame_index)
        if scene_frame_key not in self.scene_frame_vehicles:
            self.scene_frame_vehicles[scene_frame_key] = set()
        self.scene_frame_vehicles[scene_frame_key].add(event.vehicle_id)

        # Get current active agent count for this frame in this scene
        current_count = len(self.scene_frame_vehicles.get(scene_frame_key, set()))

        # Update feature extractor with active agent count
        self.feature_extractor.update_active_agent_count(
            event.frame_index, current_count
        )

        # Get previous frame's agent count for dropout detection (same scene only)
        prev_frame_index = event.frame_index - 1
        prev_scene_frame_key = (event.scene_id, prev_frame_index)
        prev_frame_vehicles = self.scene_frame_vehicles.get(
            prev_scene_frame_key, set()
        )
        prev_active_agent_count = len(prev_frame_vehicles)

        # Extract features
        features = self.feature_extractor.extract_all_features(
            frames, event.frame_index
        )

        # Detect anomalies
        anomalies = self.detector.detect(
            event,
            features,
            frames,
            active_agent_count=current_count,
            prev_active_agent_count=prev_active_agent_count,
        )

        # Emit anomaly events
        for anomaly_result in anomalies:
            anomaly_id = uuid4()
            
            # Generate human-readable IDs
            incident_id = generate_incident_id(str(anomaly_id))
            vehicle_display_id = event.vehicle_display_id or generate_vehicle_display_id(
                event.vehicle_id, event.scene_id
            )
            scene_display_id = event.scene_display_id or generate_scene_display_id(
                event.scene_id, event.event_time
            )
            
            # Create human-readable rule display name
            rule_display_names = {
                "sudden_deceleration": "Sudden Deceleration",
                "perception_instability": "Perception Instability", 
                "dropout_proxy": "Sensor Dropout",
            }
            rule_display_name = rule_display_names.get(
                anomaly_result.rule_name, anomaly_result.rule_name.replace("_", " ").title()
            )
            
            anomaly_event = AnomalyEvent(
                anomaly_id=anomaly_id,
                incident_id=incident_id,
                event_time=event.event_time,
                processing_time=datetime.utcnow(),
                vehicle_id=event.vehicle_id,
                vehicle_display_id=vehicle_display_id,
                scene_id=event.scene_id,
                scene_display_id=scene_display_id,
                frame_index=event.frame_index,
                rule_name=anomaly_result.rule_name,
                rule_display_name=rule_display_name,
                features=anomaly_result.features,
                thresholds=anomaly_result.thresholds,
                severity=anomaly_result.severity,
            )

            self.producer.produce(anomaly_event)
            logger.info(
                f"Anomaly detected: {incident_id} ({rule_display_name}) "
                f"for vehicle {vehicle_display_id} at frame {event.frame_index} "
                f"(severity: {anomaly_result.severity})"
            )

    def run(self) -> None:
        """Run the anomaly detection service.

        Consumes events from Kafka and processes them.
        """
        logger.info("Starting anomaly service")

        try:
            for event in self.consumer.consume():
                try:
                    self.process_event(event)
                except Exception as e:
                    logger.error(
                        f"Error processing event {event.event_id}: {e}",
                        exc_info=True,
                    )
                    # Continue processing other events
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down")
        except Exception as e:
            logger.error(f"Fatal error in service: {e}", exc_info=True)
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Shutdown the service gracefully."""
        logger.info("Shutting down anomaly service")
        self.producer.flush()
        self.consumer.close()
        self.producer.close()


def main() -> None:
    """Main entry point."""
    config = AnomalyConfig()
    service = AnomalyService(config)
    service.run()


if __name__ == "__main__":
    main()
