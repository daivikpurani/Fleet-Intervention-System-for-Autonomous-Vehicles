"""Action service for creating operator actions and handling state transitions."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from services.schemas.events import OperatorActionEvent
from ..db.models import Alert, AlertStatus, OperatorAction, ActionType, VehicleState
from ..kafka_producer import KafkaProducer
from .vehicle_state_service import VehicleStateService

logger = logging.getLogger(__name__)


class ActionService:
    """Service for managing operator actions."""

    def __init__(self, kafka_producer: KafkaProducer):
        """Initialize action service.

        Args:
            kafka_producer: Kafka producer for publishing action events
        """
        self.kafka_producer = kafka_producer

    def create_action(
        self,
        action_type: ActionType,
        vehicle_id: str,
        alert_id: Optional[UUID],
        actor: str,
        payload: dict,
        db: Session,
    ) -> OperatorAction:
        """Create an operator action and handle state transitions.

        Handles state transitions:
        - ACKNOWLEDGE_ALERT: Update alert status to ACKNOWLEDGED
        - RESOLVE_ALERT: Update alert status to RESOLVED (only if OPEN/ACKNOWLEDGED)
        - ASSIGN_OPERATOR: Update VehicleState.assigned_operator
        - PULL_OVER_SIMULATED/REQUEST_REMOTE_ASSIST: Update vehicle state to UNDER_INTERVENTION
        - RESUME_SIMULATION: Update vehicle state back to ALERTING or NORMAL

        Args:
            action_type: Type of action
            vehicle_id: Vehicle identifier
            alert_id: Optional alert ID (for alert-specific actions)
            actor: Actor identifier
            payload: Additional action payload
            db: Database session

        Returns:
            Created OperatorAction object

        Raises:
            ValueError: If action is invalid (e.g., resolving non-existent alert)
        """
        # Validate alert exists if alert_id is provided
        alert = None
        if alert_id:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            if alert is None:
                raise ValueError(f"Alert {alert_id} not found")
            if alert.vehicle_id != vehicle_id:
                raise ValueError(f"Alert {alert_id} does not belong to vehicle {vehicle_id}")

        # Handle state transitions based on action type
        if action_type == ActionType.ACKNOWLEDGE_ALERT:
            if alert is None:
                raise ValueError("ACKNOWLEDGE_ALERT requires alert_id")
            if alert.status != AlertStatus.OPEN:
                raise ValueError(f"Cannot acknowledge alert in status {alert.status}")
            alert.status = AlertStatus.ACKNOWLEDGED
            logger.info(f"Acknowledged alert {alert_id} for vehicle {vehicle_id}")

        elif action_type == ActionType.RESOLVE_ALERT:
            if alert is None:
                raise ValueError("RESOLVE_ALERT requires alert_id")
            if alert.status not in [AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]:
                raise ValueError(f"Cannot resolve alert in status {alert.status}")
            alert.status = AlertStatus.RESOLVED
            logger.info(f"Resolved alert {alert_id} for vehicle {vehicle_id}")

        elif action_type == ActionType.ASSIGN_OPERATOR:
            # Get operator_id from payload
            operator_id = payload.get("operator_id", actor)
            vehicle_state = db.query(VehicleState).filter(
                VehicleState.vehicle_id == vehicle_id
            ).first()
            if vehicle_state is None:
                # Create vehicle state if it doesn't exist
                vehicle_state = VehicleState(vehicle_id=vehicle_id)
                db.add(vehicle_state)
            vehicle_state.assigned_operator = operator_id
            logger.info(f"Assigned operator {operator_id} to vehicle {vehicle_id}")

        # Create action record
        action = OperatorAction(
            vehicle_id=vehicle_id,
            alert_id=alert_id,
            action_type=action_type,
            actor=actor,
            payload=payload,
        )
        db.add(action)
        db.commit()
        db.refresh(action)

        # Update vehicle state after action
        VehicleStateService.update_state(vehicle_id, db)

        # Publish to Kafka
        # Note: We need scene_id and frame_index for OperatorActionEvent
        # For now, get from alert if available, otherwise use defaults
        scene_id = alert.scene_id if alert else ""
        frame_index = alert.frame_index if alert else 0

        action_event = OperatorActionEvent(
            action_id=action.id,
            event_time=action.created_at,
            processing_time=datetime.utcnow(),
            vehicle_id=vehicle_id,
            scene_id=scene_id,
            frame_index=frame_index,
        )
        self.kafka_producer.produce(action_event)

        logger.info(
            f"Created action {action.id} of type {action_type} for vehicle {vehicle_id}"
        )

        return action

