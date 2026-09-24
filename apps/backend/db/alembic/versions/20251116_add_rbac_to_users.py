"""add rbac to users

Revision ID: 3b4c5d6e7f8g
Revises: 2a3b4c5d6e7f
Create Date: 2025-11-16 20:30:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "3b4c5d6e7f8g"
down_revision = "2a3b4c5d6e7f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add RBAC fields to users table.

    - Adds role column with default 'user'
    - Adds permissions array column
    - Creates index on role column
    """
    # Add role column
    op.add_column(
        "users", sa.Column("role", sa.String(50), nullable=False, server_default="user")
    )

    # Add permissions column
    op.add_column(
        "users", sa.Column("permissions", postgresql.ARRAY(sa.String), nullable=True)
    )

    # Create index on role
    op.create_index("ix_users_role", "users", ["role"])


def downgrade() -> None:
    """
    Remove RBAC fields from users table.
    """
    # Drop index
    op.drop_index("ix_users_role", table_name="users")

    # Drop columns
    op.drop_column("users", "permissions")
    op.drop_column("users", "role")
