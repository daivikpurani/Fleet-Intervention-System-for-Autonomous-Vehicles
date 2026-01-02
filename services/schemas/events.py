"""Pydantic models for Kafka message events.

These models define the schema for all messages published to and consumed from Kafka topics.
All models include event_time, processing_time, and appropriate identifiers.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RawTelemetryEvent(BaseModel):
    """Raw telemetry event from replay service.

    Published to: raw_telemetry topic
    Partition key: vehicle_id
    """

    # Envelope fields
    event_id: UUID = Field(..., description="Unique identifier for this event")
    event_time: datetime = Field(..., description="Timestamp when the event occurred")
    processing_time: datetime = Field(
        ..., description="Timestamp when the event was processed/published"
    )
    vehicle_id: str = Field(..., description="Identifier for the vehicle")
    scene_id: str = Field(..., description="Identifier for the scene")
    frame_index: int = Field(..., description="Frame index within the scene")
    
    # Vehicle identity fields
    is_ego: bool = Field(..., description="Whether this is the ego vehicle")
    track_id: Optional[int] = Field(None, description="Track ID for the vehicle (None for ego)")
    
    # Telemetry fields (dataset-grounded, keep naming)
    centroid: dict = Field(..., description="Vehicle position (centroid) with keys {x, y, z}")
    velocity: dict = Field(..., description="Vehicle velocity with keys {vx, vy}")
    speed: float = Field(..., description="Vehicle speed in m/s")
    yaw: Optional[float] = Field(None, description="Vehicle orientation in radians")
    label_probabilities: Optional[List[float]] = Field(None, description="Classification probabilities")


class AnomalyEvent(BaseModel):
    """Anomaly detection event from anomaly service.

    Published to: anomalies topic
    Partition key: vehicle_id
    """

    anomaly_id: UUID = Field(..., description="Unique identifier for this anomaly")
    event_time: datetime = Field(..., description="Timestamp when the anomaly was detected")
    processing_time: datetime = Field(
        ..., description="Timestamp when the event was processed/published"
    )
    vehicle_id: str = Field(..., description="Identifier for the vehicle")
    scene_id: str = Field(..., description="Identifier for the scene")
    frame_index: int = Field(..., description="Frame index within the scene")
    rule_name: str = Field(..., description="Name of the rule that triggered this anomaly")
    features: Dict[str, Any] = Field(..., description="Feature values used in detection")
    thresholds: Dict[str, Any] = Field(..., description="Threshold values used in detection")
    severity: Literal["INFO", "WARNING", "CRITICAL"] = Field(
        ..., description="Severity level: INFO, WARNING, or CRITICAL"
    )


class OperatorActionEvent(BaseModel):
    """Operator action event from operator service.

    Published to: operator_actions topic
    Partition key: vehicle_id
    """

    action_id: UUID = Field(..., description="Unique identifier for this action")
    event_time: datetime = Field(..., description="Timestamp when the action occurred")
    processing_time: datetime = Field(
        ..., description="Timestamp when the event was processed/published"
    )
    vehicle_id: str = Field(..., description="Identifier for the vehicle")
    scene_id: str = Field(..., description="Identifier for the scene")
    frame_index: int = Field(..., description="Frame index within the scene")

