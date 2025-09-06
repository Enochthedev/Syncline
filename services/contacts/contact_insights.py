"""Enhanced contact insights service for AI-powered relationship analysis."""

import logging
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, text
from sqlalchemy.orm import selectinload

from db.models.unified_contact import UnifiedContact, ContactIdentity, ContactInsight
from db.models.participant import Participant
from db.models.message import Message
from db.models.thread import Thread
from .relationship_analyzer import RelationshipAnalyzer

logger = logging.getLogger(__name__)


class ContactInsightsService:
    """Enhanced service for generating AI-powered contact insights and relationship analysis."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.relationship_analyzer = RelationshipAnalyzer(db_session)

    async def get_contact_insights(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        refresh: bool = False
    ) -> List[ContactInsight]:
        """Get AI-generated insights for a contact."""
        if not refresh:
            # Try to get existing insights first
            query = select(ContactInsight).join(UnifiedContact).where(
                and_(
                    UnifiedContact.id == contact_id,
                    UnifiedContact.tenant_id == tenant_id,
                    UnifiedContact.user_id == user_id,
                    ContactInsight.is_active == True
                )
            ).order_by(desc(ContactInsight.generated_at))

            result = await self.db.execute(query)
            existing_insights = result.scalars().all()

            # If we have recent insights (less than 7 days old), return them
            if existing_insights:
                recent_cutoff = datetime.utcnow() - timedelta(days=7)
                recent_insights = [
                    insight for insight in existing_insights
                    if insight.generated_at >= recent_cutoff
                ]
                if recent_insights:
                    return recent_insights

        # Generate new insights
        return await self._generate_contact_insights(contact_id, tenant_id, user_id)

    async def _generate_contact_insights(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> List[ContactInsight]:
        """Generate new AI insights for a contact."""
        # Get contact data
        contact = await self._get_contact_with_data(contact_id, tenant_id, user_id)
        if not contact:
            return []

        insights = []

        # Communication pattern insights
        comm_insights = await self._analyze_communication_patterns_insight(contact, tenant_id, user_id)
        insights.extend(comm_insights)

        # Relationship strength insights
        rel_insights = await self._analyze_relationship_strength_insight(contact, tenant_id, user_id)
        insights.extend(rel_insights)

        # Response pattern insights
        response_insights = await self._analyze_response_patterns_insight(contact, tenant_id, user_id)
        insights.extend(response_insights)

        # Topic affinity insights
        topic_insights = await self._analyze_topic_affinity_insight(contact, tenant_id, user_id)
        insights.extend(topic_insights)

        # Save insights to database
        for insight_data in insights:
            insight = ContactInsight(
                unified_contact_id=contact_id,
                insight_type=insight_data['type'],
                title=insight_data['title'],
                description=insight_data['description'],
                confidence_score=insight_data['confidence'],
                supporting_data=insight_data['supporting_data'],
                suggested_actions=insight_data['suggested_actions']
            )
            self.db.add(insight)

        await self.db.commit()
        return insights

    async def _get_contact_with_data(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Optional[UnifiedContact]:
        """Get contact with all related data for analysis."""
        query = select(UnifiedContact).where(
            and_(
                UnifiedContact.id == contact_id,
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id
            )
        ).options(
            selectinload(UnifiedContact.identities)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def analyze_communication_patterns(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Analyze communication patterns for a contact."""
        # Get contact's platform identities
        contact = await self._get_contact_with_data(contact_id, tenant_id, user_id)
        if not contact:
            return {}

        platform_user_ids = [
            (identity.platform, identity.platform_user_id)
            for identity in contact.identities
        ]

        if not platform_user_ids:
            return {}

        # Build participant conditions
        participant_conditions = []
        for platform, platform_user_id in platform_user_ids:
            participant_conditions.append(
                and_(
                    Participant.platform == platform,
                    Participant.platform_user_id == platform_user_id
                )
            )

        # Analyze message frequency by time periods
        patterns = {}

        # Messages by day of week
        dow_query = select(
            func.extract('dow', Message.timestamp).label('day_of_week'),
            func.count(Message.id).label('message_count')
        ).join(Participant).where(
            and_(
                Message.tenant_id == tenant_id,
                or_(*participant_conditions)
            )
        ).group_by(func.extract('dow', Message.timestamp))

        dow_result = await self.db.execute(dow_query)
        patterns['day_of_week'] = dict(dow_result.fetchall())

        # Messages by hour of day
        hour_query = select(
            func.extract('hour', Message.timestamp).label('hour'),
            func.count(Message.id).label('message_count')
        ).join(Participant).where(
            and_(
                Message.tenant_id == tenant_id,
                or_(*participant_conditions)
            )
        ).group_by(func.extract('hour', Message.timestamp))

        hour_result = await self.db.execute(hour_query)
        patterns['hour_of_day'] = dict(hour_result.fetchall())

        # Messages by platform
        platform_query = select(
            Message.platform,
            func.count(Message.id).label('message_count')
        ).join(Participant).where(
            and_(
                Message.tenant_id == tenant_id,
                or_(*participant_conditions)
            )
        ).group_by(Message.platform)

        platform_result = await self.db.execute(platform_query)
        patterns['platform_distribution'] = dict(platform_result.fetchall())

        # Recent activity trend (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        trend_query = select(
            func.date(Message.timestamp).label('date'),
            func.count(Message.id).label('message_count')
        ).join(Participant).where(
            and_(
                Message.tenant_id == tenant_id,
                Message.timestamp >= thirty_days_ago,
                or_(*participant_conditions)
            )
        ).group_by(func.date(Message.timestamp)).order_by(func.date(Message.timestamp))

        trend_result = await self.db.execute(trend_query)
        patterns['recent_trend'] = [
            {'date': str(row.date), 'count': row.message_count}
            for row in trend_result
        ]

        return patterns

    async def calculate_relationship_strength(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Calculate relationship strength metrics for a contact."""
        contact = await self._get_contact_with_data(contact_id, tenant_id, user_id)
        if not contact:
            return {}

        platform_user_ids = [
            (identity.platform, identity.platform_user_id)
            for identity in contact.identities
        ]

        if not platform_user_ids:
            return {'strength': 0.0, 'factors': {}}

        participant_conditions = []
        for platform, platform_user_id in platform_user_ids:
            participant_conditions.append(
                and_(
                    Participant.platform == platform,
                    Participant.platform_user_id == platform_user_id
                )
            )

        factors = {}

        # Message frequency factor (0-0.3)
        total_messages_query = select(func.count(Message.id)).join(Participant).where(
            and_(
                Message.tenant_id == tenant_id,
                or_(*participant_conditions)
            )
        )
        total_messages_result = await self.db.execute(total_messages_query)
        total_messages = total_messages_result.scalar() or 0

        # Recent messages (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_messages_query = select(func.count(Message.id)).join(Participant).where(
            and_(
                Message.tenant_id == tenant_id,
                Message.timestamp >= thirty_days_ago,
                or_(*participant_conditions)
            )
        )
        recent_messages_result = await self.db.execute(recent_messages_query)
        recent_messages = recent_messages_result.scalar() or 0

        # Calculate frequency factor
        # Max 0.3 for daily messages
        frequency_factor = min(0.3, (recent_messages / 30) * 0.1)
        factors['frequency'] = frequency_factor

        # Recency factor (0-0.2)
        if contact.last_interaction:
            days_since_last = (datetime.utcnow() -
                               contact.last_interaction).days
            # Decay over a year
            recency_factor = max(0, 0.2 - (days_since_last / 365) * 0.2)
        else:
            recency_factor = 0
        factors['recency'] = recency_factor

        # Consistency factor (0-0.2) - based on regular communication
        if total_messages > 10:
            # Calculate communication consistency over time
            consistency_factor = min(0.2, total_messages / 100 * 0.2)
        else:
            consistency_factor = 0
        factors['consistency'] = consistency_factor

        # Platform diversity factor (0-0.1)
        unique_platforms = len(
            set(identity.platform for identity in contact.identities))
        platform_factor = min(0.1, unique_platforms / 5 * 0.1)
        factors['platform_diversity'] = platform_factor

        # Thread participation factor (0-0.2)
        thread_count_query = select(func.count(func.distinct(Message.thread_id))).join(Participant).where(
            and_(
                Message.tenant_id == tenant_id,
                or_(*participant_conditions)
            )
        )
        thread_count_result = await self.db.execute(thread_count_query)
        thread_count = thread_count_result.scalar() or 0

        thread_factor = min(0.2, thread_count / 20 * 0.2)
        factors['thread_participation'] = thread_factor

        # Calculate total strength
        total_strength = sum(factors.values())

        # Determine strength category
        if total_strength >= 0.8:
            strength_category = "very_strong"
        elif total_strength >= 0.6:
            strength_category = "strong"
        elif total_strength >= 0.4:
            strength_category = "moderate"
        elif total_strength >= 0.2:
            strength_category = "weak"
        else:
            strength_category = "unknown"

        return {
            'strength': total_strength,
            'category': strength_category,
            'factors': factors,
            'metrics': {
                'total_messages': total_messages,
                'recent_messages': recent_messages,
                'unique_threads': thread_count,
                'unique_platforms': unique_platforms,
                'days_since_last_interaction': (datetime.utcnow() - contact.last_interaction).days if contact.last_interaction else None
            }
        }

    async def analyze_contact_network(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Analyze the contact's network and relationships."""
        # This would analyze shared threads, mutual contacts, etc.
        # For now, return a basic structure
        return {
            'mutual_contacts': [],
            'shared_groups': [],
            'network_strength': 0.0,
            'influence_score': 0.0
        }

    # Private insight generation methods

    async def _analyze_communication_patterns_insight(
        self,
        contact: UnifiedContact,
        tenant_id: UUID,
        user_id: UUID
    ) -> List[Dict[str, Any]]:
        """Generate communication pattern insights."""
        patterns = await self.analyze_communication_patterns(contact.id, tenant_id, user_id)
        insights = []

        if 'hour_of_day' in patterns and patterns['hour_of_day']:
            # Find peak communication hours
            hour_data = patterns['hour_of_day']
            peak_hour = max(hour_data.keys(), key=lambda h: hour_data[h])

            if hour_data[peak_hour] > 5:  # Significant activity
                insights.append({
                    'type': 'communication_pattern',
                    'title': f'Most Active at {int(peak_hour):02d}:00',
                    'description': f'{contact.primary_name} is most active around {int(peak_hour):02d}:00 with {hour_data[peak_hour]} messages typically sent during this hour.',
                    'confidence': 0.8,
                    'supporting_data': {'peak_hour': int(peak_hour), 'message_count': hour_data[peak_hour]},
                    'suggested_actions': [
                        f'Schedule important conversations around {int(peak_hour):02d}:00 for better response rates',
                        'Set reminders to follow up during their active hours'
                    ]
                })

        if 'platform_distribution' in patterns and patterns['platform_distribution']:
            # Find preferred platform
            platform_data = patterns['platform_distribution']
            preferred_platform = max(
                platform_data.keys(), key=lambda p: platform_data[p])

            if platform_data[preferred_platform] > 10:  # Significant usage
                insights.append({
                    'type': 'platform_preference',
                    'title': f'Prefers {preferred_platform.title()}',
                    'description': f'{contact.primary_name} primarily communicates via {preferred_platform} ({platform_data[preferred_platform]} messages).',
                    'confidence': 0.9,
                    'supporting_data': {'preferred_platform': preferred_platform, 'message_count': platform_data[preferred_platform]},
                    'suggested_actions': [
                        f'Prioritize {preferred_platform} for important communications',
                        f'Check {preferred_platform} first for responses'
                    ]
                })

        return insights

    async def _analyze_relationship_strength_insight(
        self,
        contact: UnifiedContact,
        tenant_id: UUID,
        user_id: UUID
    ) -> List[Dict[str, Any]]:
        """Generate relationship strength insights."""
        strength_data = await self.calculate_relationship_strength(contact.id, tenant_id, user_id)
        insights = []

        if strength_data.get('strength', 0) > 0:
            category = strength_data['category']
            strength = strength_data['strength']

            if category in ['strong', 'very_strong']:
                insights.append({
                    'type': 'relationship_strength',
                    'title': f'{category.replace("_", " ").title()} Relationship',
                    'description': f'You have a {category.replace("_", " ")} relationship with {contact.primary_name} (strength: {strength:.2f}). This is based on frequent communication and consistent interaction patterns.',
                    'confidence': 0.85,
                    'supporting_data': strength_data,
                    'suggested_actions': [
                        'Continue regular communication to maintain this strong relationship',
                        'Consider this contact for important collaborations or referrals'
                    ]
                })
            elif category == 'moderate':
                insights.append({
                    'type': 'relationship_opportunity',
                    'title': 'Relationship Growth Opportunity',
                    'description': f'Your relationship with {contact.primary_name} has moderate strength ({strength:.2f}). There\'s potential to strengthen this connection.',
                    'confidence': 0.7,
                    'supporting_data': strength_data,
                    'suggested_actions': [
                        'Increase communication frequency to strengthen the relationship',
                        'Engage across multiple platforms for deeper connection'
                    ]
                })

        return insights

    async def _analyze_response_patterns_insight(
        self,
        contact: UnifiedContact,
        tenant_id: UUID,
        user_id: UUID
    ) -> List[Dict[str, Any]]:
        """Generate response pattern insights."""
        # This would analyze response times, response rates, etc.
        # For now, return empty list as placeholder
        return []

    async def _analyze_topic_affinity_insight(
        self,
        contact: UnifiedContact,
        tenant_id: UUID,
        user_id: UUID
    ) -> List[Dict[str, Any]]:
        """Generate topic affinity insights."""
        # This would analyze common topics discussed
        # For now, return empty list as placeholder
        return []

    async def get_comprehensive_relationship_analysis(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get comprehensive relationship analysis including timeline, sentiment, and network."""
        try:
            # Get all relationship analysis data
            timeline_data = await self.relationship_analyzer.analyze_communication_timeline(
                contact_id, tenant_id, user_id
            )

            sentiment_data = await self.relationship_analyzer.analyze_sentiment_trends(
                contact_id, tenant_id, user_id
            )

            frequency_data = await self.relationship_analyzer.calculate_interaction_frequency_analysis(
                contact_id, tenant_id, user_id
            )

            network_data = await self.relationship_analyzer.analyze_mutual_connections(
                contact_id, tenant_id, user_id
            )

            # Generate AI insights
            ai_insights = await self.relationship_analyzer.generate_relationship_insights(
                contact_id, tenant_id, user_id
            )

            return {
                'timeline_analysis': timeline_data,
                'sentiment_analysis': sentiment_data,
                'frequency_analysis': frequency_data,
                'network_analysis': network_data,
                'ai_insights': ai_insights,
                'generated_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(
                f"Error generating comprehensive relationship analysis: {e}")
            return {}

    async def get_communication_timeline_visualization(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        days_back: int = 365
    ) -> Dict[str, Any]:
        """Get communication timeline data optimized for visualization."""
        timeline_data = await self.relationship_analyzer.analyze_communication_timeline(
            contact_id, tenant_id, user_id, days_back
        )

        if not timeline_data:
            return {}

        # Format data for frontend visualization
        visualization_data = {
            'timeline_chart': {
                'data': timeline_data.get('timeline', []),
                'chart_type': 'line',
                'x_axis': 'date',
                'y_axis': 'message_count',
                'title': 'Communication Timeline'
            },
            'trend_analysis': timeline_data.get('trend_analysis', {}),
            'summary_stats': timeline_data.get('summary', {}),
            'patterns': timeline_data.get('patterns', {})
        }

        return visualization_data

    async def get_interaction_heatmap_data(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get interaction frequency data formatted for heatmap visualization."""
        frequency_data = await self.relationship_analyzer.calculate_interaction_frequency_analysis(
            contact_id, tenant_id, user_id
        )

        if not frequency_data:
            return {}

        # Format for heatmap (day of week vs hour of day)
        hourly_pattern = frequency_data.get(
            'hourly_pattern', {}).get('data', {})
        weekly_pattern = frequency_data.get(
            'weekly_pattern', {}).get('data', {})

        # Create heatmap matrix (7 days x 24 hours)
        heatmap_matrix = []
        day_names = ['Sunday', 'Monday', 'Tuesday',
                     'Wednesday', 'Thursday', 'Friday', 'Saturday']

        for day_idx, day_name in enumerate(day_names):
            day_data = []
            for hour in range(24):
                # This is simplified - in reality you'd need to query for day+hour combinations
                base_count = weekly_pattern.get(day_name, 0) / 24
                hour_multiplier = hourly_pattern.get(
                    hour, 0) / max(hourly_pattern.values()) if hourly_pattern else 0
                day_data.append(int(base_count * hour_multiplier))
            heatmap_matrix.append(day_data)

        return {
            'heatmap_data': heatmap_matrix,
            'day_labels': day_names,
            'hour_labels': [f"{h:02d}:00" for h in range(24)],
            'peak_times': {
                'peak_hour': frequency_data.get('hourly_pattern', {}).get('peak_hour'),
                'most_active_day': frequency_data.get('weekly_pattern', {}).get('most_active_day')
            }
        }

    async def get_sentiment_trend_visualization(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        days_back: int = 90
    ) -> Dict[str, Any]:
        """Get sentiment trend data for visualization."""
        sentiment_data = await self.relationship_analyzer.analyze_sentiment_trends(
            contact_id, tenant_id, user_id, days_back
        )

        if not sentiment_data:
            return {}

        timeline = sentiment_data.get('sentiment_timeline', [])

        return {
            'sentiment_chart': {
                'data': timeline,
                'chart_type': 'area',
                'x_axis': 'date',
                'y_axis': 'avg_sentiment_score',
                'title': 'Sentiment Trend Over Time'
            },
            'sentiment_distribution': {
                'positive_avg': sum(day['positive_ratio'] for day in timeline) / len(timeline) if timeline else 0,
                'neutral_avg': sum(day['neutral_ratio'] for day in timeline) / len(timeline) if timeline else 0,
                'negative_avg': sum(day['negative_ratio'] for day in timeline) / len(timeline) if timeline else 0
            },
            'overall_sentiment': sentiment_data.get('overall_sentiment', 0),
            'sentiment_category': sentiment_data.get('summary', {}).get('sentiment_category', 'neutral')
        }

    async def get_network_visualization_data(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get network connection data for visualization."""
        network_data = await self.relationship_analyzer.analyze_mutual_connections(
            contact_id, tenant_id, user_id
        )

        if not network_data:
            return {}

        mutual_contacts = network_data.get('mutual_contacts', [])

        # Format for network graph
        nodes = [{'id': 'user', 'label': 'You', 'type': 'user'}]
        edges = []

        # Add the main contact
        contact = await self._get_contact_with_data(contact_id, tenant_id, user_id)
        if contact:
            nodes.append({
                'id': str(contact_id),
                'label': contact.primary_name,
                'type': 'main_contact'
            })
            edges.append({
                'from': 'user',
                'to': str(contact_id),
                'weight': contact.relationship_strength or 0.5
            })

        # Add mutual connections
        # Limit to top 10 for visualization
        for mutual in mutual_contacts[:10]:
            if mutual.get('unified_contact'):
                node_id = mutual['unified_contact']['id']
                nodes.append({
                    'id': node_id,
                    'label': mutual['unified_contact']['primary_name'],
                    'type': 'mutual_contact'
                })

                # Add edges
                edges.append({
                    'from': 'user',
                    'to': node_id,
                    'weight': mutual['unified_contact'].get('relationship_strength', 0.3)
                })
                edges.append({
                    'from': str(contact_id),
                    'to': node_id,
                    'weight': min(1.0, mutual['shared_threads'] / 10)
                })

        return {
            'network_graph': {
                'nodes': nodes,
                'edges': edges
            },
            'network_stats': network_data.get('network_analysis', {}),
            'mutual_contacts_list': mutual_contacts
        }

    async def refresh_all_insights(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Refresh all insights for a contact and return comprehensive analysis."""
        try:
            # Mark existing insights as inactive
            await self._deactivate_existing_insights(contact_id)

            # Generate new comprehensive analysis
            comprehensive_analysis = await self.get_comprehensive_relationship_analysis(
                contact_id, tenant_id, user_id
            )

            # Save new insights to database
            ai_insights = comprehensive_analysis.get('ai_insights', [])
            saved_insights = []

            for insight_data in ai_insights:
                insight = ContactInsight(
                    unified_contact_id=contact_id,
                    insight_type=insight_data['type'],
                    title=insight_data['title'],
                    description=insight_data['description'],
                    confidence_score=insight_data['confidence'],
                    supporting_data=insight_data['supporting_data'],
                    suggested_actions=insight_data['suggested_actions']
                )
                self.db.add(insight)
                saved_insights.append(insight)

            await self.db.commit()

            return {
                'success': True,
                'insights_generated': len(saved_insights),
                'comprehensive_analysis': comprehensive_analysis
            }

        except Exception as e:
            logger.error(
                f"Error refreshing insights for contact {contact_id}: {e}")
            await self.db.rollback()
            return {
                'success': False,
                'error': str(e)
            }

    async def _deactivate_existing_insights(self, contact_id: UUID) -> None:
        """Mark existing insights as inactive."""
        from sqlalchemy import update

        stmt = update(ContactInsight).where(
            ContactInsight.unified_contact_id == contact_id
        ).values(is_active=False)

        await self.db.execute(stmt)

    async def get_insight_accuracy_metrics(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get metrics on insight accuracy based on user feedback."""
        feedback_query = select(
            ContactInsight.insight_type,
            ContactInsight.user_feedback,
            func.count(ContactInsight.id).label('count'),
            func.avg(ContactInsight.confidence_score).label('avg_confidence')
        ).join(UnifiedContact).where(
            and_(
                UnifiedContact.id == contact_id,
                UnifiedContact.tenant_id == tenant_id,
                UnifiedContact.user_id == user_id,
                ContactInsight.user_feedback.isnot(None)
            )
        ).group_by(
            ContactInsight.insight_type,
            ContactInsight.user_feedback
        )

        feedback_result = await self.db.execute(feedback_query)
        feedback_data = feedback_result.fetchall()

        # Process feedback metrics
        accuracy_metrics = {}
        for row in feedback_data:
            insight_type = row.insight_type
            if insight_type not in accuracy_metrics:
                accuracy_metrics[insight_type] = {
                    'helpful': 0,
                    'not_helpful': 0,
                    'incorrect': 0,
                    'total': 0,
                    'avg_confidence': 0
                }

            accuracy_metrics[insight_type][row.user_feedback] = row.count
            accuracy_metrics[insight_type]['total'] += row.count
            accuracy_metrics[insight_type]['avg_confidence'] = row.avg_confidence

        # Calculate accuracy percentages
        for insight_type, metrics in accuracy_metrics.items():
            if metrics['total'] > 0:
                metrics['accuracy_rate'] = (
                    metrics['helpful'] / metrics['total']
                )
                metrics['error_rate'] = (
                    metrics['incorrect'] / metrics['total']
                )

        return accuracy_metrics
