"""Add vehicle position tracking

Revision ID: 002_add_vehicle_position
Revises: 001_initial_schema
Create Date: 2024-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_vehicle_position'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add position columns to vehicle_state table
    op.add_column('vehicle_state', sa.Column('last_position_x', sa.Float(), nullable=True))
    op.add_column('vehicle_state', sa.Column('last_position_y', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('vehicle_state', 'last_position_y')
    op.drop_column('vehicle_state', 'last_position_x')

