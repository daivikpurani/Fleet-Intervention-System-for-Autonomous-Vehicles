"""Alert service for processing anomaly events and managing alerts."""

import json
import logging
from uuid import UUID

from sqlalchemy.orm import Session

from services.schemas.events import AnomalyEvent
from ..db.models import Alert, AlertStatus
from .vehicle_state_service import VehicleStateService

logger = logging.getLogger(__name__)


class AlertService:
    """Service for managing alerts from anomaly events."""

    @staticmethod
    def process_anomaly_event(event: AnomalyEvent, db: Session) -> Alert:
        """Process an anomaly event and create or update an alert.

        Idempotency: Uses anomaly_id to prevent duplicates.
        - If alert exists: update last_seen_event_time and anomaly_payload
        - If new: create Alert with status=OPEN

        Args:
            event: AnomalyEvent from Kafka
            db: Database session

        Returns:
            Alert object (created or updated)
        """
        # Check if alert exists by anomaly_id
        existing_alert = db.query(Alert).filter(
            Alert.anomaly_id == event.anomaly_id
        ).first()

        if existing_alert:
            # Update existing alert
            existing_alert.last_seen_event_time = event.event_time
            existing_alert.anomaly_payload = json.loads(event.model_dump_json())
            db.commit()
            db.refresh(existing_alert)
            logger.debug(
                f"Updated existing alert {existing_alert.id} for anomaly {event.anomaly_id}"
            )
            return existing_alert

        # Create new alert
        alert = Alert(
            vehicle_id=event.vehicle_id,
            scene_id=event.scene_id,
            frame_index=event.frame_index,
            anomaly_id=event.anomaly_id,
            rule_name=event.rule_name,
            severity=event.severity,
            status=AlertStatus.OPEN,
            anomaly_payload=json.loads(event.model_dump_json()),
            first_seen_event_time=event.event_time,
            last_seen_event_time=event.event_time,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        logger.info(
            f"Created new alert {alert.id} for vehicle {event.vehicle_id} "
            f"(anomaly: {event.anomaly_id}, rule: {event.rule_name})"
        )

        # Update vehicle state (NORMAL -> ALERTING if first OPEN alert)
        VehicleStateService.update_state(event.vehicle_id, db)

        return alert

