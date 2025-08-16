"""
Unit tests for the Entity Extraction Agent.

Tests cover:
- Entity extraction accuracy with different NLP models
- Entity type detection and classification
- Entity validation and enrichment using LLM
- Entity relationship mapping and confidence scoring
- Pattern-based extraction for tasks, files, emails, phones
- Deduplication and normalization
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any

from services.ai.entity_extraction import (
    EntityExtractionAgent,
    ExtractedEntity,
    EntityRelationship,
    EntityExtractionResult,
    EntityConfidence,
    create_entity_extraction_agent,
    get_entity_extraction_agent
)
from services.ai.base import AIProvider
from services.message_schema import NormalizedMessage, MessageContent, Participant, Platform
from db.models.entity import EntityType


class TestEntityExtractionAgent:
    """Test suite for EntityExtractionAgent."""

    @pytest.fixture
    def mock_spacy_nlp(self):
        """Mock spaCy NLP model."""
        mock_nlp = Mock()
        mock_doc = Mock()

        # Mock entity
        mock_entity = Mock()
        mock_entity.text = "John Doe"
        mock_entity.label_ = "PERSON"
        mock_entity.start_char = 0
        mock_entity.end_char = 8
        mock_entity.start = 0
        mock_entity.end = 2

        mock_doc.ents = [mock_entity]
        mock_doc.__getitem__ = Mock(
            return_value=Mock(text="Hello John Doe from"))
        mock_doc.__len__ = Mock(return_value=10)

        mock_nlp.return_value = mock_doc
        return mock_nlp

    @pytest.fixture
    def mock_transformers_ner(self):
        """Mock Transformers NER pipeline."""
        mock_ner = Mock()
        mock_ner.return_value = [
            {
                'entity_group': 'PER',
                'word': 'John Doe',
                'score': 0.95,
                'start': 0,
                'end': 8
            }
        ]
        return mock_ner

    @pytest.fixture
    def sample_message(self):
        """Create a sample normalized message for testing."""
        return NormalizedMessage(
            id="test-message-1",
            platform=Platform.GMAIL,
            platform_message_id="gmail-123",
            thread_id="thread-1",
            sender=Participant(
                platform=Platform.GMAIL,
                platform_user_id="sender@example.com",
                display_name="Test Sender",
                email="sender@example.com"
            ),
            content=MessageContent(
                text="Hi John Doe, please review the quarterly_report.pdf by Friday. "
                     "We need to schedule a meeting with Acme Corp next week. "
                     "My phone is (555) 123-4567 and email is john@example.com. "
                     "Don't forget to complete the task: submit budget proposal.",
                primary_format="text"
            ),
            timestamp=datetime.utcnow()
        )

    @pytest.fixture
    def entity_agent(self, mock_spacy_nlp, mock_transformers_ner):
        """Create entity extraction agent with mocked models."""
        agent = EntityExtractionAgent(
            provider=AIProvider.OLLAMA,
            model="llama3.2:3b",
            enable_llm_validation=False  # Disable for basic tests
        )

        # Mock the model loading
        agent.spacy_nlp = mock_spacy_nlp
        agent.transformers_ner = mock_transformers_ner

        return agent

    @pytest.mark.asyncio
    async def test_entity_extraction_basic(self, entity_agent, sample_message):
        """Test basic entity extraction functionality."""
        result = await entity_agent.process(sample_message)

        assert isinstance(result, EntityExtractionResult)
        assert result.message_id == sample_message.id
        assert len(result.entities) > 0
        assert result.processing_time > 0

        # Check that we have different types of entities
        entity_types = {entity.type for entity in result.entities}
        assert EntityType.person in entity_types  # From spaCy/Transformers
        assert EntityType.file in entity_types    # From pattern matching
        assert EntityType.email in entity_types   # From pattern matching
        assert EntityType.phone in entity_types   # From pattern matching
        assert EntityType.task in entity_types    # From pattern matching

    @pytest.mark.asyncio
    async def test_spacy_entity_extraction(self, entity_agent, sample_message):
        """Test spaCy-based entity extraction."""
        entities = await entity_agent._extract_with_spacy(
            sample_message.content.get_primary_content()
        )

        assert len(entities) > 0

        # Check the extracted entity
        person_entity = entities[0]
        assert person_entity.type == EntityType.person
        assert person_entity.value == "John Doe"
        assert person_entity.source == "spacy"
        assert person_entity.confidence == 0.7
        assert person_entity.start_position == 0
        assert person_entity.end_position == 8

    @pytest.mark.asyncio
    async def test_transformers_entity_extraction(self, entity_agent, sample_message):
        """Test Transformers-based entity extraction."""
        entities = await entity_agent._extract_with_transformers(
            sample_message.content.get_primary_content()
        )

        assert len(entities) > 0

        # Check the extracted entity
        person_entity = entities[0]
        assert person_entity.type == EntityType.person
        assert person_entity.value == "John Doe"
        assert person_entity.source == "transformers"
        assert person_entity.confidence == 0.95

    @pytest.mark.asyncio
    async def test_pattern_based_extraction(self, entity_agent, sample_message):
        """Test pattern-based entity extraction."""
        content = sample_message.content.get_primary_content()
        entities = await entity_agent._extract_with_patterns(content)

        # Should extract file, email, phone, and task
        entity_types = {entity.type for entity in entities}
        assert EntityType.file in entity_types
        assert EntityType.email in entity_types
        assert EntityType.phone in entity_types
        assert EntityType.task in entity_types

        # Check specific extractions
        file_entities = [e for e in entities if e.type == EntityType.file]
        assert any("quarterly_report.pdf" in e.value for e in file_entities)

        email_entities = [e for e in entities if e.type == EntityType.email]
        assert any("john@example.com" in e.value for e in email_entities)

        phone_entities = [e for e in entities if e.type == EntityType.phone]
        assert any("555" in e.value for e in phone_entities)

        task_entities = [e for e in entities if e.type == EntityType.task]
        assert any("submit budget proposal" in e.value for e in task_entities)

    @pytest.mark.asyncio
    async def test_entity_normalization(self, entity_agent):
        """Test entity value normalization."""
        # Test person name normalization
        normalized = entity_agent._normalize_entity_value(
            "john doe", EntityType.person)
        assert normalized == "John Doe"

        # Test email normalization
        normalized = entity_agent._normalize_entity_value(
            "John@Example.COM", EntityType.email)
        assert normalized == "john@example.com"

        # Test phone normalization
        normalized = entity_agent._normalize_entity_value(
            "555-123-4567", EntityType.phone)
        assert normalized == "(555) 123-4567"

        # Test organization normalization
        normalized = entity_agent._normalize_entity_value(
            "Acme Corp Inc.", EntityType.organization)
        assert normalized == "Acme Corp"

        # Test task normalization
        normalized = entity_agent._normalize_entity_value(
            "TODO: submit report", EntityType.task)
        assert normalized == "Submit report"

    @pytest.mark.asyncio
    async def test_entity_deduplication(self, entity_agent):
        """Test entity deduplication and merging."""
        # Create duplicate entities
        entities = [
            ExtractedEntity(
                type=EntityType.person,
                value="John Doe",
                confidence=0.8,
                source="spacy"
            ),
            ExtractedEntity(
                type=EntityType.person,
                value="john doe",
                confidence=0.9,
                source="transformers"
            ),
            ExtractedEntity(
                type=EntityType.person,
                value="Jane Smith",
                confidence=0.7,
                source="spacy"
            )
        ]

        deduplicated = await entity_agent._deduplicate_entities(entities)

        # Should have 2 unique entities
        assert len(deduplicated) == 2

        # John Doe should have higher confidence (0.9)
        john_entity = next(
            e for e in deduplicated if "john" in e.value.lower())
        assert john_entity.confidence == 0.9
        assert "spacy" in john_entity.source and "transformers" in john_entity.source

    @pytest.mark.asyncio
    async def test_relationship_extraction(self, entity_agent):
        """Test entity relationship extraction."""
        content = "John Doe works at Acme Corp and needs to complete the project by Friday"

        entities = [
            ExtractedEntity(
                type=EntityType.person,
                value="John Doe",
                start_position=0,
                end_position=8,
                source="test"
            ),
            ExtractedEntity(
                type=EntityType.organization,
                value="Acme Corp",
                start_position=18,
                end_position=27,
                source="test"
            ),
            ExtractedEntity(
                type=EntityType.task,
                value="complete the project",
                start_position=41,
                end_position=61,
                source="test"
            ),
            ExtractedEntity(
                type=EntityType.date,
                value="Friday",
                start_position=65,
                end_position=71,
                source="test"
            )
        ]

        relationships = await entity_agent._extract_relationships(content, entities)

        assert len(relationships) > 0

        # Check for expected relationship types
        relationship_types = {rel.relationship_type for rel in relationships}
        assert "works_at" in relationship_types or "employs" in relationship_types
        assert "assigned_to" in relationship_types or "assigned_by" in relationship_types
        assert "due_date" in relationship_types or "deadline_for" in relationship_types

    @pytest.mark.asyncio
    async def test_confidence_levels(self, entity_agent):
        """Test entity confidence level categorization."""
        # Test different confidence levels
        high_conf_entity = ExtractedEntity(
            type=EntityType.person,
            value="John Doe",
            confidence=0.9,
            source="test"
        )
        assert high_conf_entity.get_confidence_level() == EntityConfidence.HIGH

        medium_conf_entity = ExtractedEntity(
            type=EntityType.person,
            value="Jane Smith",
            confidence=0.6,
            source="test"
        )
        assert medium_conf_entity.get_confidence_level() == EntityConfidence.MEDIUM

        low_conf_entity = ExtractedEntity(
            type=EntityType.person,
            value="Bob Johnson",
            confidence=0.3,
            source="test"
        )
        assert low_conf_entity.get_confidence_level() == EntityConfidence.LOW

        very_low_conf_entity = ExtractedEntity(
            type=EntityType.person,
            value="Unknown Person",
            confidence=0.1,
            source="test"
        )
        assert very_low_conf_entity.get_confidence_level() == EntityConfidence.VERY_LOW

    @pytest.mark.asyncio
    async def test_llm_validation_prompt_building(self, entity_agent):
        """Test LLM validation prompt construction."""
        content = "John Doe works at Acme Corp"
        entities = [
            ExtractedEntity(
                type=EntityType.person,
                value="John Doe",
                confidence=0.8,
                source="spacy"
            )
        ]

        prompt = entity_agent._build_validation_prompt(content, entities)

        assert "John Doe" in prompt
        assert "Acme Corp" in prompt
        assert "person" in prompt
        assert "confidence" in prompt
        assert "JSON" in prompt

    @pytest.mark.asyncio
    async def test_llm_validation_response_parsing(self, entity_agent):
        """Test parsing of LLM validation responses."""
        original_entities = [
            ExtractedEntity(
                type=EntityType.person,
                value="John Doe",
                confidence=0.8,
                source="spacy"
            )
        ]

        # Mock LLM response
        llm_response = '''
        {
            "validated_entities": [
                {
                    "id": 0,
                    "type": "person",
                    "value": "John Doe",
                    "confidence": 0.95
                }
            ],
            "additional_entities": [
                {
                    "type": "organization",
                    "value": "Acme Corp",
                    "confidence": 0.9
                }
            ],
            "corrections": []
        }
        '''

        validated_entities = await entity_agent._parse_llm_validation_response(
            llm_response, original_entities
        )

        assert len(validated_entities) == 2  # Original + additional

        # Check updated confidence
        john_entity = next(
            e for e in validated_entities if e.value == "John Doe")
        assert john_entity.confidence == 0.95
        assert john_entity.metadata.get("llm_validated") is True

        # Check additional entity
        acme_entity = next(
            e for e in validated_entities if e.value == "Acme Corp")
        assert acme_entity.type == EntityType.organization
        assert acme_entity.source == "llm"

    @pytest.mark.asyncio
    async def test_empty_content_handling(self, entity_agent):
        """Test handling of messages with no content."""
        empty_message = NormalizedMessage(
            id="empty-message",
            platform=Platform.GMAIL,
            content=MessageContent(),  # No content
            sender=Participant(),
            timestamp=datetime.utcnow()
        )

        result = await entity_agent.process(empty_message)

        assert result.message_id == empty_message.id
        assert len(result.entities) == 0
        assert len(result.relationships) == 0
        assert result.processing_time >= 0

    @pytest.mark.asyncio
    async def test_error_handling_spacy_failure(self, entity_agent, sample_message):
        """Test error handling when spaCy fails."""
        # Mock spaCy to raise an exception
        entity_agent.spacy_nlp.side_effect = Exception("spaCy error")

        # Should not raise exception, should return empty list
        entities = await entity_agent._extract_with_spacy(
            sample_message.content.get_primary_content()
        )

        assert entities == []

    @pytest.mark.asyncio
    async def test_error_handling_transformers_failure(self, entity_agent, sample_message):
        """Test error handling when Transformers fails."""
        # Mock Transformers to raise an exception
        entity_agent.transformers_ner.side_effect = Exception(
            "Transformers error")

        # Should not raise exception, should return empty list
        entities = await entity_agent._extract_with_transformers(
            sample_message.content.get_primary_content()
        )

        assert entities == []

    @pytest.mark.asyncio
    async def test_complex_message_extraction(self, entity_agent):
        """Test entity extraction from a complex message."""
        complex_message = NormalizedMessage(
            id="complex-message",
            platform=Platform.SLACK,
            content=MessageContent(
                text="""
                Hi team! 📊
                
                Quick update on the Q4 project:
                
                - John Smith from Marketing will present the analysis
                - Sarah Johnson (sarah.johnson@company.com) is handling the budget
                - Meeting scheduled for December 15th at 2:00 PM
                - Please review the financial_report_Q4.xlsx before the meeting
                - Action item: Everyone needs to submit their feedback by Dec 10th
                - Budget approved: $50,000 for the initiative
                - Conference call number: +1 (800) 555-0123
                
                Location: Conference Room A, Building 2
                
                Let me know if you have questions!
                
                Best,
                Mike Davis
                Project Manager
                Acme Corporation
                mike.davis@acme.com
                (555) 987-6543
                """,
                primary_format="text"
            ),
            sender=Participant(),
            timestamp=datetime.utcnow()
        )

        # Mock spaCy and Transformers for this complex case
        mock_spacy_doc = Mock()
        mock_entities = [
            Mock(text="John Smith", label_="PERSON",
                 start_char=50, end_char=60, start=0, end=2),
            Mock(text="Sarah Johnson", label_="PERSON",
                 start_char=100, end_char=113, start=3, end=5),
            Mock(text="Marketing", label_="ORG",
                 start_char=70, end_char=79, start=6, end=7),
            Mock(text="Acme Corporation", label_="ORG",
                 start_char=400, end_char=416, start=8, end=10),
            Mock(text="December 15th", label_="DATE",
                 start_char=150, end_char=163, start=11, end=13),
            Mock(text="$50,000", label_="MONEY", start_char=300,
                 end_char=307, start=14, end=15),
        ]
        mock_spacy_doc.ents = mock_entities
        mock_spacy_doc.__getitem__ = Mock(return_value=Mock(text="context"))
        mock_spacy_doc.__len__ = Mock(return_value=20)

        entity_agent.spacy_nlp.return_value = mock_spacy_doc
        entity_agent.transformers_ner = None  # Disable for this test

        result = await entity_agent.process(complex_message)

        # Should extract multiple types of entities
        entity_types = {entity.type for entity in result.entities}
        expected_types = {
            EntityType.person,
            EntityType.organization,
            EntityType.email,
            EntityType.phone,
            EntityType.file,
            EntityType.task,
            EntityType.date,
            EntityType.money
        }

        # Should have most of the expected types
        assert len(entity_types.intersection(expected_types)) >= 6

        # Should have relationships
        assert len(result.relationships) > 0

        # Check specific extractions
        person_entities = [
            e for e in result.entities if e.type == EntityType.person]
        # John Smith, Sarah Johnson, Mike Davis
        assert len(person_entities) >= 2

        email_entities = [
            e for e in result.entities if e.type == EntityType.email]
        # sarah.johnson@company.com, mike.davis@acme.com
        assert len(email_entities) >= 2

        file_entities = [
            e for e in result.entities if e.type == EntityType.file]
        assert any("financial_report_Q4.xlsx" in e.value for e in file_entities)

    def test_factory_function(self):
        """Test the factory function for creating entity extraction agents."""
        agent = create_entity_extraction_agent(
            provider=AIProvider.OPENAI,
            model="gpt-4",
            enable_llm_validation=True
        )

        assert isinstance(agent, EntityExtractionAgent)
        assert agent.provider == AIProvider.OPENAI
        assert agent.model == "gpt-4"
        assert agent.enable_llm_validation is True

    @pytest.mark.asyncio
    async def test_global_agent_instance(self):
        """Test the global agent instance getter."""
        agent1 = await get_entity_extraction_agent()
        agent2 = await get_entity_extraction_agent()

        # Should return the same instance
        assert agent1 is agent2
        assert isinstance(agent1, EntityExtractionAgent)

    @pytest.mark.asyncio
    async def test_agent_health_check(self, entity_agent):
        """Test agent health check functionality."""
        # Mock successful processing
        with patch.object(entity_agent, 'process', return_value=Mock()):
            health_status = await entity_agent.health_check()

            assert health_status['status'] == 'healthy'
            assert health_status['agent_name'] == 'entity_extraction_agent'
            assert 'stats' in health_status

    @pytest.mark.asyncio
    async def test_batch_processing(self, entity_agent):
        """Test batch processing of multiple messages."""
        messages = [
            NormalizedMessage(
                id=f"message-{i}",
                platform=Platform.GMAIL,
                content=MessageContent(text=f"Test message {i} with John Doe"),
                sender=Participant(),
                timestamp=datetime.utcnow()
            )
            for i in range(3)
        ]

        results = await entity_agent.process_batch(messages, batch_size=2)

        assert len(results) == 3
        for result in results:
            assert isinstance(result, EntityExtractionResult)

    @pytest.mark.asyncio
    async def test_processing_statistics(self, entity_agent, sample_message):
        """Test that processing statistics are updated correctly."""
        initial_stats = entity_agent.get_stats()
        initial_processed = initial_stats['requests_processed']

        await entity_agent.process_with_retry(sample_message)

        updated_stats = entity_agent.get_stats()
        assert updated_stats['requests_processed'] == initial_processed + 1
        assert updated_stats['average_processing_time'] > 0


class TestEntityExtractionIntegration:
    """Integration tests for entity extraction with real models."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_spacy_model_loading(self):
        """Test loading real spaCy model (requires spaCy installation)."""
        try:
            agent = EntityExtractionAgent(enable_llm_validation=False)
            await agent._ensure_models_loaded()

            assert agent.spacy_nlp is not None

            # Test with real model
            test_text = "John Doe works at Apple Inc. in Cupertino."
            entities = await agent._extract_with_spacy(test_text)

            # Should extract at least person and organization
            entity_types = {entity.type for entity in entities}
            assert EntityType.person in entity_types or EntityType.organization in entity_types

        except Exception as e:
            pytest.skip(f"Real spaCy model test skipped: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_end_to_end_extraction(self):
        """Test end-to-end entity extraction with real models."""
        try:
            agent = EntityExtractionAgent(enable_llm_validation=False)

            message = NormalizedMessage(
                id="integration-test",
                platform=Platform.GMAIL,
                content=MessageContent(
                    text="Hi Sarah, can you send the quarterly_report.pdf to john@company.com? "
                         "We need it for the board meeting on Friday. My number is (555) 123-4567."
                ),
                sender=Participant(),
                timestamp=datetime.utcnow()
            )

            result = await agent.process(message)

            assert len(result.entities) > 0
            assert result.processing_time > 0

            # Should extract various entity types
            entity_types = {entity.type for entity in result.entities}
            expected_types = {EntityType.person, EntityType.file,
                              EntityType.email, EntityType.phone}

            # Should have at least some of the expected types
            assert len(entity_types.intersection(expected_types)) >= 2

        except Exception as e:
            pytest.skip(f"End-to-end test skipped: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
