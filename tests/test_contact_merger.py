"""Unit tests for ContactMerger service."""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from services.contacts.contact_merger import ContactMerger
from db.models.unified_contact import (
    UnifiedContact, ContactIdentity, ContactInsight,
    ContactPreference, ContactRelationship
)


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def contact_merger(mock_db_session):
    """ContactMerger instance with mocked dependencies."""
    return ContactMerger(mock_db_session)


@pytest.fixture
def sample_contacts_for_merge():
    """Sample contacts for merge testing."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Primary contact
    primary_contact = UnifiedContact(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        primary_name="John Smith",
        display_name="John Smith",
        primary_email="john.smith@example.com",
        primary_phone="+1234567890",
        total_messages=30,
        total_threads=5,
        relationship_strength=0.7,
        platforms=["gmail"],
        is_favorite=True,
        custom_notes="Primary contact notes",
        tags=["work", "important"],
        first_interaction=datetime.utcnow() - timedelta(days=100),
        last_interaction=datetime.utcnow() - timedelta(days=1)
    )

    # Duplicate contact 1
    duplicate1 = UnifiedContact(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        primary_name="John Smith",
        display_name="J. Smith",
        primary_email="j.smith@example.com",  # Different email
        total_messages=20,
        total_threads=3,
        relationship_strength=0.5,
        platforms=["slack"],
        is_favorite=False,
        custom_notes="Duplicate contact notes",
        tags=["colleague"],
        first_interaction=datetime.utcnow() - timedelta(days=80),
        last_interaction=datetime.utcnow() - timedelta(days=5)
    )

    # Duplicate contact 2
    duplicate2 = UnifiedContact(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        primary_name="John A. Smith",
        display_name="John Smith",
        primary_phone="+1234567890",  # Same phone as primary
        total_messages=15,
        total_threads=2,
        relationship_strength=0.8,  # Higher than primary
        platforms=["discord"],
        is_favorite=False,
        tags=["friend"],
        first_interaction=datetime.utcnow() - timedelta(days=120),  # Earlier than primary
        last_interaction=datetime.utcnow() - timedelta(days=2)
    )

    # Add identities
    primary_contact.identities = [
        ContactIdentity(
            id=uuid.uuid4(),
            unified_contact_id=primary_contact.id,
            platform="gmail",
            platform_user_id="john.smith@example.com",
            email="john.smith@example.com",
            display_name="John Smith"
        )
    ]

    duplicate1.identities = [
        ContactIdentity(
            id=uuid.uuid4(),
            unified_contact_id=duplicate1.id,
            platform="slack",
            platform_user_id="U123456",
            platform_handle="johnsmith",
            display_name="J. Smith"
        )
    ]

    duplicate2.identities = [
        ContactIdentity(
            id=uuid.uuid4(),
            unified_contact_id=duplicate2.id,
            platform="discord",
            platform_user_id="john#1234",
            platform_handle="johnsmith",
            display_name="John Smith"
        )
    ]

    # Add insights
    primary_contact.insights = [
        ContactInsight(
            id=uuid.uuid4(),
            unified_contact_id=primary_contact.id,
            insight_type="communication_pattern",
            title="Active in mornings",
            description="Most active 9-11 AM",
            confidence_score=0.8,
            is_active=True,
            generated_at=datetime.utcnow() - timedelta(days=1)
        )
    ]

    duplicate1.insights = [
        ContactInsight(
            id=uuid.uuid4(),
            unified_contact_id=duplicate1.id,
            insight_type="communication_pattern",
            title="Active in afternoons",
            description="Most active 2-4 PM",
            confidence_score=0.6,
            is_active=True,
            generated_at=datetime.utcnow() - timedelta(days=3)
        )
    ]

    # Add preferences
    primary_contact.preferences = [
        ContactPreference(
            id=uuid.uuid4(),
            unified_contact_id=primary_contact.id,
            notification_enabled=True,
            preferred_communication_platform="gmail"
        )
    ]

    return primary_contact, [duplicate1, duplicate2]


class TestContactMerger:
    """Test cases for ContactMerger."""

    @pytest.mark.asyncio
    async def test_merge_contacts_success(self, contact_merger, mock_db_session, sample_contacts_for_merge):
        """Test successful contact merging."""
        primary_contact, duplicates = sample_contacts_for_merge
        all_contacts = [primary_contact] + duplicates

        # Mock database query to return all contacts
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = all_contacts
        mock_db_session.execute.return_value = mock_result

        # Mock database operations
        mock_db_session.delete = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        result = await contact_merger.merge_contacts(
            primary_id=primary_contact.id,
            duplicate_ids=[d.id for d in duplicates],
            tenant_id=primary_contact.tenant_id,
            user_id=primary_contact.user_id
        )

        # Verify merged data
        assert result.primary_name == "John Smith"
        assert result.total_messages == 65  # 30 + 20 + 15
        assert result.total_threads == 10   # 5 + 3 + 2
        assert result.relationship_strength == 0.8  # Highest value
        assert result.is_favorite == True  # Preserved from primary
        assert set(result.platforms) == {
            "gmail", "slack", "discord"}  # Union of platforms
        assert set(result.tags) == {"work", "important",
                                    "colleague", "friend"}  # Union of tags

        # Verify timestamps
        # Earliest
        assert result.first_interaction == duplicates[1].first_interaction
        assert result.last_interaction == primary_contact.last_interaction  # Latest

        # Verify database operations
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
        assert mock_db_session.delete.call_count == len(duplicates)

    @pytest.mark.asyncio
    async def test_merge_contacts_primary_not_found(self, contact_merger, mock_db_session):
        """Test merge when primary contact is not found."""
        # Mock database query to return empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="No contacts found to merge"):
            await contact_merger.merge_contacts(
                primary_id=uuid.uuid4(),
                duplicate_ids=[uuid.uuid4()],
                tenant_id=uuid.uuid4(),
                user_id=uuid.uuid4()
            )

    @pytest.mark.asyncio
    async def test_merge_contacts_no_duplicates(self, contact_merger, mock_db_session, sample_contacts_for_merge):
        """Test merge when no duplicate contacts are found."""
        primary_contact, _ = sample_contacts_for_merge

        # Mock database query to return only primary contact
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [primary_contact]
        mock_db_session.execute.return_value = mock_result

        result = await contact_merger.merge_contacts(
            primary_id=primary_contact.id,
            duplicate_ids=[uuid.uuid4()],  # Non-existent duplicate
            tenant_id=primary_contact.tenant_id,
            user_id=primary_contact.user_id
        )

        # Should return primary contact unchanged
        assert result == primary_contact

    def test_merge_contact_data(self, contact_merger, sample_contacts_for_merge):
        """Test merging of basic contact data."""
        primary_contact, duplicates = sample_contacts_for_merge

        # Test the private method directly
        contact_merger._merge_contact_data(primary_contact, duplicates)

        # Verify merged data
        assert primary_contact.total_messages == 65  # Sum of all messages
        assert primary_contact.total_threads == 10   # Sum of all threads
        assert primary_contact.relationship_strength == 0.8  # Highest value
        assert primary_contact.is_favorite == True  # Preserved
        assert set(primary_contact.platforms) == {"gmail", "slack", "discord"}
        assert set(primary_contact.tags) == {
            "work", "important", "colleague", "friend"}

        # Verify notes are merged
        assert "Primary contact notes" in primary_contact.custom_notes
        assert "Duplicate contact notes" in primary_contact.custom_notes

    @pytest.mark.asyncio
    async def test_merge_identities(self, contact_merger, mock_db_session, sample_contacts_for_merge):
        """Test merging of contact identities."""
        primary_contact, duplicates = sample_contacts_for_merge

        await contact_merger._merge_identities(primary_contact, duplicates)

        # Verify identities are updated to point to primary contact
        for duplicate in duplicates:
            for identity in duplicate.identities:
                assert identity.unified_contact_id == primary_contact.id

    @pytest.mark.asyncio
    async def test_merge_insights(self, contact_merger, mock_db_session, sample_contacts_for_merge):
        """Test merging of contact insights."""
        primary_contact, duplicates = sample_contacts_for_merge

        # Mock the deactivate duplicate insights method
        contact_merger._deactivate_duplicate_insights = AsyncMock()

        await contact_merger._merge_insights(primary_contact, duplicates)

        # Verify insights are updated to point to primary contact
        for duplicate in duplicates:
            for insight in duplicate.insights:
                assert insight.unified_contact_id == primary_contact.id

        # Verify deactivate method was called
        contact_merger._deactivate_duplicate_insights.assert_called_once_with(
            primary_contact.id)

    @pytest.mark.asyncio
    async def test_merge_preferences(self, contact_merger, mock_db_session, sample_contacts_for_merge):
        """Test merging of contact preferences."""
        primary_contact, duplicates = sample_contacts_for_merge

        # Mock database delete operation
        mock_db_session.delete = MagicMock()

        await contact_merger._merge_preferences(primary_contact, duplicates)

        # Since primary has preferences, duplicates' preferences should be deleted
        # (This is a simplified test - in reality, the logic is more complex)
        assert mock_db_session.delete.called

    def test_calculate_contact_similarity(self, contact_merger, sample_contacts_for_merge):
        """Test contact similarity calculation."""
        primary_contact, duplicates = sample_contacts_for_merge

        # Test similarity between primary and first duplicate
        similarity1 = contact_merger._calculate_contact_similarity(
            primary_contact, duplicates[0])
        assert 0 < similarity1 < 1  # Should be similar but not identical

        # Test similarity between primary and second duplicate (same phone)
        similarity2 = contact_merger._calculate_contact_similarity(
            primary_contact, duplicates[1])
        assert similarity2 > similarity1  # Should be more similar due to same phone

        # Test similarity with identical contact
        identical_similarity = contact_merger._calculate_contact_similarity(
            primary_contact, primary_contact)
        assert identical_similarity == 1.0

    def test_calculate_string_similarity(self, contact_merger):
        """Test string similarity calculation."""
        # Exact match
        assert contact_merger._calculate_string_similarity(
            "John Smith", "John Smith") == 1.0

        # No match
        assert contact_merger._calculate_string_similarity(
            "John Smith", "Jane Doe") == 0.0

        # Partial match
        similarity = contact_merger._calculate_string_similarity(
            "John Smith", "John")
        assert 0 < similarity < 1

        # Empty strings
        assert contact_merger._calculate_string_similarity("", "") == 1.0
        assert contact_merger._calculate_string_similarity("John", "") == 0.0

    def test_get_similarity_reasons(self, contact_merger, sample_contacts_for_merge):
        """Test getting similarity reasons between contacts."""
        primary_contact, duplicates = sample_contacts_for_merge

        # Test reasons for first duplicate
        reasons1 = contact_merger._get_similarity_reasons(
            primary_contact, duplicates[0])
        assert "Similar names" in reasons1 or "Very similar names" in reasons1

        # Test reasons for second duplicate (same phone)
        reasons2 = contact_merger._get_similarity_reasons(
            primary_contact, duplicates[1])
        assert "Same phone number" in reasons2
        assert len(reasons2) > 0

    @pytest.mark.asyncio
    async def test_find_potential_duplicates(self, contact_merger, mock_db_session, sample_contacts_for_merge):
        """Test finding potential duplicate contacts."""
        primary_contact, duplicates = sample_contacts_for_merge
        all_contacts = [primary_contact] + duplicates

        # Mock database query to return all contacts
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = all_contacts
        mock_db_session.execute.return_value = mock_result

        potential_duplicates = await contact_merger.find_potential_duplicates(
            tenant_id=primary_contact.tenant_id,
            user_id=primary_contact.user_id,
            similarity_threshold=0.3  # Lower threshold to catch more duplicates
        )

        assert len(potential_duplicates) > 0

        # Verify structure of results
        for duplicate_group in potential_duplicates:
            assert "primary_contact" in duplicate_group
            assert "similar_contacts" in duplicate_group
            assert "group_size" in duplicate_group
            assert duplicate_group["group_size"] >= 2

    @pytest.mark.asyncio
    async def test_suggest_merge_candidates(self, contact_merger, mock_db_session, sample_contacts_for_merge):
        """Test suggesting merge candidates for a specific contact."""
        primary_contact, duplicates = sample_contacts_for_merge

        # Mock database queries
        mock_target_result = MagicMock()
        mock_target_result.scalar_one_or_none.return_value = primary_contact

        mock_others_result = MagicMock()
        mock_others_result.scalars.return_value.all.return_value = duplicates

        mock_db_session.execute.side_effect = [
            mock_target_result, mock_others_result]

        candidates = await contact_merger.suggest_merge_candidates(
            contact_id=primary_contact.id,
            tenant_id=primary_contact.tenant_id,
            user_id=primary_contact.user_id
        )

        assert len(candidates) > 0

        # Verify structure of candidates
        for candidate in candidates:
            assert "contact_id" in candidate
            assert "primary_name" in candidate
            assert "similarity" in candidate
            assert "reasons" in candidate
            # Only reasonably similar contacts
            assert candidate["similarity"] > 0.5

    @pytest.mark.asyncio
    async def test_suggest_merge_candidates_contact_not_found(self, contact_merger, mock_db_session):
        """Test suggesting merge candidates when target contact is not found."""
        # Mock database query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        candidates = await contact_merger.suggest_merge_candidates(
            contact_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4()
        )

        assert candidates == []

    @pytest.mark.asyncio
    async def test_update_relationships(self, contact_merger, mock_db_session, sample_contacts_for_merge):
        """Test updating contact relationships during merge."""
        primary_contact, duplicates = sample_contacts_for_merge

        # Create mock relationships
        mock_relationships = [
            ContactRelationship(
                id=uuid.uuid4(),
                contact_a_id=duplicates[0].id,
                contact_b_id=uuid.uuid4(),
                relationship_type="colleague"
            ),
            ContactRelationship(
                id=uuid.uuid4(),
                contact_a_id=uuid.uuid4(),
                contact_b_id=duplicates[1].id,
                relationship_type="friend"
            )
        ]

        # Mock database queries for relationships
        mock_result_a = MagicMock()
        mock_result_a.scalars.return_value.all.return_value = [
            mock_relationships[0]]

        mock_result_b = MagicMock()
        mock_result_b.scalars.return_value.all.return_value = [
            mock_relationships[1]]

        mock_db_session.execute.side_effect = [mock_result_a, mock_result_b]

        # Mock the remove duplicate relationships method
        contact_merger._remove_duplicate_relationships = AsyncMock()

        await contact_merger._update_relationships(primary_contact, duplicates)

        # Verify relationships are updated to point to primary contact
        assert mock_relationships[0].contact_a_id == primary_contact.id
        assert mock_relationships[1].contact_b_id == primary_contact.id

        # Verify remove duplicates was called
        contact_merger._remove_duplicate_relationships.assert_called_once_with(
            primary_contact.id)


class TestContactMergerIntegration:
    """Integration test cases for ContactMerger."""

    @pytest.mark.asyncio
    async def test_full_merge_workflow(self, contact_merger, mock_db_session, sample_contacts_for_merge):
        """Test complete merge workflow from detection to completion."""
        primary_contact, duplicates = sample_contacts_for_merge
        all_contacts = [primary_contact] + duplicates

        # Mock all database operations
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = all_contacts
        mock_db_session.execute.return_value = mock_result
        mock_db_session.delete = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # 1. Find potential duplicates
        potential_duplicates = await contact_merger.find_potential_duplicates(
            tenant_id=primary_contact.tenant_id,
            user_id=primary_contact.user_id
        )

        assert len(potential_duplicates) > 0

        # 2. Suggest merge candidates for primary contact
        mock_db_session.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(
                return_value=primary_contact)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(
                all=MagicMock(return_value=duplicates))))
        ]

        candidates = await contact_merger.suggest_merge_candidates(
            contact_id=primary_contact.id,
            tenant_id=primary_contact.tenant_id,
            user_id=primary_contact.user_id
        )

        assert len(candidates) > 0

        # 3. Perform merge
        mock_db_session.execute.return_value = mock_result  # Reset for merge operation

        merged_contact = await contact_merger.merge_contacts(
            primary_id=primary_contact.id,
            duplicate_ids=[d.id for d in duplicates],
            tenant_id=primary_contact.tenant_id,
            user_id=primary_contact.user_id
        )

        # Verify merge was successful
        assert merged_contact.id == primary_contact.id
        assert merged_contact.total_messages > primary_contact.total_messages
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_merge_with_complex_relationships(self, contact_merger, mock_db_session, sample_contacts_for_merge):
        """Test merging contacts with complex relationship networks."""
        primary_contact, duplicates = sample_contacts_for_merge
        all_contacts = [primary_contact] + duplicates

        # Create complex relationship network
        relationships = []
        for i, duplicate in enumerate(duplicates):
            # Each duplicate has relationships with other contacts
            for j in range(2):  # 2 relationships per duplicate
                rel = ContactRelationship(
                    id=uuid.uuid4(),
                    contact_a_id=duplicate.id,
                    contact_b_id=uuid.uuid4(),
                    relationship_type="colleague",
                    strength=0.5 + (i * 0.1),
                    common_threads=5 + i,
                    discovered_at=datetime.utcnow() - timedelta(days=10 + i)
                )
                relationships.append(rel)

        # Mock database operations
        mock_contacts_result = MagicMock()
        mock_contacts_result.scalars.return_value.all.return_value = all_contacts

        mock_rel_results = [
            MagicMock(scalars=MagicMock(return_value=MagicMock(
                all=MagicMock(return_value=relationships[:2])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(
                all=MagicMock(return_value=relationships[2:]))))
        ]

        mock_db_session.execute.side_effect = [
            mock_contacts_result] + mock_rel_results + [MagicMock()]
        mock_db_session.delete = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Perform merge
        merged_contact = await contact_merger.merge_contacts(
            primary_id=primary_contact.id,
            duplicate_ids=[d.id for d in duplicates],
            tenant_id=primary_contact.tenant_id,
            user_id=primary_contact.user_id
        )

        # Verify relationships were updated
        for rel in relationships:
            assert rel.contact_a_id == primary_contact.id or rel.contact_b_id == primary_contact.id

        # Verify merge completed successfully
        assert merged_contact.id == primary_contact.id
        mock_db_session.commit.assert_called()
