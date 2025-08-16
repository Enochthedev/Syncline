"""
Core tests for the Summary Generation Agent.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from services.ai.summary import (
    SummaryGenerationAgent,
    SummaryRequest,
    SummaryResult,
    SummaryQuality,
    SummaryType,
    SummaryScope,
    get_summary_generation_agent,
    create_summary_generation_agent
)
from services.message_schema import NormalizedMessage, MessageContent, Participant, Platform
from services.ai.base import ProcessingStatus


class TestSummaryGenerationAgent:
    """Core test cases for SummaryGenerationAgent."""

    @pytest.fixture
    def agent(self):
        """Create a test summary generation agent."""
        return SummaryGenerationAgent()

    @pytest.fixture
    def sample_messages(self):
        """Create sample messages for testing."""
        now = datetime.utcnow()
        return [
            {
                'id': 'msg1',
                'content': 'Hello, how are you doing today?',
                'sender': 'Alice',
                'timestamp': now - timedelta(minutes=10),
                'platform': 'gmail',
                'thread_id': 'thread1'
            },
            {
                'id': 'msg2',
                'content': 'I am doing well, thanks! How about you?',
                'sender': 'Bob',
                'timestamp': now - timedelta(minutes=8),
                'platform': 'gmail',
                'thread_id': 'thread1'
            },
            {
                'id': 'msg3',
                'content': 'Great! I wanted to discuss the project timeline. Can we meet tomorrow?',
                'sender': 'Alice',
                'timestamp': now - timedelta(minutes=5),
                'platform': 'gmail',
                'thread_id': 'thread1'
            },
            {
                'id': 'msg4',
                'content': 'Sure, I am available at 2 PM. Let me send you the meeting invite.',
                'sender': 'Bob',
                'timestamp': now - timedelta(minutes=2),
                'platform': 'gmail',
                'thread_id': 'thread1'
            }
        ]

    @pytest.mark.asyncio
    async def test_micro_summary_generation(self, agent, sample_messages):
        """Test micro-summary generation."""
        request = SummaryRequest(
            summary_type=SummaryType.micro,
            scope_type=SummaryScope.thread,
            scope_id='thread1',
            quality=SummaryQuality.BASIC,
            max_length=100
        )

        # Mock the database operations and AI processing
        with patch('services.ai.summary.database.DatabaseOperations.get_messages_for_summary', return_value=sample_messages):
            with patch.object(agent, '_get_ai_response', return_value="Alice and Bob exchanged greetings and scheduled a meeting for tomorrow at 2 PM to discuss project timeline."):
                with patch('services.ai.summary.database.DatabaseOperations.store_summary', return_value='summary_123'):
                    result = await agent.process(request)

                    assert result.status == ProcessingStatus.COMPLETED.value
                    assert result.summary_id == 'summary_123'
                    assert 'Alice and Bob' in result.content
                    assert 'meeting' in result.content
                    assert result.word_count > 0
                    assert result.confidence_score > 0

    @pytest.mark.asyncio
    async def test_thread_summary_generation(self, agent, sample_messages):
        """Test thread-level summary generation."""
        request = SummaryRequest(
            summary_type=SummaryType.thread,
            scope_type=SummaryScope.thread,
            scope_id='thread1',
            quality=SummaryQuality.DETAILED,
            max_length=300
        )

        with patch('services.ai.summary.database.DatabaseOperations.get_messages_for_summary', return_value=sample_messages):
            with patch.object(agent, '_get_ai_response', return_value="""
                Conversation Summary:
                1. Alice and Bob exchanged friendly greetings
                2. Alice proposed discussing project timeline
                3. Meeting scheduled for tomorrow at 2 PM
                
                Action Items:
                - Bob to send meeting invite
                - Discuss project timeline in meeting
                """):
                with patch('services.ai.summary.database.DatabaseOperations.store_summary', return_value='summary_456'):
                    result = await agent.process(request)

                    assert result.status == ProcessingStatus.COMPLETED.value
                    assert len(result.key_points) > 0
                    assert len(result.action_items) > 0
                    assert 'project timeline' in result.content.lower()

    @pytest.mark.asyncio
    async def test_streaming_summary_generation(self, agent, sample_messages):
        """Test streaming summary generation."""
        request = SummaryRequest(
            summary_type=SummaryType.micro,
            scope_type=SummaryScope.thread,
            scope_id='thread1'
        )

        with patch('services.ai.summary.database.DatabaseOperations.get_messages_for_summary', return_value=sample_messages):
            with patch.object(agent, '_get_ai_response', return_value="This is a streaming summary that will be chunked into multiple parts for real-time delivery. " * 10):
                chunks = []
                async for chunk in agent.generate_streaming_summary(request):
                    chunks.append(chunk)
                    if chunk.is_final:
                        break

                assert len(chunks) > 1  # Should have multiple chunks
                assert chunks[-1].is_final  # Last chunk should be final
                assert all(chunk.request_id == request.id for chunk in chunks)

    @pytest.mark.asyncio
    async def test_batch_summary_processing(self, agent, sample_messages):
        """Test batch processing of multiple summary requests."""
        requests = [
            SummaryRequest(
                summary_type=SummaryType.micro,
                scope_type=SummaryScope.thread,
                scope_id=f'thread{i}',
                quality=SummaryQuality.BASIC
            )
            for i in range(3)
        ]

        with patch('services.ai.summary.database.DatabaseOperations.get_messages_for_summary', return_value=sample_messages):
            with patch.object(agent, '_get_ai_response', return_value="Batch processed summary content."):
                with patch('services.ai.summary.database.DatabaseOperations.store_summary', return_value='batch_summary'):
                    results = await agent.process_batch_summaries(requests, batch_size=2)

                    assert len(results) == 3
                    assert all(isinstance(result, SummaryResult)
                               for result in results)
                    assert all(
                        result.status == ProcessingStatus.COMPLETED.value for result in results)

    @pytest.mark.asyncio
    async def test_error_handling_in_summary_generation(self, agent):
        """Test error handling during summary generation."""
        request = SummaryRequest(
            summary_type=SummaryType.micro,
            scope_type=SummaryScope.thread,
            scope_id='nonexistent_thread'
        )

        # Mock failure in message retrieval
        with patch('services.ai.summary.database.DatabaseOperations.get_messages_for_summary', side_effect=Exception("Database error")):
            result = await agent.process(request)

            assert result.status == ProcessingStatus.FAILED.value
            assert result.error is not None
            assert 'database error' in result.error.lower()

    @pytest.mark.asyncio
    async def test_empty_messages_handling(self, agent):
        """Test handling of empty message lists."""
        request = SummaryRequest(
            summary_type=SummaryType.thread,
            scope_type=SummaryScope.thread,
            scope_id='empty_thread'
        )

        with patch('services.ai.summary.database.DatabaseOperations.get_messages_for_summary', return_value=[]):
            with patch('services.ai.summary.database.DatabaseOperations.store_summary', return_value='empty_summary'):
                result = await agent.process(request)

                assert result.status == ProcessingStatus.COMPLETED.value
                assert 'no messages' in result.content.lower()

    def test_summary_stats_tracking(self, agent):
        """Test summary statistics tracking."""
        initial_stats = agent.get_summary_stats()

        # Simulate successful summary generation
        agent._update_summary_stats(SummaryType.micro, 1.5, True)
        agent._update_summary_stats(SummaryType.thread, 2.0, True)
        agent._update_summary_stats(SummaryType.daily, 0.5, False)  # Failed

        updated_stats = agent.get_summary_stats()

        assert updated_stats['summaries_generated'] > initial_stats['summaries_generated']
        assert 'micro' in updated_stats['summaries_by_type']
        assert 'thread' in updated_stats['summaries_by_type']
        # Check that summary-specific stats are updated
        # 2 successful summaries
        assert updated_stats['summaries_generated'] == 2
        assert updated_stats['summaries_by_type']['micro'] == 1
        assert updated_stats['summaries_by_type']['thread'] == 1


class TestSummaryGenerationAgentIntegration:
    """Integration tests for summary generation agent."""

    @pytest.mark.asyncio
    async def test_get_summary_generation_agent_singleton(self):
        """Test that get_summary_generation_agent returns singleton."""
        agent1 = await get_summary_generation_agent()
        agent2 = await get_summary_generation_agent()

        assert agent1 is agent2
        assert isinstance(agent1, SummaryGenerationAgent)

    def test_create_summary_generation_agent_factory(self):
        """Test summary generation agent factory function."""
        agent = create_summary_generation_agent()

        assert isinstance(agent, SummaryGenerationAgent)
        assert agent.name == "SummaryGenerationAgent"

    @pytest.mark.asyncio
    async def test_agent_health_check(self):
        """Test agent health check functionality."""
        agent = SummaryGenerationAgent()

        with patch.object(agent, 'process') as mock_process:
            mock_process.return_value = SummaryResult(
                request_id='health_check',
                status=ProcessingStatus.COMPLETED.value,
                processing_time=0.5
            )

            health_status = await agent.health_check()

            assert health_status['status'] in ['healthy', 'unhealthy']
            assert 'agent_name' in health_status
            assert health_status['agent_name'] == 'SummaryGenerationAgent'


if __name__ == '__main__':
    pytest.main([__file__])
