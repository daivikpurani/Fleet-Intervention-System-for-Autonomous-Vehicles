"""REST endpoints for actions."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db.models import OperatorAction
from ..db.session import get_db
from ..models.actions import ActionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("", response_model=List[ActionResponse])
def get_actions(
    vehicle_id: Optional[str] = Query(None, description="Filter by vehicle ID"),
    db: Session = Depends(get_db),
) -> List[ActionResponse]:
    """Get operator actions with optional filters.

    Args:
        vehicle_id: Optional vehicle ID filter
        db: Database session

    Returns:
        List of actions
    """
    query = db.query(OperatorAction)

    if vehicle_id:
        query = query.filter(OperatorAction.vehicle_id == vehicle_id)

    actions = query.order_by(OperatorAction.created_at.desc()).all()
    return [ActionResponse.model_validate(action) for action in actions]
