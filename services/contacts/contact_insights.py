"""Contact insights service for AI-powered relationship analysis."""

import logging
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, text
from sqlalchemy.orm import selectinload

from db.models.unified_contact import UnifiedContact, ContactIdentity, ContactInsight
from db.models.participant import Participant
from db.models.message import Message
from db.models.thread import Thread

logger = logging.getLogger(__name__)


class ContactInsightsService:
    """Service for generating AI-powered contact insights and relationship analysis."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

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
