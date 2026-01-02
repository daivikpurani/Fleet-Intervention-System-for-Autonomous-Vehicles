"""Vehicle state service for computing and updating vehicle states."""

import logging
from sqlalchemy.orm import Session

from ..db.models import Alert, AlertStatus, OperatorAction, ActionType, VehicleState, VehicleStateEnum

logger = logging.getLogger(__name__)


class VehicleStateService:
    """Service for managing vehicle state."""

    @staticmethod
    def compute_state(vehicle_id: str, db: Session) -> VehicleStateEnum:
        """Compute vehicle state based on alerts and actions.

        Rules:
        - ALERTING: Has OPEN alerts
        - UNDER_INTERVENTION: Has PULL_OVER_SIMULATED or REQUEST_REMOTE_ASSIST action
          AND has OPEN or ACKNOWLEDGED alerts
        - NORMAL: Default (no OPEN alerts)

        Args:
            vehicle_id: Vehicle identifier
            db: Database session

        Returns:
            Computed vehicle state
        """
        # Check for OPEN alerts
        open_alerts = db.query(Alert).filter(
            Alert.vehicle_id == vehicle_id,
            Alert.status == AlertStatus.OPEN
        ).count()

        if open_alerts > 0:
            # Check for intervention actions
            intervention_actions = db.query(OperatorAction).filter(
                OperatorAction.vehicle_id == vehicle_id,
                OperatorAction.action_type.in_([
                    ActionType.PULL_OVER_SIMULATED,
                    ActionType.REQUEST_REMOTE_ASSIST
                ])
            ).order_by(OperatorAction.created_at.desc()).first()

            if intervention_actions:
                # Check if there are OPEN or ACKNOWLEDGED alerts
                active_alerts = db.query(Alert).filter(
                    Alert.vehicle_id == vehicle_id,
                    Alert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED])
                ).count()

                if active_alerts > 0:
                    return VehicleStateEnum.UNDER_INTERVENTION

            return VehicleStateEnum.ALERTING

        return VehicleStateEnum.NORMAL

    @staticmethod
    def update_state(vehicle_id: str, db: Session) -> VehicleState:
        """Update vehicle state based on current alerts and actions.

        Args:
            vehicle_id: Vehicle identifier
            db: Database session

        Returns:
            Updated VehicleState record
        """
        new_state = VehicleStateService.compute_state(vehicle_id, db)

        # Get or create vehicle state
        vehicle_state = db.query(VehicleState).filter(
            VehicleState.vehicle_id == vehicle_id
        ).first()

        if vehicle_state is None:
            vehicle_state = VehicleState(
                vehicle_id=vehicle_id,
                state=new_state
            )
            db.add(vehicle_state)
        else:
            old_state = vehicle_state.state
            vehicle_state.state = new_state
            if old_state != new_state:
                logger.info(
                    f"Vehicle {vehicle_id} state changed: {old_state} -> {new_state}"
                )

        db.commit()
        db.refresh(vehicle_state)
        return vehicle_state

    @staticmethod
    def update_position(
        vehicle_id: str,
        position_x: float,
        position_y: float,
        db: Session,
    ) -> VehicleState:
        """Update vehicle position from telemetry.

        Args:
            vehicle_id: Vehicle identifier
            position_x: X position in meters
            position_y: Y position in meters
            db: Database session

        Returns:
            Updated VehicleState record
        """
        # Get or create vehicle state
        vehicle_state = db.query(VehicleState).filter(
            VehicleState.vehicle_id == vehicle_id
        ).first()

        if vehicle_state is None:
            # Compute state based on existing alerts and actions
            computed_state = VehicleStateService.compute_state(vehicle_id, db)
            vehicle_state = VehicleState(
                vehicle_id=vehicle_id,
                state=computed_state,
                last_position_x=position_x,
                last_position_y=position_y,
            )
            db.add(vehicle_state)
        else:
            vehicle_state.last_position_x = position_x
            vehicle_state.last_position_y = position_y
            # Also update state in case alerts changed
            vehicle_state.state = VehicleStateService.compute_state(vehicle_id, db)

        db.commit()
        db.refresh(vehicle_state)
        return vehicle_state

