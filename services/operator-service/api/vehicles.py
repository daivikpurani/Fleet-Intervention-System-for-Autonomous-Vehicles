"""REST endpoints for vehicles."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.models import Alert, AlertStatus, VehicleState, ActionType
from ..db.session import get_db
from ..models.vehicles import VehicleResponse, AssignOperatorRequest
from ..models.actions import CreateActionRequest, ActionResponse
from ..services.action_service import ActionService
from ..kafka_producer import KafkaProducer
from ..config import OperatorConfig
from ..websocket.handler import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

# Global config (will be set in main.py)
_config: Optional[OperatorConfig] = None
_action_service: Optional[ActionService] = None


def set_config(config: OperatorConfig) -> None:
    """Set global configuration.

    Args:
        config: Operator service configuration
    """
    global _config, _action_service
    _config = config
    kafka_producer = KafkaProducer(config)
    _action_service = ActionService(kafka_producer)


@router.get("", response_model=List[VehicleResponse])
def get_vehicles(
    db: Session = Depends(get_db),
) -> List[VehicleResponse]:
    """Get all vehicles with their states.

    Args:
        db: Database session

    Returns:
        List of vehicles with states
    """
    vehicle_states = db.query(VehicleState).all()

    # Get open alerts count for each vehicle
    result = []
    for vehicle_state in vehicle_states:
        open_alerts_count = db.query(Alert).filter(
            Alert.vehicle_id == vehicle_state.vehicle_id,
            Alert.status == AlertStatus.OPEN
        ).count()

        result.append(
            VehicleResponse(
                vehicle_id=vehicle_state.vehicle_id,
                state=vehicle_state.state,
                assigned_operator=vehicle_state.assigned_operator,
                last_position_x=vehicle_state.last_position_x,
                last_position_y=vehicle_state.last_position_y,
                updated_at=vehicle_state.updated_at,
                open_alerts_count=open_alerts_count,
            )
        )

    return result


@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(
    vehicle_id: str,
    db: Session = Depends(get_db),
) -> VehicleResponse:
    """Get a single vehicle by ID.

    Args:
        vehicle_id: Vehicle ID
        db: Database session

    Returns:
        Vehicle details

    Raises:
        HTTPException: If vehicle not found
    """
    vehicle_state = db.query(VehicleState).filter(
        VehicleState.vehicle_id == vehicle_id
    ).first()

    if vehicle_state is None:
        raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found")

    open_alerts_count = db.query(Alert).filter(
        Alert.vehicle_id == vehicle_id,
        Alert.status == AlertStatus.OPEN
    ).count()

    return VehicleResponse(
        vehicle_id=vehicle_state.vehicle_id,
        state=vehicle_state.state,
        assigned_operator=vehicle_state.assigned_operator,
        last_position_x=vehicle_state.last_position_x,
        last_position_y=vehicle_state.last_position_y,
        updated_at=vehicle_state.updated_at,
        open_alerts_count=open_alerts_count,
    )


@router.post("/{vehicle_id}/assign", response_model=VehicleResponse)
async def assign_operator(
    vehicle_id: str,
    request: AssignOperatorRequest,
    db: Session = Depends(get_db),
) -> VehicleResponse:
    """Assign an operator to a vehicle.

    Creates an ASSIGN_OPERATOR action and updates VehicleState.assigned_operator.

    Args:
        vehicle_id: Vehicle ID
        request: Assign operator request
        db: Database session

    Returns:
        Updated vehicle state

    Raises:
        HTTPException: If vehicle not found
    """
    if _action_service is None:
        raise HTTPException(status_code=500, detail="Action service not initialized")

    try:
        action = _action_service.create_action(
            action_type=ActionType.ASSIGN_OPERATOR,
            vehicle_id=vehicle_id,
            alert_id=None,
            actor=request.actor,
            payload={"operator_id": request.operator_id},
            db=db,
        )

        vehicle_state = db.query(VehicleState).filter(
            VehicleState.vehicle_id == vehicle_id
        ).first()

        if vehicle_state is None:
            raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found")

        open_alerts_count = db.query(Alert).filter(
            Alert.vehicle_id == vehicle_id,
            Alert.status == AlertStatus.OPEN
        ).count()

        vehicle_response = VehicleResponse(
            vehicle_id=vehicle_state.vehicle_id,
            state=vehicle_state.state,
            assigned_operator=vehicle_state.assigned_operator,
            last_position_x=vehicle_state.last_position_x,
            last_position_y=vehicle_state.last_position_y,
            updated_at=vehicle_state.updated_at,
            open_alerts_count=open_alerts_count,
        )

        # Broadcast events
        await websocket_manager.broadcast("vehicle_updated", vehicle_response.model_dump())
        await websocket_manager.broadcast("operator_action_created", ActionResponse.model_validate(action).model_dump())

        return vehicle_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{vehicle_id}/action", response_model=ActionResponse)
async def create_vehicle_action(
    vehicle_id: str,
    request: CreateActionRequest,
    db: Session = Depends(get_db),
) -> ActionResponse:
    """Create an operator action for a vehicle.

    Supported actions: PULL_OVER_SIMULATED, REQUEST_REMOTE_ASSIST, RESUME_SIMULATION

    Args:
        vehicle_id: Vehicle ID
        request: Create action request
        db: Database session

    Returns:
        Created action

    Raises:
        HTTPException: If action is invalid
    """
    if _action_service is None:
        raise HTTPException(status_code=500, detail="Action service not initialized")

    # Validate action type
    valid_vehicle_actions = [
        ActionType.PULL_OVER_SIMULATED,
        ActionType.REQUEST_REMOTE_ASSIST,
        ActionType.RESUME_SIMULATION,
    ]
    if request.action_type not in valid_vehicle_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action_type for vehicle endpoint: {request.action_type}. "
            f"Must be one of: {[a.value for a in valid_vehicle_actions]}",
        )

    try:
        action = _action_service.create_action(
            action_type=request.action_type,
            vehicle_id=vehicle_id,
            alert_id=request.alert_id,
            actor=request.actor,
            payload=request.payload,
            db=db,
        )

        action_response = ActionResponse.model_validate(action)

        # Broadcast events
        await websocket_manager.broadcast("operator_action_created", action_response.model_dump())
        # Also broadcast vehicle update if state changed
        vehicle_state = db.query(VehicleState).filter(
            VehicleState.vehicle_id == vehicle_id
        ).first()
        if vehicle_state:
            open_alerts_count = db.query(Alert).filter(
                Alert.vehicle_id == vehicle_id,
                Alert.status == AlertStatus.OPEN
            ).count()
            vehicle_response = VehicleResponse(
                vehicle_id=vehicle_state.vehicle_id,
                state=vehicle_state.state,
                assigned_operator=vehicle_state.assigned_operator,
                updated_at=vehicle_state.updated_at,
                open_alerts_count=open_alerts_count,
            )
            await websocket_manager.broadcast("vehicle_updated", vehicle_response.model_dump())

        return action_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
