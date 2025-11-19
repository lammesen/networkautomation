from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "credentials",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False, unique=True),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("password", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("hostname", sa.String(length=128), nullable=False, unique=True),
        sa.Column("mgmt_ip", sa.String(length=64), nullable=False, unique=True),
        sa.Column("vendor", sa.String(length=64)),
        sa.Column("platform", sa.String(length=64)),
        sa.Column("role", sa.String(length=64)),
        sa.Column("site", sa.String(length=64)),
        sa.Column("tags", sa.String(length=256)),
        sa.Column("napalm_driver", sa.String(length=64)),
        sa.Column("netmiko_device_type", sa.String(length=64)),
        sa.Column("port", sa.Integer, server_default="22"),
        sa.Column("metadata_json", sa.Text()),
        sa.Column("credentials_id", sa.Integer, sa.ForeignKey("credentials.id")),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("target_summary_json", sa.Text()),
        sa.Column("result_summary_json", sa.Text()),
    )
    op.create_table(
        "job_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("jobs.id")),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("host", sa.String(length=128)),
        sa.Column("message", sa.Text()),
        sa.Column("extra_json", sa.Text()),
    )
    op.create_table(
        "config_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("device_id", sa.Integer, sa.ForeignKey("devices.id")),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("jobs.id")),
        sa.Column("source", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("config_text", sa.Text(), nullable=False),
        sa.Column("hash", sa.String(length=128), nullable=False),
    )
    op.create_table(
        "compliance_policies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("scope_json", sa.Text(), nullable=False),
        sa.Column("definition_yaml", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "compliance_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("policy_id", sa.Integer, sa.ForeignKey("compliance_policies.id")),
        sa.Column("device_id", sa.Integer, sa.ForeignKey("devices.id")),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("jobs.id")),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False),
    )


def downgrade():
    for table in [
        "compliance_results",
        "compliance_policies",
        "config_snapshots",
        "job_logs",
        "jobs",
        "devices",
        "users",
        "credentials",
    ]:
        op.drop_table(table)
