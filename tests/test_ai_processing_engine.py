"""
Unit tests for AI processing engine and related services.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from services.ai_processing_engine import (
    AIProcessingEngine, MessageProcessor, ProcessingType, ProcessingResult, ProcessingStatus
)
from services.ai_base import AIProvider, BaseAIAgent
from services.message_schema import (
    NormalizedMessage, MessageContent, Participant, Platform, ContentType
)


class TestMessageProcessor:
    """Test cases for MessageProcessor."""

    @pytest.fixture
    def message_processor(self):
        """Create a MessageProcessor instance for testing."""
        return MessageProcessor(provider=AIProvider.OPENAI, model="gpt-4")

    @pytest.fixture
    def sample_message(self):
        """Create a sample normalized message for testing."""
        sender = Participant(
            platform=Platform.GMAIL,
            platform_user_id="test@example.com",
            display_name="Test User",
            email="test@example.com"
        )

        content = MessageContent(
            text="This is a test message about project planning and deadlines.",
            primary_format=ContentType.TEXT
        )

        return NormalizedMessage(
            platform=Platform.GMAIL,
            platform_message_id="test_msg_123",
            thread_id="test_thread_123",
            sender=sender,
            content=content,
            timestamp=datetime.utcnow()
        )

    def test_initialization(self, message_processor):
        """Test MessageProcessor initialization."""
        assert message_processor.name == "message_processor"
        assert message_processor.provider == AIProvider.OPENAI
        assert message_processor.model == "gpt-4"
        assert message_processor.stats['requests_processed'] == 0

    @pytest.mark.asyncio
    async def test_process_message_summarization(self, message_processor, sample_message):
        """Test message processing with summarization."""
        # Mock the LLM provider
        with patch.object(message_processor, '_get_llm_provider') as mock_provider:
            mock_llm = AsyncMock()
            mock_llm.generate_completion.return_value = "Test summary of the message"
            mock_provider.return_value = mock_llm

            # Mock PII redaction service
            with patch('services.ai_processing_engine.get_pii_redaction_service') as mock_pii:
                mock_pii_service = AsyncMock()
                mock_redaction_result = Mock()
                mock_redaction_result.redacted_text = sample_message.content.text
                mock_redaction_result.entities = []
                mock_pii_service.redact_text.return_value = mock_redaction_result
                mock_pii.return_value = mock_pii_service

                result = await message_processor.process_message(
                    sample_message, ProcessingType.SUMMARIZATION
                )

                assert result['processing_type'] == 'summarization'
                assert result['result'] == "Test summary of the message"
                assert result['pii_redacted'] is False
                assert 'original_length' in result
                assert 'processed_length' in result

    @pytest.mark.asyncio
    async def test_process_message_entity_extraction(self, message_processor, sample_message):
        """Test message processing with entity extraction."""
        with patch.object(message_processor, '_get_llm_provider') as mock_provider:
            mock_llm = AsyncMock()
            mock_llm.generate_completion.return_value = '{"entities": ["project", "deadlines"]}'
            mock_provider.return_value = mock_llm

            with patch('services.ai_processing_engine.get_pii_redaction_service') as mock_pii:
                mock_pii_service = AsyncMock()
                mock_redaction_result = Mock()
                mock_redaction_result.redacted_text = sample_message.content.text
                mock_redaction_result.entities = []
                mock_pii_service.redact_text.return_value = mock_redaction_result
                mock_pii.return_value = mock_pii_service

                result = await message_processor.process_message(
                    sample_message, ProcessingType.ENTITY_EXTRACTION
                )

                assert result['processing_type'] == 'entity_extraction'
                assert 'entities' in result['result']

    @pytest.mark.asyncio
    async def test_process_text(self, message_processor):
        """Test text processing."""
        test_text = "This is a test text for processing."

        with patch.object(message_processor, '_get_llm_provider') as mock_provider:
            mock_llm = AsyncMock()
            mock_llm.generate_completion.return_value = "Processed text result"
            mock_provider.return_value = mock_llm

            with patch('services.ai_processing_engine.get_pii_redaction_service') as mock_pii:
                mock_pii_service = AsyncMock()
                mock_redaction_result = Mock()
                mock_redaction_result.redacted_text = test_text
                mock_redaction_result.entities = []
                mock_pii_service.redact_text.return_value = mock_redaction_result
                mock_pii.return_value = mock_pii_service

                result = await message_processor.process_text(
                    test_text, ProcessingType.SUMMARIZATION
                )

                assert result == "Processed text result"

    @pytest.mark.asyncio
    async def test_process_with_custom_prompt(self, message_processor):
        """Test text processing with custom prompt."""
        test_text = "Custom text"
        custom_prompt = "Please analyze this text carefully:"

        with patch.object(message_processor, '_get_llm_provider') as mock_provider:
            mock_llm = AsyncMock()
            mock_llm.generate_completion.return_value = "Custom analysis result"
            mock_provider.return_value = mock_llm

            with patch('services.ai_processing_engine.get_pii_redaction_service') as mock_pii:
                mock_pii_service = AsyncMock()
                mock_redaction_result = Mock()
                mock_redaction_result.redacted_text = test_text
                mock_redaction_result.entities = []
                mock_pii_service.redact_text.return_value = mock_redaction_result
                mock_pii.return_value = mock_pii_service

                result = await message_processor.process_text(
                    test_text, ProcessingType.CUSTOM, custom_prompt=custom_prompt
                )

                assert result == "Custom analysis result"
                # Verify the prompt was constructed correctly
                mock_llm.generate_completion.assert_called_once()
                call_args = mock_llm.generate_completion.call_args
                assert custom_prompt in call_args[1]['prompt']

    def test_build_message_prompt_summarization(self, message_processor, sample_message):
        """Test prompt building for summarization."""
        content = sample_message.content.text
        prompt = message_processor._build_message_prompt(
            sample_message, content, ProcessingType.SUMMARIZATION
        )

        assert "Summary:" in prompt
        assert sample_message.platform.value in prompt
        assert sample_message.sender.get_display_name() in prompt
        assert content in prompt

    def test_build_message_prompt_entity_extraction(self, message_processor, sample_message):
        """Test prompt building for entity extraction."""
        content = sample_message.content.text
        prompt = message_processor._build_message_prompt(
            sample_message, content, ProcessingType.ENTITY_EXTRACTION
        )

        assert "Entities" in prompt
        assert "JSON format" in prompt
        assert content in prompt

    def test_build_text_prompt(self, message_processor):
        """Test text prompt building."""
        test_text = "Test text for prompt building"

        # Test summarization prompt
        prompt = message_processor._build_text_prompt(
            test_text, ProcessingType.SUMMARIZATION
        )
        assert "summary" in prompt.lower()
        assert test_text in prompt

        # Test entity extraction prompt
        prompt = message_processor._build_text_prompt(
            test_text, ProcessingType.ENTITY_EXTRACTION
        )
        assert "entities" in prompt.lower()
        assert test_text in prompt


class TestAIProcessingEngine:
    """Test cases for AIProcessingEngine."""

    @pytest.fixture
    def ai_engine(self):
        """Create an AIProcessingEngine instance for testing."""
        return AIProcessingEngine()

    @pytest.fixture
    def sample_message(self):
        """Create a sample normalized message for testing."""
        sender = Participant(
            platform=Platform.GMAIL,
            platform_user_id="test@example.com",
            display_name="Test User",
            email="test@example.com"
        )

        content = MessageContent(
            text="This is a test message for AI processing.",
            primary_format=ContentType.TEXT
        )

        return NormalizedMessage(
            platform=Platform.GMAIL,
            platform_message_id="test_msg_456",
            thread_id="test_thread_456",
            sender=sender,
            content=content,
            timestamp=datetime.utcnow()
        )

    def test_initialization(self, ai_engine):
        """Test AIProcessingEngine initialization."""
        assert ai_engine.message_processor is not None
        assert ai_engine.stats['requests_processed'] == 0
        assert ai_engine.stats['requests_failed'] == 0

    @pytest.mark.asyncio
    async def test_process_message_single_type(self, ai_engine, sample_message):
        """Test processing a message with a single processing type."""
        with patch.object(ai_engine.message_processor, 'process_message') as mock_process:
            mock_process.return_value = {
                'processing_type': 'summarization',
                'result': 'Test summary',
                'pii_redacted': False
            }

            results = await ai_engine.process_message(
                sample_message, [ProcessingType.SUMMARIZATION]
            )

            assert len(results) == 1
            assert 'summarization' in results
            assert results['summarization'].status == ProcessingStatus.COMPLETED
            assert results['summarization'].result['result'] == 'Test summary'

    @pytest.mark.asyncio
    async def test_process_message_multiple_types(self, ai_engine, sample_message):
        """Test processing a message with multiple processing types."""
        with patch.object(ai_engine.message_processor, 'process_message') as mock_process:
            def mock_process_side_effect(message, processing_type, **kwargs):
                return {
                    'processing_type': processing_type.value,
                    'result': f'Result for {processing_type.value}',
                    'pii_redacted': False
                }

            mock_process.side_effect = mock_process_side_effect

            processing_types = [ProcessingType.SUMMARIZATION,
                                ProcessingType.ENTITY_EXTRACTION]
            results = await ai_engine.process_message(sample_message, processing_types)

            assert len(results) == 2
            assert 'summarization' in results
            assert 'entity_extraction' in results
            assert all(
                r.status == ProcessingStatus.COMPLETED for r in results.values())

    @pytest.mark.asyncio
    async def test_process_message_with_error(self, ai_engine, sample_message):
        """Test processing a message when an error occurs."""
        with patch.object(ai_engine.message_processor, 'process_message') as mock_process:
            mock_process.side_effect = Exception("Test processing error")

            results = await ai_engine.process_message(
                sample_message, [ProcessingType.SUMMARIZATION]
            )

            assert len(results) == 1
            assert 'summarization' in results
            assert results['summarization'].status == ProcessingStatus.FAILED
            assert "Test processing error" in results['summarization'].error

    @pytest.mark.asyncio
    async def test_process_text(self, ai_engine):
        """Test text processing."""
        test_text = "This is a test text for processing."

        with patch.object(ai_engine.message_processor, 'process_text') as mock_process:
            mock_process.return_value = "Processed text result"

            result = await ai_engine.process_text(test_text, ProcessingType.SUMMARIZATION)

            assert result.status == ProcessingStatus.COMPLETED
            assert result.result == "Processed text result"
            assert result.type == ProcessingType.SUMMARIZATION

    @pytest.mark.asyncio
    async def test_process_text_with_error(self, ai_engine):
        """Test text processing when an error occurs."""
        test_text = "Test text"

        with patch.object(ai_engine.message_processor, 'process_text') as mock_process:
            mock_process.side_effect = Exception("Text processing error")

            result = await ai_engine.process_text(test_text, ProcessingType.SUMMARIZATION)

            assert result.status == ProcessingStatus.FAILED
            assert "Text processing error" in result.error

    @pytest.mark.asyncio
    async def test_generate_embedding(self, ai_engine):
        """Test embedding generation."""
        test_text = "Test text for embedding"

        with patch('services.ai_processing_engine.get_embedding_service') as mock_service:
            mock_embedding_service = AsyncMock()
            mock_result = Mock()
            mock_result.embedding = [0.1, 0.2, 0.3]
            mock_result.dimensions = 3
            mock_embedding_service.generate_embedding.return_value = mock_result
            mock_service.return_value = mock_embedding_service

            result = await ai_engine.generate_embedding(test_text)

            assert result.embedding == [0.1, 0.2, 0.3]
            assert result.dimensions == 3

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self, ai_engine):
        """Test batch embedding generation."""
        test_texts = ["Text 1", "Text 2", "Text 3"]

        with patch('services.ai_processing_engine.get_embedding_service') as mock_service:
            mock_embedding_service = AsyncMock()
            mock_results = [
                Mock(embedding=[0.1, 0.2], dimensions=2),
                Mock(embedding=[0.3, 0.4], dimensions=2),
                Mock(embedding=[0.5, 0.6], dimensions=2)
            ]
            mock_embedding_service.generate_embeddings_batch.return_value = mock_results
            mock_service.return_value = mock_embedding_service

            results = await ai_engine.generate_embeddings_batch(test_texts)

            assert len(results) == 3
            assert all(r.dimensions == 2 for r in results)

    @pytest.mark.asyncio
    async def test_redact_pii(self, ai_engine):
        """Test PII redaction."""
        test_text = "Contact John Doe at john.doe@example.com"

        with patch('services.ai_processing_engine.get_pii_redaction_service') as mock_service:
            mock_pii_service = AsyncMock()
            mock_result = Mock()
            mock_result.redacted_text = "Contact [REDACTED] at [REDACTED]"
            mock_result.entities = [
                Mock(type="person_name"), Mock(type="email")]
            mock_pii_service.redact_text.return_value = mock_result
            mock_service.return_value = mock_pii_service

            result = await ai_engine.redact_pii(test_text)

            assert result.redacted_text == "Contact [REDACTED] at [REDACTED]"
            assert len(result.entities) == 2

    def test_stats_update_success(self, ai_engine):
        """Test statistics update for successful processing."""
        initial_processed = ai_engine.stats['requests_processed']

        ai_engine._update_stats(
            ProcessingType.SUMMARIZATION, 1.5, success=True)

        assert ai_engine.stats['requests_processed'] == initial_processed + 1
        assert ai_engine.stats['total_processing_time'] == 1.5
        assert 'summarization' in ai_engine.stats['processing_by_type']
        assert ai_engine.stats['processing_by_type']['summarization']['processed'] == 1

    def test_stats_update_failure(self, ai_engine):
        """Test statistics update for failed processing."""
        initial_failed = ai_engine.stats['requests_failed']

        ai_engine._update_stats(ProcessingType.SUMMARIZATION, 0, success=False)

        assert ai_engine.stats['requests_failed'] == initial_failed + 1
        assert 'summarization' in ai_engine.stats['processing_by_type']
        assert ai_engine.stats['processing_by_type']['summarization']['failed'] == 1

    def test_get_stats(self, ai_engine):
        """Test getting processing statistics."""
        # Add some test data
        ai_engine._update_stats(
            ProcessingType.SUMMARIZATION, 1.0, success=True)
        ai_engine._update_stats(
            ProcessingType.ENTITY_EXTRACTION, 2.0, success=True)
        ai_engine._update_stats(ProcessingType.SUMMARIZATION, 0, success=False)

        stats = ai_engine.get_stats()

        assert stats['requests_processed'] == 2
        assert stats['requests_failed'] == 1
        assert stats['success_rate'] == 2/3
        assert stats['average_processing_time'] == 1.5
        assert 'message_processor_stats' in stats

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, ai_engine):
        """Test health check when all services are healthy."""
        with patch.object(ai_engine, 'process_text') as mock_process_text:
            mock_result = Mock()
            mock_result.status = ProcessingStatus.COMPLETED
            mock_process_text.return_value = mock_result

            with patch('services.ai_processing_engine.get_embedding_service') as mock_embedding:
                mock_embedding_service = AsyncMock()
                mock_embedding_service.health_check.return_value = {
                    'status': 'healthy'}
                mock_embedding.return_value = mock_embedding_service

                with patch('services.ai_processing_engine.get_pii_redaction_service') as mock_pii:
                    mock_pii_service = AsyncMock()
                    mock_pii_service.health_check.return_value = {
                        'status': 'healthy'}
                    mock_pii.return_value = mock_pii_service

                    with patch.object(ai_engine.message_processor, 'health_check') as mock_mp_health:
                        mock_mp_health.return_value = {'status': 'healthy'}

                        health = await ai_engine.health_check()

                        assert health['status'] == 'healthy'
                        assert health['text_processing'] is True
                        assert health['embedding_service'] is True
                        assert health['pii_redaction'] is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, ai_engine):
        """Test health check when an error occurs."""
        with patch.object(ai_engine, 'process_text') as mock_process_text:
            mock_process_text.side_effect = Exception("Health check error")

            health = await ai_engine.health_check()

            assert health['status'] == 'unhealthy'
            assert 'error' in health
            assert 'stats' in health


if __name__ == "__main__":
    pytest.main([__file__])
