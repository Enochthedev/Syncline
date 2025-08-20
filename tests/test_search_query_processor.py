"""
Unit tests for the Search Query Processor.

Tests natural language query processing, intent detection,
and entity extraction functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from services.ai.search.query_processor import QueryProcessor
from services.ai.search.types import SearchQuery, QueryIntent, SearchFilters


class TestQueryProcessor:
    """Test suite for QueryProcessor."""

    @pytest.fixture
    def processor(self):
        """Create a query processor for testing."""
        processor = QueryProcessor()
        processor.ai_engine = None  # Use basic mode for testing
        return processor

    @pytest.fixture
    def processor_with_ai(self):
        """Create a query processor with mocked AI engine."""
        processor = QueryProcessor()
        processor.ai_engine = Mock()
        processor.ai_engine.generate_text = AsyncMock()
        return processor

    def test_intent_detection_commitment_queries(self, processor):
        """Test intent detection for commitment-related queries."""
        test_cases = [
            ("what did I promise John", QueryIntent.COMMITMENT_SEARCH),
            ("my commitments to the team", QueryIntent.COMMITMENT_SEARCH),
            ("what am I supposed to deliver", QueryIntent.COMMITMENT_SEARCH),
            ("deadline for the project", QueryIntent.COMMITMENT_SEARCH),
            ("I agreed to help with", QueryIntent.COMMITMENT_SEARCH),
        ]

        for query_text, expected_intent in test_cases:
            detected_intent = processor._detect_intent(query_text)
            assert detected_intent == expected_intent, f"Failed for: {query_text}"

    def test_intent_detection_person_queries(self, processor):
        """Test intent detection for person-related queries."""
        test_cases = [
            ("messages from Alice", QueryIntent.PERSON_SEARCH),
            ("conversation with Bob", QueryIntent.PERSON_SEARCH),
            ("John said something", QueryIntent.PERSON_SEARCH),
            ("talk to Sarah about", QueryIntent.PERSON_SEARCH),
            ("messages to team@company.com", QueryIntent.PERSON_SEARCH),
        ]

        for query_text, expected_intent in test_cases:
            detected_intent = processor._detect_intent(query_text)
            assert detected_intent == expected_intent, f"Failed for: {query_text}"

    def test_intent_detection_time_queries(self, processor):
        """Test intent detection for time-based queries."""
        test_cases = [
            ("yesterday", QueryIntent.TIME_BASED_SEARCH),
            ("last week's discussion", QueryIntent.TIME_BASED_SEARCH),
            ("before 2024-01-15", QueryIntent.TIME_BASED_SEARCH),
            ("3 days ago", QueryIntent.TIME_BASED_SEARCH),
            ("in January", QueryIntent.TIME_BASED_SEARCH),
        ]

        for query_text, expected_intent in test_cases:
            detected_intent = processor._detect_intent(query_text)
            assert detected_intent == expected_intent, f"Failed for: {query_text}"

    def test_intent_detection_file_queries(self, processor):
        """Test intent detection for file-related queries."""
        test_cases = [
            ("files shared with team", QueryIntent.FILE_SEARCH),
            ("shared attachments", QueryIntent.FILE_SEARCH),
            ("documents sent", QueryIntent.FILE_SEARCH),
            ("image files in chat", QueryIntent.FILE_SEARCH),
        ]

        for query_text, expected_intent in test_cases:
            detected_intent = processor._detect_intent(query_text)
            assert detected_intent == expected_intent, f"Failed for: {query_text}"

    def test_intent_detection_topic_queries(self, processor):
        """Test intent detection for topic-related queries."""
        test_cases = [
            ("about the project", QueryIntent.TOPIC_SEARCH),
            ("regarding the meeting", QueryIntent.TOPIC_SEARCH),
            ("discussion on budget", QueryIntent.TOPIC_SEARCH),
            ("project Alpha updates", QueryIntent.TOPIC_SEARCH),
        ]

        for query_text, expected_intent in test_cases:
            detected_intent = processor._detect_intent(query_text)
            assert detected_intent == expected_intent, f"Failed for: {query_text}"

    def test_intent_detection_general_fallback(self, processor):
        """Test fallback to general search for ambiguous queries."""
        test_cases = [
            "hello world",
            "random text here",
            "search everything",
            "find information",
            "help me",
        ]

        for query_text in test_cases:
            detected_intent = processor._detect_intent(query_text)
            assert detected_intent == QueryIntent.GENERAL_SEARCH, f"Failed for: {query_text}"

    @pytest.mark.asyncio
    async def test_entity_extraction_basic(self, processor):
        """Test basic entity extraction without AI."""
        query_text = "Send the report to John Smith at john@company.com"

        entities = await processor._extract_entities(query_text)

        # Should extract person name and email
        person_entities = [e for e in entities if e["type"] == "person"]
        email_entities = [e for e in entities if e["type"] == "email"]

        assert len(person_entities) >= 1
        assert len(email_entities) == 1
        assert email_entities[0]["value"] == "john@company.com"

    @pytest.mark.asyncio
    async def test_entity_extraction_with_ai(self, processor_with_ai):
        """Test entity extraction with AI engine."""
        query_text = "Discuss the Q4 budget with the marketing team"

        # Mock AI response
        processor_with_ai.ai_engine.generate_text.return_value = """
        person: marketing team
        topic: Q4 budget
        organization: marketing team
        """

        entities = await processor_with_ai._extract_entities(query_text)

        # Should have basic entities plus AI-extracted ones
        assert len(entities) > 0

        # Verify AI was called
        processor_with_ai.ai_engine.generate_text.assert_called_once()

    def test_temporal_constraint_extraction(self, processor):
        """Test extraction of temporal constraints from queries."""
        test_cases = [
            ("messages from yesterday", "yesterday"),
            ("last week's updates", "last week"),
            ("3 days ago discussion", "3 days ago"),
            ("this week's meetings", "this week"),
        ]

        for query_text, expected_temporal in test_cases:
            constraints = processor._extract_temporal_constraints(query_text)

            # Should extract some temporal constraint
            assert len(
                constraints) > 0, f"No temporal constraints found for: {query_text}"

            if "date_from" in constraints:
                assert isinstance(constraints["date_from"], datetime)

    def test_temporal_constraint_date_ranges(self, processor):
        """Test extraction of date range constraints."""
        query_text = "messages between 2024-01-01 and 2024-01-31"

        constraints = processor._extract_temporal_constraints(query_text)

        assert "date_from" in constraints
        assert "date_to" in constraints
        assert constraints["date_from"] < constraints["date_to"]

    def test_query_text_processing(self, processor):
        """Test query text cleaning and processing."""
        test_cases = [
            ("Find the messages about project", "find messages about project"),
            ("Show me all files from John", "show all files from john"),
            ("What did I say to the team?", "what did say team?"),
            ("A very long query with many stop words",
             "very long query many stop words"),
        ]

        for original, expected in test_cases:
            processed = processor._process_query_text(original)
            assert processed == expected, f"Processing failed for: {original}"

    @pytest.mark.asyncio
    async def test_intent_enhancement_commitment_search(self, processor):
        """Test intent-specific query enhancements for commitment search."""
        query = SearchQuery(
            text="what did I promise",
            intent=QueryIntent.COMMITMENT_SEARCH
        )

        enhanced_query = await processor._apply_intent_enhancements(query)

        assert enhanced_query.filters is not None
        assert "commitment" in enhanced_query.filters.entity_types
        assert "task" in enhanced_query.filters.entity_types
        assert "deadline" in enhanced_query.filters.entity_types

    @pytest.mark.asyncio
    async def test_intent_enhancement_person_search(self, processor):
        """Test intent-specific query enhancements for person search."""
        query = SearchQuery(
            text="messages from John",
            intent=QueryIntent.PERSON_SEARCH,
            extracted_entities=[
                {"type": "person", "value": "John", "confidence": 0.9}
            ]
        )

        enhanced_query = await processor._apply_intent_enhancements(query)

        assert enhanced_query.filters is not None
        assert enhanced_query.filters.participants == ["John"]

    @pytest.mark.asyncio
    async def test_intent_enhancement_file_search(self, processor):
        """Test intent-specific query enhancements for file search."""
        query = SearchQuery(
            text="shared files",
            intent=QueryIntent.FILE_SEARCH
        )

        enhanced_query = await processor._apply_intent_enhancements(query)

        assert enhanced_query.filters is not None
        assert enhanced_query.filters.has_attachments is True

    @pytest.mark.asyncio
    async def test_intent_enhancement_time_search(self, processor):
        """Test intent-specific query enhancements for time-based search."""
        yesterday = datetime.utcnow() - timedelta(days=1)

        query = SearchQuery(
            text="messages from yesterday",
            intent=QueryIntent.TIME_BASED_SEARCH,
            temporal_constraints={"date_from": yesterday}
        )

        enhanced_query = await processor._apply_intent_enhancements(query)

        assert enhanced_query.filters is not None
        assert enhanced_query.filters.date_from is not None
        assert enhanced_query.filters.date_from.date() == yesterday.date()

    @pytest.mark.asyncio
    async def test_full_query_processing_pipeline(self, processor):
        """Test the complete query processing pipeline."""
        query = SearchQuery(
            text="What files did John share last week?",
            limit=20
        )

        processed_query = await processor.process_query(query)

        # Verify all processing steps were applied
        assert processed_query.intent is not None
        assert processed_query.processed_text is not None
        assert processed_query.extracted_entities is not None
        assert processed_query.temporal_constraints is not None

        # Should detect as file search with person and time elements
        assert processed_query.intent in [
            QueryIntent.FILE_SEARCH,
            QueryIntent.PERSON_SEARCH,
            QueryIntent.TIME_BASED_SEARCH
        ]

    def test_search_suggestions_generation(self, processor):
        """Test generation of search suggestions."""
        test_cases = [
            ("promise", ["commitments from last week",
             "promises to [person name]"]),
            ("file", ["files shared with [person]",
             "documents from [platform]"]),
            ("who", ["messages from [person]", "conversations with [person]"]),
        ]

        for query_text, expected_suggestions in test_cases:
            suggestions = processor.generate_search_suggestions(query_text)

            assert len(suggestions) > 0
            assert len(suggestions) <= 5  # Should limit to 5 suggestions

            # Check if any expected suggestions are present
            suggestion_text = " ".join(suggestions).lower()
            for expected in expected_suggestions:
                if "[" not in expected:  # Skip template suggestions
                    assert expected.lower() in suggestion_text

    def test_search_suggestions_limit(self, processor):
        """Test that search suggestions are limited to reasonable number."""
        # Use a query that might generate many suggestions
        suggestions = processor.generate_search_suggestions(
            "project meeting file person")

        assert len(suggestions) <= 5
        assert all(isinstance(s, str) for s in suggestions)
        assert all(len(s) > 0 for s in suggestions)

    @pytest.mark.asyncio
    async def test_error_handling_in_processing(self, processor):
        """Test error handling during query processing."""
        # Create a query that might cause issues
        query = SearchQuery(text="")  # Empty query

        # Should not raise exception, should return original query
        processed_query = await processor.process_query(query)

        assert processed_query is not None
        assert processed_query.text == ""

    @pytest.mark.asyncio
    async def test_entity_confidence_scoring(self, processor):
        """Test that extracted entities have appropriate confidence scores."""
        query_text = "Send email to john@company.com and call Jane Smith"

        entities = await processor._extract_entities(query_text)

        for entity in entities:
            assert "confidence" in entity
            assert 0.0 <= entity["confidence"] <= 1.0

            # Email addresses should have high confidence
            if entity["type"] == "email":
                assert entity["confidence"] >= 0.8

    def test_temporal_parsing_edge_cases(self, processor):
        """Test temporal parsing with edge cases."""
        edge_cases = [
            "sometime yesterday maybe",  # Ambiguous
            "in the future",  # Vague
            "2024-13-45",  # Invalid date
            "last week or so",  # Approximate
        ]

        for query_text in edge_cases:
            # Should not crash, may or may not extract constraints
            constraints = processor._extract_temporal_constraints(query_text)
            assert isinstance(constraints, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
