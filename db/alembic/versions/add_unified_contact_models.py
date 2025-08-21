"""Add unified contact models

Revision ID: add_unified_contact_models
Revises: bb04e9c4a9aa
Create Date: 2025-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_unified_contact_models'
down_revision = 'bb04e9c4a9aa'
branch_labels = None
depends_on = None


def upgrade():
    # Create unified_contacts table
    op.create_table('unified_contacts',
                    sa.Column('id', postgresql.UUID(
                        as_uuid=True), nullable=False),
                    sa.Column('tenant_id', postgresql.UUID(
                        as_uuid=True), nullable=False),
                    sa.Column('user_id', postgresql.UUID(
                        as_uuid=True), nullable=False),
                    sa.Column('primary_name', sa.String(
                        length=255), nullable=False),
                    sa.Column('display_name', sa.String(
                        length=255), nullable=True),
                    sa.Column('profile_photo_url', sa.String(
                        length=1000), nullable=True),
                    sa.Column('primary_email', sa.String(
                        length=255), nullable=True),
                    sa.Column('primary_phone', sa.String(
                        length=50), nullable=True),
                    sa.Column('last_interaction',
                              sa.DateTime(), nullable=True),
                    sa.Column('first_interaction',
                              sa.DateTime(), nullable=True),
                    sa.Column('total_messages', sa.Integer(),
                              nullable=True, default=0),
                    sa.Column('total_threads', sa.Integer(),
                              nullable=True, default=0),
                    sa.Column('platforms', sa.JSON(),
                              nullable=True, default=list),
                    sa.Column('preferred_platform', sa.String(
                        length=50), nullable=True),
                    sa.Column('relationship_strength', sa.Float(),
                              nullable=True, default=0.0),
                    sa.Column('communication_frequency', sa.String(
                        length=20), nullable=True, default='never'),
                    sa.Column('response_time_avg', sa.Float(), nullable=True),
                    sa.Column('sentiment_score', sa.Float(),
                              nullable=True, default=0.0),
                    sa.Column('top_topics', sa.JSON(),
                              nullable=True, default=list),
                    sa.Column('common_entities', sa.JSON(),
                              nullable=True, default=list),
                    sa.Column('shared_interests', sa.JSON(),
                              nullable=True, default=list),
                    sa.Column('mutual_contacts', sa.JSON(),
                              nullable=True, default=list),
                    sa.Column('interaction_patterns', sa.JSON(),
                              nullable=True, default=dict),
                    sa.Column('custom_notes', sa.Text(), nullable=True),
                    sa.Column('tags', sa.JSON(), nullable=True, default=list),
                    sa.Column('is_favorite', sa.Boolean(),
                              nullable=True, default=False),
                    sa.Column('is_archived', sa.Boolean(),
                              nullable=True, default=False),
                    sa.Column('notification_preferences', sa.JSON(),
                              nullable=True, default=dict),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.Column('last_sync_at', sa.DateTime(), nullable=True),
                    sa.Column('extra_metadata', sa.JSON(),
                              nullable=True, default=dict),
                    sa.ForeignKeyConstraint(
                        ['user_id'], ['users.id'], ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id')
                    )

    # Create indexes for unified_contacts
    op.create_index('ix_unified_contacts_tenant_user',
                    'unified_contacts', ['tenant_id', 'user_id'])
    op.create_index('ix_unified_contacts_primary_name',
                    'unified_contacts', ['primary_name'])
    op.create_index('ix_unified_contacts_primary_email',
                    'unified_contacts', ['primary_email'])
    op.create_index('ix_unified_contacts_last_interaction',
                    'unified_contacts', ['last_interaction'])
    op.create_index('ix_unified_contacts_relationship_strength',
                    'unified_contacts', ['relationship_strength'])
    op.create_index('ix_unified_contacts_communication_frequency',
                    'unified_contacts', ['communication_frequency'])
    op.create_index('ix_unified_contacts_is_favorite',
                    'unified_contacts', ['is_favorite'])
    op.create_index('ix_unified_contacts_is_archived',
                    'unified_contacts', ['is_archived'])

    # Create contact_identities table
    op.create_table('contact_identities',
                    sa.Column('id', postgresql.UUID(
                        as_uuid=True), nullable=False),
                    sa.Column('unified_contact_id', postgresql.UUID(
                        as_uuid=True), nullable=False),
                    sa.Column('platform', sa.String(
                        length=50), nullable=False),
                    sa.Column('platform_user_id', sa.String(
                        length=255), nullable=False),
                    sa.Column('platform_handle', sa.String(
                        length=255), nullable=True),
                    sa.Column('display_name', sa.String(
                        length=255), nullable=True),
                    sa.Column('email', sa.String(length=255), nullable=True),
                    sa.Column('phone', sa.String(length=50), nullable=True),
                    sa.Column('profile_url', sa.String(
                        length=1000), nullable=True),
                    sa.Column('avatar_url', sa.String(
                        length=1000), nullable=True),
                    sa.Column('is_verified', sa.Boolean(),
                              nullable=True, default=False),
                    sa.Column('is_active', sa.Boolean(),
                              nullable=True, default=True),
                    sa.Column('last_seen', sa.DateTime(), nullable=True),
                    sa.Column('platform_metadata', sa.JSON(),
                              nullable=True, default=dict),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.ForeignKeyConstraint(['unified_contact_id'], [
                        'unified_contacts.id'], ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id')
                    )

    # Create indexes for contact_identities
    op.create_index('ix_contact_identities_unified_contact',
                    'contact_identities', ['unified_contact_id'])
    op.create_index('ix_contact_identities_platform',
                    'contact_identities', ['platform'])
    op.create_index('ix_contact_identities_platform_user',
                    'contact_identities', ['platform', 'platform_user_id'])
    op.create_index('ix_contact_identities_email',
                    'contact_identities', ['email'])
    op.create_index('ix_contact_identities_phone',
                    'contact_identities', ['phone'])

    # Create contact_insights table
    op.create_table('contact_insights',
                    sa.Column('id', postgresql.UUID(
                        as_uuid=True), nullable=False),
                    sa.Column('unified_contact_id', postgresql.UUID(
                        as_uuid=True), nullable=False),
                    sa.Column('insight_type', sa.String(
                        length=50), nullable=False),
                    sa.Column('title', sa.String(length=255), nullable=False),
                    sa.Column('description', sa.Text(), nullable=False),
                    sa.Column('confidence_score', sa.Float(),
                              nullable=True, default=0.0),
                    sa.Column('supporting_data', sa.JSON(),
                              nullable=True, default=dict),
                    sa.Column('suggested_actions', sa.JSON(),
                              nullable=True, default=list),
                    sa.Column('generated_at', sa.DateTime(), nullable=True),
                    sa.Column('expires_at', sa.DateTime(), nullable=True),
                    sa.Column('is_active', sa.Boolean(),
                              nullable=True, default=True),
                    sa.Column('user_feedback', sa.String(
                        length=20), nullable=True),
                    sa.ForeignKeyConstraint(['unified_contact_id'], [
                        'unified_contacts.id'], ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id')
                    )

    # Create indexes for contact_insights
    op.create_index('ix_contact_insights_unified_contact',
                    'contact_insights', ['unified_contact_id'])
    op.create_index('ix_contact_insights_type',
                    'contact_insights', ['insight_type'])
    op.create_index('ix_contact_insights_generated_at',
                    'contact_insights', ['generated_at'])
    op.create_index('ix_contact_insights_confidence',
                    'contact_insights', ['confidence_score'])

    # Create contact_preferences table
    op.create_table('contact_preferences',
                    sa.Column('id', postgresql.UUID(
                        as_uuid=True), nullable=False),
                    sa.Column('unified_contact_id', postgresql.UUID(
                        as_uuid=True), nullable=False),
                    sa.Column('notification_enabled', sa.Boolean(),
                              nullable=True, default=True),
                    sa.Column('preferred_communication_platform',
                              sa.String(length=50), nullable=True),
                    sa.Column('reminder_frequency', sa.String(
                        length=20), nullable=True, default='normal'),
                    sa.Column('custom_ringtone', sa.String(
                        length=255), nullable=True),
                    sa.Column('custom_notification_sound',
                              sa.String(length=255), nullable=True),
                    sa.Column('share_presence', sa.Boolean(),
                              nullable=True, default=True),
                    sa.Column('share_read_receipts', sa.Boolean(),
                              nullable=True, default=True),
                    sa.Column('auto_reply_enabled', sa.Boolean(),
                              nullable=True, default=False),
                    sa.Column('auto_reply_message', sa.Text(), nullable=True),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.ForeignKeyConstraint(['unified_contact_id'], [
                        'unified_contacts.id'], ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id')
                    )

    # Create index for contact_preferences
    op.create_index('ix_contact_preferences_unified_contact',
                    'contact_preferences', ['unified_contact_id'])

    # Create contact_relationships table
    op.create_table('contact_relationships',
                    sa.Column('id', postgresql.UUID(
                        as_uuid=True), nullable=False),
                    sa.Column('contact_a_id', postgresql.UUID(
                        as_uuid=True), nullable=False),
                    sa.Column('contact_b_id', postgresql.UUID(
                        as_uuid=True), nullable=False),
                    sa.Column('relationship_type', sa.String(
                        length=50), nullable=False),
                    sa.Column('strength', sa.Float(),
                              nullable=True, default=0.0),
                    sa.Column('common_threads', sa.Integer(),
                              nullable=True, default=0),
                    sa.Column('common_groups', sa.JSON(),
                              nullable=True, default=list),
                    sa.Column('shared_interactions', sa.Integer(),
                              nullable=True, default=0),
                    sa.Column('discovered_at', sa.DateTime(), nullable=True),
                    sa.Column('last_interaction',
                              sa.DateTime(), nullable=True),
                    sa.Column('is_confirmed', sa.Boolean(),
                              nullable=True, default=False),
                    sa.Column('confidence_score', sa.Float(),
                              nullable=True, default=0.0),
                    sa.ForeignKeyConstraint(
                        ['contact_a_id'], ['unified_contacts.id'], ondelete='CASCADE'),
                    sa.ForeignKeyConstraint(
                        ['contact_b_id'], ['unified_contacts.id'], ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id')
                    )

    # Create indexes for contact_relationships
    op.create_index('ix_contact_relationships_contact_a',
                    'contact_relationships', ['contact_a_id'])
    op.create_index('ix_contact_relationships_contact_b',
                    'contact_relationships', ['contact_b_id'])
    op.create_index('ix_contact_relationships_type',
                    'contact_relationships', ['relationship_type'])
    op.create_index('ix_contact_relationships_strength',
                    'contact_relationships', ['strength'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('contact_relationships')
    op.drop_table('contact_preferences')
    op.drop_table('contact_insights')
    op.drop_table('contact_identities')
    op.drop_table('unified_contacts')
