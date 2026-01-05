"""add_encrypted_credentials_column

Revision ID: b6928c7e6097
Revises: 9a4f32d90c53
Create Date: 2025-12-31 09:48:18.642973

Adds encrypted credentials column to platform_connections table.

Migration Steps:
1. Add new credentials_encrypted TEXT column
2. Existing credentials column renamed to credentials (keeps legacy data intact)
3. New connections will use encrypted format automatically via model property

Note: Actual data migration (encrypting existing credentials) happens lazily
via the PlatformConnection.migrate_to_encrypted() method when connections
are accessed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6928c7e6097'
down_revision: Union[str, None] = '9a4f32d90c53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add credentials_encrypted column for encrypted credential storage.

    The existing 'credentials' JSONB column is preserved for backward
    compatibility during migration.
    """
    # Add new encrypted credentials column
    op.add_column(
        'platform_connections',
        sa.Column('credentials_encrypted', sa.Text(), nullable=True)
    )

    # Note: We do NOT drop the old credentials column yet to maintain
    # backward compatibility. The model's hybrid_property handles both formats.


def downgrade() -> None:
    """
    Remove credentials_encrypted column.

    WARNING: This will lose encrypted credentials. Only run if you're
    certain you want to revert to unencrypted storage.
    """
    op.drop_column('platform_connections', 'credentials_encrypted')
