"""setup_core_infrastructure_and_models

Revision ID: 371092c79315
Revises: d347c2562c35
Create Date: 2025-08-10 10:43:43.323572

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '371092c79315'
down_revision: Union[str, Sequence[str], None] = 'd347c2562c35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Note: Using string instead of enum for platform to avoid enum creation issues
    
    # Create participants table
    op.create_table('participants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('platform_user_id', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('avatar_url', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('participant_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('platform', 'platform_user_id', name='uq_platform_participant')
    )
    op.create_index('ix_participants_display_name', 'participants', ['display_name'])
    op.create_index('ix_participants_email', 'participants', ['email'])
    op.create_index('ix_participants_platform', 'participants', ['platform'])
    
    # Create threads table
    op.create_table('threads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('platform_thread_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('participants', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('thread_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('platform', 'platform_thread_id', name='uq_platform_thread')
    )
    op.create_index('ix_threads_last_message', 'threads', ['last_message_at'])
    op.create_index('ix_threads_participants', 'threads', ['participants'], postgresql_using='gin')
    op.create_index('ix_threads_platform', 'threads', ['platform'])
    
    # Create messages table
    op.create_table('messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('platform_message_id', sa.String(length=255), nullable=False),
        sa.Column('thread_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_text', sa.Text(), nullable=True),
        sa.Column('content_html', sa.Text(), nullable=True),
        sa.Column('content_markdown', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('message_metadata', sa.JSON(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['sender_id'], ['participants.id'], ),
        sa.ForeignKeyConstraint(['thread_id'], ['threads.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('platform', 'platform_message_id', name='uq_platform_message')
    )
    op.create_index('ix_messages_platform_timestamp', 'messages', ['platform', 'timestamp'])
    op.create_index('ix_messages_sender_timestamp', 'messages', ['sender_id', 'timestamp'])
    op.create_index('ix_messages_thread_timestamp', 'messages', ['thread_id', 'timestamp'])
    
    # Create entities table
    op.create_table('entities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('normalized_value', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('entity_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_entities_confidence', 'entities', ['confidence'])
    op.create_index('ix_entities_normalized', 'entities', ['normalized_value'])
    op.create_index('ix_entities_type_value', 'entities', ['type', 'value'])
    
    # Create summaries table
    op.create_table('summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('scope_type', sa.String(length=50), nullable=False),
        sa.Column('scope_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('key_points', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('action_items', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('entities', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('timeframe_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('timeframe_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('summary_metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['scope_id'], ['threads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_summaries_created', 'summaries', ['created_at'])
    op.create_index('ix_summaries_scope_id', 'summaries', ['scope_id'])
    op.create_index('ix_summaries_timeframe', 'summaries', ['timeframe_start', 'timeframe_end'])
    op.create_index('ix_summaries_type_scope', 'summaries', ['type', 'scope_type'])
    
    # Create attachments table
    op.create_table('attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=500), nullable=True),
        sa.Column('original_filename', sa.String(length=500), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('storage_path', sa.String(length=1000), nullable=True),
        sa.Column('storage_url', sa.String(length=1000), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('thumbnail_path', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attachment_metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_attachments_filename', 'attachments', ['filename'])
    op.create_index('ix_attachments_hash', 'attachments', ['content_hash'])
    op.create_index('ix_attachments_message', 'attachments', ['message_id'])
    op.create_index('ix_attachments_mime_type', 'attachments', ['mime_type'])
    
    # Create message_entities table
    op.create_table('message_entities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('start_position', sa.Integer(), nullable=True),
        sa.Column('end_position', sa.Integer(), nullable=True),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_message_entities_entity', 'message_entities', ['entity_id'])
    op.create_index('ix_message_entities_message', 'message_entities', ['message_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order
    op.drop_table('message_entities')
    op.drop_table('attachments')
    op.drop_table('summaries')
    op.drop_table('entities')
    op.drop_table('messages')
    op.drop_table('threads')
    op.drop_table('participants')
    
    # Note: No enum types to drop since we used strings
