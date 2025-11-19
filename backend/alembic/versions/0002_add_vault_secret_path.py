"""add vault secret path to credentials

Revision ID: 0002_add_vault_secret_path
Revises: 0001_initial
Create Date: 2024-06-07
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_vault_secret_path"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("credentials", sa.Column("secret_path", sa.String(length=256), nullable=True))


def downgrade() -> None:
    op.drop_column("credentials", "secret_path")
