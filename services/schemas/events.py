"""Pydantic models for Kafka message events.

These models define the schema for all messages published to and consumed from Kafka topics.
All models include event_time, processing_time, and appropriate identifiers.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RawTelemetryEvent(BaseModel):
    """Raw telemetry event from replay service.

    Published to: raw_telemetry topic
    Partition key: vehicle_id
    """

    event_id: UUID = Field(..., description="Unique identifier for this event")
    event_time: datetime = Field(..., description="Timestamp when the event occurred")
    processing_time: datetime = Field(
        ..., description="Timestamp when the event was processed/published"
    )
    vehicle_id: str = Field(..., description="Identifier for the vehicle")
    scene_id: str = Field(..., description="Identifier for the scene")
    frame_index: int = Field(..., description="Frame index within the scene")


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

