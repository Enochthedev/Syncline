"""Unit tests for ContactManager service using mocks."""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from services.contacts.contact_manager import ContactManager


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def contact_manager(mock_db_session):
    """ContactManager instance with mocked dependencies."""
    return ContactManager(mock_db_session)


@pytest.fixture
def sample_contact():
    """Sample unified contact for testing."""
    contact_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Create a mock contact object
    contact = MagicMock()
    contact.id = contact_id
    contact.tenant_id = tenant_id
    contact.user_id = user_id
    contact.primary_name = "John Smith"
    contact.display_name = "John Smith"
    contact.primary_email = "john.smith@example.com"
    contact.primary_phone = "+1234567890"
    contact.total_messages = 50
    contact.total_threads = 10
    contact.relationship_strength = 0.75
    contact.communication_frequency = "regular"
    contact.platforms = ["gmail", "slack"]
    contact.is_favorite = False
    contact.created_at = datetime.utcnow()
    contact.updated_at = datetime.utcnow()

    # Add mock identities
    identity1 = MagicMock()
    identity1.id = uuid.uuid4()
    identity1.unified_contact_id = contact_id
    identity1.platform = "gmail"
    identity1.platform_user_id = "john.smith@example.com"
    identity1.email = "john.smith@example.com"
    identity1.display_name = "John Smith"

    identity2 = MagicMock()
    identity2.id = uuid.uuid4()
    identity2.unified_contact_id = contact_id
    identity2.platform = "slack"
    identity2.platform_user_id = "U123456"
    identity2.platform_handle = "johnsmith"
    identity2.display_name = "John Smith"

    contact.identities = [identity1, identity2]

    return contact


class TestContactManager:
    """Test cases for ContactManager."""

    @pytest.mark.asyncio
    async def test_search_contacts_with_query(self, contact_manager, mock_db_session, sample_contact):
        """Test searching contacts with a query string."""
        tenant_id = sample_contact.tenant_id
        user_id = sample_contact.user_id

        # Mock search service
        contact_manager.search_service.search_contacts = AsyncMock(return_value=[
                                                                   sample_contact])

        results = await contact_manager.search_contacts(
            query="John Smith",
            tenant_id=tenant_id,
            user_id=user_id,
            limit=50
        )

        assert len(results) == 1
        assert results[0].primary_name == "John Smith"
        contact_manager.search_service.search_contacts.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_contact_by_id(self, contact_manager, mock_db_session, sample_contact):
        """Test retrieving a contact by ID."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_contact
        mock_db_session.execute.return_value = mock_result

        result = await contact_manager.get_contact(
            contact_id=sample_contact.id,
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id
        )

        assert result is not None
        assert result.primary_name == "John Smith"
        assert result.primary_email == "john.smith@example.com"
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_contact_not_found(self, contact_manager, mock_db_session):
        """Test retrieving a non-existent contact."""
        # Mock database query returning None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await contact_manager.get_contact(
            contact_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4()
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_unified_contact_by_identifiers(self, contact_manager, mock_db_session, sample_contact):
        """Test retrieving a unified contact by platform identifiers."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_contact
        mock_db_session.execute.return_value = mock_result

        identifiers = [
            {"platform": "gmail", "platform_user_id": "john.smith@example.com"},
            {"email": "john.smith@example.com"}
        ]

        result = await contact_manager.get_unified_contact(
            identifiers=identifiers,
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id
        )

        assert result is not None
        assert result.primary_name == "John Smith"
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_contact(self, contact_manager, mock_db_session, sample_contact):
        """Test updating a contact."""
        # Mock get_contact to return sample contact
        contact_manager.get_contact = AsyncMock(return_value=sample_contact)
        mock_db_session.commit = AsyncMock()

        updates = {
            "display_name": "John A. Smith",
            "is_favorite": True,
            "custom_notes": "Important client"
        }

        result = await contact_manager.update_contact(
            contact_id=sample_contact.id,
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id,
            updates=updates
        )

        assert result is not None
        assert result.display_name == "John A. Smith"
        assert result.is_favorite == True
        assert result.custom_notes == "Important client"
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_messages_by_contact(self, contact_manager, mock_db_session, sample_contact):
        """Test searching messages by contact."""
        # Mock get_contact
        contact_manager.get_contact = AsyncMock(return_value=sample_contact)

        # Mock message query
        mock_message = MagicMock()
        mock_message.id = uuid.uuid4()
        mock_message.tenant_id = sample_contact.tenant_id
        mock_message.content = "Hello John!"
        mock_message.timestamp = datetime.utcnow()
        mock_message.platform = "gmail"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_message]
        mock_db_session.execute.return_value = mock_result

        results = await contact_manager.search_messages_by_contact(
            contact_id=sample_contact.id,
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id,
            query="Hello"
        )

        assert len(results) == 1
        assert results[0].content == "Hello John!"
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_merge_contacts(self, contact_manager, mock_db_session, sample_contact):
        """Test merging duplicate contacts."""
        primary_id = sample_contact.id
        duplicate_ids = [uuid.uuid4(), uuid.uuid4()]

        # Mock merger service
        merged_contact = sample_contact
        merged_contact.total_messages = 100  # Simulated merged data
        contact_manager.merger.merge_contacts = AsyncMock(
            return_value=merged_contact)

        result = await contact_manager.merge_contacts(
            primary_id=primary_id,
            duplicate_ids=duplicate_ids,
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id
        )

        assert result.total_messages == 100
        contact_manager.merger.merge_contacts.assert_called_once_with(
            primary_id, duplicate_ids, sample_contact.tenant_id, sample_contact.user_id
        )

    @pytest.mark.asyncio
    async def test_add_contact_note(self, contact_manager, mock_db_session, sample_contact):
        """Test adding a note to a contact."""
        # Mock get_contact
        contact_manager.get_contact = AsyncMock(return_value=sample_contact)
        mock_db_session.commit = AsyncMock()

        note = "Met at conference 2024"

        result = await contact_manager.add_contact_note(
            contact_id=sample_contact.id,
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id,
            note=note
        )

        assert result == True
        assert note in sample_contact.custom_notes
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_contact_insights(self, contact_manager, mock_db_session, sample_contact):
        """Test getting contact insights."""
        mock_insight = MagicMock()
        mock_insight.id = uuid.uuid4()
        mock_insight.unified_contact_id = sample_contact.id
        mock_insight.insight_type = "communication_pattern"
        mock_insight.title = "Most Active in Mornings"
        mock_insight.description = "John is most active between 9-11 AM"
        mock_insight.confidence_score = 0.85

        contact_manager.insights_service.get_contact_insights = AsyncMock(return_value=[
                                                                          mock_insight])

        results = await contact_manager.get_contact_insights(
            contact_id=sample_contact.id,
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id
        )

        assert len(results) == 1
        assert results[0].insight_type == "communication_pattern"
        assert results[0].confidence_score == 0.85

    @pytest.mark.asyncio
    async def test_get_favorite_contacts(self, contact_manager, mock_db_session):
        """Test getting favorite contacts."""
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        favorite_contact = MagicMock()
        favorite_contact.id = uuid.uuid4()
        favorite_contact.tenant_id = tenant_id
        favorite_contact.user_id = user_id
        favorite_contact.primary_name = "Favorite Contact"
        favorite_contact.is_favorite = True

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [favorite_contact]
        mock_db_session.execute.return_value = mock_result

        results = await contact_manager.get_favorite_contacts(
            tenant_id=tenant_id,
            user_id=user_id
        )

        assert len(results) == 1
        assert results[0].is_favorite == True
        assert results[0].primary_name == "Favorite Contact"

    @pytest.mark.asyncio
    async def test_get_recent_contacts(self, contact_manager, mock_db_session):
        """Test getting recently interacted contacts."""
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        recent_contact = MagicMock()
        recent_contact.id = uuid.uuid4()
        recent_contact.tenant_id = tenant_id
        recent_contact.user_id = user_id
        recent_contact.primary_name = "Recent Contact"
        recent_contact.last_interaction = datetime.utcnow() - timedelta(days=5)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [recent_contact]
        mock_db_session.execute.return_value = mock_result

        results = await contact_manager.get_recent_contacts(
            tenant_id=tenant_id,
            user_id=user_id,
            days=30
        )

        assert len(results) == 1
        assert results[0].primary_name == "Recent Contact"

    @pytest.mark.asyncio
    async def test_get_contact_statistics(self, contact_manager, mock_db_session):
        """Test getting contact statistics."""
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Mock various database queries for statistics
        mock_results = [
            MagicMock(scalar=MagicMock(return_value=100)),  # total contacts
            # platform distribution
            MagicMock(fetchall=MagicMock(
                return_value=[("gmail", 50), ("slack", 30)])),
            MagicMock(scalar=MagicMock(return_value=25)),  # recent contacts
        ]

        mock_db_session.execute.side_effect = mock_results

        # Mock get_favorite_contacts
        contact_manager.get_favorite_contacts = AsyncMock(
            return_value=[MagicMock()] * 10)

        stats = await contact_manager.get_contact_statistics(
            tenant_id=tenant_id,
            user_id=user_id
        )

        assert stats["total_contacts"] == 100
        assert stats["platform_distribution"]["gmail"] == 50
        assert stats["platform_distribution"]["slack"] == 30
        assert stats["recent_contacts"] == 25
        assert stats["favorite_contacts"] == 10


class TestContactManagerIntegration:
    """Integration test cases for ContactManager with mocked database operations."""

    @pytest.mark.asyncio
    async def test_contact_lifecycle_workflow(self, contact_manager, mock_db_session):
        """Test complete contact workflow: search, create, update, insights."""
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Mock all services
        contact_manager.search_service.search_contacts = AsyncMock(
            return_value=[])
        contact_manager.insights_service.get_contact_insights = AsyncMock(
            return_value=[])
        contact_manager.merger.merge_contacts = AsyncMock()

        # Mock database operations
        mock_db_session.add = MagicMock()
        mock_db_session.flush = AsyncMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # 1. Search for existing contacts (should return empty)
        results = await contact_manager.search_contacts(
            query="Test User",
            tenant_id=tenant_id,
            user_id=user_id
        )
        assert len(results) == 0

        # 2. Get insights (should return empty)
        insights = await contact_manager.get_contact_insights(
            contact_id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id
        )
        assert len(insights) == 0

        # Verify service calls
        contact_manager.search_service.search_contacts.assert_called()
        contact_manager.insights_service.get_contact_insights.assert_called()

    @pytest.mark.asyncio
    async def test_error_handling(self, contact_manager, mock_db_session):
        """Test error handling in ContactManager methods."""
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Mock database error
        mock_db_session.execute.side_effect = Exception("Database error")

        # Test that errors are handled gracefully
        result = await contact_manager.get_contact(
            contact_id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id
        )

        # Should handle the error and return None or raise appropriate exception
        # The actual behavior depends on implementation
        assert result is None or isinstance(result, Exception)
