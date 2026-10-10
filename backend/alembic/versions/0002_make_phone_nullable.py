"""make phone nullable

Revision ID: 0002_make_phone_nullable
Revises: 0001_initial_schema
Create Date: 2026-10-11 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002_make_phone_nullable'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('pickup_requests', 'phone',
               existing_type=sa.String(length=20),
               nullable=True)


def downgrade() -> None:
    op.alter_column('pickup_requests', 'phone',
               existing_type=sa.String(length=20),
               nullable=False)
