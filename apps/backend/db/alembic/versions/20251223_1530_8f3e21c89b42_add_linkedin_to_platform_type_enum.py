"""add_linkedin_to_platform_type_enum

Revision ID: 8f3e21c89b42
Revises: 045e54df57ce
Create Date: 2025-12-23 15:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f3e21c89b42"
down_revision: Union[str, None] = "045e54df57ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'linkedin' to the platform_type enum
    # PostgreSQL doesn't support adding enum values in a transaction by default
    # so we need to use raw SQL
    op.execute("ALTER TYPE platform_type ADD VALUE IF NOT EXISTS 'linkedin'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values
    # This would require recreating the enum and all columns using it
    # For safety, we'll leave this as a no-op
    pass
