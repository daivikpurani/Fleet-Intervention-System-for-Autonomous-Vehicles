"""SQLAlchemy models for alerts, operator actions, and vehicle state."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class AlertStatus(str, Enum):
    """Alert status enumeration."""

    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class Severity(str, Enum):
    """Severity level enumeration."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class ActionType(str, Enum):
    """Operator action type enumeration."""

    ACKNOWLEDGE_ALERT = "ACKNOWLEDGE_ALERT"
    RESOLVE_ALERT = "RESOLVE_ALERT"
    ASSIGN_OPERATOR = "ASSIGN_OPERATOR"
    PULL_OVER_SIMULATED = "PULL_OVER_SIMULATED"
    REQUEST_REMOTE_ASSIST = "REQUEST_REMOTE_ASSIST"
    RESUME_SIMULATION = "RESUME_SIMULATION"


class VehicleStateEnum(str, Enum):
    """Vehicle state enumeration."""

    NORMAL = "NORMAL"
    ALERTING = "ALERTING"
    UNDER_INTERVENTION = "UNDER_INTERVENTION"


class Alert(Base):
    """Alert model for storing anomaly events."""

    __tablename__ = "alerts"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    vehicle_id = Column(Text, nullable=False, index=True)
    scene_id = Column(Text, nullable=False)
    frame_index = Column(String, nullable=False)
    anomaly_id = Column(PostgresUUID(as_uuid=True), nullable=False, unique=True)
    rule_name = Column(Text, nullable=False)
    severity = Column(SQLEnum(Severity), nullable=False)
    status = Column(SQLEnum(AlertStatus), nullable=False, default=AlertStatus.OPEN)
    anomaly_payload = Column(JSONB, nullable=False)
    first_seen_event_time = Column(DateTime(timezone=True), nullable=False)
    last_seen_event_time = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    actions = relationship("OperatorAction", back_populates="alert", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("ix_alerts_vehicle_id_status", "vehicle_id", "status"),
        UniqueConstraint("anomaly_id", name="uq_alerts_anomaly_id"),
    )

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, vehicle_id={self.vehicle_id}, status={self.status})>"


class OperatorAction(Base):
    """Operator action model for storing operator actions."""

    __tablename__ = "operator_actions"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    vehicle_id = Column(Text, nullable=False, index=True)
    alert_id = Column(PostgresUUID(as_uuid=True), ForeignKey("alerts.id"), nullable=True)
    action_type = Column(SQLEnum(ActionType), nullable=False)
    actor = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    alert = relationship("Alert", back_populates="actions")

    # Indexes
    __table_args__ = (Index("ix_operator_actions_vehicle_id_created_at", "vehicle_id", "created_at"),)

    def __repr__(self) -> str:
        return f"<OperatorAction(id={self.id}, vehicle_id={self.vehicle_id}, action_type={self.action_type})>"


class VehicleState(Base):
    """Vehicle state model for tracking vehicle state."""

    __tablename__ = "vehicle_state"

    vehicle_id = Column(Text, primary_key=True)
    state = Column(SQLEnum(VehicleStateEnum), nullable=False, default=VehicleStateEnum.NORMAL)
    assigned_operator = Column(Text, nullable=True)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<VehicleState(vehicle_id={self.vehicle_id}, state={self.state})>"
