"""
Tests for summary generation utility modules.
"""

import pytest
from datetime import datetime, timedelta

from services.ai.summary.content_parser import ContentParser
from services.ai.summary.prompt_builder import PromptBuilder
from services.ai.summary.data_analyzer import DataAnalyzer
from services.ai.summary.types import SummaryRequest, SummaryResult, SummaryQuality, SummaryType, SummaryScope


class TestContentParser:
    """Test cases for ContentParser utility."""

    def test_key_points_extraction(self):
        """Test extraction of key points from summary content."""
        content = """
        Summary of the conversation:
        1. Alice proposed a new project timeline
        2. Bob agreed to the proposed changes
        3. Meeting scheduled for next week
        
        Important: The deadline is critical for success.
        """

        key_points = ContentParser.extract_key_points(content)

        assert len(key_points) >= 3
        assert any('project timeline' in point.lower() for point in key_points)
        assert any('meeting scheduled' in point.lower()
                   for point in key_points)

    def test_action_items_extraction(self):
        """Test extraction of action items from summary content."""
        content = """
        Discussion summary with action items:
        - Alice will send the updated proposal
        - Bob needs to review the budget
        - Follow up meeting should be scheduled
        - Team must complete the review by Friday
        """

        action_items = ContentParser.extract_action_items(content)

        assert len(action_items) > 0
        assert any('send' in item.lower() or 'review' in item.lower()
                   for item in action_items)

    def test_entities_extraction(self):
        """Test extraction of entities from summary content."""
        content = """
        Alice and Bob discussed the Microsoft project with Google Analytics.
        The meeting with Acme Corporation is scheduled for next Tuesday.
        John Smith will be joining the team soon.
        """

        entities = ContentParser.extract_entities(content)

        assert len(entities) > 0
        # Should extract names and organizations
        extracted_text = ' '.join(entities)
        assert any(name in extracted_text for name in [
                   'Alice', 'Bob', 'Microsoft', 'Google', 'Acme'])

    def test_confidence_score_calculation(self):
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

        high_score = ContentParser.calculate_confidence_score(
            high_quality_result)

        # Low quality result
        low_quality_result = SummaryResult(
            request_id='test',
            content='Short.',
            key_points=[],
            action_items=[],
            entities=[],
            word_count=1
        )

        low_score = ContentParser.calculate_confidence_score(
            low_quality_result)

        assert high_score > low_score
        assert 0 <= high_score <= 1
        assert 0 <= low_score <= 1


class TestPromptBuilder:
    """Test cases for PromptBuilder utility."""

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
            }
        ]

    def test_prompt_building_for_different_types(self, sample_messages):
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
        micro_prompt = PromptBuilder.build_summary_prompt(
            sample_messages, micro_request)

        assert 'micro' in micro_prompt.lower()
        assert '200 words max' in micro_prompt

        # Test thread summary prompt
        thread_request = SummaryRequest(
            **{**base_request.__dict__, 'summary_type': SummaryType.thread})
        thread_prompt = PromptBuilder.build_summary_prompt(
            sample_messages, thread_request)

        assert 'thread' in thread_prompt.lower()
        assert 'main topics' in thread_prompt.lower()

    def test_daily_summary_prompt(self):
        """Test daily summary prompt building."""
        grouped_messages = {
            'Thread 1': [
                {'timestamp': datetime.utcnow(), 'sender': 'Alice',
                 'content': 'Hello'},
                {'timestamp': datetime.utcnow(), 'sender': 'Bob',
                 'content': 'Hi there'}
            ]
        }

        request = SummaryRequest(
            summary_type=SummaryType.daily,
            timeframe_start=datetime.utcnow()
        )

        prompt = PromptBuilder.build_daily_summary_prompt(
            grouped_messages, request)

        assert 'daily summary' in prompt.lower()
        assert 'conversations' in prompt.lower()


class TestDataAnalyzer:
    """Test cases for DataAnalyzer utility."""

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
                'content': 'Great! I wanted to discuss the project timeline.',
                'sender': 'Alice',
                'timestamp': now - timedelta(minutes=5),
                'platform': 'gmail',
                'thread_id': 'thread2'
            }
        ]

    def test_weekly_trends_analysis(self, sample_messages):
        """Test weekly trends analysis functionality."""
        trends = DataAnalyzer.analyze_weekly_trends(sample_messages)

        assert 'daily_counts' in trends
        assert 'active_threads' in trends
        assert 'top_contacts' in trends
        assert 'total_messages' in trends

        assert trends['total_messages'] == len(sample_messages)
        assert trends['active_threads'] > 0
        assert len(trends['top_contacts']) > 0

    def test_message_grouping_for_daily_summary(self, sample_messages):
        """Test message grouping for daily summaries."""
        grouped = DataAnalyzer.group_messages_for_daily_summary(
            sample_messages)

        assert len(grouped) > 0
        # All messages should be grouped
        total_grouped_messages = sum(len(msgs) for msgs in grouped.values())
        assert total_grouped_messages == len(sample_messages)


if __name__ == '__main__':
    pytest.main([__file__])
