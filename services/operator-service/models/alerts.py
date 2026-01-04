"""Pydantic models for alert API requests and responses."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ..db.models import AlertStatus, Severity


class AlertResponse(BaseModel):
    """Alert response model."""

    id: UUID
    incident_id: Optional[str] = Field(None, description="Human-readable incident ID (e.g., INC-7K3P2)")
    vehicle_id: str
    vehicle_display_id: Optional[str] = Field(None, description="Human-readable vehicle ID (e.g., AV-SF01)")
    scene_id: str
    scene_display_id: Optional[str] = Field(None, description="Human-readable scene ID (e.g., RUN-0104-A)")
    frame_index: int
    anomaly_id: UUID
    rule_name: str
    rule_display_name: Optional[str] = Field(None, description="Human-readable rule name")
    severity: Severity
    status: AlertStatus
    anomaly_payload: Dict[str, Any]
    first_seen_event_time: datetime
    last_seen_event_time: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class AcknowledgeAlertRequest(BaseModel):
    """Request model for acknowledging an alert."""

    actor: str = Field(..., description="Actor identifier")


class ResolveAlertRequest(BaseModel):
    """Request model for resolving an alert."""

    actor: str = Field(..., description="Actor identifier")
    action_type: str = Field(
        default="RESOLVE_ALERT",
        description="Action type (must be RESOLVE_ALERT)",
    )
