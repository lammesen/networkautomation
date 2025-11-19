"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=100), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create credentials table
    op.create_table('credentials',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('username', sa.String(length=100), nullable=False),
    sa.Column('password', sa.String(length=255), nullable=False),
    sa.Column('enable_password', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_credentials_id'), 'credentials', ['id'], unique=False)

    # Create devices table
    op.create_table('devices',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('hostname', sa.String(length=255), nullable=False),
    sa.Column('mgmt_ip', sa.String(length=45), nullable=False),
    sa.Column('vendor', sa.String(length=50), nullable=False),
    sa.Column('platform', sa.String(length=50), nullable=False),
    sa.Column('role', sa.String(length=50), nullable=True),
    sa.Column('site', sa.String(length=100), nullable=True),
    sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('credentials_ref', sa.Integer(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['credentials_ref'], ['credentials.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('hostname')
    )
    op.create_index(op.f('ix_devices_hostname'), 'devices', ['hostname'], unique=True)
    op.create_index(op.f('ix_devices_id'), 'devices', ['id'], unique=False)
    op.create_index('ix_devices_role', 'devices', ['role'], unique=False)
    op.create_index('ix_devices_site', 'devices', ['site'], unique=False)
    op.create_index('ix_devices_vendor', 'devices', ['vendor'], unique=False)

    # Create jobs table
    op.create_table('jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('requested_at', sa.DateTime(), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.Column('target_summary_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('result_summary_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('payload_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_jobs_id'), 'jobs', ['id'], unique=False)
    op.create_index('ix_jobs_status', 'jobs', ['status'], unique=False)
    op.create_index('ix_jobs_type', 'jobs', ['type'], unique=False)
    op.create_index('ix_jobs_user_id', 'jobs', ['user_id'], unique=False)

    # Create job_logs table
    op.create_table('job_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('ts', sa.DateTime(), nullable=False),
    sa.Column('level', sa.String(length=10), nullable=False),
    sa.Column('host', sa.String(length=255), nullable=True),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('extra_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_logs_id'), 'job_logs', ['id'], unique=False)
    op.create_index('ix_job_logs_job_id', 'job_logs', ['job_id'], unique=False)

    # Create config_snapshots table
    op.create_table('config_snapshots',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=True),
    sa.Column('source', sa.String(length=50), nullable=False),
    sa.Column('config_text', sa.Text(), nullable=False),
    sa.Column('hash', sa.String(length=64), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_config_snapshots_id'), 'config_snapshots', ['id'], unique=False)
    op.create_index('ix_config_snapshots_created_at', 'config_snapshots', ['created_at'], unique=False)
    op.create_index('ix_config_snapshots_device_id', 'config_snapshots', ['device_id'], unique=False)

    # Create compliance_policies table
    op.create_table('compliance_policies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('scope_json', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('definition_yaml', sa.Text(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_compliance_policies_id'), 'compliance_policies', ['id'], unique=False)

    # Create compliance_results table
    op.create_table('compliance_results',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('policy_id', sa.Integer(), nullable=False),
    sa.Column('device_id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('ts', sa.DateTime(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('details_json', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
    sa.ForeignKeyConstraint(['policy_id'], ['compliance_policies.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_compliance_results_id'), 'compliance_results', ['id'], unique=False)
    op.create_index('ix_compliance_results_device_id', 'compliance_results', ['device_id'], unique=False)
    op.create_index('ix_compliance_results_policy_id', 'compliance_results', ['policy_id'], unique=False)
    op.create_index('ix_compliance_results_ts', 'compliance_results', ['ts'], unique=False)


def downgrade() -> None:
    op.drop_table('compliance_results')
    op.drop_table('compliance_policies')
    op.drop_table('config_snapshots')
    op.drop_table('job_logs')
    op.drop_table('jobs')
    op.drop_table('devices')
    op.drop_table('credentials')
    op.drop_table('users')
