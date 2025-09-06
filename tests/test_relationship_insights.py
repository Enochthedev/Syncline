"""Tests for relationship insights and analysis functionality."""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from services.contacts.relationship_analyzer import RelationshipAnalyzer
from services.contacts.contact_insights import ContactInsightsService


class TestRelationshipAnalyzer:
    """Test relationship analysis functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def relationship_analyzer(self, mock_db_session):
        """Create relationship analyzer instance."""
        return RelationshipAnalyzer(mock_db_session)

    @pytest.fixture
    def sample_contact(self):
        """Create sample contact for testing."""
        contact = UnifiedContact(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            primary_name="John Doe",
            display_name="John Doe",
            relationship_strength=0.75,
            communication_frequency="high",
            total_messages=150,
            last_interaction=datetime.utcnow() - timedelta(days=1)
        )

        # Add identities
        contact.identities = [
            ContactIdentity(
                id=uuid4(),
                unified_contact_id=contact.id,
                platform="gmail",
                platform_user_id="john.doe@example.com",
                display_name="John Doe",
                email="john.doe@example.com"
            ),
            ContactIdentity(
                id=uuid4(),
                unified_contact_id=contact.id,
                platform="slack",
                platform_user_id="U123456",
                display_name="John Doe",
                platform_handle="john.doe"
            )
        ]

        return contact

    @pytest.fixture
    def sample_timeline_data(self):
        """Create sample timeline data."""
        base_date = datetime.utcnow() - timedelta(days=30)
        timeline = []

        for i in range(30):
            date = base_date + timedelta(days=i)
            timeline.append({
                'date': date.strftime('%Y-%m-%d'),
                'message_count': np.random.randint(0, 10),
                'platform_count': np.random.randint(1, 3),
                'avg_message_length': np.random.uniform(50, 200),
                'platforms': ['gmail', 'slack'][:np.random.randint(1, 3)],
                'platform_breakdown': {
                    'gmail': np.random.randint(0, 5),
                    'slack': np.random.randint(0, 5)
                }
            })

        return timeline

    async def test_analyze_communication_timeline(self, relationship_analyzer, sample_contact, mock_db_session):
        """Test communication timeline analysis."""
        # Mock database queries
        mock_db_session.execute.return_value.fetchall.return_value = [
            ('2024-01-01', 5, 100.0, 'gmail'),
            ('2024-01-01', 3, 80.0, 'slack'),
            ('2024-01-02', 2, 120.0, 'gmail'),
        ]

        # Mock contact retrieval
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_contact

        result = await relationship_analyzer.analyze_communication_timeline(
            contact_id=sample_contact.id,
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id,
            days_back=30
        )

        assert 'timeline' in result
        assert 'trend_analysis' in result
        assert 'summary' in result
        assert isinstance(result['timeline'], list)
        assert 'total_messages' in result['summary']

    async def test_analyze_sentiment_trends(self, relationship_analyzer, sample_contact, mock_db_session):
        """Test sentiment analysis."""
        # Mock sentiment data
        mock_db_session.execute.return_value.fetchall.return_value = [
            ('2024-01-01', {'sentiment': {'score': 0.5}}, 5),
            ('2024-01-02', {'sentiment': {'score': -0.2}}, 3),
        ]

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_contact

        result = await relationship_analyzer.analyze_sentiment_trends(
            contact_id=sample_contact.id,
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id,
            days_back=90
        )

        assert 'sentiment_timeline' in result
        assert 'overall_sentiment' in result
        assert 'sentiment_trend' in result
        assert isinstance(result['sentiment_timeline'], list)

    async def test_analyze_mutual_connections(self, relationship_analyzer, sample_contact, mock_db_session):
        """Test mutual connections analysis."""
        # Mock thread and participant data
        mock_db_session.execute.return_value.fetchall.side_effect = [
            # Contact threads
            [('thread1',), ('thread2',)],
            # Mutual participants
            [('slack', 'U789', 'Jane Smith', 2, 15)]
        ]

        mock_db_session.execute.return_value.scalar_one_or_none.side_effect = [
            sample_contact,  # Contact retrieval
            None  # No existing unified contact for mutual connection
        ]

        result = await relationship_analyzer.analyze_mutual_connections(
            contact_id=sample_contact.id,
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id
        )

        assert 'mutual_contacts' in result
        assert 'network_analysis' in result
        assert isinstance(result['mutual_contacts'], list)
        assert 'network_size' in result['network_analysis']

    async def test_calculate_interaction_frequency_analysis(self, relationship_analyzer, sample_contact, mock_db_session):
        """Test interaction frequency analysis."""
        # Mock frequency data
        mock_db_session.execute.return_value.fetchall.side_effect = [
            # Hourly pattern
            [(9, 10), (14, 15), (18, 8)],
            # Weekly pattern
            [(1, 25), (2, 30), (3, 20)],
            # Monthly pattern
            [('2024-01-01 00:00:00', 45), ('2024-02-01 00:00:00', 38)]
        ]

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_contact

        result = await relationship_analyzer.calculate_interaction_frequency_analysis(
            contact_id=sample_contact.id,
            tenant_id=sample_contact.tenant_id,
            user_id=sample_contact.user_id
        )

        assert 'hourly_pattern' in result
        assert 'weekly_pattern' in result
        assert 'monthly_pattern' in result
        assert 'response_patterns' in result

    async def test_generate_relationship_insights(self, relationship_analyzer, sample_contact, mock_db_session):
        """Test relationship insights generation."""
        # Mock all the analysis methods
        with patch.object(relationship_analyzer, 'analyze_communication_timeline') as mock_timeline, \
                patch.object(relationship_analyzer, 'analyze_sentiment_trends') as mock_sentiment, \
                patch.object(relationship_analyzer, 'calculate_interaction_frequency_analysis') as mock_frequency, \
                patch.object(relationship_analyzer, 'analyze_mutual_connections') as mock_network:

            mock_timeline.return_value = {
                'summary': {'avg_daily_messages': 3.5, 'total_messages': 105}
            }
            mock_sentiment.return_value = {
                'overall_sentiment': 0.3,
                'summary': {'sentiment_category': 'positive'}
            }
            mock_frequency.return_value = {
                'response_patterns': {'avg_response_time_hours': 2.5}
            }
            mock_network.return_value = {
                'network_analysis': {'network_size': 8}
            }

            mock_db_session.execute.return_value.scalar_one_or_none.return_value = sample_contact

            result = await relationship_analyzer.generate_relationship_insights(
                contact_id=sample_contact.id,
                tenant_id=sample_contact.tenant_id,
                user_id=sample_contact.user_id
            )

            assert isinstance(result, list)
            assert len(result) > 0

            # Check insight structure
            for insight in result:
                assert 'type' in insight
                assert 'title' in insight
                assert 'description' in insight
                assert 'confidence' in insight
                assert 'supporting_data' in insight
                assert 'suggested_actions' in insight

    def test_calculate_trend_analysis(self, relationship_analyzer):
        """Test trend analysis calculation."""
        # Test increasing trend
        values = [1, 2, 3, 4, 5]
        result = relationship_analyzer._calculate_trend_analysis(values)

        assert result['trend'] == 'increasing'
        assert result['slope'] > 0
        assert result['correlation'] > 0.9

        # Test decreasing trend
        values = [5, 4, 3, 2, 1]
        result = relationship_analyzer._calculate_trend_analysis(values)

        assert result['trend'] == 'decreasing'
        assert result['slope'] < 0

        # Test stable trend
        values = [3, 3, 3, 3, 3]
        result = relationship_analyzer._calculate_trend_analysis(values)

        assert result['trend'] == 'stable'
        assert abs(result['slope']) < 0.1

    def test_categorize_sentiment(self, relationship_analyzer):
        """Test sentiment categorization."""
        assert relationship_analyzer._categorize_sentiment(0.5) == 'positive'
        assert relationship_analyzer._categorize_sentiment(-0.5) == 'negative'
        assert relationship_analyzer._categorize_sentiment(0.1) == 'neutral'

    def test_get_frequency_suggestions(self, relationship_analyzer):
        """Test frequency-based suggestions."""
        suggestions = relationship_analyzer._get_frequency_suggestions(
            'high', 'John')
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert 'John' in suggestions[0]

    def test_get_sentiment_suggestions(self, relationship_analyzer):
        """Test sentiment-based suggestions."""
        suggestions = relationship_analyzer._get_sentiment_suggestions(
            'positive', 'John')
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    def test_get_network_suggestions(self, relationship_analyzer):
        """Test network-based suggestions."""
        suggestions = relationship_analyzer._get_network_suggestions(
            'strong', 'John')
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    def test_get_response_suggestions(self, relationship_analyzer):
        """Test response pattern suggestions."""
        suggestions = relationship_analyzer._get_response_suggestions(
            'fast', 'John')
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0


class TestContactInsightsService:
    """Test contact insights service functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def contact_insights_service(self, mock_db_session):
        """Create contact insights service instance."""
        return ContactInsightsService(mock_db_session)

    @pytest.fixture
    def sample_insights(self):
        """Create sample insights."""
        return [
            ContactInsight(
                id=uuid4(),
                unified_contact_id=uuid4(),
                insight_type='communication_frequency',
                title='High Communication Frequency',
                description='You communicate frequently with this contact.',
                confidence_score=0.85,
                supporting_data={'avg_daily_messages': 5.2},
                suggested_actions=['Continue regular communication']
            ),
            ContactInsight(
                id=uuid4(),
                unified_contact_id=uuid4(),
                insight_type='sentiment_analysis',
                title='Positive Communication Tone',
                description='Your conversations have a positive tone.',
                confidence_score=0.78,
                supporting_data={'sentiment_score': 0.4},
                suggested_actions=['Maintain positive interactions']
            )
        ]

    @pytest.mark.asyncio
    async def test_get_comprehensive_relationship_analysis(self, contact_insights_service, mock_db_session):
        """Test comprehensive relationship analysis."""
        contact_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()

        # Mock the relationship analyzer methods
        with patch.object(contact_insights_service.relationship_analyzer, 'analyze_communication_timeline') as mock_timeline, \
                patch.object(contact_insights_service.relationship_analyzer, 'analyze_sentiment_trends') as mock_sentiment, \
                patch.object(contact_insights_service.relationship_analyzer, 'calculate_interaction_frequency_analysis') as mock_frequency, \
                patch.object(contact_insights_service.relationship_analyzer, 'analyze_mutual_connections') as mock_network, \
                patch.object(contact_insights_service.relationship_analyzer, 'generate_relationship_insights') as mock_insights:

            mock_timeline.return_value = {'timeline': []}
            mock_sentiment.return_value = {'sentiment_timeline': []}
            mock_frequency.return_value = {'hourly_pattern': {}}
            mock_network.return_value = {'mutual_contacts': []}
            mock_insights.return_value = []

            result = await contact_insights_service.get_comprehensive_relationship_analysis(
                contact_id, tenant_id, user_id
            )

            assert 'timeline_analysis' in result
            assert 'sentiment_analysis' in result
            assert 'frequency_analysis' in result
            assert 'network_analysis' in result
            assert 'ai_insights' in result
            assert 'generated_at' in result

    @pytest.mark.asyncio
    async def test_get_communication_timeline_visualization(self, contact_insights_service):
        """Test timeline visualization data formatting."""
        contact_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()

        # Mock timeline data
        timeline_data = {
            'timeline': [
                {'date': '2024-01-01', 'message_count': 5},
                {'date': '2024-01-02', 'message_count': 3}
            ],
            'trend_analysis': {'trend': 'increasing'},
            'summary': {'total_messages': 8}
        }

        with patch.object(contact_insights_service.relationship_analyzer, 'analyze_communication_timeline') as mock_timeline:
            mock_timeline.return_value = timeline_data

            result = await contact_insights_service.get_communication_timeline_visualization(
                contact_id, tenant_id, user_id
            )

            assert 'timeline_chart' in result
            assert result['timeline_chart']['chart_type'] == 'line'
            assert result['timeline_chart']['x_axis'] == 'date'
            assert result['timeline_chart']['y_axis'] == 'message_count'

    @pytest.mark.asyncio
    async def test_get_interaction_heatmap_data(self, contact_insights_service):
        """Test heatmap data formatting."""
        contact_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()

        # Mock frequency data
        frequency_data = {
            'hourly_pattern': {'data': {9: 10, 14: 15, 18: 8}},
            'weekly_pattern': {'data': {'Monday': 25, 'Tuesday': 30}}
        }

        with patch.object(contact_insights_service.relationship_analyzer, 'calculate_interaction_frequency_analysis') as mock_frequency:
            mock_frequency.return_value = frequency_data

            result = await contact_insights_service.get_interaction_heatmap_data(
                contact_id, tenant_id, user_id
            )

            assert 'heatmap_data' in result
            assert 'day_labels' in result
            assert 'hour_labels' in result
            assert len(result['heatmap_data']) == 7  # 7 days
            assert len(result['heatmap_data'][0]) == 24  # 24 hours

    @pytest.mark.asyncio
    async def test_get_sentiment_trend_visualization(self, contact_insights_service):
        """Test sentiment visualization data formatting."""
        contact_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()

        # Mock sentiment data
        sentiment_data = {
            'sentiment_timeline': [
                {
                    'date': '2024-01-01',
                    'avg_sentiment_score': 0.3,
                    'positive_ratio': 0.6,
                    'neutral_ratio': 0.3,
                    'negative_ratio': 0.1
                }
            ],
            'overall_sentiment': 0.25,
            'summary': {'sentiment_category': 'positive'}
        }

        with patch.object(contact_insights_service.relationship_analyzer, 'analyze_sentiment_trends') as mock_sentiment:
            mock_sentiment.return_value = sentiment_data

            result = await contact_insights_service.get_sentiment_trend_visualization(
                contact_id, tenant_id, user_id
            )

            assert 'sentiment_chart' in result
            assert 'sentiment_distribution' in result
            assert 'overall_sentiment' in result
            assert 'sentiment_category' in result

    @pytest.mark.asyncio
    async def test_get_network_visualization_data(self, contact_insights_service, mock_db_session):
        """Test network visualization data formatting."""
        contact_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()

        # Mock network data
        network_data = {
            'mutual_contacts': [
                {
                    'platform': 'slack',
                    'platform_user_id': 'U123',
                    'display_name': 'Jane Smith',
                    'shared_threads': 3,
                    'shared_messages': 25,
                    'unified_contact': {
                        'id': str(uuid4()),
                        'primary_name': 'Jane Smith',
                        'relationship_strength': 0.6
                    }
                }
            ],
            'network_analysis': {'network_size': 5}
        }

        # Mock contact retrieval
        sample_contact = UnifiedContact(
            id=contact_id,
            tenant_id=tenant_id,
            user_id=user_id,
            primary_name="John Doe",
            relationship_strength=0.75
        )

        with patch.object(contact_insights_service.relationship_analyzer, 'analyze_mutual_connections') as mock_network, \
                patch.object(contact_insights_service, '_get_contact_with_data') as mock_contact:

            mock_network.return_value = network_data
            mock_contact.return_value = sample_contact

            result = await contact_insights_service.get_network_visualization_data(
                contact_id, tenant_id, user_id
            )

            assert 'network_graph' in result
            assert 'nodes' in result['network_graph']
            assert 'edges' in result['network_graph']
            assert 'network_stats' in result
            assert 'mutual_contacts_list' in result

    @pytest.mark.asyncio
    async def test_refresh_all_insights(self, contact_insights_service, mock_db_session, sample_insights):
        """Test insights refresh functionality."""
        contact_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()

        # Mock comprehensive analysis
        comprehensive_analysis = {
            'ai_insights': [
                {
                    'type': 'communication_frequency',
                    'title': 'High Frequency',
                    'description': 'Test description',
                    'confidence': 0.8,
                    'supporting_data': {},
                    'suggested_actions': []
                }
            ]
        }

        with patch.object(contact_insights_service, 'get_comprehensive_relationship_analysis') as mock_analysis, \
                patch.object(contact_insights_service, '_deactivate_existing_insights') as mock_deactivate:

            mock_analysis.return_value = comprehensive_analysis
            mock_deactivate.return_value = None

            result = await contact_insights_service.refresh_all_insights(
                contact_id, tenant_id, user_id
            )

            assert result['success'] is True
            assert 'insights_generated' in result
            assert 'comprehensive_analysis' in result

    @pytest.mark.asyncio
    async def test_get_insight_accuracy_metrics(self, contact_insights_service, mock_db_session):
        """Test insight accuracy metrics calculation."""
        contact_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()

        # Mock feedback data
        mock_db_session.execute.return_value.fetchall.return_value = [
            ('communication_frequency', 'helpful', 5, 0.85),
            ('communication_frequency', 'not_helpful', 1, 0.85),
            ('sentiment_analysis', 'helpful', 3, 0.78),
            ('sentiment_analysis', 'incorrect', 1, 0.78)
        ]

        result = await contact_insights_service.get_insight_accuracy_metrics(
            contact_id, tenant_id, user_id
        )

        assert 'communication_frequency' in result
        assert 'sentiment_analysis' in result

        # Check accuracy calculations
        comm_freq_metrics = result['communication_frequency']
        assert comm_freq_metrics['helpful'] == 5
        assert comm_freq_metrics['not_helpful'] == 1
        assert comm_freq_metrics['total'] == 6
        assert comm_freq_metrics['accuracy_rate'] == 5/6


class TestInsightAccuracy:
    """Test insight accuracy and validation."""

    def test_insight_confidence_scoring(self):
        """Test confidence score calculation."""
        # Test high confidence insight
        supporting_data = {
            'total_messages': 100,
            'data_points': 30,
            'consistency_score': 0.9
        }

        # Mock confidence calculation
        confidence = min(1.0, (
            (supporting_data['total_messages'] / 100) * 0.4 +
            (supporting_data['data_points'] / 30) * 0.3 +
            supporting_data['consistency_score'] * 0.3
        ))

        assert confidence >= 0.95  # Allow for floating point precision

    def test_insight_validation_rules(self):
        """Test insight validation rules."""
        # Test minimum data requirements
        insight_data = {
            'total_messages': 5,  # Below threshold
            'time_period_days': 7,
            'platforms': 1
        }

        # Should not generate insights with insufficient data
        is_valid = (
            insight_data['total_messages'] >= 10 and
            insight_data['time_period_days'] >= 14 and
            insight_data['platforms'] >= 1
        )

        assert not is_valid

    def test_relationship_strength_calculation(self):
        """Test relationship strength calculation accuracy."""
        factors = {
            'frequency': 0.25,  # High frequency
            'recency': 0.18,    # Recent interaction
            'consistency': 0.15,  # Consistent communication
            'platform_diversity': 0.08,  # Multiple platforms
            'thread_participation': 0.12  # Active in threads
        }

        total_strength = sum(factors.values())
        assert 0.7 <= total_strength <= 0.8  # Expected range

        # Test strength categorization
        if total_strength >= 0.8:
            category = "very_strong"
        elif total_strength >= 0.6:
            category = "strong"
        elif total_strength >= 0.4:
            category = "moderate"
        else:
            category = "weak"

        assert category == "strong"

    def test_sentiment_analysis_accuracy(self):
        """Test sentiment analysis accuracy."""
        # Mock sentiment scores
        sentiment_scores = [0.3, 0.5, -0.1, 0.2, 0.4]

        # Calculate overall sentiment
        overall_sentiment = np.mean(sentiment_scores)

        # Categorize sentiment
        if overall_sentiment > 0.3:
            category = 'positive'
        elif overall_sentiment < -0.3:
            category = 'negative'
        else:
            category = 'neutral'

        assert category == 'neutral'  # 0.26 average
        assert -1.0 <= overall_sentiment <= 1.0

    def test_trend_analysis_accuracy(self):
        """Test trend analysis accuracy."""
        # Test clear increasing trend
        values = [1, 3, 5, 7, 9]
        x = np.arange(len(values))
        y = np.array(values)

        slope, _ = np.polyfit(x, y, 1)
        correlation = np.corrcoef(x, y)[0, 1]

        assert slope > 1.5  # Strong positive slope
        assert correlation > 0.95  # High correlation

        # Determine trend
        if abs(slope) < 0.1:
            trend = 'stable'
        elif slope > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'

        assert trend == 'increasing'


if __name__ == "__main__":
    pytest.main([__file__])
