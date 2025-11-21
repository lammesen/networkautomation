"""Add multi-tenancy

Revision ID: 002_add_tenancy
Revises: 001_initial
Create Date: 2025-11-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = '002_add_tenancy'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create customers table
    op.create_table('customers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_customers_id'), 'customers', ['id'], unique=False)

    # 2. Create user_customers table
    op.create_table('user_customers',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'customer_id')
    )

    # 3. Data Migration: Create default customer
    customers_table = table('customers',
        column('id', sa.Integer),
        column('name', sa.String),
        column('created_at', sa.DateTime)
    )
    
    # Insert default customer
    op.bulk_insert(customers_table,
        [
            {'name': 'Default Organization', 'created_at': datetime.utcnow()}
        ]
    )
    
    connection = op.get_bind()
    # Use text() for raw SQL
    default_customer_id = connection.execute(
        sa.text("SELECT id FROM customers WHERE name = 'Default Organization'")
    ).scalar()

    # 4. Add customer_id columns (nullable=True first)
    op.add_column('credentials', sa.Column('customer_id', sa.Integer(), nullable=True))
    op.add_column('devices', sa.Column('customer_id', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('customer_id', sa.Integer(), nullable=True))
    op.add_column('compliance_policies', sa.Column('customer_id', sa.Integer(), nullable=True))

    # 5. Populate customer_id
    op.execute(sa.text(f"UPDATE credentials SET customer_id = {default_customer_id}"))
    op.execute(sa.text(f"UPDATE devices SET customer_id = {default_customer_id}"))
    op.execute(sa.text(f"UPDATE jobs SET customer_id = {default_customer_id}"))
    op.execute(sa.text(f"UPDATE compliance_policies SET customer_id = {default_customer_id}"))
    
    # Assign all existing users to the default customer
    users_result = connection.execute(sa.text("SELECT id FROM users"))
    user_customers_data = [
        {'user_id': row[0], 'customer_id': default_customer_id}
        for row in users_result
    ]
    if user_customers_data:
        user_customers_table = table('user_customers',
            column('user_id', sa.Integer),
            column('customer_id', sa.Integer)
        )
        op.bulk_insert(user_customers_table, user_customers_data)

    # 6. Alter columns to nullable=False
    op.alter_column('credentials', 'customer_id', nullable=False)
    op.alter_column('devices', 'customer_id', nullable=False)
    op.alter_column('jobs', 'customer_id', nullable=False)
    op.alter_column('compliance_policies', 'customer_id', nullable=False)

    # 7. Create foreign keys
    op.create_foreign_key(None, 'credentials', 'customers', ['customer_id'], ['id'])
    op.create_foreign_key(None, 'devices', 'customers', ['customer_id'], ['id'])
    op.create_foreign_key(None, 'jobs', 'customers', ['customer_id'], ['id'])
    op.create_foreign_key(None, 'compliance_policies', 'customers', ['customer_id'], ['id'])
    
    # 8. Update unique constraints
    # Note: We rely on naming conventions. If constraints have different names, this might fail.
    # Since we are using Postgres, we can try to drop constraint by name if we know it, 
    # or drop index if the constraint is implemented via index.
    
    # Credential
    op.drop_constraint('credentials_name_key', 'credentials', type_='unique')
    op.create_unique_constraint('uix_credential_customer_name', 'credentials', ['customer_id', 'name'])

    # Device
    # 'ix_devices_hostname' is a unique index. We need to drop it and recreate it as non-unique (for quick search) 
    # or just drop it and rely on the new composite constraint.
    op.drop_index('ix_devices_hostname', table_name='devices')
    op.drop_constraint('devices_hostname_key', 'devices', type_='unique')
    op.create_index(op.f('ix_devices_hostname'), 'devices', ['hostname'], unique=False)
    op.create_unique_constraint('uix_device_customer_hostname', 'devices', ['customer_id', 'hostname'])

    # CompliancePolicy
    op.drop_constraint('compliance_policies_name_key', 'compliance_policies', type_='unique')
    op.create_unique_constraint('uix_policy_customer_name', 'compliance_policies', ['customer_id', 'name'])
    
    # Jobs index
    op.create_index('ix_jobs_customer_id', 'jobs', ['customer_id'], unique=False)


def downgrade() -> None:
    op.drop_constraint('uix_policy_customer_name', 'compliance_policies', type_='unique')
    op.create_unique_constraint('compliance_policies_name_key', 'compliance_policies', ['name'])
    op.drop_constraint(None, 'compliance_policies', type_='foreignkey')
    op.drop_column('compliance_policies', 'customer_id')

    op.drop_constraint('uix_device_customer_hostname', 'devices', type_='unique')
    op.drop_index(op.f('ix_devices_hostname'), table_name='devices')
    op.create_index('ix_devices_hostname', 'devices', ['hostname'], unique=True)
    op.create_unique_constraint('devices_hostname_key', 'devices', ['hostname'])
    op.drop_constraint(None, 'devices', type_='foreignkey')
    op.drop_column('devices', 'customer_id')

    op.drop_constraint('uix_credential_customer_name', 'credentials', type_='unique')
    op.create_unique_constraint('credentials_name_key', 'credentials', ['name'])
    op.drop_constraint(None, 'credentials', type_='foreignkey')
    op.drop_column('credentials', 'customer_id')
    
    op.drop_index('ix_jobs_customer_id', 'jobs')
    op.drop_constraint(None, 'jobs', type_='foreignkey')
    op.drop_column('jobs', 'customer_id')

    op.drop_table('user_customers')
    op.drop_table('customers')
