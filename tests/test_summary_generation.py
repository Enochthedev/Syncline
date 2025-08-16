"""
Unit tests for the Summary Generation Agent.

Tests cover:
- Summary generation for different types (micro, thread, daily, weekly)
- Streaming summary generation
- Batch processing
- Incremental updates
- Summary quality and consistency
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from services.ai.summary_generation import (
    SummaryGenerationAgent,
    SummaryRequest,
    SummaryResult,
    StreamingSummaryChunk,
    SummaryQuality,
    get_summary_generation_agent,
    create_summary_generation_agent
)
from services.message_schema import NormalizedMessage, MessageContent, Participant, Platform
from services.ai.base import ProcessingStatus

# Mock enums for testing without database


class MockEnum:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        if isinstance(other, MockEnum):
            return self.value == other.value
        return self.value == other

    def __str__(self):
        return self.value

    def __repr__(self):
        return f"MockEnum('{self.value}')"


class MockSummaryType:
    micro = MockEnum("micro")
    thread = MockEnum("thread")
    daily = MockEnum("daily")
    weekly = MockEnum("weekly")


class MockSummaryScope:
    message = MockEnum("message")
    thread = MockEnum("thread")
    contact = MockEnum("contact")
    global_scope = MockEnum("global")


# Use mock enums in tests
SummaryType = MockSummaryType()
SummaryScope = MockSummaryScope()


class TestSummaryGenerationAgent:
    """Test cases for SummaryGenerationAgent."""

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

    @pytest.fixture
    def sample_normalized_message(self):
        """Create a sample normalized message."""
        return NormalizedMessage(
            id='test_msg_1',
            platform=Platform.GMAIL,
            platform_message_id='gmail_123',
            thread_id='thread_1',
            sender=Participant(
                platform=Platform.GMAIL,
                platform_user_id='user_1',
                display_name='Test User',
                email='test@example.com'
            ),
            content=MessageContent(
                text='This is a test message for incremental summary updates.',
                primary_format='text'
            ),
            timestamp=datetime.utcnow()
        )

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

        # Mock the message retrieval and AI processing
        with patch.object(agent, '_get_messages_for_summary', return_value=sample_messages):
            with patch('services.ai.summary_generation.get_ai_processing_engine') as mock_engine:
                mock_ai = AsyncMock()
                mock_ai.process_text.return_value = Mock(
                    result="Alice and Bob exchanged greetings and scheduled a meeting for tomorrow at 2 PM to discuss project timeline."
                )
                mock_engine.return_value = mock_ai

                with patch.object(agent, '_store_summary', return_value='summary_123'):
                    result = await agent.process(request)

                    assert result.status == ProcessingStatus.COMPLETED
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

        with patch.object(agent, '_get_messages_for_summary', return_value=sample_messages):
            with patch('services.ai.summary_generation.get_ai_processing_engine') as mock_engine:
                mock_ai = AsyncMock()
                mock_ai.process_text.return_value = Mock(
                    result="""
                    Conversation Summary:
                    1. Alice and Bob exchanged friendly greetings
                    2. Alice proposed discussing project timeline
                    3. Meeting scheduled for tomorrow at 2 PM
                    
                    Action Items:
                    - Bob to send meeting invite
                    - Discuss project timeline in meeting
                    """
                )
                mock_engine.return_value = mock_ai

                with patch.object(agent, '_store_summary', return_value='summary_456'):
                    result = await agent.process(request)

                    assert result.status == ProcessingStatus.COMPLETED
                    assert len(result.key_points) > 0
                    assert len(result.action_items) > 0
                    assert 'project timeline' in result.content.lower()

    @pytest.mark.asyncio
    async def test_daily_summary_generation(self, agent, sample_messages):
        """Test daily summary generation."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        request = SummaryRequest(
            summary_type=SummaryType.daily,
            scope_type=SummaryScope.global_scope,
            timeframe_start=today,
            timeframe_end=today + timedelta(days=1),
            quality=SummaryQuality.COMPREHENSIVE
        )

        with patch.object(agent, '_get_messages_for_summary', return_value=sample_messages):
            with patch('services.ai.summary_generation.get_ai_processing_engine') as mock_engine:
                mock_ai = AsyncMock()
                mock_ai.process_text.return_value = Mock(
                    result="""
                    Daily Summary for 2024-01-15:
                    
                    Key Conversations:
                    - Thread thread1: Alice and Bob discussed project timeline and scheduled meeting
                    
                    Action Items:
                    - Meeting scheduled for tomorrow at 2 PM
                    - Bob to send meeting invite
                    
                    Communication Patterns:
                    - 4 messages exchanged
                    - Professional and friendly tone
                    """
                )
                mock_engine.return_value = mock_ai

                with patch.object(agent, '_store_summary', return_value='summary_789'):
                    result = await agent.process(request)

                    assert result.status == ProcessingStatus.COMPLETED
                    assert 'daily summary' in result.content.lower()
                    assert len(result.action_items) > 0

    @pytest.mark.asyncio
    async def test_weekly_summary_generation(self, agent, sample_messages):
        """Test weekly summary generation."""
        week_start = datetime.utcnow().replace(hour=0, minute=0, second=0,
                                               microsecond=0) - timedelta(days=7)

        request = SummaryRequest(
            summary_type=SummaryType.weekly,
            scope_type=SummaryScope.global_scope,
            timeframe_start=week_start,
            timeframe_end=week_start + timedelta(days=7),
            quality=SummaryQuality.COMPREHENSIVE
        )

        with patch.object(agent, '_get_messages_for_summary', return_value=sample_messages):
            with patch('services.ai.summary_generation.get_ai_processing_engine') as mock_engine:
                mock_ai = AsyncMock()
                mock_ai.process_text.return_value = Mock(
                    result="""
                    Weekly Summary:
                    
                    Communication Trends:
                    - 4 total messages across 1 active conversation
                    - Most active contact: Alice (2 messages)
                    - Peak activity: Recent day
                    
                    Key Themes:
                    - Project planning and coordination
                    - Meeting scheduling
                    
                    Relationship Insights:
                    - Professional collaboration between Alice and Bob
                    - Proactive communication about project timelines
                    """
                )
                mock_engine.return_value = mock_ai

                with patch.object(agent, '_store_summary', return_value='summary_weekly'):
                    result = await agent.process(request)

                    assert result.status == ProcessingStatus.COMPLETED
                    assert 'weekly' in result.content.lower()
                    assert 'trends' in result.content.lower()

    @pytest.mark.asyncio
    async def test_streaming_summary_generation(self, agent, sample_messages):
        """Test streaming summary generation."""
        request = SummaryRequest(
            summary_type=SummaryType.micro,
            scope_type=SummaryScope.thread,
            scope_id='thread1'
        )

        with patch.object(agent, '_get_messages_for_summary', return_value=sample_messages):
            with patch('services.ai.summary_generation.get_ai_processing_engine') as mock_engine:
                mock_ai = AsyncMock()
                mock_ai.process_text.return_value = Mock(
                    result="This is a streaming summary that will be chunked into multiple parts for real-time delivery. " * 10
                )
                mock_engine.return_value = mock_ai

                chunks = []
                async for chunk in agent.generate_streaming_summary(request):
                    chunks.append(chunk)
                    if chunk.is_final:
                        break

                assert len(chunks) > 1  # Should have multiple chunks
                assert chunks[-1].is_final  # Last chunk should be final
                assert all(chunk.request_id == request.id for chunk in chunks)

                # Reconstruct content from chunks
                full_content = ' '.join(
                    chunk.content for chunk in chunks if chunk.chunk_type == 'content')
                assert 'streaming summary' in full_content

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

        with patch.object(agent, '_get_messages_for_summary', return_value=sample_messages):
            with patch('services.ai.summary_generation.get_ai_processing_engine') as mock_engine:
                mock_ai = AsyncMock()
                mock_ai.process_text.return_value = Mock(
                    result="Batch processed summary content."
                )
                mock_engine.return_value = mock_ai

                with patch.object(agent, '_store_summary', return_value='batch_summary'):
                    results = await agent.process_batch_summaries(requests, batch_size=2)

                    assert len(results) == 3
                    assert all(isinstance(result, SummaryResult)
                               for result in results)
                    assert all(result.status ==
                               ProcessingStatus.COMPLETED for result in results)

    @pytest.mark.asyncio
    async def test_incremental_summary_update(self, agent, sample_normalized_message):
        """Test incremental summary updates with new messages."""
        thread_id = 'thread_1'

        # Mock existing summary
        existing_summary = Mock()
        existing_summary.content = "Previous summary content"
        existing_summary.created_at = datetime.utcnow() - timedelta(hours=2)

        with patch.object(agent, '_get_latest_thread_summary', return_value=existing_summary):
            with patch.object(agent, '_should_update_summary', return_value=True):
                with patch.object(agent, 'process', return_value=SummaryResult(
                    request_id='update_req',
                    content='Updated summary with new message content',
                    status=ProcessingStatus.COMPLETED
                )) as mock_process:

                    result = await agent.update_incremental_summary(thread_id, sample_normalized_message)

                    assert result is not None
                    assert result.status == ProcessingStatus.COMPLETED
                    assert 'updated summary' in result.content.lower()
                    mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_incremental_update_when_not_needed(self, agent, sample_normalized_message):
        """Test that incremental updates are skipped when not needed."""
        thread_id = 'thread_1'

        existing_summary = Mock()
        existing_summary.content = "Recent summary content"
        existing_summary.created_at = datetime.utcnow() - timedelta(minutes=10)

        # Mock DB_AVAILABLE to be True for this test
        with patch('services.ai.summary_generation.DB_AVAILABLE', True):
            with patch.object(agent, '_get_latest_thread_summary', return_value=existing_summary):
                with patch.object(agent, '_should_update_summary', return_value=False):

                    result = await agent.update_incremental_summary(thread_id, sample_normalized_message)

                    assert result is None

    def test_key_points_extraction(self, agent):
        """Test extraction of key points from summary content."""
        content = """
        Summary of the conversation:
        1. Alice proposed a new project timeline
        2. Bob agreed to the proposed changes
        3. Meeting scheduled for next week
        
        Important: The deadline is critical for success.
        """

        key_points = agent._extract_key_points(content)

        assert len(key_points) >= 3
        assert any('project timeline' in point.lower() for point in key_points)
        assert any('meeting scheduled' in point.lower()
                   for point in key_points)

    def test_action_items_extraction(self, agent):
        """Test extraction of action items from summary content."""
        content = """
        Discussion summary with action items:
        - Alice will send the updated proposal
        - Bob needs to review the budget
        - Follow up meeting should be scheduled
        - Team must complete the review by Friday
        """

        action_items = agent._extract_action_items(content)

        assert len(action_items) > 0
        assert any('send' in item.lower() or 'review' in item.lower()
                   for item in action_items)

    def test_entities_extraction(self, agent):
        """Test extraction of entities from summary content."""
        content = """
        Alice and Bob discussed the Microsoft project with Google Analytics.
        The meeting with Acme Corporation is scheduled for next Tuesday.
        John Smith will be joining the team soon.
        """

        entities = agent._extract_entities(content)

        assert len(entities) > 0
        # Should extract names and organizations
        extracted_text = ' '.join(entities)
        assert any(name in extracted_text for name in [
                   'Alice', 'Bob', 'Microsoft', 'Google', 'Acme'])

    def test_confidence_score_calculation(self, agent):
        """Test confidence score calculation based on summary quality."""
        # High quality result
        high_quality_result = SummaryResult(
            request_id='test',
            content='A comprehensive summary with detailed analysis.',
            key_points=['Point 1', 'Point 2', 'Point 3'],
            action_items=['Action 1', 'Action 2'],
            entities=['Alice', 'Bob', 'Project'],
            word_count=150
        )

        high_score = agent._calculate_confidence_score(high_quality_result)

        # Low quality result
        low_quality_result = SummaryResult(
            request_id='test',
            content='Short.',
            key_points=[],
            action_items=[],
            entities=[],
            word_count=1
        )

        low_score = agent._calculate_confidence_score(low_quality_result)

        assert high_score > low_score
        assert 0 <= high_score <= 1
        assert 0 <= low_score <= 1

    def test_weekly_trends_analysis(self, agent, sample_messages):
        """Test weekly trends analysis functionality."""
        trends = agent._analyze_weekly_trends(sample_messages)

        assert 'daily_counts' in trends
        assert 'active_threads' in trends
        assert 'top_contacts' in trends
        assert 'total_messages' in trends

        assert trends['total_messages'] == len(sample_messages)
        assert trends['active_threads'] > 0
        assert len(trends['top_contacts']) > 0

    def test_message_grouping_for_daily_summary(self, agent, sample_messages):
        """Test message grouping for daily summaries."""
        grouped = agent._group_messages_for_daily_summary(sample_messages)

        assert len(grouped) > 0
        # All messages should be grouped
        total_grouped_messages = sum(len(msgs) for msgs in grouped.values())
        assert total_grouped_messages == len(sample_messages)

    @pytest.mark.asyncio
    async def test_error_handling_in_summary_generation(self, agent):
        """Test error handling during summary generation."""
        request = SummaryRequest(
            summary_type=SummaryType.micro,
            scope_type=SummaryScope.thread,
            scope_id='nonexistent_thread'
        )

        # Mock failure in message retrieval
        with patch.object(agent, '_get_messages_for_summary', side_effect=Exception("Database error")):
            result = await agent.process(request)

            assert result.status == ProcessingStatus.FAILED
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

        with patch.object(agent, '_get_messages_for_summary', return_value=[]):
            with patch.object(agent, '_store_summary', return_value='empty_summary'):
                result = await agent.process(request)

                assert result.status == ProcessingStatus.COMPLETED
                assert 'no messages' in result.content.lower()

    def test_prompt_building_for_different_types(self, agent, sample_messages):
        """Test prompt building for different summary types."""
        base_request = SummaryRequest(
            scope_type=SummaryScope.thread,
            scope_id='thread1',
            quality=SummaryQuality.DETAILED,
            max_length=200
        )

        # Test micro summary prompt
        micro_request = SummaryRequest(
            **{**base_request.__dict__, 'summary_type': SummaryType.micro})
        micro_prompt = agent._build_summary_prompt(
            sample_messages, micro_request)

        assert 'micro' in micro_prompt.lower()
        assert '200 words max' in micro_prompt

        # Test thread summary prompt
        thread_request = SummaryRequest(
            **{**base_request.__dict__, 'summary_type': SummaryType.thread})
        thread_prompt = agent._build_summary_prompt(
            sample_messages, thread_request)

        assert 'thread' in thread_prompt.lower()
        assert 'main topics' in thread_prompt.lower()

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

    @pytest.mark.asyncio
    async def test_summary_quality_consistency(self, agent, sample_messages):
        """Test consistency of summary quality across multiple generations."""
        request = SummaryRequest(
            summary_type=SummaryType.thread,
            scope_type=SummaryScope.thread,
            scope_id='thread1',
            quality=SummaryQuality.DETAILED
        )

        results = []

        with patch.object(agent, '_get_messages_for_summary', return_value=sample_messages):
            with patch('services.ai.summary_generation.get_ai_processing_engine') as mock_engine:
                mock_ai = AsyncMock()
                mock_ai.process_text.return_value = Mock(
                    result="Consistent summary content with key points and action items."
                )
                mock_engine.return_value = mock_ai

                with patch.object(agent, '_store_summary', return_value='consistency_test'):
                    # Generate multiple summaries
                    for _ in range(3):
                        result = await agent.process(request)
                        results.append(result)

        # Check consistency
        assert all(result.status ==
                   ProcessingStatus.COMPLETED for result in results)
        assert all(result.confidence_score > 0.5 for result in results)

        # Word counts should be reasonably consistent
        word_counts = [result.word_count for result in results]
        avg_word_count = sum(word_counts) / len(word_counts)
        assert all(abs(count - avg_word_count) /
                   avg_word_count < 0.5 for count in word_counts)


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
                status=ProcessingStatus.COMPLETED,
                processing_time=0.5
            )

            health_status = await agent.health_check()

            assert health_status['status'] in ['healthy', 'unhealthy']
            assert 'agent_name' in health_status
            assert health_status['agent_name'] == 'SummaryGenerationAgent'


if __name__ == '__main__':
    pytest.main([__file__])
