"""
Entity Graph Builder for relationship analysis.

Builds entity graphs with relationship analysis including:
- Entity extraction and linking
- Relationship detection and weighting
- Community detection
- Centrality analysis
- Key entity identification
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import defaultdict, Counter
import networkx as nx
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import settings
from db.session import get_async_session
from db.models.message import Message
from db.models.entity import Entity, MessageEntity, EntityType
from db.models.user import User
from services.ai.entity.extractor import EntityExtractor

from .types import (
    BatchJob,
    BatchJobResult,
    EntityGraphRequest,
    EntityGraphScope,
    EntityGraph,
    EntityRelationship
)

logger = logging.getLogger(__name__)


class EntityGraphBuilder:
    """
    Builder for entity relationship graphs.

    Analyzes messages to build comprehensive entity graphs with:
    - Entity co-occurrence analysis
    - Relationship strength calculation
    - Community detection
    - Centrality metrics
    - Temporal relationship tracking
    """

    def __init__(self):
        """Initialize the entity graph builder."""
        self.entity_extractor = EntityExtractor()

        # Configuration
        self.max_entities_per_graph = getattr(
            settings, 'ENTITY_GRAPH_MAX_ENTITIES', 1000)
        self.min_relationship_strength = getattr(
            settings, 'ENTITY_GRAPH_MIN_STRENGTH', 0.1)
        self.relationship_decay_days = getattr(
            settings, 'ENTITY_GRAPH_DECAY_DAYS', 30)

        logger.info("Initialized EntityGraphBuilder")

    async def build_entity_graph(self, job: BatchJob) -> BatchJobResult:
        """
        Build entity graph for the specified scope.

        Args:
            job: Batch job with parameters for graph building

        Returns:
            BatchJobResult with graph building results
        """
        start_time = datetime.utcnow()
        result = BatchJobResult(job_id=job.id, success=False)

        try:
            tenant_id = job.tenant_id
            if not tenant_id:
                raise ValueError(
                    "Tenant ID is required for entity graph building")

            # Parse job parameters
            scope = EntityGraphScope(job.parameters.get(
                'scope', EntityGraphScope.TENANT))
            scope_id = job.parameters.get('scope_id')
            include_relationships = job.parameters.get(
                'include_relationships', True)
            min_confidence = job.parameters.get('min_confidence', 0.5)

            # Time range (default to last 30 days)
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            if 'start_date' in job.parameters:
                start_date = datetime.fromisoformat(
                    job.parameters['start_date'])
            if 'end_date' in job.parameters:
                end_date = datetime.fromisoformat(job.parameters['end_date'])

            logger.info(
                f"Building entity graph for {scope} scope in tenant {tenant_id}")

            async with get_async_session() as session:
                # Get entities and messages for the scope
                entities, messages = await self._get_scope_data(
                    session, tenant_id, scope, scope_id, start_date, end_date, min_confidence
                )

                if not entities:
                    result.success = True
                    result.summary = "No entities found for the specified scope"
                    return result

                job.progress = 20.0

                # Build entity relationships
                relationships = []
                if include_relationships:
                    relationships = await self._build_relationships(
                        session, entities, messages, min_confidence
                    )

                job.progress = 60.0

                # Create entity graph
                entity_graph = await self._create_entity_graph(
                    scope, scope_id or tenant_id, entities, relationships
                )

                job.progress = 80.0

                # Perform graph analysis
                if job.parameters.get('detect_communities', True):
                    entity_graph.communities = await self._detect_communities(entity_graph)

                if job.parameters.get('calculate_centrality', True):
                    entity_graph.centrality_scores = await self._calculate_centrality(entity_graph)

                if job.parameters.get('find_key_entities', True):
                    entity_graph.key_entities = await self._find_key_entities(entity_graph)

                job.progress = 90.0

                # Store the entity graph
                await self._store_entity_graph(session, entity_graph)

            # Calculate results
            duration = (datetime.utcnow() - start_time).total_seconds()

            result.success = True
            result.duration_seconds = duration
            result.items_processed = len(entities)
            result.items_failed = 0
            result.summary = f"Built entity graph with {len(entities)} entities and {len(relationships)} relationships"

            job.progress = 100.0

            logger.info(f"Successfully built entity graph in {duration:.2f}s")

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            result.duration_seconds = duration
            result.error_type = type(e).__name__
            result.error_details = str(e)
            logger.error(f"Entity graph building failed: {e}")

        return result

    async def _get_scope_data(
        self,
        session: AsyncSession,
        tenant_id: str,
        scope: EntityGraphScope,
        scope_id: Optional[str],
        start_date: datetime,
        end_date: datetime,
        min_confidence: float
    ) -> Tuple[List[Entity], List[Message]]:
        """Get entities and messages for the specified scope."""

        # Build base message query
        message_query = select(Message).where(
            and_(
                Message.tenant_id == tenant_id,
                Message.timestamp >= start_date,
                Message.timestamp < end_date
            )
        )

        # Apply scope filters
        if scope == EntityGraphScope.USER and scope_id:
            message_query = message_query.where(
                or_(
                    Message.sender_id == scope_id,
                    Message.recipients.contains([scope_id])
                )
            )
        elif scope == EntityGraphScope.CONTACT and scope_id:
            message_query = message_query.where(
                or_(
                    Message.sender_id == scope_id,
                    Message.recipients.contains([scope_id])
                )
            )
        elif scope == EntityGraphScope.THREAD and scope_id:
            message_query = message_query.where(Message.thread_id == scope_id)

        # Get messages
        message_result = await session.execute(message_query.limit(self.max_entities_per_graph))
        messages = message_result.scalars().all()

        if not messages:
            return [], []

        # Get entities from these messages
        message_ids = [str(msg.id) for msg in messages]

        entity_query = select(Entity).join(MessageEntity).where(
            and_(
                MessageEntity.message_id.in_(message_ids),
                Entity.confidence >= min_confidence
            )
        ).distinct()

        entity_result = await session.execute(entity_query)
        entities = entity_result.scalars().all()

        return entities, messages

    async def _build_relationships(
        self,
        session: AsyncSession,
        entities: List[Entity],
        messages: List[Message],
        min_confidence: float
    ) -> List[EntityRelationship]:
        """Build relationships between entities based on co-occurrence."""

        # Create entity lookup
        entity_lookup = {str(entity.id): entity for entity in entities}

        # Get message-entity associations
        message_ids = [str(msg.id) for msg in messages]

        associations_query = select(MessageEntity).where(
            MessageEntity.message_id.in_(message_ids)
        )

        associations_result = await session.execute(associations_query)
        associations = associations_result.scalars().all()

        # Group entities by message
        message_entities = defaultdict(list)
        for assoc in associations:
            if str(assoc.entity_id) in entity_lookup:
                message_entities[str(assoc.message_id)].append(
                    str(assoc.entity_id))

        # Calculate co-occurrence relationships
        relationships = []
        entity_pairs = defaultdict(lambda: {
            'count': 0,
            'messages': [],
            'first_seen': None,
            'last_seen': None
        })

        # Count co-occurrences
        for message in messages:
            msg_id = str(message.id)
            if msg_id not in message_entities:
                continue

            msg_entity_ids = message_entities[msg_id]

            # Create pairs from entities in the same message
            for i, entity1_id in enumerate(msg_entity_ids):
                for entity2_id in msg_entity_ids[i+1:]:
                    # Create consistent pair key
                    pair_key = tuple(sorted([entity1_id, entity2_id]))

                    pair_data = entity_pairs[pair_key]
                    pair_data['count'] += 1
                    pair_data['messages'].append(msg_id)

                    if pair_data['first_seen'] is None or message.timestamp < pair_data['first_seen']:
                        pair_data['first_seen'] = message.timestamp
                    if pair_data['last_seen'] is None or message.timestamp > pair_data['last_seen']:
                        pair_data['last_seen'] = message.timestamp

        # Create relationship objects
        for (entity1_id, entity2_id), data in entity_pairs.items():
            if data['count'] < 2:  # Require at least 2 co-occurrences
                continue

            # Calculate relationship weight
            weight = min(1.0, data['count'] / 10.0)  # Normalize to 0-1

            # Apply temporal decay
            if data['last_seen']:
                days_since = (datetime.utcnow() - data['last_seen']).days
                decay_factor = max(
                    0.1, 1.0 - (days_since / self.relationship_decay_days))
                weight *= decay_factor

            if weight < self.min_relationship_strength:
                continue

            # Determine relationship type based on entity types
            entity1 = entity_lookup[entity1_id]
            entity2 = entity_lookup[entity2_id]
            relationship_type = self._determine_relationship_type(
                entity1, entity2)

            relationship = EntityRelationship(
                source_entity_id=entity1_id,
                target_entity_id=entity2_id,
                relationship_type=relationship_type,
                weight=weight,
                confidence=min(entity1.confidence or 0.5,
                               entity2.confidence or 0.5),
                context_messages=data['messages'][:5],  # Keep first 5 messages
                first_seen=data['first_seen'] or datetime.utcnow(),
                last_seen=data['last_seen'] or datetime.utcnow(),
                frequency=data['count']
            )

            relationships.append(relationship)

        return relationships

    def _determine_relationship_type(self, entity1: Entity, entity2: Entity) -> str:
        """Determine the type of relationship between two entities."""

        type1 = EntityType(entity1.type)
        type2 = EntityType(entity2.type)

        # Define relationship type mappings
        type_pairs = {
            (EntityType.person, EntityType.person): "person_to_person",
            (EntityType.person, EntityType.organization): "person_to_org",
            (EntityType.person, EntityType.topic): "person_interested_in",
            (EntityType.person, EntityType.file): "person_shared_file",
            (EntityType.organization, EntityType.organization): "org_to_org",
            (EntityType.organization, EntityType.topic): "org_involved_in",
            (EntityType.topic, EntityType.topic): "related_topics",
            (EntityType.file, EntityType.topic): "file_about_topic",
            (EntityType.task, EntityType.person): "task_assigned_to",
            (EntityType.task, EntityType.topic): "task_related_to"
        }

        # Try both orders
        pair_key = (type1, type2)
        if pair_key in type_pairs:
            return type_pairs[pair_key]

        pair_key = (type2, type1)
        if pair_key in type_pairs:
            return type_pairs[pair_key]

        return "co_occurrence"

    async def _create_entity_graph(
        self,
        scope: EntityGraphScope,
        scope_id: str,
        entities: List[Entity],
        relationships: List[EntityRelationship]
    ) -> EntityGraph:
        """Create an EntityGraph object from entities and relationships."""

        entity_ids = [str(entity.id) for entity in entities]

        # Calculate basic graph statistics
        total_entities = len(entities)
        total_relationships = len(relationships)

        # Create NetworkX graph for analysis
        G = nx.Graph()
        G.add_nodes_from(entity_ids)

        for rel in relationships:
            G.add_edge(rel.source_entity_id,
                       rel.target_entity_id, weight=rel.weight)

        # Calculate graph metrics
        avg_degree = sum(dict(G.degree()).values()) / \
            total_entities if total_entities > 0 else 0
        density = nx.density(G) if total_entities > 1 else 0

        try:
            clustering_coefficient = nx.average_clustering(G)
        except:
            clustering_coefficient = 0.0

        return EntityGraph(
            scope=scope,
            scope_id=scope_id,
            entities=entity_ids,
            relationships=relationships,
            total_entities=total_entities,
            total_relationships=total_relationships,
            avg_degree=avg_degree,
            density=density,
            clustering_coefficient=clustering_coefficient
        )

    async def _detect_communities(self, entity_graph: EntityGraph) -> Dict[str, List[str]]:
        """Detect communities in the entity graph."""

        if len(entity_graph.entities) < 3:
            return {"main": entity_graph.entities}

        try:
            # Create NetworkX graph
            G = nx.Graph()
            G.add_nodes_from(entity_graph.entities)

            for rel in entity_graph.relationships:
                G.add_edge(rel.source_entity_id,
                           rel.target_entity_id, weight=rel.weight)

            # Use Louvain community detection
            import networkx.algorithms.community as nx_comm
            communities = nx_comm.louvain_communities(G)

            # Convert to dictionary format
            community_dict = {}
            for i, community in enumerate(communities):
                community_dict[f"community_{i}"] = list(community)

            return community_dict

        except Exception as e:
            logger.warning(f"Community detection failed: {e}")
            return {"main": entity_graph.entities}

    async def _calculate_centrality(self, entity_graph: EntityGraph) -> Dict[str, float]:
        """Calculate centrality scores for entities."""

        if len(entity_graph.entities) < 2:
            return {entity_id: 1.0 for entity_id in entity_graph.entities}

        try:
            # Create NetworkX graph
            G = nx.Graph()
            G.add_nodes_from(entity_graph.entities)

            for rel in entity_graph.relationships:
                G.add_edge(rel.source_entity_id,
                           rel.target_entity_id, weight=rel.weight)

            # Calculate betweenness centrality
            centrality = nx.betweenness_centrality(G, weight='weight')

            return centrality

        except Exception as e:
            logger.warning(f"Centrality calculation failed: {e}")
            return {entity_id: 0.5 for entity_id in entity_graph.entities}

    async def _find_key_entities(self, entity_graph: EntityGraph) -> List[str]:
        """Find key entities based on centrality and relationship count."""

        # Combine centrality scores with relationship counts
        entity_scores = {}

        # Count relationships per entity
        relationship_counts = defaultdict(int)
        for rel in entity_graph.relationships:
            relationship_counts[rel.source_entity_id] += 1
            relationship_counts[rel.target_entity_id] += 1

        # Calculate combined scores
        for entity_id in entity_graph.entities:
            centrality_score = entity_graph.centrality_scores.get(
                entity_id, 0.0)
            relationship_count = relationship_counts[entity_id]

            # Normalize relationship count (max 10 relationships = score 1.0)
            relationship_score = min(1.0, relationship_count / 10.0)

            # Combined score (weighted average)
            combined_score = (centrality_score * 0.6) + \
                (relationship_score * 0.4)
            entity_scores[entity_id] = combined_score

        # Sort by score and return top entities
        sorted_entities = sorted(
            entity_scores.items(), key=lambda x: x[1], reverse=True)

        # Return top 20% or at least top 5
        num_key_entities = max(5, len(entity_graph.entities) // 5)
        key_entities = [entity_id for entity_id,
                        score in sorted_entities[:num_key_entities]]

        return key_entities

    async def _store_entity_graph(self, session: AsyncSession, entity_graph: EntityGraph) -> None:
        """Store the entity graph in the database."""

        # For now, we'll store the graph as JSON metadata in a summary record
        # In a production system, you might want dedicated graph storage

        from db.models.summary import Summary, SummaryType, SummaryScope

        try:
            graph_summary = Summary(
                type="entity_graph",
                scope_type=entity_graph.scope.value,
                scope_id=entity_graph.scope_id,
                content=f"Entity graph with {entity_graph.total_entities} entities and {entity_graph.total_relationships} relationships",
                summary_metadata={
                    'graph_type': 'entity_relationship',
                    'scope': entity_graph.scope.value,
                    'total_entities': entity_graph.total_entities,
                    'total_relationships': entity_graph.total_relationships,
                    'avg_degree': entity_graph.avg_degree,
                    'density': entity_graph.density,
                    'clustering_coefficient': entity_graph.clustering_coefficient,
                    'communities': entity_graph.communities,
                    'centrality_scores': entity_graph.centrality_scores,
                    'key_entities': entity_graph.key_entities,
                    'generated_at': entity_graph.generated_at.isoformat()
                }
            )

            session.add(graph_summary)
            await session.commit()

            logger.info(
                f"Stored entity graph for {entity_graph.scope} {entity_graph.scope_id}")

        except Exception as e:
            logger.error(f"Error storing entity graph: {e}")
            await session.rollback()
