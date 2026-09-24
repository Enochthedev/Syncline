"""add fulltext search to messages

Revision ID: 2a3b4c5d6e7f
Revises: cd551087417f
Create Date: 2025-11-16 19:58:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "2a3b4c5d6e7f"
down_revision = "cd551087417f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add full-text search support to messages table.

    - Adds a tsvector column for full-text search
    - Creates a GIN index on the tsvector column
    - Creates a trigger to automatically update the tsvector column
    """
    # Add tsvector column for full-text search
    op.add_column(
        "messages", sa.Column("search_vector", postgresql.TSVECTOR, nullable=True)
    )

    # Create function to update search vector
    op.execute("""
        CREATE OR REPLACE FUNCTION messages_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.content->>'text', '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.platform, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.thread_id, '')), 'D');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger to automatically update search vector
    op.execute("""
        CREATE TRIGGER messages_search_vector_trigger
        BEFORE INSERT OR UPDATE OF content, platform, thread_id
        ON messages
        FOR EACH ROW
        EXECUTE FUNCTION messages_search_vector_update();
    """)

    # Create GIN index for full-text search
    op.create_index(
        "idx_messages_search_vector",
        "messages",
        ["search_vector"],
        postgresql_using="gin",
    )

    # Update existing rows with search vectors
    op.execute("""
        UPDATE messages
        SET search_vector =
            setweight(to_tsvector('english', COALESCE(content->>'text', '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(platform, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(thread_id, '')), 'D')
        WHERE search_vector IS NULL;
    """)

    # Make search_vector NOT NULL after populating existing rows
    op.alter_column("messages", "search_vector", nullable=False)


def downgrade() -> None:
    """
    Remove full-text search support from messages table.
    """
    # Drop index
    op.drop_index("idx_messages_search_vector", table_name="messages")

    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS messages_search_vector_trigger ON messages;")

    # Drop function
    op.execute("DROP FUNCTION IF EXISTS messages_search_vector_update();")

    # Drop column
    op.drop_column("messages", "search_vector")
