"""add_composite_indexes_to_platform_connections

Revision ID: 7f2ba54a32b7
Revises: c33589a78bc8
Create Date: 2025-12-31 16:26:47.771081

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f2ba54a32b7'
down_revision: Union[str, None] = 'c33589a78bc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add composite indexes to platform_connections table for query optimization."""

    # Composite index on (user_id, platform, status) - most common query pattern
    # Used in queries like: WHERE user_id = X AND platform = Y AND status = Z
    op.create_index(
        'ix_platform_connections_user_platform_status',
        'platform_connections',
        ['user_id', 'platform', 'status'],
        unique=False
    )

    # Composite index on (user_id, platform) for queries without status filter
    # Used in queries like: WHERE user_id = X AND platform = Y
    op.create_index(
        'ix_platform_connections_user_platform',
        'platform_connections',
        ['user_id', 'platform'],
        unique=False
    )

    # Composite index on (user_id, status) for queries across all platforms
    # Used in queries like: WHERE user_id = X AND status = Y
    op.create_index(
        'ix_platform_connections_user_status',
        'platform_connections',
        ['user_id', 'status'],
        unique=False
    )


def downgrade() -> None:
    """Remove composite indexes from platform_connections table."""

    # Drop composite indexes in reverse order
    op.drop_index('ix_platform_connections_user_status', table_name='platform_connections')
    op.drop_index('ix_platform_connections_user_platform', table_name='platform_connections')
    op.drop_index('ix_platform_connections_user_platform_status', table_name='platform_connections')
