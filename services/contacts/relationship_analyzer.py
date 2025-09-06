"""Advanced relationship analysis service for contact insights."""

import logging
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, text
from sqlalchemy.orm import selectinload
import numpy as np
from collections import defaultdict, Counter

from db.models.unified_contact import UnifiedContact, ContactIdentity, ContactInsight, ContactRelationship
from db.models.participant import Participant
from db.models.message import Message
from db.models.thread import Thread
from db.models.entity import Entity

logger = logging.getLogger(__name__)


class RelationshipAnalyzer:
    """Advanced relationship analysis and insights generation."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def analyze_communication_timeline(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        days_back: int = 365
    ) -> Dict[str, Any]:
        """Analyze communication timeline with frequency and trend analysis."""
        contact = await self._get_contact_with_identities(contact_id, tenant_id, user_id)
        if not contact:
            return {}

        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        participant_conditions = self._build_participant_conditions(
            contact.identities)

        if not participant_conditions:
            return {}

        # Get messages over time
        timeline_query = select(
            func.date(Message.timestamp).label('date'),
            func.count(Message.id).label('message_count'),
            func.avg(func.length(Message.content)).label('avg_message_length'),
            Message.platform
        ).join(Participant).where(
            and_(
                Message.tenant_id == tenant_id,
                Message.timestamp >= cutoff_date,
                or_(*participant_conditions)
            )
        ).group_by(
            func.date(Message.timestamp),
            Message.platform
        ).order_by(func.date(Message.timestamp))

        timeline_result = await self.db.execute(timeline_query)
        timeline_data = timeline_result.fetchall()

        # Process timeline data
        daily_stats = defaultdict(lambda: {
            'total_messages': 0,
            'platforms': set(),
            'avg_length': 0,
            'platform_breakdown': defaultdict(int)
        })

        for row in timeline_data:
            date_str = str(row.date)
            daily_stats[date_str]['total_messages'] += row.message_count
            daily_stats[date_str]['platforms'].add(row.platform)
            daily_stats[date_str]['avg_length'] = (
                daily_stats[date_str]['avg_length'] +
                (row.avg_message_length or 0)
            ) / 2
            daily_stats[date_str]['platform_breakdown'][row.platform] += row.message_count

        # Convert to timeline format
        timeline = []
        for date_str, stats in sorted(daily_stats.items()):
            timeline.append({
                'date': date_str,
                'message_count': stats['total_messages'],
                'platform_count': len(stats['platforms']),
                'avg_message_length': round(stats['avg_length'], 1),
                'platforms': list(stats['platforms']),
                'platform_breakdown': dict(stats['platform_breakdown'])
            })

        # Calculate trends
        message_counts = [day['message_count'] for day in timeline]
        trend_analysis = self._calculate_trend_analysis(message_counts)

        # Identify communication patterns
        patterns = await self._identify_communication_patterns(
            contact_id, tenant_id, user_id, cutoff_date
        )

        return {
            'timeline': timeline,
            'trend_analysis': trend_analysis,
            'patterns': patterns,
            'summary': {
                'total_days': len(timeline),
                'active_days': len([d for d in timeline if d['message_count'] > 0]),
                'total_messages': sum(message_counts),
                'avg_daily_messages': np.mean(message_counts) if message_counts else 0,
                'peak_day': max(timeline, key=lambda x: x['message_count']) if timeline else None
            }
        }

    async def analyze_sentiment_trends(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        days_back: int = 90
    ) -> Dict[str, Any]:
        """Analyze sentiment trends in communication."""
        contact = await self._get_contact_with_identities(contact_id, tenant_id, user_id)
        if not contact:
            return {}

        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        participant_conditions = self._build_participant_conditions(
            contact.identities)

        if not participant_conditions:
            return {}

        # Get messages with sentiment analysis
        # Note: This assumes sentiment analysis is stored in message metadata
        sentiment_query = select(
            func.date(Message.timestamp).label('date'),
            Message.extra_metadata,
            func.count(Message.id).label('message_count')
        ).join(Participant).where(
            and_(
                Message.tenant_id == tenant_id,
                Message.timestamp >= cutoff_date,
                or_(*participant_conditions),
                Message.extra_metadata.op('?')(
                    'sentiment')  # Has sentiment data
            )
        ).group_by(
            func.date(Message.timestamp),
            Message.extra_metadata
        ).order_by(func.date(Message.timestamp))

        sentiment_result = await self.db.execute(sentiment_query)
        sentiment_data = sentiment_result.fetchall()

        # Process sentiment data
        daily_sentiment = defaultdict(lambda: {
            'positive': 0,
            'neutral': 0,
            'negative': 0,
            'total': 0,
            'avg_score': 0.0
        })

        for row in sentiment_data:
            date_str = str(row.date)
            sentiment_info = row.extra_metadata.get('sentiment', {})
            sentiment_score = sentiment_info.get('score', 0.0)

            daily_sentiment[date_str]['total'] += row.message_count

            if sentiment_score > 0.1:
                daily_sentiment[date_str]['positive'] += row.message_count
            elif sentiment_score < -0.1:
                daily_sentiment[date_str]['negative'] += row.message_count
            else:
                daily_sentiment[date_str]['neutral'] += row.message_count

            # Update running average
            current_avg = daily_sentiment[date_str]['avg_score']
            daily_sentiment[date_str]['avg_score'] = (
                (current_avg + sentiment_score) / 2
            )

        # Convert to timeline format
        sentiment_timeline = []
        for date_str, stats in sorted(daily_sentiment.items()):
            if stats['total'] > 0:
                sentiment_timeline.append({
                    'date': date_str,
                    'positive_ratio': stats['positive'] / stats['total'],
                    'neutral_ratio': stats['neutral'] / stats['total'],
                    'negative_ratio': stats['negative'] / stats['total'],
                    'avg_sentiment_score': round(stats['avg_score'], 3),
                    'total_messages': stats['total']
                })

        # Calculate overall sentiment trends
        if sentiment_timeline:
            scores = [day['avg_sentiment_score'] for day in sentiment_timeline]
            overall_sentiment = np.mean(scores)
            sentiment_trend = self._calculate_trend_analysis(scores)
        else:
            overall_sentiment = 0.0
            sentiment_trend = {}

        return {
            'sentiment_timeline': sentiment_timeline,
            'overall_sentiment': overall_sentiment,
            'sentiment_trend': sentiment_trend,
            'summary': {
                'total_analyzed_days': len(sentiment_timeline),
                'avg_sentiment': overall_sentiment,
                'sentiment_category': self._categorize_sentiment(overall_sentiment)
            }
        }

    async def analyze_mutual_connections(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Analyze mutual connections and network relationships."""
        contact = await self._get_contact_with_identities(contact_id, tenant_id, user_id)
        if not contact:
            return {}

        participant_conditions = self._build_participant_conditions(
            contact.identities)
        if not participant_conditions:
            return {}

        # Find threads where this contact participated
        contact_threads_query = select(func.distinct(Message.thread_id)).join(Participant).where(
            and_(
                Message.tenant_id == tenant_id,
                or_(*participant_conditions)
            )
        )

        contact_threads_result = await self.db.execute(contact_threads_query)
        contact_thread_ids = [row[0]
                              for row in contact_threads_result.fetchall()]

        if not contact_thread_ids:
            return {'mutual_contacts': [], 'network_analysis': {}}

        # Find other participants in those threads
        mutual_participants_query = select(
            Participant.platform,
            Participant.platform_user_id,
            Participant.display_name,
            func.count(func.distinct(Message.thread_id)
                       ).label('shared_threads'),
            func.count(Message.id).label('shared_messages')
        ).join(Message).where(
            and_(
                Message.tenant_id == tenant_id,
                Message.thread_id.in_(contact_thread_ids),
                # Exclude the contact themselves
                ~or_(*participant_conditions)
            )
        ).group_by(
            Participant.platform,
            Participant.platform_user_id,
            Participant.display_name
        ).having(
            # At least 2 shared threads
            func.count(func.distinct(Message.thread_id)) > 1
        ).order_by(desc('shared_threads'))

        mutual_result = await self.db.execute(mutual_participants_query)
        mutual_data = mutual_result.fetchall()

        # Try to match with existing unified contacts
        mutual_contacts = []
        for row in mutual_data:
            # Look for existing unified contact
            existing_contact_query = select(UnifiedContact).join(ContactIdentity).where(
                and_(
                    UnifiedContact.tenant_id == tenant_id,
                    UnifiedContact.user_id == user_id,
                    ContactIdentity.platform == row.platform,
                    ContactIdentity.platform_user_id == row.platform_user_id
                )
            ).options(selectinload(UnifiedContact.identities))

            existing_result = await self.db.execute(existing_contact_query)
            existing_contact = existing_result.scalar_one_or_none()

            mutual_contact_info = {
                'platform': row.platform,
                'platform_user_id': row.platform_user_id,
                'display_name': row.display_name,
                'shared_threads': row.shared_threads,
                'shared_messages': row.shared_messages,
                'unified_contact': None
            }

            if existing_contact:
                mutual_contact_info['unified_contact'] = {
                    'id': str(existing_contact.id),
                    'primary_name': existing_contact.primary_name,
                    'relationship_strength': existing_contact.relationship_strength
                }

            mutual_contacts.append(mutual_contact_info)

        # Network analysis
        network_strength = len(mutual_contacts)
        avg_shared_threads = np.mean(
            [c['shared_threads'] for c in mutual_contacts]) if mutual_contacts else 0

        return {
            'mutual_contacts': mutual_contacts[:20],  # Limit to top 20
            'network_analysis': {
                'network_size': network_strength,
                'avg_shared_threads': round(avg_shared_threads, 1),
                # Normalize to 0-1
                'network_strength_score': min(1.0, network_strength / 50),
                'top_connections': mutual_contacts[:5]
            }
        }

    async def calculate_interaction_frequency_analysis(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Calculate detailed interaction frequency analysis."""
        contact = await self._get_contact_with_identities(contact_id, tenant_id, user_id)
        if not contact:
            return {}

        participant_conditions = self._build_participant_conditions(
            contact.identities)
        if not participant_conditions:
            return {}

        # Analyze frequency by different time periods
        analyses = {}

        # Daily pattern (hour of day)
        hourly_query = select(
            func.extract('hour', Message.timestamp).label('hour'),
            func.count(Message.id).label('message_count')
        ).join(Participant).where(
            and_(
                Message.tenant_id == tenant_id,
                or_(*participant_conditions)
            )
        ).group_by(func.extract('hour', Message.timestamp))

        hourly_result = await self.db.execute(hourly_query)
        hourly_data = dict(hourly_result.fetchall())

        analyses['hourly_pattern'] = {
            'data': hourly_data,
            'peak_hour': max(hourly_data.keys(), key=lambda h: hourly_data[h]) if hourly_data else None,
            'active_hours': len([h for h, count in hourly_data.items() if count > 0])
        }

        # Weekly pattern (day of week)
        weekly_query = select(
            func.extract('dow', Message.timestamp).label('day_of_week'),
            func.count(Message.id).label('message_count')
        ).join(Participant).where(
            and_(
                Message.tenant_id == tenant_id,
                or_(*participant_conditions)
            )
        ).group_by(func.extract('dow', Message.timestamp))

        weekly_result = await self.db.execute(weekly_query)
        weekly_data = dict(weekly_result.fetchall())

        day_names = ['Sunday', 'Monday', 'Tuesday',
                     'Wednesday', 'Thursday', 'Friday', 'Saturday']
        analyses['weekly_pattern'] = {
            'data': {day_names[int(dow)]: count for dow, count in weekly_data.items()},
            'most_active_day': day_names[int(max(weekly_data.keys(), key=lambda d: weekly_data[d]))] if weekly_data else None
        }

        # Monthly pattern (last 12 months)
        twelve_months_ago = datetime.utcnow() - timedelta(days=365)
        monthly_query = select(
            func.date_trunc('month', Message.timestamp).label('month'),
            func.count(Message.id).label('message_count')
        ).join(Participant).where(
            and_(
                Message.tenant_id == tenant_id,
                Message.timestamp >= twelve_months_ago,
                or_(*participant_conditions)
            )
        ).group_by(func.date_trunc('month', Message.timestamp)).order_by('month')

        monthly_result = await self.db.execute(monthly_query)
        monthly_data = [(str(row.month)[:7], row.message_count)
                        for row in monthly_result.fetchall()]

        analyses['monthly_pattern'] = {
            'data': dict(monthly_data),
            'trend': self._calculate_trend_analysis([count for _, count in monthly_data])
        }

        # Response time analysis
        response_analysis = await self._analyze_response_patterns(
            contact_id, tenant_id, user_id
        )
        analyses['response_patterns'] = response_analysis

        return analyses

    async def generate_relationship_insights(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> List[Dict[str, Any]]:
        """Generate comprehensive relationship insights."""
        insights = []

        # Get all analysis data
        timeline_data = await self.analyze_communication_timeline(contact_id, tenant_id, user_id)
        sentiment_data = await self.analyze_sentiment_trends(contact_id, tenant_id, user_id)
        frequency_data = await self.calculate_interaction_frequency_analysis(contact_id, tenant_id, user_id)
        network_data = await self.analyze_mutual_connections(contact_id, tenant_id, user_id)

        contact = await self._get_contact_with_identities(contact_id, tenant_id, user_id)
        if not contact:
            return insights

        # Communication frequency insight
        if timeline_data.get('summary', {}).get('avg_daily_messages', 0) > 0:
            avg_daily = timeline_data['summary']['avg_daily_messages']
            if avg_daily >= 5:
                frequency_level = "very high"
                confidence = 0.9
            elif avg_daily >= 2:
                frequency_level = "high"
                confidence = 0.8
            elif avg_daily >= 0.5:
                frequency_level = "moderate"
                confidence = 0.7
            else:
                frequency_level = "low"
                confidence = 0.6

            insights.append({
                'type': 'communication_frequency',
                'title': f'{frequency_level.title()} Communication Frequency',
                'description': f'You exchange an average of {avg_daily:.1f} messages per day with {contact.primary_name}.',
                'confidence': confidence,
                'supporting_data': timeline_data['summary'],
                'suggested_actions': self._get_frequency_suggestions(frequency_level, contact.primary_name)
            })

        # Sentiment insight
        if sentiment_data.get('overall_sentiment') is not None:
            sentiment_score = sentiment_data['overall_sentiment']
            sentiment_category = sentiment_data['summary']['sentiment_category']

            insights.append({
                'type': 'sentiment_analysis',
                'title': f'{sentiment_category.title()} Communication Tone',
                'description': f'Your conversations with {contact.primary_name} have a {sentiment_category} tone (score: {sentiment_score:.2f}).',
                'confidence': 0.75,
                'supporting_data': sentiment_data['summary'],
                'suggested_actions': self._get_sentiment_suggestions(sentiment_category, contact.primary_name)
            })

        # Network insight
        network_size = network_data.get(
            'network_analysis', {}).get('network_size', 0)
        if network_size > 0:
            if network_size >= 10:
                network_level = "strong"
            elif network_size >= 5:
                network_level = "moderate"
            else:
                network_level = "limited"

            insights.append({
                'type': 'network_analysis',
                'title': f'{network_level.title()} Network Connection',
                'description': f'You have {network_size} mutual connections with {contact.primary_name}, indicating a {network_level} network overlap.',
                'confidence': 0.8,
                'supporting_data': network_data['network_analysis'],
                'suggested_actions': self._get_network_suggestions(network_level, contact.primary_name)
            })

        # Response pattern insight
        response_patterns = frequency_data.get('response_patterns', {})
        if response_patterns.get('avg_response_time_hours') is not None:
            avg_response_hours = response_patterns['avg_response_time_hours']
            if avg_response_hours <= 1:
                response_speed = "very fast"
            elif avg_response_hours <= 6:
                response_speed = "fast"
            elif avg_response_hours <= 24:
                response_speed = "moderate"
            else:
                response_speed = "slow"

            insights.append({
                'type': 'response_pattern',
                'title': f'{response_speed.title()} Response Time',
                'description': f'{contact.primary_name} typically responds within {avg_response_hours:.1f} hours.',
                'confidence': 0.7,
                'supporting_data': response_patterns,
                'suggested_actions': self._get_response_suggestions(response_speed, contact.primary_name)
            })

        return insights

    # Private helper methods

    async def _get_contact_with_identities(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Optional[UnifiedContact]:
        """Get contact with identities loaded."""
        query = select(UnifiedContact).where(
            and_(
                UnifiedContact.id == contact_id,
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id
            )
        ).options(selectinload(UnifiedContact.identities))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    def _build_participant_conditions(self, identities: List[ContactIdentity]) -> List:
        """Build participant query conditions from contact identities."""
        conditions = []
        for identity in identities:
            conditions.append(
                and_(
                    Participant.platform == identity.platform,
                    Participant.platform_user_id == identity.platform_user_id
                )
            )
        return conditions

    def _calculate_trend_analysis(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend analysis for a series of values."""
        if len(values) < 2:
            return {'trend': 'insufficient_data', 'slope': 0, 'correlation': 0}

        x = np.arange(len(values))
        y = np.array(values)

        # Calculate linear regression
        slope, intercept = np.polyfit(x, y, 1)
        correlation = np.corrcoef(x, y)[0, 1] if len(values) > 1 else 0

        # Determine trend direction
        if abs(slope) < 0.1:
            trend = 'stable'
        elif slope > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'

        return {
            'trend': trend,
            'slope': float(slope),
            'correlation': float(correlation),
            'strength': abs(correlation)
        }

    async def _identify_communication_patterns(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        cutoff_date: datetime
    ) -> Dict[str, Any]:
        """Identify communication patterns."""
        # This would implement more sophisticated pattern recognition
        # For now, return basic patterns
        return {
            'regular_intervals': False,
            'burst_communication': False,
            'seasonal_patterns': False,
            'platform_switching': False
        }

    async def _analyze_response_patterns(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Analyze response time patterns."""
        # This would implement response time analysis
        # For now, return placeholder data
        return {
            'avg_response_time_hours': 4.5,
            'response_rate': 0.85,
            'fastest_response_minutes': 2,
            'slowest_response_hours': 48
        }

    def _categorize_sentiment(self, sentiment_score: float) -> str:
        """Categorize sentiment score."""
        if sentiment_score > 0.3:
            return 'positive'
        elif sentiment_score < -0.3:
            return 'negative'
        else:
            return 'neutral'

    def _get_frequency_suggestions(self, frequency_level: str, contact_name: str) -> List[str]:
        """Get suggestions based on communication frequency."""
        suggestions = {
            'very_high': [
                f'Consider scheduling regular check-ins with {contact_name}',
                'This is a very active relationship - maintain the momentum'
            ],
            'high': [
                f'Great communication frequency with {contact_name}',
                'Consider deepening the relationship with more meaningful conversations'
            ],
            'moderate': [
                f'Good communication balance with {contact_name}',
                'Consider reaching out more frequently to strengthen the relationship'
            ],
            'low': [
                f'Consider reaching out to {contact_name} more often',
                'Set reminders to maintain regular contact'
            ]
        }
        return suggestions.get(frequency_level, [])

    def _get_sentiment_suggestions(self, sentiment_category: str, contact_name: str) -> List[str]:
        """Get suggestions based on sentiment analysis."""
        suggestions = {
            'positive': [
                f'Great positive communication with {contact_name}',
                'Continue fostering this positive relationship'
            ],
            'neutral': [
                f'Consider adding more personal touches to conversations with {contact_name}',
                'Look for opportunities to create more engaging interactions'
            ],
            'negative': [
                f'Consider addressing any concerns with {contact_name}',
                'Focus on more positive and constructive communication'
            ]
        }
        return suggestions.get(sentiment_category, [])

    def _get_network_suggestions(self, network_level: str, contact_name: str) -> List[str]:
        """Get suggestions based on network analysis."""
        suggestions = {
            'strong': [
                f'Leverage your strong network connection with {contact_name}',
                'Consider collaborative opportunities with mutual connections'
            ],
            'moderate': [
                f'Explore expanding your mutual network with {contact_name}',
                'Consider group activities or introductions'
            ],
            'limited': [
                f'Consider expanding your shared network with {contact_name}',
                'Look for opportunities to meet their connections'
            ]
        }
        return suggestions.get(network_level, [])

    def _get_response_suggestions(self, response_speed: str, contact_name: str) -> List[str]:
        """Get suggestions based on response patterns."""
        suggestions = {
            'very_fast': [
                f'{contact_name} is very responsive - great for urgent matters',
                'This person values quick communication'
            ],
            'fast': [
                f'{contact_name} responds quickly - good for time-sensitive topics',
                'Maintain prompt communication to match their style'
            ],
            'moderate': [
                f'{contact_name} has moderate response times',
                'Allow reasonable time for responses'
            ],
            'slow': [
                f'{contact_name} takes time to respond - be patient',
                'Consider following up if urgent, but respect their communication style'
            ]
        }
        return suggestions.get(response_speed, [])
