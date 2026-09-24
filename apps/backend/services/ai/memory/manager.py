"""
Memory Management Service

Centralized service for managing the memory system:
- Memory creation and storage
- Automatic memory extraction from messages
- Memory retrieval and search
- Integration with proactive memory agent
- Memory lifecycle management
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import settings
from db.models.contact import Contact
from db.models.entity import Entity
from db.models.memory import Memory, MemoryImportance, MemoryType
from db.models.message import Message
from services.ai.embeddings import EmbeddingService, get_embedding_service
from services.ai.memory.proactive_agent import (
    MemoryContext,
    MemoryRecallType,
    MemoryRecommendation,
    ProactiveMemoryAgent,
)
from services.ai.providers import GenerationConfig, LLMProvider, get_llm_provider
from services.vector_db.chroma_client import ChromaDBClient, get_chroma_client

logger = logging.getLogger(__name__)


class MemoryExtractionResult(BaseModel):
    """Result of memory extraction from a message."""

    memories: List[Dict[str, Any]] = Field(description="Extracted memories")
    entities_found: List[str] = Field(description="Entities found in message")
    commitments_found: List[Dict[str, Any]] = Field(description="Commitments found")
    topics: List[str] = Field(description="Topics identified")
    confidence: float = Field(description="Extraction confidence")


class MemorySearchResult(BaseModel):
    """Memory search result."""

    memory_id: UUID = Field(description="Memory ID")
    memory_type: str = Field(description="Memory type")
    content: str = Field(description="Memory content")
    importance: int = Field(description="Memory importance")
    relevance_score: float = Field(description="Relevance score")
    snippet: str = Field(description="Relevant snippet")

    class Config:
        from_attributes = True


class MemoryManager:
    """
    Centralized memory management service.

    Provides functionality for:
    - Automatic memory extraction from messages
    - Memory storage and retrieval
    - Memory search and filtering
    - Integration with proactive memory agent
    - Memory lifecycle management
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        embedding_service: Optional[EmbeddingService] = None,
        chroma_client: Optional[ChromaDBClient] = None,
        proactive_agent: Optional[ProactiveMemoryAgent] = None,
    ):
        """
        Initialize memory manager.

        Args:
            llm_provider: LLM provider for extraction and analysis
            embedding_service: Embedding service for similarity
            chroma_client: Vector database client
            proactive_agent: Proactive memory agent
        """
        self.llm_provider = llm_provider or get_llm_provider()
        self.embedding_service = embedding_service or get_embedding_service()
        self.chroma_client = chroma_client or get_chroma_client()
        self.proactive_agent = proactive_agent or ProactiveMemoryAgent(
            llm_provider=self.llm_provider,
            embedding_service=self.embedding_service,
            chroma_client=self.chroma_client,
        )

        logger.info("Initialized MemoryManager")

    # =============================================================================
    # Memory Extraction
    # =============================================================================

    async def extract_memories_from_message(
        self,
        db: AsyncSession,
        message: Message,
        auto_store: bool = True,
    ) -> MemoryExtractionResult:
        """
        Extract memories from a message using AI.

        Args:
            db: Database session
            message: Message to extract memories from
            auto_store: Whether to automatically store extracted memories

        Returns:
            Memory extraction result
        """
        try:
            # Build extraction prompt
            prompt = self._build_extraction_prompt(message)

            # Generate extraction using LLM
            config = GenerationConfig(temperature=0.1, max_tokens=1000)
            response = await self.llm_provider.generate(prompt, config=config)

            # Parse extraction result
            extraction_result = await self._parse_extraction_response(response, message)

            # Store memories if requested
            if auto_store and extraction_result.memories:
                stored_memories = []
                for memory_data in extraction_result.memories:
                    memory = await self.create_memory(
                        db=db,
                        type=MemoryType(memory_data.get("type", "fact")),
                        content=memory_data["content"],
                        importance=MemoryImportance(memory_data.get("importance", 3)),
                        contact_id=message.sender_id,
                        thread_id=message.thread_id,
                        platform=message.platform,
                        source_message_id=message.id,
                        memory_metadata=memory_data.get("metadata", {}),
                    )
                    if memory:
                        stored_memories.append(memory)

                logger.info(
                    f"Stored {len(stored_memories)} memories from message {message.id}"
                )

            return extraction_result

        except Exception as e:
            logger.error(f"Failed to extract memories from message {message.id}: {e}")
            return MemoryExtractionResult(
                memories=[],
                entities_found=[],
                commitments_found=[],
                topics=[],
                confidence=0.0,
            )

    def _build_extraction_prompt(self, message: Message) -> str:
        """Build prompt for memory extraction."""
        content = message.content.get("text", "") if message.content else ""

        prompt = f"""
        Extract important memories from this message:

        Message Content: {content}
        Platform: {message.platform}
        Timestamp: {message.timestamp}

        Extract the following types of information:

        1. FACTS - Important factual information about people, places, events
        2. COMMITMENTS - Promises, deadlines, tasks, appointments
        3. PREFERENCES - Personal preferences, likes, dislikes
        4. RELATIONSHIPS - Information about relationships between people
        5. PERSONAL - Personal information about individuals
        6. TASKS - Action items or things to do

        For each memory, provide:
        - type: One of the types above (lowercase)
        - content: Clear, concise description of the memory
        - importance: 1-5 (1=very low, 5=very high)
        - metadata: Additional context (due_date for commitments, etc.)

        Also identify:
        - entities: People, organizations, locations mentioned
        - commitments: Specific commitments with due dates
        - topics: Main topics discussed

        Format as JSON:
        {{
            "memories": [
                {{
                    "type": "fact",
                    "content": "Description of the memory",
                    "importance": 3,
                    "metadata": {{"key": "value"}}
                }}
            ],
            "entities": ["entity1", "entity2"],
            "commitments": [
                {{
                    "description": "Commitment description",
                    "due_date": "2024-01-15",
                    "priority": "high"
                }}
            ],
            "topics": ["topic1", "topic2"],
            "confidence": 0.8
        }}

        Only extract genuinely important information. Skip small talk and trivial details.
        """

        return prompt

    async def _parse_extraction_response(
        self,
        response: str,
        message: Message,
    ) -> MemoryExtractionResult:
        """Parse LLM response for memory extraction."""
        try:
            import json

            # Try to extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                return MemoryExtractionResult(
                    memories=data.get("memories", []),
                    entities_found=data.get("entities", []),
                    commitments_found=data.get("commitments", []),
                    topics=data.get("topics", []),
                    confidence=data.get("confidence", 0.5),
                )
            else:
                # Fallback: simple text parsing
                return MemoryExtractionResult(
                    memories=[],
                    entities_found=[],
                    commitments_found=[],
                    topics=[],
                    confidence=0.0,
                )

        except Exception as e:
            logger.error(f"Failed to parse extraction response: {e}")
            return MemoryExtractionResult(
                memories=[],
                entities_found=[],
                commitments_found=[],
                topics=[],
                confidence=0.0,
            )

    # =============================================================================
    # Memory CRUD Operations
    # =============================================================================

    async def create_memory(
        self,
        db: AsyncSession,
        type: MemoryType,
        content: str,
        importance: MemoryImportance,
        contact_id: Optional[UUID] = None,
        thread_id: Optional[str] = None,
        platform: Optional[str] = None,
        source_message_id: Optional[UUID] = None,
        memory_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Memory]:
        """Create a new memory."""
        try:
            memory = Memory(
                id=uuid4(),
                type=type,
                content=content,
                importance=importance,
                contact_id=contact_id,
                thread_id=thread_id,
                platform=platform,
                source_message_id=source_message_id,
                memory_metadata=memory_metadata or {},
                is_active=True,
                access_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_accessed_at=datetime.utcnow(),
            )

            db.add(memory)
            await db.flush()  # Get the ID

            # Store embedding in vector database
            try:
                embedding = await self.embedding_service.get_embedding(content)
                await self.chroma_client.add_documents(
                    collection_name="memories",
                    documents=[content],
                    embeddings=[embedding],
                    metadatas=[
                        {
                            "memory_id": str(memory.id),
                            "type": type.value,
                            "importance": importance.value,
                            "platform": platform or "",
                            "contact_id": str(contact_id) if contact_id else "",
                            "created_at": memory.created_at.isoformat(),
                        }
                    ],
                    ids=[str(memory.id)],
                )
            except Exception as e:
                logger.warning(f"Failed to store memory embedding: {e}")

            await db.commit()

            logger.info(f"Created memory {memory.id}: {type.value}")
            return memory

        except Exception as e:
            logger.error(f"Failed to create memory: {e}")
            await db.rollback()
            return None

    async def get_memory(
        self,
        db: AsyncSession,
        memory_id: UUID,
        update_access: bool = True,
    ) -> Optional[Memory]:
        """Get a memory by ID."""
        try:
            query = select(Memory).where(Memory.id == memory_id)
            result = await db.execute(query)
            memory = result.scalar_one_or_none()

            if memory and update_access:
                # Update access tracking
                memory.access_count += 1
                memory.last_accessed_at = datetime.utcnow()
                await db.commit()

            return memory

        except Exception as e:
            logger.error(f"Failed to get memory {memory_id}: {e}")
            return None

    async def update_memory(
        self,
        db: AsyncSession,
        memory_id: UUID,
        content: Optional[str] = None,
        importance: Optional[MemoryImportance] = None,
        memory_metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update a memory."""
        try:
            query = select(Memory).where(Memory.id == memory_id)
            result = await db.execute(query)
            memory = result.scalar_one_or_none()

            if not memory:
                return False

            if content is not None:
                memory.content = content

                # Update embedding
                try:
                    embedding = await self.embedding_service.get_embedding(content)
                    await self.chroma_client.update_documents(
                        collection_name="memories",
                        ids=[str(memory_id)],
                        documents=[content],
                        embeddings=[embedding],
                    )
                except Exception as e:
                    logger.warning(f"Failed to update memory embedding: {e}")

            if importance is not None:
                memory.importance = importance

            if memory_metadata is not None:
                memory.memory_metadata = memory_metadata

            memory.updated_at = datetime.utcnow()
            await db.commit()

            logger.info(f"Updated memory {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            await db.rollback()
            return False

    async def delete_memory(
        self,
        db: AsyncSession,
        memory_id: UUID,
        soft_delete: bool = True,
    ) -> bool:
        """Delete a memory."""
        try:
            query = select(Memory).where(Memory.id == memory_id)
            result = await db.execute(query)
            memory = result.scalar_one_or_none()

            if not memory:
                return False

            if soft_delete:
                memory.is_active = False
                memory.updated_at = datetime.utcnow()
            else:
                await db.delete(memory)

                # Remove from vector database
                try:
                    await self.chroma_client.delete_documents(
                        collection_name="memories",
                        ids=[str(memory_id)],
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete memory embedding: {e}")

            await db.commit()

            logger.info(f"Deleted memory {memory_id} (soft={soft_delete})")
            return True

        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            await db.rollback()
            return False

    # =============================================================================
    # Memory Search and Retrieval
    # =============================================================================

    async def search_memories(
        self,
        db: AsyncSession,
        query: str,
        contact_id: Optional[UUID] = None,
        memory_types: Optional[List[MemoryType]] = None,
        importance_min: Optional[MemoryImportance] = None,
        platform: Optional[str] = None,
        limit: int = 20,
        min_relevance: float = 0.3,
    ) -> List[MemorySearchResult]:
        """Search memories using semantic and metadata filters."""
        try:
            # Semantic search using vector database
            search_results = await self.chroma_client.search(
                query_text=query,
                collection_name="memories",
                limit=limit * 2,  # Get more to filter
                min_score=min_relevance,
                metadata_filter=(
                    {
                        "contact_id": str(contact_id) if contact_id else None,
                        "platform": platform,
                    }
                    if contact_id or platform
                    else None
                ),
            )

            # Get memory IDs from search results
            memory_ids = []
            relevance_scores = {}

            for result in search_results:
                memory_id = UUID(result.metadata.get("memory_id"))
                memory_ids.append(memory_id)
                relevance_scores[memory_id] = result.score

            if not memory_ids:
                return []

            # Build database query with filters
            query_db = select(Memory).where(
                and_(
                    Memory.id.in_(memory_ids),
                    Memory.is_active == True,
                )
            )

            if memory_types:
                query_db = query_db.where(Memory.type.in_(memory_types))

            if importance_min:
                query_db = query_db.where(Memory.importance >= importance_min)

            result = await db.execute(query_db)
            memories = result.scalars().all()

            # Create search results
            search_results = []
            for memory in memories:
                relevance = relevance_scores.get(memory.id, 0.0)
                snippet = self._create_memory_snippet(memory.content, query)

                search_results.append(
                    MemorySearchResult(
                        memory_id=memory.id,
                        memory_type=memory.type,
                        content=memory.content,
                        importance=memory.importance,
                        relevance_score=relevance,
                        snippet=snippet,
                    )
                )

            # Sort by relevance
            search_results.sort(key=lambda r: r.relevance_score, reverse=True)

            logger.info(f"Found {len(search_results)} memories for query: {query}")
            return search_results[:limit]

        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    def _create_memory_snippet(
        self, content: str, query: str, max_length: int = 200
    ) -> str:
        """Create a snippet of memory content highlighting query terms."""
        query_terms = query.lower().split()
        content_lower = content.lower()

        # Find the best position to start the snippet
        best_pos = 0
        best_score = 0

        for i in range(len(content) - max_length + 1):
            snippet = content[i : i + max_length].lower()
            score = sum(1 for term in query_terms if term in snippet)
            if score > best_score:
                best_score = score
                best_pos = i

        # Create snippet
        snippet = content[best_pos : best_pos + max_length]
        if best_pos > 0:
            snippet = "..." + snippet
        if best_pos + max_length < len(content):
            snippet = snippet + "..."

        return snippet

    # =============================================================================
    # Proactive Memory Integration
    # =============================================================================

    async def get_proactive_memories(
        self,
        db: AsyncSession,
        context: MemoryContext,
        recall_types: Optional[List[MemoryRecallType]] = None,
        limit: int = 10,
    ) -> List[Memory]:
        """Get proactively recalled memories for context."""
        if recall_types is None:
            recall_types = [
                MemoryRecallType.CONTEXTUAL,
                MemoryRecallType.COMMITMENT,
                MemoryRecallType.RELATIONSHIP,
            ]

        return await self.proactive_agent.recall_memories(
            db=db,
            context=context,
            recall_types=recall_types,
            limit=limit,
        )

    async def get_recommendations(
        self,
        db: AsyncSession,
        context: MemoryContext,
        limit: int = 10,
    ) -> List[MemoryRecommendation]:
        """Get proactive recommendations based on memories."""
        return await self.proactive_agent.generate_recommendations(
            db=db,
            context=context,
            limit=limit,
        )

    # =============================================================================
    # Memory Maintenance
    # =============================================================================

    async def run_maintenance(
        self,
        db: AsyncSession,
        apply_decay: bool = True,
        consolidate_memories: bool = True,
    ) -> Dict[str, int]:
        """Run memory maintenance tasks."""
        results = {
            "decayed_memories": 0,
            "consolidated_memories": 0,
            "cleaned_memories": 0,
        }

        try:
            if apply_decay:
                results["decayed_memories"] = (
                    await self.proactive_agent.apply_memory_decay(db)
                )

            if consolidate_memories:
                results["consolidated_memories"] = (
                    await self.proactive_agent.consolidate_memories(db)
                )

            # Clean up very old, low-importance memories
            cutoff_date = datetime.utcnow() - timedelta(days=365)  # 1 year

            query = select(Memory).where(
                and_(
                    Memory.is_active == True,
                    Memory.importance == MemoryImportance.VERY_LOW,
                    Memory.last_accessed_at < cutoff_date,
                    Memory.access_count <= 1,
                )
            )

            result = await db.execute(query)
            old_memories = result.scalars().all()

            for memory in old_memories:
                await self.delete_memory(db, memory.id, soft_delete=True)
                results["cleaned_memories"] += 1

            logger.info(f"Memory maintenance completed: {results}")
            return results

        except Exception as e:
            logger.error(f"Memory maintenance failed: {e}")
            return results

    async def get_memory_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Get memory system statistics."""
        try:
            # Total memories
            total_query = select(func.count(Memory.id)).where(Memory.is_active == True)
            total_result = await db.execute(total_query)
            total_memories = total_result.scalar()

            # Memories by type
            type_query = (
                select(Memory.type, func.count(Memory.id))
                .where(Memory.is_active == True)
                .group_by(Memory.type)
            )
            type_result = await db.execute(type_query)
            memories_by_type = {row[0].value: row[1] for row in type_result}

            # Memories by importance
            importance_query = (
                select(Memory.importance, func.count(Memory.id))
                .where(Memory.is_active == True)
                .group_by(Memory.importance)
            )
            importance_result = await db.execute(importance_query)
            memories_by_importance = {row[0].value: row[1] for row in importance_result}

            # Recent activity
            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            recent_query = select(func.count(Memory.id)).where(
                and_(
                    Memory.is_active == True,
                    Memory.created_at >= recent_cutoff,
                )
            )
            recent_result = await db.execute(recent_query)
            recent_memories = recent_result.scalar()

            return {
                "total_memories": total_memories,
                "memories_by_type": memories_by_type,
                "memories_by_importance": memories_by_importance,
                "recent_memories": recent_memories,
                "last_updated": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {}


# Global memory manager instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get the global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


__all__ = [
    "MemoryManager",
    "MemoryExtractionResult",
    "MemorySearchResult",
    "get_memory_manager",
]
