"""Add LinkedIn-specific entity types

Revision ID: linkedin_entity_types
Revises: 550d022883b1
Create Date: 2025-08-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'linkedin_entity_types'
down_revision = '550d022883b1'
branch_labels = None
depends_on = None


def upgrade():
    """Add LinkedIn-specific entity types to the system."""
    # The entity types are handled by the enum in the code
    # No database schema changes needed for enum values
    pass


def downgrade():
    """Remove LinkedIn-specific entity types."""
    # No database schema changes to revert
    pass
