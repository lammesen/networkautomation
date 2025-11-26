"""Add topology links table for CDP/LLDP neighbor discovery.

Revision ID: 005_add_topology_links
Revises: 004_add_reachability
Create Date: 2025-01-01 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "005_add_topology_links"
down_revision = "004_add_reachability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "topology_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("local_device_id", sa.Integer(), nullable=False),
        sa.Column("local_interface", sa.String(100), nullable=False),
        sa.Column("remote_device_id", sa.Integer(), nullable=True),
        sa.Column("remote_hostname", sa.String(255), nullable=False),
        sa.Column("remote_interface", sa.String(100), nullable=False),
        sa.Column("remote_ip", sa.String(45), nullable=True),
        sa.Column("remote_platform", sa.String(100), nullable=True),
        sa.Column("protocol", sa.String(10), nullable=False),
        sa.Column("discovered_at", sa.DateTime(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["local_device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["remote_device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "customer_id",
            "local_device_id",
            "local_interface",
            "remote_device_id",
            "remote_interface",
            name="uix_topology_link",
        ),
    )
    op.create_index("ix_topology_links_local_device_id", "topology_links", ["local_device_id"])
    op.create_index("ix_topology_links_remote_device_id", "topology_links", ["remote_device_id"])
    op.create_index("ix_topology_links_customer_id", "topology_links", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_topology_links_customer_id", table_name="topology_links")
    op.drop_index("ix_topology_links_remote_device_id", table_name="topology_links")
    op.drop_index("ix_topology_links_local_device_id", table_name="topology_links")
    op.drop_table("topology_links")
