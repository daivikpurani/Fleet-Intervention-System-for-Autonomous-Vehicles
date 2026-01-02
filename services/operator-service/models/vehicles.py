"""Pydantic models for vehicle API requests and responses."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ..db.models import VehicleStateEnum


class VehicleResponse(BaseModel):
    """Vehicle response model."""

    vehicle_id: str
    state: VehicleStateEnum
    assigned_operator: Optional[str]
    last_position_x: Optional[float] = Field(None, description="Last known X position in meters")
    last_position_y: Optional[float] = Field(None, description="Last known Y position in meters")
    updated_at: datetime
    open_alerts_count: int = Field(default=0, description="Number of OPEN alerts for this vehicle")

    class Config:
        """Pydantic config."""

        from_attributes = True


class AssignOperatorRequest(BaseModel):
    """Request model for assigning an operator to a vehicle."""

    operator_id: str = Field(..., description="Operator identifier")
    actor: str = Field(..., description="Actor identifier (who is making the assignment)")
