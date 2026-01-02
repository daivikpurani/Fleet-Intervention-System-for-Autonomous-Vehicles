"""Initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vehicle_id', sa.Text(), nullable=False),
        sa.Column('scene_id', sa.Text(), nullable=False),
        sa.Column('frame_index', sa.Integer(), nullable=False),
        sa.Column('anomaly_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rule_name', sa.Text(), nullable=False),
        sa.Column('severity', sa.Enum('INFO', 'WARNING', 'CRITICAL', name='severity'), nullable=False),
        sa.Column('status', sa.Enum('OPEN', 'ACKNOWLEDGED', 'RESOLVED', name='alertstatus'), nullable=False),
        sa.Column('anomaly_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('first_seen_event_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_event_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_alerts_vehicle_id', 'alerts', ['vehicle_id'])
    op.create_index('ix_alerts_vehicle_id_status', 'alerts', ['vehicle_id', 'status'])
    op.create_unique_constraint('uq_alerts_anomaly_id', 'alerts', ['anomaly_id'])

    # Create operator_actions table
    op.create_table(
        'operator_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vehicle_id', sa.Text(), nullable=False),
        sa.Column('alert_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action_type', sa.Enum('ACKNOWLEDGE_ALERT', 'RESOLVE_ALERT', 'ASSIGN_OPERATOR', 'PULL_OVER_SIMULATED', 'REQUEST_REMOTE_ASSIST', 'RESUME_SIMULATION', name='actiontype'), nullable=False),
        sa.Column('actor', sa.Text(), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_operator_actions_vehicle_id', 'operator_actions', ['vehicle_id'])
    op.create_index('ix_operator_actions_vehicle_id_created_at', 'operator_actions', ['vehicle_id', 'created_at'])
    op.create_foreign_key('fk_operator_actions_alert_id', 'operator_actions', 'alerts', ['alert_id'], ['id'])

    # Create vehicle_state table
    op.create_table(
        'vehicle_state',
        sa.Column('vehicle_id', sa.Text(), primary_key=True),
        sa.Column('state', sa.Enum('NORMAL', 'ALERTING', 'UNDER_INTERVENTION', name='vehiclestateenum'), nullable=False),
        sa.Column('assigned_operator', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('vehicle_state')
    op.drop_table('operator_actions')
    op.drop_table('alerts')
    op.execute('DROP TYPE IF EXISTS vehiclestateenum')
    op.execute('DROP TYPE IF EXISTS actiontype')
    op.execute('DROP TYPE IF EXISTS alertstatus')
    op.execute('DROP TYPE IF EXISTS severity')

