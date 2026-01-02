"""REST endpoints for alerts."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db.models import Alert, AlertStatus, ActionType
from ..db.session import get_db
from ..models.alerts import AlertResponse, AcknowledgeAlertRequest, ResolveAlertRequest
from ..services.action_service import ActionService
from ..services.alert_service import AlertService
from ..kafka_producer import KafkaProducer
from ..config import OperatorConfig
from ..websocket.handler import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])

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


@router.get("", response_model=List[AlertResponse])
def get_alerts(
    status: Optional[AlertStatus] = Query(None, description="Filter by alert status"),
    vehicle_id: Optional[str] = Query(None, description="Filter by vehicle ID"),
    db: Session = Depends(get_db),
) -> List[AlertResponse]:
    """Get alerts with optional filters.

    Args:
        status: Optional status filter
        vehicle_id: Optional vehicle ID filter
        db: Database session

    Returns:
        List of alerts
    """
    query = db.query(Alert)

    if status:
        query = query.filter(Alert.status == status)
    if vehicle_id:
        query = query.filter(Alert.vehicle_id == vehicle_id)

    alerts = query.order_by(Alert.created_at.desc()).all()
    return [AlertResponse.model_validate(alert) for alert in alerts]


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
) -> AlertResponse:
    """Get a single alert by ID.

    Args:
        alert_id: Alert ID
        db: Database session

    Returns:
        Alert details

    Raises:
        HTTPException: If alert not found
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return AlertResponse.model_validate(alert)


@router.post("/{alert_id}/ack", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: UUID,
    request: AcknowledgeAlertRequest,
    db: Session = Depends(get_db),
) -> AlertResponse:
    """Acknowledge an alert.

    Creates an ACKNOWLEDGE_ALERT action and updates alert status to ACKNOWLEDGED.

    Args:
        alert_id: Alert ID
        request: Acknowledge request
        db: Database session

    Returns:
        Updated alert

    Raises:
        HTTPException: If alert not found or invalid state
    """
    if _action_service is None:
        raise HTTPException(status_code=500, detail="Action service not initialized")

    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert is None:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        action =         _action_service.create_action(
            action_type=ActionType.ACKNOWLEDGE_ALERT,
            vehicle_id=alert.vehicle_id,
            alert_id=alert_id,
            actor=request.actor,
            payload={},
            db=db,
        )

        db.refresh(alert)
        alert_response = AlertResponse.model_validate(alert)

        # Broadcast events
        await websocket_manager.broadcast("alert_updated", alert_response.model_dump())
        from ..models.actions import ActionResponse
        await websocket_manager.broadcast("operator_action_created", ActionResponse.model_validate(action).model_dump())

        return alert_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: UUID,
    request: ResolveAlertRequest,
    db: Session = Depends(get_db),
) -> AlertResponse:
    """Resolve an alert.

    Creates a RESOLVE_ALERT action and updates alert status to RESOLVED.

    Args:
        alert_id: Alert ID
        request: Resolve request (must include action_type)
        db: Database session

    Returns:
        Updated alert

    Raises:
        HTTPException: If alert not found or invalid state
    """
    if _action_service is None:
        raise HTTPException(status_code=500, detail="Action service not initialized")

    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert is None:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        if request.action_type != "RESOLVE_ALERT":
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action_type: {request.action_type}. Must be RESOLVE_ALERT",
            )

        action = _action_service.create_action(
            action_type=ActionType.RESOLVE_ALERT,
            vehicle_id=alert.vehicle_id,
            alert_id=alert_id,
            actor=request.actor,
            payload={},
            db=db,
        )

        db.refresh(alert)
        alert_response = AlertResponse.model_validate(alert)

        # Broadcast events
        await websocket_manager.broadcast("alert_updated", alert_response.model_dump())
        from ..models.actions import ActionResponse
        await websocket_manager.broadcast("operator_action_created", ActionResponse.model_validate(action).model_dump())

        return alert_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
