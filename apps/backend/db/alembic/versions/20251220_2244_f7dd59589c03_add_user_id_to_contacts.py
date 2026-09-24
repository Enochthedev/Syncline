"""add_user_id_to_contacts

Revision ID: f7dd59589c03
Revises: 3b4c5d6e7f8g
Create Date: 2025-12-20 22:44:35.536984

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7dd59589c03"
down_revision: Union[str, None] = "3b4c5d6e7f8g"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id column to contacts table - nullable first for existing data
    op.add_column("contacts", sa.Column("user_id", sa.UUID(), nullable=True))
    op.create_index(op.f("ix_contacts_user_id"), "contacts", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_contacts_user_id",
        "contacts",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_contacts_user_id", "contacts", type_="foreignkey")
    op.drop_index(op.f("ix_contacts_user_id"), table_name="contacts")
    op.drop_column("contacts", "user_id")
