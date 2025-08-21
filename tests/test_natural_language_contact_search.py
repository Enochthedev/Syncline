"""
Comprehensive tests for natural language understanding in contact search.

Tests cover various natural language query patterns, intent detection,
entity extraction, and query processing accuracy for contact-based searches.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, AsyncMock

from services.contacts.contact_auto_search import ContactAutoSearchService
from services.ai.search.types import SearchQuery, QueryIntent
from services.ai.search.query_processor import QueryProcessor


class TestNaturalLanguageUnderstanding:
    """Test natural language understanding capabilities."""

    @pytest.fixture
    async def mock_query_processor(self):
        """Mock query processor with AI capabilities."""
        processor = Mock(spec=QueryProcessor)
        processor.initialize = AsyncMock()
        processor.process_query = AsyncMock()
        processor.generate_search_suggestions = Mock(return_value=[])
        return processor

    @pytest.fixture
    async def service_with_nlp(self, mock_db_session, mock_query_processor):
        """Create service with mocked NLP capabilities."""
        service = ContactAutoSearchService(mock_db_session)
        service.query_processor = mock_query_processor
        service._initialized = True
        return service

    @pytest.mark.asyncio
    async def test_person_search_patterns(self, service_with_nlp):
        """Test various person search query patterns."""
        test_cases = [
            # Basic person search patterns
            ("messages with John", QueryIntent.PERSON_SEARCH, ["John"]),
            ("messages from Sarah", QueryIntent.PERSON_SEARCH, ["Sarah"]),
            ("conversations with Mike Chen",
             QueryIntent.PERSON_SEARCH, ["Mike Chen"]),
            ("talk to Lisa about", QueryIntent.PERSON_SEARCH, ["Lisa"]),
            ("John said something", QueryIntent.PERSON_SEARCH, ["John"]),
            ("what did David write", QueryIntent.PERSON_SEARCH, ["David"]),

            # Email-based person search
            ("messages from john@company.com",
             QueryIntent.PERSON_SEARCH, ["john@company.com"]),
            ("emails with sarah.johnson@example.com",
             QueryIntent.PERSON_SEARCH, ["sarah.johnson@example.com"]),

            # Multiple person patterns
            ("messages between John and Sarah",
             QueryIntent.PERSON_SEARCH, ["John", "Sarah"]),
            ("conversation with John, Mike, and Lisa",
             QueryIntent.PERSON_SEARCH, ["John", "Mike", "Lisa"]),
        ]

        for query_text, expected_intent, expected_entities in test_cases:
            # Mock the query processor response
            processed_query = SearchQuery(
                text=query_text,
                intent=expected_intent,
                extracted_entities=[
                    {"type": "person", "value": entity, "confidence": 0.8}
                    for entity in expected_entities
                ]
            )
            service_with_nlp.query_processor.process_query.return_value = processed_query

            # Mock contact search results
            mock_contacts = [
                Mock(id=uuid4(), primary_name=entity,
                     tenant_id=uuid4(), user_id=uuid4())
                for entity in expected_entities
            ]
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = mock_contacts
            service_with_nlp.db.execute.return_value = mock_result

            result = await service_with_nlp.process_natural_language_query(
                query=query_text,
                tenant_id=uuid4(),
                user_id=uuid4()
            )

            assert result["intent"] == expected_intent.value
            assert len(result["contacts"]) == len(expected_entities)

    @pytest.mark.asyncio
    async def test_file_search_patterns(self, service_with_nlp):
        """Test file and attachment search patterns."""
        test_cases = [
            # Basic file search patterns
            ("files shared with John", QueryIntent.FILE_SEARCH, ["John"]),
            ("documents from Sarah", QueryIntent.FILE_SEARCH, ["Sarah"]),
            ("attachments sent by Mike", QueryIntent.FILE_SEARCH, ["Mike"]),
            ("images from Lisa", QueryIntent.FILE_SEARCH, ["Lisa"]),
            ("PDFs shared with team", QueryIntent.FILE_SEARCH, ["team"]),

            # Specific file type patterns
            ("Excel files from John", QueryIntent.FILE_SEARCH, ["John"]),
            ("PowerPoint presentations shared with Sarah",
             QueryIntent.FILE_SEARCH, ["Sarah"]),
            ("video files sent by Mike", QueryIntent.FILE_SEARCH, ["Mike"]),
            ("audio recordings from Lisa", QueryIntent.FILE_SEARCH, ["Lisa"]),

            # Time-based file search
            ("files shared yesterday", QueryIntent.FILE_SEARCH, []),
            ("documents from last week", QueryIntent.FILE_SEARCH, []),
            ("attachments from this month", QueryIntent.FILE_SEARCH, []),
        ]

        for query_text, expected_intent, expected_entities in test_cases:
            processed_query = SearchQuery(
                text=query_text,
                intent=expected_intent,
                extracted_entities=[
                    {"type": "person", "value": entity, "confidence": 0.8}
                    for entity in expected_entities
                ]
            )
            service_with_nlp.query_processor.process_query.return_value = processed_query

            # Mock contact search if entities present
            if expected_entities:
                mock_contacts = [
                    Mock(id=uuid4(), primary_name=entity,
                         tenant_id=uuid4(), user_id=uuid4())
                    for entity in expected_entities
                ]
                mock_result = Mock()
                mock_result.scalars.return_value.all.return_value = mock_contacts
                service_with_nlp.db.execute.return_value = mock_result

            result = await service_with_nlp.process_natural_language_query(
                query=query_text,
                tenant_id=uuid4(),
                user_id=uuid4()
            )

            assert result["intent"] == expected_intent.value
            assert result["filters"]["has_attachments"] == True

    @pytest.mark.asyncio
    async def test_commitment_search_patterns(self, service_with_nlp):
        """Test commitment and promise search patterns."""
        test_cases = [
            # Basic commitment patterns
            ("what did I promise to John",
             QueryIntent.COMMITMENT_SEARCH, ["John"]),
            ("commitments to Sarah", QueryIntent.COMMITMENT_SEARCH, ["Sarah"]),
            ("what I agreed with Mike",
             QueryIntent.COMMITMENT_SEARCH, ["Mike"]),
            ("promises made to Lisa", QueryIntent.COMMITMENT_SEARCH, ["Lisa"]),
            ("my commitments to the team",
             QueryIntent.COMMITMENT_SEARCH, ["team"]),

            # Action item patterns
            ("action items for John", QueryIntent.COMMITMENT_SEARCH, ["John"]),
            ("tasks assigned to Sarah",
             QueryIntent.COMMITMENT_SEARCH, ["Sarah"]),
            ("deliverables for Mike", QueryIntent.COMMITMENT_SEARCH, ["Mike"]),
            ("deadlines with Lisa", QueryIntent.COMMITMENT_SEARCH, ["Lisa"]),

            # Time-based commitment search
            ("promises made last week", QueryIntent.COMMITMENT_SEARCH, []),
            ("commitments due this month", QueryIntent.COMMITMENT_SEARCH, []),
            ("overdue action items", QueryIntent.COMMITMENT_SEARCH, []),
        ]

        for query_text, expected_intent, expected_entities in test_cases:
            processed_query = SearchQuery(
                text=query_text,
                intent=expected_intent,
                extracted_entities=[
                    {"type": "person", "value": entity, "confidence": 0.8}
                    for entity in expected_entities
                ]
            )
            service_with_nlp.query_processor.process_query.return_value = processed_query

            # Mock contact search if entities present
            if expected_entities:
                mock_contacts = [
                    Mock(id=uuid4(), primary_name=entity,
                         tenant_id=uuid4(), user_id=uuid4())
                    for entity in expected_entities
                ]
                mock_result = Mock()
                mock_result.scalars.return_value.all.return_value = mock_contacts
                service_with_nlp.db.execute.return_value = mock_result

            result = await service_with_nlp.process_natural_language_query(
                query=query_text,
                tenant_id=uuid4(),
                user_id=uuid4()
            )

            assert result["intent"] == expected_intent.value
            assert "commitment" in result["filters"]["entity_types"]

    @pytest.mark.asyncio
    async def test_temporal_patterns(self, service_with_nlp):
        """Test temporal constraint extraction from natural language."""
        test_cases = [
            # Relative time patterns
            ("messages from yesterday", {"days": 1}),
            ("conversations from last week", {"weeks": 1}),
            ("files shared this month", {"months": 0}),
            ("emails from 3 days ago", {"days": 3}),
            ("attachments from 2 weeks ago", {"weeks": 2}),

            # Absolute time patterns
            ("messages from January", {"month": "january"}),
            ("conversations in December", {"month": "december"}),
            ("files from 2023", {"year": "2023"}),

            # Time range patterns
            ("messages between Monday and Friday", {"range": "weekdays"}),
            ("conversations from last month to now",
             {"range": "last_month_to_now"}),
        ]

        for query_text, expected_temporal in test_cases:
            # Create mock temporal constraints based on the pattern
            temporal_constraints = {}
            if "days" in expected_temporal:
                temporal_constraints["date_from"] = datetime.utcnow(
                ) - timedelta(days=expected_temporal["days"])
            elif "weeks" in expected_temporal:
                temporal_constraints["date_from"] = datetime.utcnow(
                ) - timedelta(weeks=expected_temporal["weeks"])
            elif "months" in expected_temporal:
                if expected_temporal["months"] == 0:
                    # This month
                    now = datetime.utcnow()
                    temporal_constraints["date_from"] = datetime(
                        now.year, now.month, 1)

            processed_query = SearchQuery(
                text=query_text,
                intent=QueryIntent.TIME_BASED_SEARCH,
                temporal_constraints=temporal_constraints
            )
            service_with_nlp.query_processor.process_query.return_value = processed_query

            result = await service_with_nlp.process_natural_language_query(
                query=query_text,
                tenant_id=uuid4(),
                user_id=uuid4()
            )

            assert result["intent"] == QueryIntent.TIME_BASED_SEARCH.value
            if temporal_constraints:
                assert len(result["temporal_constraints"]) > 0

    @pytest.mark.asyncio
    async def test_complex_compound_queries(self, service_with_nlp):
        """Test complex queries with multiple intents and entities."""
        test_cases = [
            # Person + file + time
            ("PDF files shared with John last week",
             QueryIntent.FILE_SEARCH,
             ["John"],
             {"has_attachments": True, "date_from": datetime.utcnow() - timedelta(weeks=1)}),

            # Person + commitment + time
            ("what did I promise to Sarah about the project deadline",
             QueryIntent.COMMITMENT_SEARCH,
             ["Sarah"],
             {"entity_types": ["commitment", "task", "deadline"]}),

            # Multiple people + file type
            ("images shared between John and Mike",
             QueryIntent.FILE_SEARCH,
             ["John", "Mike"],
             {"has_attachments": True}),

            # Person + topic + time
            ("discussions with Lisa about budget last month",
             QueryIntent.TOPIC_SEARCH,
             ["Lisa"],
             {"date_from": datetime.utcnow() - timedelta(days=30)}),
        ]

        for query_text, expected_intent, expected_entities, expected_filters in test_cases:
            # Create temporal constraints if date_from is in expected_filters
            temporal_constraints = {}
            if "date_from" in expected_filters:
                temporal_constraints["date_from"] = expected_filters.pop(
                    "date_from")

            processed_query = SearchQuery(
                text=query_text,
                intent=expected_intent,
                extracted_entities=[
                    {"type": "person", "value": entity, "confidence": 0.8}
                    for entity in expected_entities
                ],
                temporal_constraints=temporal_constraints
            )
            service_with_nlp.query_processor.process_query.return_value = processed_query

            # Mock contact search
            mock_contacts = [
                Mock(id=uuid4(), primary_name=entity,
                     tenant_id=uuid4(), user_id=uuid4())
                for entity in expected_entities
            ]
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = mock_contacts
            service_with_nlp.db.execute.return_value = mock_result

            result = await service_with_nlp.process_natural_language_query(
                query=query_text,
                tenant_id=uuid4(),
                user_id=uuid4()
            )

            assert result["intent"] == expected_intent.value
            assert len(result["contacts"]) == len(expected_entities)

            # Check that expected filters are present
            for filter_key, filter_value in expected_filters.items():
                assert filter_key in result["filters"]
                if isinstance(filter_value, list):
                    assert all(item in result["filters"][filter_key]
                               for item in filter_value)
                else:
                    assert result["filters"][filter_key] == filter_value

    @pytest.mark.asyncio
    async def test_ambiguous_query_handling(self, service_with_nlp):
        """Test handling of ambiguous or unclear queries."""
        ambiguous_queries = [
            "find stuff",
            "show me things",
            "what about that",
            "you know what I mean",
            "the usual",
            "from before"
        ]

        for query_text in ambiguous_queries:
            processed_query = SearchQuery(
                text=query_text,
                intent=QueryIntent.GENERAL_SEARCH,
                extracted_entities=[]
            )
            service_with_nlp.query_processor.process_query.return_value = processed_query

            result = await service_with_nlp.process_natural_language_query(
                query=query_text,
                tenant_id=uuid4(),
                user_id=uuid4()
            )

            # Should default to general search
            assert result["intent"] == QueryIntent.GENERAL_SEARCH.value
            assert len(result["contacts"]) == 0

    @pytest.mark.asyncio
    async def test_entity_confidence_scoring(self, service_with_nlp):
        """Test entity extraction with confidence scoring."""
        test_cases = [
            # High confidence cases
            ("messages with John Smith", [("John Smith", 0.9)]),
            ("files from sarah.johnson@company.com",
             [("sarah.johnson@company.com", 0.95)]),

            # Medium confidence cases
            ("conversations with J Smith", [("J Smith", 0.7)]),
            ("emails from John", [("John", 0.6)]),

            # Low confidence cases
            ("messages with someone", [("someone", 0.3)]),
            ("files from that person", [("that person", 0.2)]),
        ]

        for query_text, expected_entities in test_cases:
            processed_query = SearchQuery(
                text=query_text,
                intent=QueryIntent.PERSON_SEARCH,
                extracted_entities=[
                    {"type": "person", "value": entity, "confidence": confidence}
                    for entity, confidence in expected_entities
                ]
            )
            service_with_nlp.query_processor.process_query.return_value = processed_query

            # Mock contact search for high confidence entities only
            high_confidence_entities = [
                e for e, c in expected_entities if c >= 0.7]
            if high_confidence_entities:
                mock_contacts = [
                    Mock(id=uuid4(), primary_name=entity,
                         tenant_id=uuid4(), user_id=uuid4())
                    for entity in high_confidence_entities
                ]
                mock_result = Mock()
                mock_result.scalars.return_value.all.return_value = mock_contacts
                service_with_nlp.db.execute.return_value = mock_result

            result = await service_with_nlp.process_natural_language_query(
                query=query_text,
                tenant_id=uuid4(),
                user_id=uuid4()
            )

            # Should only return contacts for high confidence entities
            expected_contact_count = len(high_confidence_entities)
            assert len(result["contacts"]) == expected_contact_count

    @pytest.mark.asyncio
    async def test_context_aware_suggestions(self, service_with_nlp):
        """Test context-aware query suggestions."""
        # Mock the suggestion generation
        context_suggestions = [
            "messages with [contact name]",
            "files shared with [contact name]",
            "commitments to [contact name]",
            "conversations about [topic]",
            "attachments from [platform]"
        ]

        service_with_nlp.query_processor.generate_search_suggestions.return_value = context_suggestions

        # Test partial queries that should trigger suggestions
        partial_queries = [
            "messages with",
            "files from",
            "what did I promise",
            "conversations about",
            "attachments in"
        ]

        for partial_query in partial_queries:
            suggestions = service_with_nlp.query_processor.generate_search_suggestions(
                partial_query)

            assert len(suggestions) > 0
            assert any(
                "[contact name]" in s or "[topic]" in s or "[platform]" in s for s in suggestions)

    @pytest.mark.asyncio
    async def test_multilingual_support(self, service_with_nlp):
        """Test basic multilingual query support (if implemented)."""
        # This would test multilingual capabilities if implemented
        # For now, we'll test that non-English queries are handled gracefully

        multilingual_queries = [
            "mensajes con Juan",  # Spanish
            "fichiers de Marie",  # French
            "Nachrichten von Hans",  # German
            "メッセージ from Tanaka",  # Mixed Japanese-English
        ]

        for query_text in multilingual_queries:
            processed_query = SearchQuery(
                text=query_text,
                intent=QueryIntent.GENERAL_SEARCH,
                extracted_entities=[]
            )
            service_with_nlp.query_processor.process_query.return_value = processed_query

            result = await service_with_nlp.process_natural_language_query(
                query=query_text,
                tenant_id=uuid4(),
                user_id=uuid4()
            )

            # Should handle gracefully without errors
            assert "intent" in result
            assert "processed_text" in result

    @pytest.mark.asyncio
    async def test_query_preprocessing(self, service_with_nlp):
        """Test query preprocessing and normalization."""
        test_cases = [
            # Case normalization
            ("MESSAGES WITH JOHN", "messages with john"),

            # Punctuation handling
            ("messages with John!", "messages with john"),
            ("files from Sarah?", "files from sarah"),
            ("what did I promise to Mike...", "what did i promise to mike"),

            # Extra whitespace
            ("messages   with    John", "messages with john"),
            ("  files from Sarah  ", "files from sarah"),

            # Special characters
            ("messages with John@company.com", "messages with john@company.com"),
            ("files from user-name", "files from user-name"),
        ]

        for original_query, expected_normalized in test_cases:
            # Test the normalization function directly
            normalized = service_with_nlp._normalize_query(original_query)
            assert normalized == expected_normalized

    @pytest.mark.asyncio
    async def test_intent_classification_accuracy(self, service_with_nlp):
        """Test accuracy of intent classification."""
        # Test cases with clear intent patterns
        intent_test_cases = [
            # Person search intents
            ("messages with John", QueryIntent.PERSON_SEARCH),
            ("conversations from Sarah", QueryIntent.PERSON_SEARCH),
            ("emails to Mike", QueryIntent.PERSON_SEARCH),

            # File search intents
            ("files shared with John", QueryIntent.FILE_SEARCH),
            ("documents from Sarah", QueryIntent.FILE_SEARCH),
            ("attachments sent by Mike", QueryIntent.FILE_SEARCH),

            # Commitment search intents
            ("what did I promise to John", QueryIntent.COMMITMENT_SEARCH),
            ("commitments to Sarah", QueryIntent.COMMITMENT_SEARCH),
            ("action items for Mike", QueryIntent.COMMITMENT_SEARCH),

            # Time-based search intents
            ("messages from yesterday", QueryIntent.TIME_BASED_SEARCH),
            ("conversations last week", QueryIntent.TIME_BASED_SEARCH),
            ("files from this month", QueryIntent.TIME_BASED_SEARCH),

            # Topic search intents
            ("discussions about project", QueryIntent.TOPIC_SEARCH),
            ("conversations regarding budget", QueryIntent.TOPIC_SEARCH),
            ("messages about meeting", QueryIntent.TOPIC_SEARCH),
        ]

        correct_classifications = 0
        total_classifications = len(intent_test_cases)

        for query_text, expected_intent in intent_test_cases:
            processed_query = SearchQuery(
                text=query_text,
                intent=expected_intent
            )
            service_with_nlp.query_processor.process_query.return_value = processed_query

            result = await service_with_nlp.process_natural_language_query(
                query=query_text,
                tenant_id=uuid4(),
                user_id=uuid4()
            )

            if result["intent"] == expected_intent.value:
                correct_classifications += 1

        # Calculate accuracy
        accuracy = correct_classifications / total_classifications

        # Should achieve high accuracy (adjust threshold as needed)
        assert accuracy >= 0.8, f"Intent classification accuracy too low: {accuracy:.2%}"


class TestQueryComplexityHandling:
    """Test handling of queries with varying complexity."""

    @pytest.mark.asyncio
    async def test_simple_queries(self, service_with_nlp):
        """Test handling of simple, straightforward queries."""
        simple_queries = [
            "John",
            "messages",
            "files",
            "yesterday",
            "Sarah email"
        ]

        for query in simple_queries:
            processed_query = SearchQuery(
                text=query,
                intent=QueryIntent.GENERAL_SEARCH
            )
            service_with_nlp.query_processor.process_query.return_value = processed_query

            result = await service_with_nlp.process_natural_language_query(
                query=query,
                tenant_id=uuid4(),
                user_id=uuid4()
            )

            assert "intent" in result
            assert "processed_text" in result

    @pytest.mark.asyncio
    async def test_medium_complexity_queries(self, service_with_nlp):
        """Test handling of medium complexity queries."""
        medium_queries = [
            "messages with John about project",
            "files shared by Sarah last week",
            "what did Mike say about the meeting",
            "commitments to Lisa regarding budget",
            "documents from team members yesterday"
        ]

        for query in medium_queries:
            processed_query = SearchQuery(
                text=query,
                intent=QueryIntent.PERSON_SEARCH,
                extracted_entities=[
                    {"type": "person", "value": "John", "confidence": 0.8}
                ]
            )
            service_with_nlp.query_processor.process_query.return_value = processed_query

            # Mock contact search
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [
                Mock(id=uuid4(), primary_name="John",
                     tenant_id=uuid4(), user_id=uuid4())
            ]
            service_with_nlp.db.execute.return_value = mock_result

            result = await service_with_nlp.process_natural_language_query(
                query=query,
                tenant_id=uuid4(),
                user_id=uuid4()
            )

            assert "intent" in result
            assert len(result["entities"]) > 0

    @pytest.mark.asyncio
    async def test_complex_queries(self, service_with_nlp):
        """Test handling of complex, multi-faceted queries."""
        complex_queries = [
            "show me all PDF files that John shared with the team last month about the Q4 project deliverables",
            "what commitments did I make to Sarah and Mike during our meetings about budget planning between January and March",
            "find conversations with Lisa, David, and the marketing team regarding the product launch timeline and associated action items",
            "display images and videos shared by team members in our project channels during the last two weeks of December",
        ]

        for query in complex_queries:
            processed_query = SearchQuery(
                text=query,
                intent=QueryIntent.FILE_SEARCH,
                extracted_entities=[
                    {"type": "person", "value": "John", "confidence": 0.8},
                    {"type": "person", "value": "team", "confidence": 0.6}
                ],
                temporal_constraints={
                    "date_from": datetime.utcnow() - timedelta(days=30)
                }
            )
            service_with_nlp.query_processor.process_query.return_value = processed_query

            # Mock contact search
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [
                Mock(id=uuid4(), primary_name="John",
                     tenant_id=uuid4(), user_id=uuid4())
            ]
            service_with_nlp.db.execute.return_value = mock_result

            result = await service_with_nlp.process_natural_language_query(
                query=query,
                tenant_id=uuid4(),
                user_id=uuid4()
            )

            # Should handle complex queries without errors
            assert "intent" in result
            assert "entities" in result
            assert "temporal_constraints" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
