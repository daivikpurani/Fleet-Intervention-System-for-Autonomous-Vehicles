"""Add display ID fields for human-readable identifiers.

Revision ID: 003_add_display_ids
Revises: 002_add_vehicle_position
Create Date: 2026-01-04
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_display_ids'
down_revision = '002_add_vehicle_position'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add display ID columns to alerts and vehicle_state tables."""
    
    # Add columns to alerts table
    op.add_column('alerts', sa.Column('vehicle_display_id', sa.Text(), nullable=True,
                                       comment='Human-readable vehicle ID (e.g., AV-SF01)'))
    op.add_column('alerts', sa.Column('scene_display_id', sa.Text(), nullable=True,
                                       comment='Human-readable scene ID (e.g., RUN-0104-A)'))
    op.add_column('alerts', sa.Column('incident_id', sa.Text(), nullable=True,
                                       comment='Human-readable incident ID (e.g., INC-7K3P2)'))
    op.add_column('alerts', sa.Column('rule_display_name', sa.Text(), nullable=True,
                                       comment='Human-readable rule name'))
    
    # Create index on incident_id for quick lookups
    op.create_index('ix_alerts_incident_id', 'alerts', ['incident_id'])
    
    # Add columns to vehicle_state table
    op.add_column('vehicle_state', sa.Column('vehicle_display_id', sa.Text(), nullable=True,
                                              comment='Human-readable vehicle ID (e.g., AV-SF01)'))
    op.add_column('vehicle_state', sa.Column('vehicle_type', sa.Text(), nullable=True,
                                              comment='Vehicle type label'))
    op.add_column('vehicle_state', sa.Column('last_yaw', sa.Float(), nullable=True,
                                              comment='Last known heading in radians'))
    op.add_column('vehicle_state', sa.Column('last_speed', sa.Float(), nullable=True,
                                              comment='Last known speed in m/s'))


def downgrade() -> None:
    """Remove display ID columns."""
    
    # Remove from alerts table
    op.drop_index('ix_alerts_incident_id', 'alerts')
    op.drop_column('alerts', 'rule_display_name')
    op.drop_column('alerts', 'incident_id')
    op.drop_column('alerts', 'scene_display_id')
    op.drop_column('alerts', 'vehicle_display_id')
    
    # Remove from vehicle_state table
    op.drop_column('vehicle_state', 'last_speed')
    op.drop_column('vehicle_state', 'last_yaw')
    op.drop_column('vehicle_state', 'vehicle_type')
    op.drop_column('vehicle_state', 'vehicle_display_id')

