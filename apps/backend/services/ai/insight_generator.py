"""
Insight Generator Service

Analyzes communication patterns and generates insights:
- Message frequency tracking per contact
- Trending topics identification
- Sentiment detection
- Communication pattern analysis
- Relationship insights
"""

import asyncio
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import settings
from db.models.contact import Contact
from db.models.entity import Entity
from db.models.message import Message
from db.models.thread import Thread
from services.ai.providers import GenerationConfig, LLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


class SentimentType(str, Enum):
    """Sentiment types."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


class InsightType(str, Enum):
    """Types of insights."""

    FREQUENCY = "frequency"
    TOPICS = "topics"
    SENTIMENT = "sentiment"
    PATTERNS = "patterns"
    RELATIONSHIP = "relationship"


class CommunicationInsight:
    """
    Represents a communication insight.

    Attributes:
        insight_type: Type of insight
        title: Insight title
        description: Detailed description
        data: Supporting data
        confidence: Confidence score (0.0 to 1.0)
        generated_at: When insight was generated
    """

    def __init__(
        self,
        insight_type: InsightType,
        title: str,
        description: str,
        data: dict,
        confidence: float = 1.0,
    ):
        self.insight_type = insight_type
        self.title = title
        self.description = description
        self.data = data
        self.confidence = confidence
        self.generated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "type": self.insight_type.value,
            "title": self.title,
            "description": self.description,
            "data": self.data,
            "confidence": self.confidence,
            "generated_at": self.generated_at.isoformat(),
        }


class InsightGenerator:
    """
    Service for generating communication insights.

    Provides functionality for:
    - Tracking message frequency per contact
    - Identifying trending topics
    - Detecting sentiment
    - Analyzing communication patterns
    - Generating relationship insights
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize insight generator.

        Args:
            llm_provider: LLM provider for AI-based insights
            model: Model name for generation
        """
        self.llm_provider = llm_provider or get_llm_provider()
        self.model = model or settings.DEFAULT_CHAT_MODEL

        logger.info(f"Initialized InsightGenerator with model {self.model}")

    async def generate_contact_insights(
        self,
        contact_id: UUID,
        db: AsyncSession,
        days: int = 30,
    ) -> list[CommunicationInsight]:
        """
        Generate comprehensive insights for a contact.

        Args:
            contact_id: Contact ID
            db: Database session
            days: Number of days to analyze

        Returns:
            List of insights
        """
        try:
            insights = []

            # Get contact
            contact = await db.get(Contact, contact_id)
            if not contact:
                logger.error(f"Contact {contact_id} not found")
                return []

            # Generate frequency insights
            frequency_insight = await self._analyze_message_frequency(
                contact_id, db, days
            )
            if frequency_insight:
                insights.append(frequency_insight)

            # Generate topic insights
            topic_insights = await self._identify_trending_topics(contact_id, db, days)
            insights.extend(topic_insights)

            # Generate sentiment insights
            sentiment_insight = await self._analyze_sentiment(contact_id, db, days)
            if sentiment_insight:
                insights.append(sentiment_insight)

            # Generate pattern insights
            pattern_insights = await self._analyze_communication_patterns(
                contact_id, db, days
            )
            insights.extend(pattern_insights)

            logger.info(f"Generated {len(insights)} insights for contact {contact_id}")
            return insights

        except Exception as e:
            logger.error(f"Failed to generate contact insights: {e}")
            return []

    async def _analyze_message_frequency(
        self,
        contact_id: UUID,
        db: AsyncSession,
        days: int,
    ) -> Optional[CommunicationInsight]:
        """
        Analyze message frequency for a contact.

        Args:
            contact_id: Contact ID
            db: Database session
            days: Number of days to analyze

        Returns:
            Frequency insight or None
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Get threads for contact
            result = await db.execute(
                select(Thread).where(Thread.contact_id == contact_id)
            )
            threads = result.scalars().all()

            if not threads:
                return None

            thread_ids = [str(t.id) for t in threads]

            # Count messages per day
            result = await db.execute(
                select(
                    func.date(Message.timestamp).label("date"),
                    func.count(Message.id).label("count"),
                )
                .where(Message.thread_id.in_(thread_ids))
                .where(Message.timestamp >= cutoff_date)
                .group_by(func.date(Message.timestamp))
                .order_by(func.date(Message.timestamp))
            )
            daily_counts = result.all()

            if not daily_counts:
                return None

            # Calculate statistics
            counts = [count for _, count in daily_counts]
            total_messages = sum(counts)
            avg_per_day = total_messages / days
            max_per_day = max(counts)

            # Determine frequency level
            if avg_per_day >= 10:
                frequency_level = "very high"
            elif avg_per_day >= 5:
                frequency_level = "high"
            elif avg_per_day >= 2:
                frequency_level = "moderate"
            elif avg_per_day >= 0.5:
                frequency_level = "low"
            else:
                frequency_level = "very low"

            return CommunicationInsight(
                insight_type=InsightType.FREQUENCY,
                title=f"{frequency_level.title()} Communication Frequency",
                description=(
                    f"Over the past {days} days, you exchanged {total_messages} "
                    f"messages with this contact (avg {avg_per_day:.1f} per day). "
                    f"Peak activity: {max_per_day} messages in a single day."
                ),
                data={
                    "total_messages": total_messages,
                    "days_analyzed": days,
                    "avg_per_day": round(avg_per_day, 2),
                    "max_per_day": max_per_day,
                    "frequency_level": frequency_level,
                    "daily_counts": [
                        {"date": date.isoformat(), "count": count}
                        for date, count in daily_counts
                    ],
                },
                confidence=1.0,
            )

        except Exception as e:
            logger.error(f"Failed to analyze message frequency: {e}")
            return None

    async def _identify_trending_topics(
        self,
        contact_id: UUID,
        db: AsyncSession,
        days: int,
    ) -> list[CommunicationInsight]:
        """
        Identify trending topics in conversations.

        Args:
            contact_id: Contact ID
            db: Database session
            days: Number of days to analyze

        Returns:
            List of topic insights
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Get threads for contact
            result = await db.execute(
                select(Thread).where(Thread.contact_id == contact_id)
            )
            threads = result.scalars().all()

            if not threads:
                return []

            thread_ids = [str(t.id) for t in threads]

            # Get messages
            result = await db.execute(
                select(Message)
                .where(Message.thread_id.in_(thread_ids))
                .where(Message.timestamp >= cutoff_date)
            )
            messages = result.scalars().all()

            if not messages:
                return []

            message_ids = [msg.id for msg in messages]

            # Get entities from messages
            result = await db.execute(
                select(Entity)
                .where(Entity.message_id.in_(message_ids))
                .where(Entity.entity_type.in_(["ORG", "PRODUCT", "EVENT", "TOPIC"]))
            )
            entities = result.scalars().all()

            if not entities:
                return []

            # Count entity occurrences
            entity_counts = Counter(entity.entity_text.lower() for entity in entities)

            # Get top topics
            top_topics = entity_counts.most_common(5)

            if not top_topics:
                return []

            insights = []

            # Create insight for top topics
            topic_list = [f"{topic} ({count} mentions)" for topic, count in top_topics]

            insights.append(
                CommunicationInsight(
                    insight_type=InsightType.TOPICS,
                    title="Trending Topics",
                    description=(
                        f"Most discussed topics: {', '.join([t[0] for t in top_topics[:3]])}. "
                        f"These topics appeared frequently in your recent conversations."
                    ),
                    data={
                        "topics": [
                            {"topic": topic, "count": count}
                            for topic, count in top_topics
                        ],
                        "total_entities": len(entities),
                        "unique_topics": len(entity_counts),
                    },
                    confidence=0.8,
                )
            )

            return insights

        except Exception as e:
            logger.error(f"Failed to identify trending topics: {e}")
            return []

    async def _analyze_sentiment(
        self,
        contact_id: UUID,
        db: AsyncSession,
        days: int,
    ) -> Optional[CommunicationInsight]:
        """
        Analyze sentiment of conversations with a contact.

        Args:
            contact_id: Contact ID
            db: Database session
            days: Number of days to analyze

        Returns:
            Sentiment insight or None
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Get threads for contact
            result = await db.execute(
                select(Thread).where(Thread.contact_id == contact_id)
            )
            threads = result.scalars().all()

            if not threads:
                return None

            thread_ids = [str(t.id) for t in threads]

            # Get recent messages
            result = await db.execute(
                select(Message)
                .where(Message.thread_id.in_(thread_ids))
                .where(Message.timestamp >= cutoff_date)
                .order_by(Message.timestamp.desc())
                .limit(50)
            )
            messages = result.scalars().all()

            if not messages:
                return None

            # Extract text from messages
            texts = []
            for msg in messages:
                text = self._extract_text_from_message(msg)
                if text:
                    texts.append(text)

            if not texts:
                return None

            # Use LLM to analyze sentiment
            sentiment = await self._detect_sentiment_with_llm(texts)

            if not sentiment:
                return None

            return CommunicationInsight(
                insight_type=InsightType.SENTIMENT,
                title=f"{sentiment['overall'].title()} Communication Tone",
                description=sentiment.get("description", ""),
                data={
                    "overall_sentiment": sentiment["overall"],
                    "confidence": sentiment.get("confidence", 0.7),
                    "messages_analyzed": len(texts),
                    "sentiment_breakdown": sentiment.get("breakdown", {}),
                },
                confidence=sentiment.get("confidence", 0.7),
            )

        except Exception as e:
            logger.error(f"Failed to analyze sentiment: {e}")
            return None

    async def _analyze_communication_patterns(
        self,
        contact_id: UUID,
        db: AsyncSession,
        days: int,
    ) -> list[CommunicationInsight]:
        """
        Analyze communication patterns with a contact.

        Args:
            contact_id: Contact ID
            db: Database session
            days: Number of days to analyze

        Returns:
            List of pattern insights
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Get threads for contact
            result = await db.execute(
                select(Thread).where(Thread.contact_id == contact_id)
            )
            threads = result.scalars().all()

            if not threads:
                return []

            thread_ids = [str(t.id) for t in threads]

            # Get messages
            result = await db.execute(
                select(Message)
                .where(Message.thread_id.in_(thread_ids))
                .where(Message.timestamp >= cutoff_date)
            )
            messages = result.scalars().all()

            if not messages:
                return []

            insights = []

            # Analyze time patterns
            time_pattern = self._analyze_time_patterns(messages)
            if time_pattern:
                insights.append(
                    CommunicationInsight(
                        insight_type=InsightType.PATTERNS,
                        title="Communication Time Patterns",
                        description=time_pattern["description"],
                        data=time_pattern["data"],
                        confidence=0.8,
                    )
                )

            # Analyze platform usage
            platform_pattern = self._analyze_platform_patterns(messages)
            if platform_pattern:
                insights.append(
                    CommunicationInsight(
                        insight_type=InsightType.PATTERNS,
                        title="Platform Usage Patterns",
                        description=platform_pattern["description"],
                        data=platform_pattern["data"],
                        confidence=0.9,
                    )
                )

            # Analyze response patterns
            response_pattern = self._analyze_response_patterns(messages)
            if response_pattern:
                insights.append(
                    CommunicationInsight(
                        insight_type=InsightType.PATTERNS,
                        title="Response Patterns",
                        description=response_pattern["description"],
                        data=response_pattern["data"],
                        confidence=0.7,
                    )
                )

            return insights

        except Exception as e:
            logger.error(f"Failed to analyze communication patterns: {e}")
            return []

    async def _detect_sentiment_with_llm(self, texts: list[str]) -> Optional[dict]:
        """
        Detect sentiment using LLM.

        Args:
            texts: List of message texts

        Returns:
            Sentiment analysis result
        """
        try:
            # Sample texts if too many
            sample_texts = texts[:20] if len(texts) > 20 else texts

            # Build prompt
            prompt = f"""Analyze the sentiment of these messages and provide a brief assessment.

Messages:
{chr(10).join(f"- {text[:200]}" for text in sample_texts)}

Provide:
1. Overall sentiment (positive, neutral, negative, or mixed)
2. Brief description of the tone
3. Confidence level (0.0 to 1.0)

Format your response as:
Sentiment: [sentiment]
Description: [description]
Confidence: [confidence]"""

            config = GenerationConfig(
                temperature=0.2,
                max_tokens=200,
            )

            response = await self.llm_provider.generate(
                prompt=prompt,
                model=self.model,
                config=config,
            )

            # Parse response
            lines = response.strip().split("\n")
            sentiment_data = {}

            for line in lines:
                if line.startswith("Sentiment:"):
                    sentiment_data["overall"] = line.split(":", 1)[1].strip().lower()
                elif line.startswith("Description:"):
                    sentiment_data["description"] = line.split(":", 1)[1].strip()
                elif line.startswith("Confidence:"):
                    try:
                        confidence_str = line.split(":", 1)[1].strip()
                        sentiment_data["confidence"] = float(confidence_str)
                    except ValueError:
                        sentiment_data["confidence"] = 0.7

            # Validate sentiment
            if sentiment_data.get("overall") not in [
                "positive",
                "neutral",
                "negative",
                "mixed",
            ]:
                sentiment_data["overall"] = "neutral"

            return sentiment_data

        except Exception as e:
            logger.error(f"Failed to detect sentiment with LLM: {e}")
            return None

    def _analyze_time_patterns(self, messages: list[Message]) -> Optional[dict]:
        """
        Analyze time-based communication patterns.

        Args:
            messages: List of messages

        Returns:
            Time pattern data
        """
        try:
            if not messages:
                return None

            # Count messages by hour of day
            hour_counts = defaultdict(int)
            day_counts = defaultdict(int)

            for msg in messages:
                hour_counts[msg.timestamp.hour] += 1
                day_counts[msg.timestamp.strftime("%A")] += 1

            # Find peak hours
            peak_hour = max(hour_counts.items(), key=lambda x: x[1])

            # Find peak day
            peak_day = max(day_counts.items(), key=lambda x: x[1])

            # Determine time preference
            morning = sum(hour_counts[h] for h in range(6, 12))
            afternoon = sum(hour_counts[h] for h in range(12, 18))
            evening = sum(hour_counts[h] for h in range(18, 24))
            night = sum(hour_counts[h] for h in range(0, 6))

            time_periods = {
                "morning": morning,
                "afternoon": afternoon,
                "evening": evening,
                "night": night,
            }

            preferred_time = max(time_periods.items(), key=lambda x: x[1])[0]

            return {
                "description": (
                    f"Most active during {preferred_time} hours. "
                    f"Peak activity: {peak_hour[1]} messages at {peak_hour[0]:02d}:00. "
                    f"Most active day: {peak_day[0]} ({peak_day[1]} messages)."
                ),
                "data": {
                    "peak_hour": peak_hour[0],
                    "peak_hour_count": peak_hour[1],
                    "peak_day": peak_day[0],
                    "peak_day_count": peak_day[1],
                    "preferred_time": preferred_time,
                    "time_distribution": time_periods,
                    "hourly_distribution": dict(hour_counts),
                    "daily_distribution": dict(day_counts),
                },
            }

        except Exception as e:
            logger.error(f"Failed to analyze time patterns: {e}")
            return None

    def _analyze_platform_patterns(self, messages: list[Message]) -> Optional[dict]:
        """
        Analyze platform usage patterns.

        Args:
            messages: List of messages

        Returns:
            Platform pattern data
        """
        try:
            if not messages:
                return None

            # Count messages by platform
            platform_counts = Counter(msg.platform for msg in messages)

            if not platform_counts:
                return None

            total = sum(platform_counts.values())
            primary_platform = platform_counts.most_common(1)[0]

            # Calculate percentages
            platform_percentages = {
                platform: (count / total) * 100
                for platform, count in platform_counts.items()
            }

            return {
                "description": (
                    f"Primary communication platform: {primary_platform[0]} "
                    f"({primary_platform[1]} messages, "
                    f"{platform_percentages[primary_platform[0]]:.1f}%). "
                    f"Uses {len(platform_counts)} platform(s) total."
                ),
                "data": {
                    "primary_platform": primary_platform[0],
                    "primary_count": primary_platform[1],
                    "platform_counts": dict(platform_counts),
                    "platform_percentages": platform_percentages,
                    "total_platforms": len(platform_counts),
                },
            }

        except Exception as e:
            logger.error(f"Failed to analyze platform patterns: {e}")
            return None

    def _analyze_response_patterns(self, messages: list[Message]) -> Optional[dict]:
        """
        Analyze response time patterns.

        Args:
            messages: List of messages

        Returns:
            Response pattern data
        """
        try:
            if len(messages) < 2:
                return None

            # Sort messages by timestamp
            sorted_messages = sorted(messages, key=lambda m: m.timestamp)

            # Calculate response times (time between consecutive messages)
            response_times = []
            for i in range(1, len(sorted_messages)):
                time_diff = (
                    sorted_messages[i].timestamp - sorted_messages[i - 1].timestamp
                ).total_seconds() / 60  # Convert to minutes

                # Only consider reasonable response times (< 24 hours)
                if time_diff < 1440:
                    response_times.append(time_diff)

            if not response_times:
                return None

            # Calculate statistics
            avg_response = sum(response_times) / len(response_times)

            # Categorize response speed
            if avg_response < 5:
                speed = "very fast"
            elif avg_response < 30:
                speed = "fast"
            elif avg_response < 120:
                speed = "moderate"
            elif avg_response < 360:
                speed = "slow"
            else:
                speed = "very slow"

            return {
                "description": (
                    f"Average response time: {avg_response:.1f} minutes ({speed}). "
                    f"Based on {len(response_times)} message exchanges."
                ),
                "data": {
                    "avg_response_minutes": round(avg_response, 2),
                    "response_speed": speed,
                    "sample_size": len(response_times),
                },
            }

        except Exception as e:
            logger.error(f"Failed to analyze response patterns: {e}")
            return None

    def _extract_text_from_message(self, message: Message) -> str:
        """
        Extract text content from message.

        Args:
            message: Message object

        Returns:
            Text content
        """
        try:
            content = message.content

            if isinstance(content, dict):
                text = content.get("text", "")

                if not text:
                    text = content.get("html", "")

                return text.strip()

            if isinstance(content, str):
                return content.strip()

            return ""

        except Exception as e:
            logger.error(f"Failed to extract text from message: {e}")
            return ""

    async def health_check(self) -> bool:
        """
        Check health of insight generator.

        Returns:
            True if healthy
        """
        try:
            return await self.llm_provider.health_check()
        except Exception as e:
            logger.error(f"Insight generator health check failed: {e}")
            return False


# Global service instance
_insight_generator: Optional[InsightGenerator] = None


def get_insight_generator() -> InsightGenerator:
    """
    Get the global insight generator instance.

    Returns:
        Insight generator
    """
    global _insight_generator

    if _insight_generator is None:
        _insight_generator = InsightGenerator()

    return _insight_generator


__all__ = [
    "InsightGenerator",
    "InsightType",
    "SentimentType",
    "CommunicationInsight",
    "get_insight_generator",
]
