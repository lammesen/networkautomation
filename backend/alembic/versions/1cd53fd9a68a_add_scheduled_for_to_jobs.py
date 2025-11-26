"""add scheduled_for to jobs

Revision ID: 1cd53fd9a68a
Revises: 004_add_reachability
Create Date: 2025-11-23 01:09:58.513828

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1cd53fd9a68a'
down_revision: Union[str, None] = '004_add_reachability'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("scheduled_for", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "scheduled_for")
