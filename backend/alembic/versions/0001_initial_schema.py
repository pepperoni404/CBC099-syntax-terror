"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-10 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable PostGIS extension if PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('CREATE EXTENSION IF NOT EXISTS postgis;')

    # 1. agents table
    op.create_table(
        'agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('shift_start', sa.Time(), nullable=False),
        sa.Column('shift_end', sa.Time(), nullable=False),
        sa.Column('current_location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='idle', nullable=False),
        sa.CheckConstraint("status IN ('idle', 'en route', 'busy')", name='agents_status_check'),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. pickup_requests table
    op.create_table(
        'pickup_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('customer_name', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('address', sa.String(length=255), nullable=False),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=False),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('priority', sa.String(length=10), server_default='normal', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='Pending', nullable=False),
        sa.Column('assigned_agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('scheduled_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('unassigned_reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint('window_end > window_start', name='pickup_requests_window_check'),
        sa.CheckConstraint("priority IN ('urgent', 'normal', 'low')", name='pickup_requests_priority_check'),
        sa.CheckConstraint("status IN ('Pending', 'Scheduled', 'En route', 'Picked up', 'Delivered to hub', 'Unassigned', 'Cancelled')", name='pickup_requests_status_check'),
        sa.ForeignKeyConstraint(['assigned_agent_id'], ['agents.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_pickup_requests_status', 'pickup_requests', ['status'])
    op.create_index('idx_pickup_requests_agent', 'pickup_requests', ['assigned_agent_id'])
    op.create_index('idx_pickup_requests_window', 'pickup_requests', ['window_start', 'window_end'])

    # 3. status_history table
    op.create_table(
        'status_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint("status IN ('Pending', 'Scheduled', 'En route', 'Picked up', 'Delivered to hub', 'Unassigned', 'Cancelled')", name='status_history_status_check'),
        sa.ForeignKeyConstraint(['request_id'], ['pickup_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_status_history_request_id', 'status_history', ['request_id'])
    op.create_index('idx_status_history_request_timestamp', 'status_history', ['request_id', 'timestamp'])


def downgrade() -> None:
    op.drop_index('idx_status_history_request_timestamp', table_name='status_history')
    op.drop_index('idx_status_history_request_id', table_name='status_history')
    op.drop_table('status_history')

    op.drop_index('idx_pickup_requests_window', table_name='pickup_requests')
    op.drop_index('idx_pickup_requests_agent', table_name='pickup_requests')
    op.drop_index('idx_pickup_requests_status', table_name='pickup_requests')
    op.drop_table('pickup_requests')

    op.drop_table('agents')
