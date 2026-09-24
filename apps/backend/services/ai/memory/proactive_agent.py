"""
Proactive Memory Agent

Advanced memory management system that:
- Proactively recalls relevant context
- Manages memory importance and decay
- Consolidates memories over time
- Provides context-aware recommendations
- Tracks commitments and follow-ups
- Builds contact dossiers
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import settings
from db.models.contact import Contact
from db.models.entity import Entity
from db.models.memory import Memory, MemoryImportance, MemoryType
from db.models.message import Message
from db.models.summary import Summary
from services.ai.embeddings import EmbeddingService, get_embedding_service
from services.ai.providers import GenerationConfig, LLMProvider, get_llm_provider
from services.vector_db.chroma_client import ChromaDBClient, get_chroma_client

logger = logging.getLogger(__name__)


class MemoryRecallType(str, Enum):
    """Types of memory recall."""

    CONTEXTUAL = "contextual"  # Based on current context
    TEMPORAL = "temporal"  # Based on time patterns
    SEMANTIC = "semantic"  # Based on content similarity
    COMMITMENT = "commitment"  # Based on commitments and follow-ups
    RELATIONSHIP = "relationship"  # Based on contact relationships


class MemoryRecommendation(BaseModel):
    """Memory-based recommendation."""

    type: str = Field(description="Recommendation type")
    title: str = Field(description="Recommendation title")
    description: str = Field(description="Recommendation description")
    priority: float = Field(description="Priority score (0.0 to 1.0)")
    memory_ids: List[UUID] = Field(description="Related memory IDs")
    suggested_action: Optional[str] = Field(None, description="Suggested action")
    due_date: Optional[datetime] = Field(None, description="Due date if applicable")
    contact_id: Optional[UUID] = Field(None, description="Related contact")


class MemoryContext(BaseModel):
    """Context for memory operations."""

    current_contact: Optional[UUID] = Field(None, description="Current contact")
    current_thread: Optional[str] = Field(None, description="Current thread")
    current_platform: Optional[str] = Field(None, description="Current platform")
    keywords: List[str] = Field(default_factory=list, description="Context keywords")
    entities: List[str] = Field(default_factory=list, description="Context entities")
    time_window: Optional[Tuple[datetime, datetime]] = Field(
        None, description="Time window"
    )


class ProactiveMemoryAgent:
    """
    Proactive memory management agent.

    Provides functionality for:
    - Proactive memory recall based on context
    - Memory importance scoring and decay
    - Memory consolidation and cleanup
    - Context-aware recommendations
    - Commitment tracking and reminders
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        embedding_service: Optional[EmbeddingService] = None,
        chroma_client: Optional[ChromaDBClient] = None,
        memory_decay_days: int = 30,
        consolidation_threshold: int = 10,
    ):
        """
        Initialize proactive memory agent.

        Args:
            llm_provider: LLM provider for analysis
            embedding_service: Embedding service for similarity
            chroma_client: Vector database client
            memory_decay_days: Days after which memories start decaying
            consolidation_threshold: Number of similar memories to trigger consolidation
        """
        self.llm_provider = llm_provider or get_llm_provider()
        self.embedding_service = embedding_service or get_embedding_service()
        self.chroma_client = chroma_client or get_chroma_client()
        self.memory_decay_days = memory_decay_days
        self.consolidation_threshold = consolidation_threshold

        logger.info(
            f"Initialized ProactiveMemoryAgent with decay_days={memory_decay_days}, "
            f"consolidation_threshold={consolidation_threshold}"
        )

    # =============================================================================
    # Memory Recall
    # =============================================================================

    async def recall_memories(
        self,
        db: AsyncSession,
        context: MemoryContext,
        recall_types: List[MemoryRecallType],
        limit: int = 20,
        min_relevance: float = 0.3,
    ) -> List[Memory]:
        """
        Proactively recall relevant memories based on context.

        Args:
            db: Database session
            context: Current context
            recall_types: Types of recall to perform
            limit: Maximum memories to recall
            min_relevance: Minimum relevance score

        Returns:
            List of relevant memories
        """
        all_memories = []

        for recall_type in recall_types:
            try:
                if recall_type == MemoryRecallType.CONTEXTUAL:
                    memories = await self._recall_contextual(
                        db, context, limit // len(recall_types)
                    )
                elif recall_type == MemoryRecallType.TEMPORAL:
                    memories = await self._recall_temporal(
                        db, context, limit // len(recall_types)
                    )
                elif recall_type == MemoryRecallType.SEMANTIC:
                    memories = await self._recall_semantic(
                        db, context, limit // len(recall_types)
                    )
                elif recall_type == MemoryRecallType.COMMITMENT:
                    memories = await self._recall_commitments(
                        db, context, limit // len(recall_types)
                    )
                elif recall_type == MemoryRecallType.RELATIONSHIP:
                    memories = await self._recall_relationship(
                        db, context, limit // len(recall_types)
                    )
                else:
                    continue

                all_memories.extend(memories)

            except Exception as e:
                logger.error(f"Failed to recall {recall_type} memories: {e}")
                continue

        # Remove duplicates and sort by relevance
        unique_memories = {}
        for memory in all_memories:
            if memory.id not in unique_memories:
                unique_memories[memory.id] = memory

        # Calculate relevance scores and filter
        relevant_memories = []
        for memory in unique_memories.values():
            relevance = await self._calculate_memory_relevance(memory, context)
            if relevance >= min_relevance:
                memory.relevance_score = relevance  # Add dynamic attribute
                relevant_memories.append(memory)

        # Sort by relevance and importance
        relevant_memories.sort(
            key=lambda m: (getattr(m, "relevance_score", 0.0), m.importance.value),
            reverse=True,
        )

        logger.info(f"Recalled {len(relevant_memories)} relevant memories")
        return relevant_memories[:limit]

    async def _recall_contextual(
        self,
        db: AsyncSession,
        context: MemoryContext,
        limit: int,
    ) -> List[Memory]:
        """Recall memories based on current context."""
        query = select(Memory).where(
            and_(
                Memory.is_active == True,
                Memory.importance != MemoryImportance.VERY_LOW,
            )
        )

        # Filter by contact
        if context.current_contact:
            query = query.where(Memory.contact_id == context.current_contact)

        # Filter by platform
        if context.current_platform:
            query = query.where(
                Memory.memory_metadata.op("->>")("platform") == context.current_platform
            )

        # Filter by keywords in content
        if context.keywords:
            keyword_conditions = []
            for keyword in context.keywords:
                keyword_conditions.append(Memory.content.ilike(f"%{keyword}%"))
            query = query.where(or_(*keyword_conditions))

        query = query.order_by(desc(Memory.last_accessed_at)).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def _recall_temporal(
        self,
        db: AsyncSession,
        context: MemoryContext,
        limit: int,
    ) -> List[Memory]:
        """Recall memories based on temporal patterns."""
        now = datetime.utcnow()

        # Look for memories from similar time periods (same day of week, month, etc.)
        query = select(Memory).where(
            and_(
                Memory.is_active == True,
                Memory.importance != MemoryImportance.VERY_LOW,
                # Memories from the same day of week in previous weeks
                func.extract("dow", Memory.created_at) == func.extract("dow", now),
            )
        )

        if context.time_window:
            start_time, end_time = context.time_window
            query = query.where(
                and_(
                    Memory.created_at >= start_time,
                    Memory.created_at <= end_time,
                )
            )

        query = query.order_by(desc(Memory.importance), desc(Memory.created_at)).limit(
            limit
        )

        result = await db.execute(query)
        return result.scalars().all()

    async def _recall_semantic(
        self,
        db: AsyncSession,
        context: MemoryContext,
        limit: int,
    ) -> List[Memory]:
        """Recall memories based on semantic similarity."""
        if not context.keywords and not context.entities:
            return []

        # Create query text from context
        query_text = " ".join(context.keywords + context.entities)

        try:
            # Get similar memories from vector database
            search_results = await self.chroma_client.search(
                query_text=query_text,
                collection_name="memories",
                limit=limit * 2,  # Get more to filter
                min_score=0.3,
            )

            # Get memory IDs from search results
            memory_ids = [
                UUID(result.metadata.get("memory_id")) for result in search_results
            ]

            if not memory_ids:
                return []

            # Fetch memories from database
            query = select(Memory).where(
                and_(
                    Memory.id.in_(memory_ids),
                    Memory.is_active == True,
                )
            )

            result = await db.execute(query)
            return result.scalars().all()[:limit]

        except Exception as e:
            logger.error(f"Failed semantic memory recall: {e}")
            return []

    async def _recall_commitments(
        self,
        db: AsyncSession,
        context: MemoryContext,
        limit: int,
    ) -> List[Memory]:
        """Recall commitment-related memories."""
        query = select(Memory).where(
            and_(
                Memory.is_active == True,
                Memory.type == MemoryType.COMMITMENT,
                Memory.importance.in_(
                    [MemoryImportance.HIGH, MemoryImportance.VERY_HIGH]
                ),
            )
        )

        # Filter by contact if specified
        if context.current_contact:
            query = query.where(Memory.contact_id == context.current_contact)

        # Look for overdue or upcoming commitments
        now = datetime.utcnow()
        query = query.where(
            or_(
                # Overdue commitments
                and_(
                    Memory.memory_metadata.op("->>")("due_date").isnot(None),
                    func.cast(Memory.memory_metadata.op("->>")("due_date"), db.DateTime)
                    < now,
                ),
                # Upcoming commitments (next 7 days)
                and_(
                    Memory.memory_metadata.op("->>")("due_date").isnot(None),
                    func.cast(Memory.memory_metadata.op("->>")("due_date"), db.DateTime)
                    <= now + timedelta(days=7),
                ),
            )
        )

        query = query.order_by(
            func.cast(Memory.memory_metadata.op("->>")("due_date"), db.DateTime)
        ).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def _recall_relationship(
        self,
        db: AsyncSession,
        context: MemoryContext,
        limit: int,
    ) -> List[Memory]:
        """Recall relationship-related memories."""
        if not context.current_contact:
            return []

        query = select(Memory).where(
            and_(
                Memory.is_active == True,
                Memory.contact_id == context.current_contact,
                Memory.type.in_([MemoryType.PERSONAL, MemoryType.RELATIONSHIP]),
            )
        )

        query = query.order_by(
            desc(Memory.importance), desc(Memory.last_accessed_at)
        ).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def _calculate_memory_relevance(
        self,
        memory: Memory,
        context: MemoryContext,
    ) -> float:
        """Calculate relevance score for a memory given context."""
        relevance = 0.0

        # Base relevance from importance
        importance_scores = {
            MemoryImportance.VERY_LOW: 0.1,
            MemoryImportance.LOW: 0.3,
            MemoryImportance.MEDIUM: 0.5,
            MemoryImportance.HIGH: 0.7,
            MemoryImportance.VERY_HIGH: 0.9,
        }
        relevance += importance_scores.get(memory.importance, 0.5)

        # Recency boost
        days_old = (datetime.utcnow() - memory.created_at).days
        recency_boost = max(0.0, 1.0 - (days_old / 30.0))  # Decay over 30 days
        relevance += recency_boost * 0.3

        # Context matching
        if context.current_contact and memory.contact_id == context.current_contact:
            relevance += 0.4

        if context.current_platform:
            memory_platform = (
                memory.memory_metadata.get("platform")
                if memory.memory_metadata
                else None
            )
            if memory_platform == context.current_platform:
                relevance += 0.2

        # Keyword matching
        if context.keywords:
            content_lower = memory.content.lower()
            keyword_matches = sum(
                1 for keyword in context.keywords if keyword.lower() in content_lower
            )
            relevance += (keyword_matches / len(context.keywords)) * 0.3

        # Access frequency boost
        if memory.access_count > 1:
            frequency_boost = min(0.2, memory.access_count * 0.05)
            relevance += frequency_boost

        return min(1.0, relevance)

    # =============================================================================
    # Memory Importance and Decay
    # =============================================================================

    async def update_memory_importance(
        self,
        db: AsyncSession,
        memory_id: UUID,
        new_importance: MemoryImportance,
        reason: Optional[str] = None,
    ) -> bool:
        """Update memory importance with reasoning."""
        try:
            query = select(Memory).where(Memory.id == memory_id)
            result = await db.execute(query)
            memory = result.scalar_one_or_none()

            if not memory:
                return False

            old_importance = memory.importance
            memory.importance = new_importance
            memory.updated_at = datetime.utcnow()

            # Update metadata with change reason
            if not memory.memory_metadata:
                memory.memory_metadata = {}

            if "importance_history" not in memory.memory_metadata:
                memory.memory_metadata["importance_history"] = []

            memory.memory_metadata["importance_history"].append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "old_importance": old_importance.value,
                    "new_importance": new_importance.value,
                    "reason": reason,
                }
            )

            await db.commit()

            logger.info(
                f"Updated memory {memory_id} importance: {old_importance} -> {new_importance}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to update memory importance: {e}")
            await db.rollback()
            return False

    async def apply_memory_decay(
        self,
        db: AsyncSession,
        decay_factor: float = 0.1,
        min_importance: MemoryImportance = MemoryImportance.VERY_LOW,
    ) -> int:
        """Apply time-based decay to memory importance."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.memory_decay_days)

            # Find memories that haven't been accessed recently
            query = select(Memory).where(
                and_(
                    Memory.is_active == True,
                    Memory.last_accessed_at < cutoff_date,
                    Memory.importance != min_importance,
                )
            )

            result = await db.execute(query)
            memories = result.scalars().all()

            decayed_count = 0

            for memory in memories:
                # Calculate decay based on time since last access
                days_since_access = (datetime.utcnow() - memory.last_accessed_at).days
                decay_amount = min(
                    1, (days_since_access / self.memory_decay_days) * decay_factor
                )

                # Don't decay very important memories as much
                if memory.importance == MemoryImportance.VERY_HIGH:
                    decay_amount *= 0.5
                elif memory.importance == MemoryImportance.HIGH:
                    decay_amount *= 0.7

                # Apply decay if significant
                if decay_amount > 0.3:
                    current_value = memory.importance.value
                    new_value = max(min_importance.value, current_value - 1)

                    if new_value != current_value:
                        new_importance = MemoryImportance(new_value)
                        await self.update_memory_importance(
                            db,
                            memory.id,
                            new_importance,
                            f"Time-based decay (unused for {days_since_access} days)",
                        )
                        decayed_count += 1

            logger.info(f"Applied decay to {decayed_count} memories")
            return decayed_count

        except Exception as e:
            logger.error(f"Failed to apply memory decay: {e}")
            return 0

    # =============================================================================
    # Memory Consolidation
    # =============================================================================

    async def consolidate_memories(
        self,
        db: AsyncSession,
        contact_id: Optional[UUID] = None,
        similarity_threshold: float = 0.8,
    ) -> int:
        """Consolidate similar memories to reduce redundancy."""
        try:
            # Find memories to consolidate
            query = select(Memory).where(
                and_(
                    Memory.is_active == True,
                    Memory.importance
                    != MemoryImportance.VERY_HIGH,  # Don't consolidate very important memories
                )
            )

            if contact_id:
                query = query.where(Memory.contact_id == contact_id)

            result = await db.execute(query)
            memories = result.scalars().all()

            if len(memories) < 2:
                return 0

            consolidated_count = 0
            processed_ids = set()

            for i, memory1 in enumerate(memories):
                if memory1.id in processed_ids:
                    continue

                similar_memories = [memory1]

                for j, memory2 in enumerate(memories[i + 1 :], i + 1):
                    if memory2.id in processed_ids:
                        continue

                    # Check similarity
                    similarity = await self._calculate_memory_similarity(
                        memory1, memory2
                    )

                    if similarity >= similarity_threshold:
                        similar_memories.append(memory2)
                        processed_ids.add(memory2.id)

                # Consolidate if we have enough similar memories
                if len(similar_memories) >= self.consolidation_threshold:
                    consolidated_memory = await self._create_consolidated_memory(
                        db, similar_memories
                    )

                    if consolidated_memory:
                        # Mark original memories as consolidated
                        for memory in similar_memories:
                            memory.is_active = False
                            memory.memory_metadata = memory.memory_metadata or {}
                            memory.memory_metadata["consolidated_into"] = str(
                                consolidated_memory.id
                            )
                            memory.updated_at = datetime.utcnow()

                        consolidated_count += len(similar_memories)
                        processed_ids.update(m.id for m in similar_memories)

            await db.commit()

            logger.info(f"Consolidated {consolidated_count} memories")
            return consolidated_count

        except Exception as e:
            logger.error(f"Failed to consolidate memories: {e}")
            await db.rollback()
            return 0

    async def _calculate_memory_similarity(
        self,
        memory1: Memory,
        memory2: Memory,
    ) -> float:
        """Calculate similarity between two memories."""
        # Basic similarity checks
        similarity = 0.0

        # Same contact
        if memory1.contact_id == memory2.contact_id:
            similarity += 0.3

        # Same type
        if memory1.type == memory2.type:
            similarity += 0.2

        # Content similarity using embeddings
        try:
            embedding1 = await self.embedding_service.get_embedding(memory1.content)
            embedding2 = await self.embedding_service.get_embedding(memory2.content)

            # Calculate cosine similarity
            import numpy as np

            dot_product = np.dot(embedding1, embedding2)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)

            if norm1 > 0 and norm2 > 0:
                cosine_sim = dot_product / (norm1 * norm2)
                similarity += cosine_sim * 0.5

        except Exception as e:
            logger.warning(f"Failed to calculate embedding similarity: {e}")
            # Fallback to simple text similarity
            common_words = set(memory1.content.lower().split()) & set(
                memory2.content.lower().split()
            )
            total_words = len(
                set(memory1.content.lower().split())
                | set(memory2.content.lower().split())
            )
            if total_words > 0:
                similarity += (len(common_words) / total_words) * 0.3

        return min(1.0, similarity)

    async def _create_consolidated_memory(
        self,
        db: AsyncSession,
        memories: List[Memory],
    ) -> Optional[Memory]:
        """Create a consolidated memory from similar memories."""
        try:
            # Use LLM to create consolidated content
            memory_contents = [
                f"Memory {i+1}: {m.content}" for i, m in enumerate(memories)
            ]
            content_text = "\n\n".join(memory_contents)

            prompt = f"""
            Consolidate the following similar memories into a single, comprehensive memory:

            {content_text}

            Create a consolidated memory that:
            1. Captures all important information
            2. Removes redundancy
            3. Maintains chronological context
            4. Is clear and concise

            Consolidated Memory:
            """

            config = GenerationConfig(temperature=0.1, max_tokens=500)
            consolidated_content = await self.llm_provider.generate(
                prompt, config=config
            )

            # Determine consolidated memory properties
            highest_importance = max(m.importance for m in memories)
            most_recent = max(memories, key=lambda m: m.created_at)

            # Create consolidated memory
            consolidated_memory = Memory(
                type=most_recent.type,
                content=consolidated_content.strip(),
                importance=highest_importance,
                contact_id=most_recent.contact_id,
                thread_id=most_recent.thread_id,
                platform=most_recent.platform,
                memory_metadata={
                    "consolidated_from": [str(m.id) for m in memories],
                    "consolidation_date": datetime.utcnow().isoformat(),
                    "original_count": len(memories),
                },
                is_active=True,
                access_count=sum(m.access_count for m in memories),
                last_accessed_at=max(m.last_accessed_at for m in memories),
            )

            db.add(consolidated_memory)
            await db.flush()  # Get the ID

            logger.info(
                f"Created consolidated memory {consolidated_memory.id} from {len(memories)} memories"
            )
            return consolidated_memory

        except Exception as e:
            logger.error(f"Failed to create consolidated memory: {e}")
            return None

    # =============================================================================
    # Recommendations
    # =============================================================================

    async def generate_recommendations(
        self,
        db: AsyncSession,
        context: MemoryContext,
        limit: int = 10,
    ) -> List[MemoryRecommendation]:
        """Generate proactive recommendations based on memories."""
        recommendations = []

        try:
            # Get relevant memories
            memories = await self.recall_memories(
                db,
                context,
                [
                    MemoryRecallType.COMMITMENT,
                    MemoryRecallType.CONTEXTUAL,
                    MemoryRecallType.RELATIONSHIP,
                ],
                limit=50,
            )

            # Generate different types of recommendations
            recommendations.extend(
                await self._generate_commitment_recommendations(memories)
            )
            recommendations.extend(
                await self._generate_follow_up_recommendations(memories)
            )
            recommendations.extend(
                await self._generate_relationship_recommendations(memories)
            )
            recommendations.extend(
                await self._generate_context_recommendations(memories, context)
            )

            # Sort by priority and limit
            recommendations.sort(key=lambda r: r.priority, reverse=True)

            logger.info(f"Generated {len(recommendations)} recommendations")
            return recommendations[:limit]

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return []

    async def _generate_commitment_recommendations(
        self,
        memories: List[Memory],
    ) -> List[MemoryRecommendation]:
        """Generate commitment-based recommendations."""
        recommendations = []

        for memory in memories:
            if memory.type != MemoryType.COMMITMENT:
                continue

            metadata = memory.memory_metadata or {}
            due_date_str = metadata.get("due_date")

            if due_date_str:
                try:
                    due_date = datetime.fromisoformat(due_date_str)
                    now = datetime.utcnow()

                    if due_date < now:
                        # Overdue commitment
                        days_overdue = (now - due_date).days
                        recommendations.append(
                            MemoryRecommendation(
                                type="overdue_commitment",
                                title=f"Overdue Commitment ({days_overdue} days)",
                                description=(
                                    memory.content[:200] + "..."
                                    if len(memory.content) > 200
                                    else memory.content
                                ),
                                priority=0.9,
                                memory_ids=[memory.id],
                                suggested_action="Follow up on this commitment",
                                due_date=due_date,
                                contact_id=memory.contact_id,
                            )
                        )
                    elif due_date <= now + timedelta(days=3):
                        # Upcoming commitment
                        days_until = (due_date - now).days
                        recommendations.append(
                            MemoryRecommendation(
                                type="upcoming_commitment",
                                title=f"Upcoming Commitment ({days_until} days)",
                                description=(
                                    memory.content[:200] + "..."
                                    if len(memory.content) > 200
                                    else memory.content
                                ),
                                priority=0.7,
                                memory_ids=[memory.id],
                                suggested_action="Prepare for this commitment",
                                due_date=due_date,
                                contact_id=memory.contact_id,
                            )
                        )

                except ValueError:
                    continue

        return recommendations

    async def _generate_follow_up_recommendations(
        self,
        memories: List[Memory],
    ) -> List[MemoryRecommendation]:
        """Generate follow-up recommendations."""
        recommendations = []

        # Look for memories that might need follow-up
        for memory in memories:
            if memory.type in [MemoryType.TASK, MemoryType.COMMITMENT]:
                days_since_created = (datetime.utcnow() - memory.created_at).days

                if days_since_created >= 7 and memory.access_count <= 1:
                    recommendations.append(
                        MemoryRecommendation(
                            type="follow_up",
                            title="Follow-up Needed",
                            description=f"No recent activity on: {memory.content[:100]}...",
                            priority=0.6,
                            memory_ids=[memory.id],
                            suggested_action="Check status and follow up",
                            contact_id=memory.contact_id,
                        )
                    )

        return recommendations

    async def _generate_relationship_recommendations(
        self,
        memories: List[Memory],
    ) -> List[MemoryRecommendation]:
        """Generate relationship-based recommendations."""
        recommendations = []

        # Group memories by contact
        contact_memories = {}
        for memory in memories:
            if memory.contact_id:
                if memory.contact_id not in contact_memories:
                    contact_memories[memory.contact_id] = []
                contact_memories[memory.contact_id].append(memory)

        # Generate recommendations for each contact
        for contact_id, contact_mems in contact_memories.items():
            if len(contact_mems) >= 3:  # Significant relationship
                last_interaction = max(contact_mems, key=lambda m: m.created_at)
                days_since = (datetime.utcnow() - last_interaction.created_at).days

                if days_since >= 14:  # Haven't interacted in 2 weeks
                    recommendations.append(
                        MemoryRecommendation(
                            type="relationship_maintenance",
                            title="Reconnect with Contact",
                            description=f"No recent interaction for {days_since} days",
                            priority=0.5,
                            memory_ids=[
                                m.id for m in contact_mems[-3:]
                            ],  # Last 3 memories
                            suggested_action="Reach out to maintain relationship",
                            contact_id=contact_id,
                        )
                    )

        return recommendations

    async def _generate_context_recommendations(
        self,
        memories: List[Memory],
        context: MemoryContext,
    ) -> List[MemoryRecommendation]:
        """Generate context-aware recommendations."""
        recommendations = []

        # Look for patterns in current context
        if context.current_contact and context.keywords:
            relevant_memories = [
                m
                for m in memories
                if m.contact_id == context.current_contact
                and any(
                    keyword.lower() in m.content.lower() for keyword in context.keywords
                )
            ]

            if relevant_memories:
                recommendations.append(
                    MemoryRecommendation(
                        type="context_reminder",
                        title="Relevant Context",
                        description=f"Found {len(relevant_memories)} related memories for current conversation",
                        priority=0.4,
                        memory_ids=[m.id for m in relevant_memories[:5]],
                        suggested_action="Review related context",
                        contact_id=context.current_contact,
                    )
                )

        return recommendations
