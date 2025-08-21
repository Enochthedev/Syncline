"""
Comprehensive tests for contact-based auto-search functionality.

Tests cover search accuracy, performance, natural language understanding,
fuzzy matching, and all aspects of the intelligent contact search system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from services.contacts.contact_auto_search import ContactAutoSearchService
from services.ai.search.types import SearchQuery, QueryIntent
from db.models.unified_contact import UnifiedContact, ContactIdentity
from db.models.message import Message
from db.models.thread import Thread
from db.models.participant import Participant
from db.models.attachment import Attachment


class TestContactAutoSearchService:
    """Test suite for ContactAutoSearchService."""

    @pytest.fixture
    async def mock_db_session(self):
        """Mock database session."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    async def service(self, mock_db_session):
        """Create ContactAutoSearchService instance."""
        service = ContactAutoSearchService(mock_db_session)
        service.query_processor = Mock()
        service.query_processor.initialize = AsyncMock()
        service.query_processor.process_query = AsyncMock()
        service.query_processor.generate_search_suggestions = Mock(
            return_value=[])
        service._initialized = True
        return service

    @pytest.fixture
    def sample_contact(self):
        """Create sample contact for testing."""
        contact = UnifiedContact(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            primary_name="John Smith",
            display_name="John Smith",
            primary_email="john.smith@example.com",
            primary_phone="+1-555-0123",
            last_interaction=datetime.utcnow() - timedelta(days=2),
            total_messages=150,
            platforms=["gmail", "slack"],
            relationship_strength=0.8,
            communication_frequency="frequent",
            is_favorite=True,
            tags=["work", "important"]
        )

        # Add identities
        contact.identities = [
            ContactIdentity(
                id=uuid4(),
                unified_contact_id=contact.id,
                platform="gmail",
                platform_user_id="john.smith@example.com",
                display_name="John Smith",
                email="john.smith@example.com",
                is_verified=True
            ),
            ContactIdentity(
                id=uuid4(),
                unified_contact_id=contact.id,
                platform="slack",
                platform_user_id="U123456789",
                platform_handle="johnsmith",
                display_name="John Smith",
                is_verified=True
            )
        ]

        return contact

    @pytest.fixture
    def sample_contacts_list(self, sample_contact):
        """Create list of sample contacts."""
        contacts = [sample_contact]

        # Add more contacts for comprehensive testing
        for i in range(5):
            contact = UnifiedContact(
                id=uuid4(),
                tenant_id=sample_contact.tenant_id,
                user_id=sample_contact.user_id,
                primary_name=f"Contact {i}",
                display_name=f"Contact {i}",
                primary_email=f"contact{i}@example.com",
                last_interaction=datetime.utcnow() - timedelta(days=i+1),
                total_messages=50 - i*10,
                platforms=["gmail"],
                relationship_strength=0.5 + i*0.1,
                communication_frequency="regular",
                is_favorite=i < 2
            )
            contact.identities = [
                ContactIdentity(
                    id=uuid4(),
                    unified_contact_id=contact.id,
                    platform="gmail",
                    platform_user_id=f"contact{i}@example.com",
                    display_name=f"Contact {i}",
                    email=f"contact{i}@example.com"
                )
            ]
            contacts.append(contact)

        return contacts


class TestRealTimeContactSearch:
    """Test real-time contact search functionality."""

    @pytest.mark.asyncio
    async def test_search_contacts_realtime_basic(self, service, sample_contacts_list):
        """Test basic real-time contact search."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = sample_contacts_list[:3]
        service.db.execute.return_value = mock_result

        # Test search
        result = await service.search_contacts_realtime(
            query="John",
            tenant_id=sample_contacts_list[0].tenant_id,
            user_id=sample_contacts_list[0].user_id,
            limit=10
        )

        # Verify results
        assert "contacts" in result
        assert "suggestions" in result
        assert "query" in result
        assert result["query"] == "John"
        assert result["normalized_query"] == "john"
        assert len(result["contacts"]) <= 10

    @pytest.mark.asyncio
    async def test_fuzzy_matching_names(self, service, sample_contact):
        """Test fuzzy matching for contact names."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_contact]
        service.db.execute.return_value = mock_result

        # Test various fuzzy queries
        test_queries = [
            "Jon Smith",      # Typo in first name
            "John Smth",      # Missing letter
            "J Smith",        # Abbreviated first name
            "Smith",          # Last name only
            "john smith"      # Case insensitive
        ]

        for query in test_queries:
            result = await service.search_contacts_realtime(
                query=query,
                tenant_id=sample_contact.tenant_id,
                user_id=sample_contact.user_id,
                limit=10
            )

            assert len(result["contacts"]
                       ) > 0, f"No results for query: {query}"

    @pytest.mark.asyncio
    async def test_email_search(self, service, sample_contact):
        """Test contact search by email address."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_contact]
        service.db.execute.return_value = mock_result

        # Test email search
        result = await service.search_contacts_realtime(
            query="john.smith@example.com",
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id,
            limit=10
        )

        assert len(result["contacts"]) > 0
        assert result["contacts"][0]["primary_email"] == "john.smith@example.com"

    @pytest.mark.asyncio
    async def test_phone_search(self, service, sample_contact):
        """Test contact search by phone number."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_contact]
        service.db.execute.return_value = mock_result

        # Test phone search with different formats
        phone_queries = [
            "+1-555-0123",
            "555-0123",
            "5550123",
            "(555) 012-3"
        ]

        for query in phone_queries:
            result = await service.search_contacts_realtime(
                query=query,
                tenant_id=sample_contact.tenant_id,
                user_id=sample_contact.user_id,
                limit=10
            )

            assert len(result["contacts"]
                       ) > 0, f"No results for phone query: {query}"

    @pytest.mark.asyncio
    async def test_platform_handle_search(self, service, sample_contact):
        """Test search by platform handles."""
        # Mock database response for identity search
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_contact]
        service.db.execute.return_value = mock_result

        # Test platform handle search
        result = await service.search_contacts_realtime(
            query="johnsmith",
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id,
            limit=10
        )

        assert len(result["contacts"]) > 0

    @pytest.mark.asyncio
    async def test_empty_query_default_suggestions(self, service, sample_contacts_list):
        """Test default suggestions for empty/short queries."""
        # Mock favorite and recent contacts
        favorites = [c for c in sample_contacts_list if c.is_favorite]
        recent = sample_contacts_list[:3]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = favorites
        service.db.execute.return_value = mock_result

        # Test short query
        result = await service.search_contacts_realtime(
            query="a",  # Too short
            tenant_id=sample_contacts_list[0].tenant_id,
            user_id=sample_contacts_list[0].user_id,
            limit=10
        )

        assert "suggestions" in result
        assert len(result["suggestions"]) > 0

    @pytest.mark.asyncio
    async def test_contact_enrichment(self, service, sample_contact):
        """Test contact result enrichment with interaction indicators."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_contact]
        service.db.execute.return_value = mock_result

        result = await service.search_contacts_realtime(
            query="John",
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id,
            limit=10
        )

        contact_data = result["contacts"][0]

        # Verify enrichment data
        assert "recent_interaction" in contact_data
        assert "platform_distribution" in contact_data
        assert "interaction_indicators" in contact_data

        # Check interaction indicators
        indicators = contact_data["interaction_indicators"]
        assert "has_recent_messages" in indicators
        assert "is_frequent_contact" in indicators
        assert "has_unread_messages" in indicators


class TestNaturalLanguageProcessing:
    """Test natural language query processing."""

    @pytest.mark.asyncio
    async def test_person_search_intent(self, service, sample_contact):
        """Test detection of person search intent."""
        # Mock query processor
        processed_query = SearchQuery(
            text="messages with John Smith",
            intent=QueryIntent.PERSON_SEARCH,
            extracted_entities=[
                {"type": "person", "value": "John Smith", "confidence": 0.9}
            ]
        )
        service.query_processor.process_query.return_value = processed_query

        # Mock contact search
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_contact]
        service.db.execute.return_value = mock_result

        result = await service.process_natural_language_query(
            query="messages with John Smith",
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id
        )

        assert result["intent"] == "person_search"
        assert len(result["contacts"]) > 0
        assert result["contacts"][0]["contact"]["primary_name"] == "John Smith"

    @pytest.mark.asyncio
    async def test_file_search_intent(self, service, sample_contact):
        """Test detection of file search intent."""
        processed_query = SearchQuery(
            text="files shared with John",
            intent=QueryIntent.FILE_SEARCH,
            extracted_entities=[
                {"type": "person", "value": "John", "confidence": 0.8}
            ]
        )
        service.query_processor.process_query.return_value = processed_query

        # Mock contact search
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_contact]
        service.db.execute.return_value = mock_result

        result = await service.process_natural_language_query(
            query="files shared with John",
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id
        )

        assert result["intent"] == "file_search"
        assert result["filters"]["has_attachments"] == True

    @pytest.mark.asyncio
    async def test_commitment_search_intent(self, service, sample_contact):
        """Test detection of commitment search intent."""
        processed_query = SearchQuery(
            text="what did I promise to John",
            intent=QueryIntent.COMMITMENT_SEARCH,
            extracted_entities=[
                {"type": "person", "value": "John", "confidence": 0.8}
            ]
        )
        service.query_processor.process_query.return_value = processed_query

        # Mock contact search
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_contact]
        service.db.execute.return_value = mock_result

        result = await service.process_natural_language_query(
            query="what did I promise to John",
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id
        )

        assert result["intent"] == "commitment_search"
        assert "commitment" in result["filters"]["entity_types"]

    @pytest.mark.asyncio
    async def test_temporal_constraint_extraction(self, service, sample_contact):
        """Test extraction of temporal constraints."""
        from datetime import datetime, timedelta

        processed_query = SearchQuery(
            text="messages with John last week",
            intent=QueryIntent.PERSON_SEARCH,
            temporal_constraints={
                "date_from": datetime.utcnow() - timedelta(weeks=1)
            },
            extracted_entities=[
                {"type": "person", "value": "John", "confidence": 0.8}
            ]
        )
        service.query_processor.process_query.return_value = processed_query

        # Mock contact search
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_contact]
        service.db.execute.return_value = mock_result

        result = await service.process_natural_language_query(
            query="messages with John last week",
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id
        )

        assert "date_from" in result["temporal_constraints"]


class TestContactMessageSearch:
    """Test contact-filtered message search."""

    @pytest.fixture
    def sample_messages(self, sample_contact):
        """Create sample messages for testing."""
        messages = []
        for i in range(10):
            message = Message(
                id=uuid4(),
                tenant_id=sample_contact.tenant_id,
                platform="gmail",
                platform_message_id=f"msg_{i}",
                thread_id=uuid4(),
                sender_id=uuid4(),
                content_text=f"This is message {i} content",
                timestamp=datetime.utcnow() - timedelta(hours=i),
                attachments=[]
            )

            # Add mock thread and sender
            message.thread = Thread(
                id=message.thread_id,
                tenant_id=sample_contact.tenant_id,
                platform="gmail",
                platform_thread_id=f"thread_{i}",
                title=f"Thread {i}"
            )

            message.sender = Participant(
                id=message.sender_id,
                tenant_id=sample_contact.tenant_id,
                platform="gmail",
                platform_user_id="john.smith@example.com",
                display_name="John Smith"
            )

            messages.append(message)

        return messages

    @pytest.mark.asyncio
    async def test_search_messages_by_contact(self, service, sample_contact, sample_messages):
        """Test searching messages by contact."""
        # Mock contact retrieval
        contact_result = Mock()
        contact_result.scalar_one_or_none.return_value = sample_contact

        # Mock message search
        message_result = Mock()
        message_result.scalars.return_value.all.return_value = sample_messages[:5]

        service.db.execute.side_effect = [contact_result, message_result]

        result = await service.search_messages_by_contact(
            contact_id=sample_contact.id,
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id,
            query="content",
            limit=10,
            group_by_thread=False
        )

        assert "messages" in result
        assert "contact" in result
        assert len(result["messages"]) > 0
        assert result["contact"]["id"] == str(sample_contact.id)

    @pytest.mark.asyncio
    async def test_thread_grouping(self, service, sample_contact, sample_messages):
        """Test message grouping by conversation threads."""
        # Mock contact retrieval
        contact_result = Mock()
        contact_result.scalar_one_or_none.return_value = sample_contact

        # Mock message search
        message_result = Mock()
        message_result.scalars.return_value.all.return_value = sample_messages

        service.db.execute.side_effect = [contact_result, message_result]

        result = await service.search_messages_by_contact(
            contact_id=sample_contact.id,
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id,
            group_by_thread=True
        )

        assert "threads" in result
        assert len(result["threads"]) > 0

        # Check thread structure
        thread = result["threads"][0]
        assert "thread_id" in thread
        assert "latest_message" in thread
        assert "message_count" in thread
        assert "messages" in thread

    @pytest.mark.asyncio
    async def test_message_preview_creation(self, service):
        """Test message content preview creation."""
        # Test various content types
        test_cases = [
            ("This is a short message", "This is a short message"),
            ("This is a very long message that should be truncated because it exceeds the maximum length limit for previews and should end with ellipsis",
             "This is a very long message that should be truncated because it exceeds the maximum length limit for previews and should end..."),
            ("   Multiple   spaces   should   be   normalized   ",
             "Multiple spaces should be normalized"),
            ("", ""),
            (None, "")
        ]

        for content, expected in test_cases:
            preview = service._create_message_preview(content)
            assert preview == expected

    @pytest.mark.asyncio
    async def test_contact_not_found(self, service, sample_contact):
        """Test handling when contact is not found."""
        # Mock contact not found
        contact_result = Mock()
        contact_result.scalar_one_or_none.return_value = None
        service.db.execute.return_value = contact_result

        result = await service.search_messages_by_contact(
            contact_id=uuid4(),  # Non-existent contact
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id
        )

        assert result["contact"] is None
        assert "error" in result
        assert result["error"] == "Contact not found"


class TestSharedContentSearch:
    """Test shared content search functionality."""

    @pytest.fixture
    def sample_attachments(self, sample_contact):
        """Create sample attachments for testing."""
        attachments = []

        # File attachments
        for i in range(3):
            attachment = Attachment(
                id=uuid4(),
                message_id=uuid4(),
                filename=f"document_{i}.pdf",
                content_type="application/pdf",
                file_size=1024 * (i + 1),
                file_path=f"/attachments/document_{i}.pdf"
            )

            # Add mock message
            attachment.message = Message(
                id=attachment.message_id,
                tenant_id=sample_contact.tenant_id,
                platform="gmail",
                platform_message_id=f"msg_{i}",
                thread_id=uuid4(),
                sender_id=uuid4(),
                timestamp=datetime.utcnow() - timedelta(days=i)
            )

            attachments.append(attachment)

        # Media attachments
        for i in range(2):
            attachment = Attachment(
                id=uuid4(),
                message_id=uuid4(),
                filename=f"image_{i}.jpg",
                content_type="image/jpeg",
                file_size=2048 * (i + 1),
                file_path=f"/attachments/image_{i}.jpg"
            )

            attachment.message = Message(
                id=attachment.message_id,
                tenant_id=sample_contact.tenant_id,
                platform="gmail",
                platform_message_id=f"img_msg_{i}",
                thread_id=uuid4(),
                sender_id=uuid4(),
                timestamp=datetime.utcnow() - timedelta(days=i)
            )

            attachments.append(attachment)

        return attachments

    @pytest.mark.asyncio
    async def test_get_shared_files(self, service, sample_contact, sample_attachments):
        """Test getting shared files with contact."""
        # Mock contact retrieval
        contact_result = Mock()
        contact_result.scalar_one_or_none.return_value = sample_contact

        # Mock file attachments
        file_attachments = [
            att for att in sample_attachments if att.content_type.startswith("application/")]
        file_result = Mock()
        file_result.scalars.return_value.all.return_value = file_attachments

        # Mock media attachments
        media_attachments = [
            att for att in sample_attachments if att.content_type.startswith("image/")]
        media_result = Mock()
        media_result.scalars.return_value.all.return_value = media_attachments

        # Mock links (empty for now)
        links_result = Mock()
        links_result.scalars.return_value.all.return_value = []

        service.db.execute.side_effect = [
            contact_result, file_result, media_result]

        result = await service.get_shared_content_with_contact(
            contact_id=sample_contact.id,
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id
        )

        assert "shared_files" in result
        assert "shared_media" in result
        assert "shared_links" in result
        assert "contact" in result
        assert len(result["shared_files"]) > 0
        assert len(result["shared_media"]) > 0

    @pytest.mark.asyncio
    async def test_content_type_filtering(self, service, sample_contact, sample_attachments):
        """Test filtering by content type."""
        # Mock contact retrieval
        contact_result = Mock()
        contact_result.scalar_one_or_none.return_value = sample_contact

        # Mock filtered results
        filtered_result = Mock()
        filtered_result.scalars.return_value.all.return_value = sample_attachments[:2]

        service.db.execute.side_effect = [
            contact_result, filtered_result, Mock(), Mock()]

        result = await service.get_shared_content_with_contact(
            contact_id=sample_contact.id,
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id,
            content_type="files"
        )

        assert "shared_files" in result


class TestSearchSuggestions:
    """Test search suggestion functionality."""

    @pytest.mark.asyncio
    async def test_name_suggestions(self, service, sample_contacts_list):
        """Test name-based search suggestions."""
        # Mock database response
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (contact.primary_name, contact.display_name, contact.id)
            for contact in sample_contacts_list[:3]
        ]
        service.db.execute.return_value = mock_result

        suggestions = await service._get_name_suggestions(
            query="Jo",
            tenant_id=sample_contacts_list[0].tenant_id,
            user_id=sample_contacts_list[0].user_id,
            limit=5
        )

        assert len(suggestions) > 0
        assert all(s["type"] == "name" for s in suggestions)

    @pytest.mark.asyncio
    async def test_platform_suggestions(self, service, sample_contacts_list):
        """Test platform-specific suggestions."""
        # Mock database response
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ("johnsmith", "slack", "John Smith", sample_contacts_list[0].id)
        ]
        service.db.execute.return_value = mock_result

        suggestions = await service._get_platform_suggestions(
            query="john",
            tenant_id=sample_contacts_list[0].tenant_id,
            user_id=sample_contacts_list[0].user_id,
            limit=5
        )

        assert len(suggestions) > 0
        assert all(s["type"] == "handle" for s in suggestions)
        assert all(s["text"].startswith("@") for s in suggestions)


class TestPerformanceAndAccuracy:
    """Test search performance and accuracy."""

    @pytest.mark.asyncio
    async def test_search_performance(self, service, sample_contacts_list):
        """Test search response time performance."""
        import time

        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = sample_contacts_list
        service.db.execute.return_value = mock_result

        start_time = time.time()

        result = await service.search_contacts_realtime(
            query="John",
            tenant_id=sample_contacts_list[0].tenant_id,
            user_id=sample_contacts_list[0].user_id,
            limit=50
        )

        end_time = time.time()
        response_time = end_time - start_time

        # Should respond within reasonable time (adjust threshold as needed)
        assert response_time < 1.0, f"Search took too long: {response_time}s"
        assert len(result["contacts"]) > 0

    @pytest.mark.asyncio
    async def test_fuzzy_matching_accuracy(self, service, sample_contact):
        """Test accuracy of fuzzy matching algorithm."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_contact]
        service.db.execute.return_value = mock_result

        # Test cases with expected match quality
        test_cases = [
            ("John Smith", True),      # Exact match
            ("Jon Smith", True),       # Single character typo
            ("John Smth", True),       # Missing character
            ("J Smith", True),         # Abbreviated first name
            ("Smith", True),           # Last name only
            ("john smith", True),      # Case insensitive
            ("xyz", False),            # No match expected
        ]

        for query, should_match in test_cases:
            result = await service.search_contacts_realtime(
                query=query,
                tenant_id=sample_contact.tenant_id,
                user_id=sample_contact.user_id,
                limit=10
            )

            has_results = len(result["contacts"]) > 0
            assert has_results == should_match, f"Query '{query}' match expectation failed"

    @pytest.mark.asyncio
    async def test_large_dataset_handling(self, service):
        """Test handling of large contact datasets."""
        # Create large mock dataset
        large_dataset = []
        tenant_id = uuid4()
        user_id = uuid4()

        for i in range(1000):
            contact = UnifiedContact(
                id=uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                primary_name=f"Contact {i:04d}",
                display_name=f"Contact {i:04d}",
                primary_email=f"contact{i:04d}@example.com"
            )
            large_dataset.append(contact)

        # Mock database response with pagination
        mock_result = Mock()
        # Simulate limit
        mock_result.scalars.return_value.all.return_value = large_dataset[:50]
        service.db.execute.return_value = mock_result

        result = await service.search_contacts_realtime(
            query="Contact",
            tenant_id=tenant_id,
            user_id=user_id,
            limit=50
        )

        assert len(result["contacts"]) == 50
        assert result["has_more"] == True


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_database_error_handling(self, service, sample_contact):
        """Test handling of database errors."""
        # Mock database error
        service.db.execute.side_effect = Exception(
            "Database connection failed")

        result = await service.search_contacts_realtime(
            query="John",
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id,
            limit=10
        )

        assert "error" in result
        assert result["contacts"] == []

    @pytest.mark.asyncio
    async def test_invalid_input_handling(self, service, sample_contact):
        """Test handling of invalid inputs."""
        # Test empty query
        result = await service.search_contacts_realtime(
            query="",
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id,
            limit=10
        )

        # Should return default suggestions
        assert "suggestions" in result
        assert result["total_results"] == 0

    @pytest.mark.asyncio
    async def test_service_initialization_failure(self, mock_db_session):
        """Test handling of service initialization failure."""
        service = ContactAutoSearchService(mock_db_session)
        service.query_processor.initialize.side_effect = Exception(
            "AI engine failed")

        # Should handle initialization failure gracefully
        try:
            await service.initialize()
            assert False, "Should have raised exception"
        except Exception as e:
            assert "AI engine failed" in str(e)

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, service, sample_contacts_list):
        """Test handling of concurrent search requests."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = sample_contacts_list
        service.db.execute.return_value = mock_result

        # Create multiple concurrent requests
        tasks = []
        for i in range(10):
            task = service.search_contacts_realtime(
                query=f"Contact {i}",
                tenant_id=sample_contacts_list[0].tenant_id,
                user_id=sample_contacts_list[0].user_id,
                limit=10
            )
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All requests should complete successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert "contacts" in result


# Integration test fixtures and utilities
@pytest.fixture
def integration_test_data():
    """Create comprehensive test data for integration tests."""
    tenant_id = uuid4()
    user_id = uuid4()

    # Create contacts with various characteristics
    contacts = []

    # Primary test contact
    john = UnifiedContact(
        id=uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        primary_name="John Smith",
        display_name="John Smith",
        primary_email="john.smith@company.com",
        primary_phone="+1-555-0123",
        last_interaction=datetime.utcnow() - timedelta(days=1),
        total_messages=250,
        platforms=["gmail", "slack", "teams"],
        relationship_strength=0.9,
        communication_frequency="daily",
        is_favorite=True,
        tags=["work", "manager", "important"]
    )
    contacts.append(john)

    # Add more diverse contacts for comprehensive testing
    test_contacts = [
        ("Sarah Johnson", "sarah.j@company.com", ["gmail"], "frequent", False),
        ("Mike Chen", "mike.chen@company.com",
         ["slack", "teams"], "regular", True),
        ("Lisa Rodriguez", "lisa.r@company.com",
         ["gmail", "whatsapp"], "occasional", False),
        ("David Kim", "david.kim@company.com", ["teams"], "rare", False),
    ]

    for name, email, platforms, freq, favorite in test_contacts:
        contact = UnifiedContact(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            primary_name=name,
            display_name=name,
            primary_email=email,
            platforms=platforms,
            communication_frequency=freq,
            is_favorite=favorite,
            last_interaction=datetime.utcnow() - timedelta(days=len(contacts))
        )
        contacts.append(contact)

    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "contacts": contacts
    }


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
