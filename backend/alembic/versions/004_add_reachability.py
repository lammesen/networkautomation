"""Add reachability fields

Revision ID: 004_add_reachability
Revises: 003_add_ip_ranges
Create Date: 2025-11-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_add_reachability'
down_revision: Union[str, None] = '003_add_ip_ranges'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('devices', sa.Column('reachability_status', sa.String(length=20), nullable=True))
    op.add_column('devices', sa.Column('last_reachability_check', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('devices', 'last_reachability_check')
    op.drop_column('devices', 'reachability_status')
