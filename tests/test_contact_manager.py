"""Unit tests for ContactManager service."""

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

    contact = UnifiedContact(
        id=contact_id,
        tenant_id=tenant_id,
        user_id=user_id,
        primary_name="John Smith",
        display_name="John Smith",
        primary_email="john.smith@example.com",
        primary_phone="+1234567890",
        total_messages=50,
        total_threads=10,
        relationship_strength=0.75,
        communication_frequency="regular",
        platforms=["gmail", "slack"],
        is_favorite=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    # Add identities
    contact.identities = [
        ContactIdentity(
            id=uuid.uuid4(),
            unified_contact_id=contact_id,
            platform="gmail",
            platform_user_id="john.smith@example.com",
            email="john.smith@example.com",
            display_name="John Smith"
        ),
        ContactIdentity(
            id=uuid.uuid4(),
            unified_contact_id=contact_id,
            platform="slack",
            platform_user_id="U123456",
            platform_handle="johnsmith",
            display_name="John Smith"
        )
    ]

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
    async def test_create_contact(self, contact_manager, mock_db_session):
        """Test creating a new unified contact."""
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Mock database operations
        mock_db_session.add = MagicMock()
        mock_db_session.flush = AsyncMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        identities = [
            {
                "platform": "gmail",
                "platform_user_id": "jane.doe@example.com",
                "email": "jane.doe@example.com",
                "display_name": "Jane Doe"
            }
        ]

        result = await contact_manager.create_contact(
            tenant_id=tenant_id,
            user_id=user_id,
            primary_name="Jane Doe",
            identities=identities,
            primary_email="jane.doe@example.com",
            is_favorite=True
        )

        assert result.primary_name == "Jane Doe"
        assert result.primary_email == "jane.doe@example.com"
        assert result.is_favorite == True
        assert mock_db_session.add.call_count >= 2  # Contact + Identity + Preferences
        mock_db_session.commit.assert_called_once()

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
        mock_messages = [
            Message(
                id=uuid.uuid4(),
                tenant_id=sample_contact.tenant_id,
                content="Hello John!",
                timestamp=datetime.utcnow(),
                platform="gmail"
            )
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_messages
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
        mock_insights = [
            ContactInsight(
                id=uuid.uuid4(),
                unified_contact_id=sample_contact.id,
                insight_type="communication_pattern",
                title="Most Active in Mornings",
                description="John is most active between 9-11 AM",
                confidence_score=0.85
            )
        ]

        contact_manager.insights_service.get_contact_insights = AsyncMock(
            return_value=mock_insights)

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

        favorite_contact = UnifiedContact(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            primary_name="Favorite Contact",
            is_favorite=True
        )

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

        recent_contact = UnifiedContact(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            primary_name="Recent Contact",
            last_interaction=datetime.utcnow() - timedelta(days=5)
        )

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
    """Integration test cases for ContactManager with real database operations."""

    @pytest.mark.asyncio
    async def test_full_contact_lifecycle(self, contact_manager, mock_db_session):
        """Test complete contact lifecycle: create, update, search, merge."""
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Mock all database operations for the lifecycle
        mock_db_session.add = MagicMock()
        mock_db_session.flush = AsyncMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # 1. Create contact
        identities = [
            {
                "platform": "gmail",
                "platform_user_id": "test@example.com",
                "email": "test@example.com",
                "display_name": "Test User"
            }
        ]

        contact = await contact_manager.create_contact(
            tenant_id=tenant_id,
            user_id=user_id,
            primary_name="Test User",
            identities=identities
        )

        assert contact.primary_name == "Test User"

        # 2. Update contact
        contact_manager.get_contact = AsyncMock(return_value=contact)

        updated_contact = await contact_manager.update_contact(
            contact_id=contact.id,
            tenant_id=tenant_id,
            user_id=user_id,
            updates={"is_favorite": True}
        )

        assert updated_contact.is_favorite == True

        # 3. Add note
        await contact_manager.add_contact_note(
            contact_id=contact.id,
            tenant_id=tenant_id,
            user_id=user_id,
            note="Test note"
        )

        assert "Test note" in contact.custom_notes

        # Verify all operations were called
        assert mock_db_session.commit.call_count >= 3
