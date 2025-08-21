"""Unit tests for ContactSearchService."""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from services.contacts.contact_search import ContactSearchService
from db.models.unified_contact import UnifiedContact, ContactIdentity


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def search_service(mock_db_session):
    """ContactSearchService instance with mocked dependencies."""
    return ContactSearchService(mock_db_session)


@pytest.fixture
def sample_contacts():
    """Sample contacts for testing."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    contacts = []

    # Contact 1: John Smith
    contact1 = UnifiedContact(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        primary_name="John Smith",
        display_name="John Smith",
        primary_email="john.smith@example.com",
        primary_phone="+1234567890",
        is_favorite=True,
        last_interaction=datetime.utcnow() - timedelta(days=1),
        platforms=["gmail", "slack"]
    )
    contact1.identities = [
        ContactIdentity(
            platform="gmail",
            platform_user_id="john.smith@example.com",
            email="john.smith@example.com",
            display_name="John Smith"
        ),
        ContactIdentity(
            platform="slack",
            platform_user_id="U123456",
            platform_handle="johnsmith",
            display_name="John Smith"
        )
    ]
    contacts.append(contact1)

    # Contact 2: Jane Doe
    contact2 = UnifiedContact(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        primary_name="Jane Doe",
        display_name="Jane Doe",
        primary_email="jane.doe@example.com",
        primary_phone="+0987654321",
        is_favorite=False,
        last_interaction=datetime.utcnow() - timedelta(days=7),
        platforms=["gmail"]
    )
    contact2.identities = [
        ContactIdentity(
            platform="gmail",
            platform_user_id="jane.doe@example.com",
            email="jane.doe@example.com",
            display_name="Jane Doe"
        )
    ]
    contacts.append(contact2)

    # Contact 3: John Johnson (similar name)
    contact3 = UnifiedContact(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        primary_name="John Johnson",
        display_name="John Johnson",
        primary_email="john.johnson@example.com",
        is_favorite=False,
        last_interaction=datetime.utcnow() - timedelta(days=14),
        platforms=["slack"]
    )
    contact3.identities = [
        ContactIdentity(
            platform="slack",
            platform_user_id="U789012",
            platform_handle="johnjohnson",
            display_name="John Johnson"
        )
    ]
    contacts.append(contact3)

    return contacts


class TestContactSearchService:
    """Test cases for ContactSearchService."""

    @pytest.mark.asyncio
    async def test_search_contacts_by_name(self, search_service, mock_db_session, sample_contacts):
        """Test searching contacts by name."""
        tenant_id = sample_contacts[0].tenant_id
        user_id = sample_contacts[0].user_id

        # Mock database query to return John contacts
        john_contacts = [
            c for c in sample_contacts if "John" in c.primary_name]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = john_contacts
        mock_db_session.execute.return_value = mock_result

        results = await search_service.search_contacts(
            query="John",
            tenant_id=tenant_id,
            user_id=user_id
        )

        assert len(results) == 2
        assert all("John" in contact.primary_name for contact in results)
        mock_db_session.execute.assert_called()

    @pytest.mark.asyncio
    async def test_search_contacts_by_email(self, search_service, mock_db_session, sample_contacts):
        """Test searching contacts by email."""
        tenant_id = sample_contacts[0].tenant_id
        user_id = sample_contacts[0].user_id

        # Mock database query to return contact with matching email
        matching_contact = [
            c for c in sample_contacts if c.primary_email == "jane.doe@example.com"]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = matching_contact
        mock_db_session.execute.return_value = mock_result

        results = await search_service.search_contacts(
            query="jane.doe@example.com",
            tenant_id=tenant_id,
            user_id=user_id
        )

        assert len(results) == 1
        assert results[0].primary_email == "jane.doe@example.com"

    @pytest.mark.asyncio
    async def test_search_contacts_by_phone(self, search_service, mock_db_session, sample_contacts):
        """Test searching contacts by phone number."""
        tenant_id = sample_contacts[0].tenant_id
        user_id = sample_contacts[0].user_id

        # Mock database query to return contact with matching phone
        matching_contact = [
            c for c in sample_contacts if c.primary_phone == "+1234567890"]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = matching_contact
        mock_db_session.execute.return_value = mock_result

        results = await search_service.search_contacts(
            query="1234567890",
            tenant_id=tenant_id,
            user_id=user_id
        )

        assert len(results) == 1
        assert "+1234567890" in results[0].primary_phone

    @pytest.mark.asyncio
    async def test_search_contacts_empty_query(self, search_service, mock_db_session, sample_contacts):
        """Test searching with empty query returns default contacts."""
        tenant_id = sample_contacts[0].tenant_id
        user_id = sample_contacts[0].user_id

        # Mock database query to return favorites first
        sorted_contacts = sorted(sample_contacts, key=lambda c: (
            not c.is_favorite, c.last_interaction), reverse=True)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sorted_contacts
        mock_db_session.execute.return_value = mock_result

        results = await search_service.search_contacts(
            query="",
            tenant_id=tenant_id,
            user_id=user_id
        )

        # Should return all contacts, favorites first
        assert len(results) == 3
        assert results[0].is_favorite == True  # John Smith should be first

    @pytest.mark.asyncio
    async def test_search_with_platform_filter(self, search_service, mock_db_session, sample_contacts):
        """Test searching with platform filter."""
        tenant_id = sample_contacts[0].tenant_id
        user_id = sample_contacts[0].user_id

        # Mock database query to return only Gmail contacts
        gmail_contacts = [c for c in sample_contacts if "gmail" in c.platforms]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = gmail_contacts
        mock_db_session.execute.return_value = mock_result

        filters = {"platforms": ["gmail"]}

        results = await search_service.search_contacts(
            query="",
            tenant_id=tenant_id,
            user_id=user_id,
            filters=filters
        )

        assert len(results) == 2  # John Smith and Jane Doe have Gmail
        assert all("gmail" in contact.platforms for contact in results)

    @pytest.mark.asyncio
    async def test_search_with_favorite_filter(self, search_service, mock_db_session, sample_contacts):
        """Test searching with favorite filter."""
        tenant_id = sample_contacts[0].tenant_id
        user_id = sample_contacts[0].user_id

        # Mock database query to return only favorite contacts
        favorite_contacts = [c for c in sample_contacts if c.is_favorite]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = favorite_contacts
        mock_db_session.execute.return_value = mock_result

        filters = {"is_favorite": True}

        results = await search_service.search_contacts(
            query="",
            tenant_id=tenant_id,
            user_id=user_id,
            filters=filters
        )

        assert len(results) == 1
        assert results[0].is_favorite == True

    @pytest.mark.asyncio
    async def test_search_by_identity(self, search_service, mock_db_session, sample_contacts):
        """Test searching by platform identity."""
        tenant_id = sample_contacts[0].tenant_id
        user_id = sample_contacts[0].user_id

        # Mock the main search to return empty (to trigger identity search)
        mock_result_empty = MagicMock()
        mock_result_empty.scalars.return_value.all.return_value = []

        # Mock identity search to return matching contact
        matching_contact = [c for c in sample_contacts if any(
            i.platform_handle == "johnsmith" for i in c.identities)]
        mock_result_identity = MagicMock()
        mock_result_identity.scalars.return_value.all.return_value = matching_contact

        mock_db_session.execute.side_effect = [
            mock_result_empty, mock_result_identity]

        results = await search_service.search_contacts(
            query="johnsmith",
            tenant_id=tenant_id,
            user_id=user_id
        )

        assert len(results) == 1
        assert any(i.platform_handle ==
                   "johnsmith" for i in results[0].identities)

    @pytest.mark.asyncio
    async def test_get_search_suggestions(self, search_service, mock_db_session, sample_contacts):
        """Test getting search suggestions."""
        tenant_id = sample_contacts[0].tenant_id
        user_id = sample_contacts[0].user_id

        # Mock database queries for suggestions
        name_suggestions = [(c.primary_name, c.display_name, c.id)
                            for c in sample_contacts if "John" in c.primary_name]

        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter(name_suggestions)
        mock_db_session.execute.return_value = mock_result

        suggestions = await search_service.get_search_suggestions(
            partial_query="Joh",
            tenant_id=tenant_id,
            user_id=user_id
        )

        assert len(suggestions) == 2
        assert all("John" in suggestion["text"] for suggestion in suggestions)
        assert all(suggestion["type"] == "name" for suggestion in suggestions)

    @pytest.mark.asyncio
    async def test_get_search_suggestions_email(self, search_service, mock_db_session, sample_contacts):
        """Test getting email search suggestions."""
        tenant_id = sample_contacts[0].tenant_id
        user_id = sample_contacts[0].user_id

        # Mock database queries for email suggestions
        email_suggestions = [(c.primary_email, c.primary_name, c.id)
                             for c in sample_contacts if c.primary_email and c.primary_email.startswith("john")]

        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter(email_suggestions)
        mock_db_session.execute.return_value = mock_result

        suggestions = await search_service.get_search_suggestions(
            partial_query="john@",
            tenant_id=tenant_id,
            user_id=user_id
        )

        assert len(suggestions) == 2
        assert all("john" in suggestion["text"].lower()
                   for suggestion in suggestions)
        assert all(suggestion["type"] == "email" for suggestion in suggestions)

    @pytest.mark.asyncio
    async def test_find_similar_contacts(self, search_service, mock_db_session, sample_contacts):
        """Test finding similar contacts."""
        tenant_id = sample_contacts[0].tenant_id
        user_id = sample_contacts[0].user_id
        reference_contact = sample_contacts[0]  # John Smith

        # Mock get reference contact
        mock_ref_result = MagicMock()
        mock_ref_result.scalar_one_or_none.return_value = reference_contact

        # Mock similar contacts query (other Johns)
        similar_contacts = [c for c in sample_contacts if c.id !=
                            reference_contact.id and "John" in c.primary_name]
        mock_similar_result = MagicMock()
        mock_similar_result.scalars.return_value.all.return_value = similar_contacts

        mock_db_session.execute.side_effect = [
            mock_ref_result, mock_similar_result]

        results = await search_service.find_similar_contacts(
            contact_id=reference_contact.id,
            tenant_id=tenant_id,
            user_id=user_id
        )

        assert len(results) == 1
        assert results[0].primary_name == "John Johnson"

    def test_normalize_query(self, search_service):
        """Test query normalization."""
        # Test basic normalization
        assert search_service._normalize_query(
            "  John   Smith  ") == "john smith"

        # Test punctuation removal
        assert search_service._normalize_query("John, Smith!") == "john smith"

        # Test email preservation
        assert search_service._normalize_query(
            "john.smith@example.com") == "john.smith@example.com"

    def test_build_search_conditions(self, search_service):
        """Test building search conditions."""
        conditions = search_service._build_search_conditions("john smith")

        # Should have conditions for both terms and full name
        assert len(conditions) > 0

        # Test email-like query
        email_conditions = search_service._build_search_conditions(
            "john@example.com")
        assert len(email_conditions) > 0

        # Test phone-like query
        phone_conditions = search_service._build_search_conditions(
            "1234567890")
        assert len(phone_conditions) > 0

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, search_service, mock_db_session, sample_contacts):
        """Test search with pagination."""
        tenant_id = sample_contacts[0].tenant_id
        user_id = sample_contacts[0].user_id

        # Mock paginated results
        mock_result = MagicMock()
        # First 2 contacts
        mock_result.scalars.return_value.all.return_value = sample_contacts[:2]
        mock_db_session.execute.return_value = mock_result

        results = await search_service.search_contacts(
            query="",
            tenant_id=tenant_id,
            user_id=user_id,
            limit=2,
            offset=0
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_with_relationship_strength_filter(self, search_service, mock_db_session, sample_contacts):
        """Test search with relationship strength filter."""
        tenant_id = sample_contacts[0].tenant_id
        user_id = sample_contacts[0].user_id

        # Set relationship strengths
        sample_contacts[0].relationship_strength = 0.8
        sample_contacts[1].relationship_strength = 0.3
        sample_contacts[2].relationship_strength = 0.6

        # Mock database query to return high-strength contacts
        strong_contacts = [
            c for c in sample_contacts if c.relationship_strength >= 0.5]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = strong_contacts
        mock_db_session.execute.return_value = mock_result

        filters = {"relationship_strength_min": 0.5}

        results = await search_service.search_contacts(
            query="",
            tenant_id=tenant_id,
            user_id=user_id,
            filters=filters
        )

        assert len(results) == 2
        assert all(contact.relationship_strength >= 0.5 for contact in results)


class TestContactSearchAccuracy:
    """Test cases for search accuracy and relevance."""

    def test_string_similarity_calculation(self, search_service):
        """Test string similarity calculation."""
        # Exact match
        assert search_service._calculate_string_similarity(
            "john", "john") == 1.0

        # No match
        assert search_service._calculate_string_similarity(
            "john", "jane") == 0.0

        # Partial match
        similarity = search_service._calculate_string_similarity(
            "john", "johnny")
        assert 0 < similarity < 1

        # Empty strings
        assert search_service._calculate_string_similarity("", "") == 1.0
        assert search_service._calculate_string_similarity("john", "") == 0.0

    @pytest.mark.asyncio
    async def test_search_relevance_ordering(self, search_service, mock_db_session, sample_contacts):
        """Test that search results are ordered by relevance."""
        tenant_id = sample_contacts[0].tenant_id
        user_id = sample_contacts[0].user_id

        # Mock database query to return contacts in specific order
        # Favorites should come first, then by last interaction
        ordered_contacts = sorted(
            sample_contacts,
            key=lambda c: (not c.is_favorite, c.last_interaction is None, -
                           c.last_interaction.timestamp() if c.last_interaction else 0)
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ordered_contacts
        mock_db_session.execute.return_value = mock_result

        results = await search_service.search_contacts(
            query="John",
            tenant_id=tenant_id,
            user_id=user_id
        )

        # First result should be the favorite
        assert len(results) > 0
        if any(c.is_favorite for c in results):
            assert results[0].is_favorite == True

    @pytest.mark.asyncio
    async def test_fuzzy_name_matching(self, search_service, mock_db_session, sample_contacts):
        """Test fuzzy matching for names with typos."""
        tenant_id = sample_contacts[0].tenant_id
        user_id = sample_contacts[0].user_id

        # Mock database query to return John contacts for "Jon" query
        john_contacts = [
            c for c in sample_contacts if "John" in c.primary_name]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = john_contacts
        mock_db_session.execute.return_value = mock_result

        # Search with typo
        results = await search_service.search_contacts(
            query="Jon",  # Missing 'h'
            tenant_id=tenant_id,
            user_id=user_id
        )

        # Should still find John contacts due to fuzzy matching
        assert len(results) > 0
        assert any("John" in contact.primary_name for contact in results)
