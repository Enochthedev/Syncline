"""add_google_chat_to_platform_type_enum

Revision ID: 9a4f32d90c53
Revises: 8f3e21c89b42
Create Date: 2025-12-25 19:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9a4f32d90c53"
down_revision: Union[str, None] = "8f3e21c89b42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'google_chat' to the platform_type enum
    op.execute("ALTER TYPE platform_type ADD VALUE IF NOT EXISTS 'google_chat'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values
    pass
