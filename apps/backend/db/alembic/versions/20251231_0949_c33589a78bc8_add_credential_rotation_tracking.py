"""add_credential_rotation_tracking

Revision ID: c33589a78bc8
Revises: b6928c7e6097
Create Date: 2025-12-31 09:49:57.431774

Adds credential rotation tracking columns to platform_connections table:
- credentials_rotated_at: Timestamp of last rotation
- credentials_version: Version string (e.g., "v1", "v2") for audit trail
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c33589a78bc8"
down_revision: Union[str, None] = "b6928c7e6097"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add credential rotation tracking columns.
    """
    # Add rotation timestamp column
    op.add_column(
        "platform_connections",
        sa.Column("credentials_rotated_at", sa.DateTime(), nullable=True),
    )

    # Add version tracking column with default value
    op.add_column(
        "platform_connections",
        sa.Column(
            "credentials_version",
            sa.String(length=50),
            nullable=False,
            server_default="v1",
        ),
    )


def downgrade() -> None:
    """
    Remove credential rotation tracking columns.
    """
    op.drop_column("platform_connections", "credentials_version")
    op.drop_column("platform_connections", "credentials_rotated_at")
