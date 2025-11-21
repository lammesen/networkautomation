"""Add customer IP ranges

Revision ID: 003_add_ip_ranges
Revises: 002_add_tenancy
Create Date: 2025-11-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_ip_ranges'
down_revision: Union[str, None] = '002_add_tenancy'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('customer_ip_ranges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('cidr', sa.String(length=45), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customer_ip_ranges_customer_id'), 'customer_ip_ranges', ['customer_id'], unique=False)
    op.create_index(op.f('ix_customer_ip_ranges_id'), 'customer_ip_ranges', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_customer_ip_ranges_id'), table_name='customer_ip_ranges')
    op.drop_index(op.f('ix_customer_ip_ranges_customer_id'), table_name='customer_ip_ranges')
    op.drop_table('customer_ip_ranges')
