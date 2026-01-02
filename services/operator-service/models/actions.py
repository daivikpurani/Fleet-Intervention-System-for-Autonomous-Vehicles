"""Pydantic models for action API requests and responses."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ..db.models import ActionType


class CreateActionRequest(BaseModel):
    """Request model for creating an operator action."""

    action_type: ActionType = Field(..., description="Type of action")
    alert_id: Optional[UUID] = Field(None, description="Optional alert ID")
    actor: str = Field(..., description="Actor identifier")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Additional payload")


class ActionResponse(BaseModel):
    """Action response model."""

    id: UUID
    vehicle_id: str
    alert_id: Optional[UUID]
    action_type: ActionType
    actor: str
    payload: Dict[str, Any]
    created_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True
