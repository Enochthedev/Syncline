"""
Main entity extraction orchestrator.

This module coordinates different entity extraction methods and
provides a unified interface for entity extraction.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict

from .types import ExtractedEntity, EntityRelation, ExtractionResult
from .processors import SpacyProcessor, TransformerProcessor, LLMProcessor
from ..base import BaseAIAgent, AIProvider
from db.models.entity import EntityType
from config.config import settings

logger = logging.getLogger(__name__)


class EntityExtractor(BaseAIAgent):
    """
    Main entity extraction service that coordinates multiple extraction methods.

    Uses a multi-stage approach:
    1. spaCy for fast initial extraction
    2. Transformers for advanced NER
    3. LLM for validation and enrichment
    """

    def __init__(self, provider: AIProvider = None, model: str = None):
        """Initialize entity extractor."""
        super().__init__(
            name="entity_extractor",
            provider=provider,
            model=model
        )

        # Initialize processors
        self.spacy_processor = SpacyProcessor()
        self.transformer_processor = TransformerProcessor()
        self.llm_processor = LLMProcessor(provider, model)

        # Configuration
        self.use_spacy = True
        self.use_transformers = True
        self.use_llm = True
        self.confidence_threshold = 0.5

        # Statistics
        self.stats = {
            'extractions_performed': 0,
            'entities_extracted': 0,
            'methods_used': defaultdict(int),
            'processing_time_total': 0.0
        }

    async def extract_entities(
        self,
        text: str,
        methods: Optional[List[str]] = None,
        confidence_threshold: Optional[float] = None
    ) -> ExtractionResult:
        """
        Extract entities from text using multiple methods.

        Args:
            text: Text to extract entities from
            methods: List of methods to use ['spacy', 'transformers', 'llm']
            confidence_threshold: Minimum confidence threshold

        Returns:
            ExtractionResult with extracted entities and metadata
        """
        start_time = datetime.utcnow()

        # Use default methods if not specified
        if methods is None:
            methods = []
            if self.use_spacy:
                methods.append('spacy')
            if self.use_transformers:
                methods.append('transformers')
            if self.use_llm:
                methods.append('llm')

        # Use instance threshold if not specified
        threshold = confidence_threshold or self.confidence_threshold

        # Extract entities using each method
        all_entities = []
        methods_used = []

        for method in methods:
            try:
                if method == 'spacy' and self.use_spacy:
                    entities = await self.spacy_processor.extract_entities(text)
                    all_entities.extend(entities)
                    methods_used.append('spacy')
                    self.stats['methods_used']['spacy'] += 1

                elif method == 'transformers' and self.use_transformers:
                    entities = await self.transformer_processor.extract_entities(text)
                    all_entities.extend(entities)
                    methods_used.append('transformers')
                    self.stats['methods_used']['transformers'] += 1

                elif method == 'llm' and self.use_llm:
                    entities = await self.llm_processor.extract_entities(text)
                    all_entities.extend(entities)
                    methods_used.append('llm')
                    self.stats['methods_used']['llm'] += 1

            except Exception as e:
                logger.error(
                    f"Entity extraction failed for method {method}: {e}")
                continue

        # Deduplicate and merge entities
        merged_entities = self._merge_entities(all_entities)

        # Filter by confidence threshold
        filtered_entities = [
            e for e in merged_entities
            if e.confidence >= threshold
        ]

        # Extract relationships (basic implementation)
        relations = self._extract_relations(filtered_entities, text)

        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()

        # Update statistics
        self.stats['extractions_performed'] += 1
        self.stats['entities_extracted'] += len(filtered_entities)
        self.stats['processing_time_total'] += processing_time

        # Calculate confidence statistics
        confidence_stats = self._calculate_confidence_stats(filtered_entities)

        result = ExtractionResult(
            entities=filtered_entities,
            relations=relations,
            processing_time=processing_time,
            methods_used=methods_used,
            confidence_stats=confidence_stats,
            metadata={
                'original_text_length': len(text),
                'entities_before_filtering': len(merged_entities),
                'confidence_threshold': threshold,
                'methods_requested': methods
            }
        )

        logger.debug(
            f"Extracted {len(filtered_entities)} entities in {processing_time:.2f}s "
            f"using methods: {methods_used}"
        )

        return result

    def _merge_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Merge duplicate entities from different methods."""
        if not entities:
            return []

        # Group entities by normalized value and type
        entity_groups = defaultdict(list)

        for entity in entities:
            # Create a key for grouping similar entities
            normalized_value = entity.value.lower().strip()
            key = (entity.type, normalized_value)
            entity_groups[key].append(entity)

        merged_entities = []

        for (entity_type, normalized_value), group in entity_groups.items():
            if len(group) == 1:
                # Single entity, no merging needed
                merged_entities.append(group[0])
            else:
                # Multiple entities, merge them
                merged_entity = self._merge_entity_group(group)
                merged_entities.append(merged_entity)

        return merged_entities

    def _merge_entity_group(self, entities: List[ExtractedEntity]) -> ExtractedEntity:
        """Merge a group of similar entities."""
        # Use the entity with highest confidence as base
        base_entity = max(entities, key=lambda e: e.confidence)

        # Calculate weighted average confidence
        total_confidence = sum(e.confidence for e in entities)
        avg_confidence = total_confidence / len(entities)

        # Combine methods used
        methods_used = list(set(e.source_method for e in entities))

        # Merge metadata
        merged_metadata = {}
        for entity in entities:
            merged_metadata.update(entity.metadata)

        merged_metadata['merged_from_methods'] = methods_used
        merged_metadata['original_confidences'] = [
            e.confidence for e in entities]

        return ExtractedEntity(
            type=base_entity.type,
            value=base_entity.value,
            normalized_value=base_entity.normalized_value,
            # Slight boost for consensus
            confidence=min(avg_confidence * 1.1, 1.0),
            start_position=base_entity.start_position,
            end_position=base_entity.end_position,
            source_method='+'.join(methods_used),
            context=base_entity.context,
            metadata=merged_metadata
        )

    def _extract_relations(
        self,
        entities: List[ExtractedEntity],
        text: str
    ) -> List[EntityRelation]:
        """Extract basic relationships between entities."""
        relations = []

        # Simple relationship extraction based on proximity and patterns
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                # Check if entities are related based on proximity
                if (entity1.start_position is not None and
                        entity2.start_position is not None):

                    distance = abs(entity1.start_position -
                                   entity2.start_position)

                    # If entities are close, they might be related
                    if distance < 100:  # Within 100 characters
                        relation_type = self._determine_relation_type(
                            entity1, entity2)
                        if relation_type:
                            relation = EntityRelation(
                                source_entity=entity1,
                                target_entity=entity2,
                                relation_type=relation_type,
                                confidence=0.6,  # Basic confidence for proximity-based relations
                                context=text[
                                    min(entity1.start_position, entity2.start_position):
                                    max(entity1.end_position or 0,
                                        entity2.end_position or 0)
                                ]
                            )
                            relations.append(relation)

        return relations

    def _determine_relation_type(
        self,
        entity1: ExtractedEntity,
        entity2: ExtractedEntity
    ) -> Optional[str]:
        """Determine the type of relationship between two entities."""
        # Simple rule-based relationship detection
        type1, type2 = entity1.type, entity2.type

        if type1 == EntityType.PERSON and type2 == EntityType.ORGANIZATION:
            return "works_for"
        elif type1 == EntityType.ORGANIZATION and type2 == EntityType.PERSON:
            return "employs"
        elif type1 == EntityType.PERSON and type2 == EntityType.LOCATION:
            return "located_in"
        elif type1 == EntityType.ORGANIZATION and type2 == EntityType.LOCATION:
            return "based_in"
        elif type1 == EntityType.PERSON and type2 == EntityType.EMAIL:
            return "has_email"
        elif type1 == EntityType.PERSON and type2 == EntityType.PHONE:
            return "has_phone"

        return None

    def _calculate_confidence_stats(self, entities: List[ExtractedEntity]) -> Dict[str, Any]:
        """Calculate confidence statistics for extracted entities."""
        if not entities:
            return {}

        confidences = [e.confidence for e in entities]

        return {
            'total_entities': len(entities),
            'avg_confidence': sum(confidences) / len(confidences),
            'min_confidence': min(confidences),
            'max_confidence': max(confidences),
            'high_confidence_count': len([c for c in confidences if c >= 0.8]),
            'medium_confidence_count': len([c for c in confidences if 0.5 <= c < 0.8]),
            'low_confidence_count': len([c for c in confidences if c < 0.5])
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics."""
        base_stats = super().get_stats()

        avg_processing_time = (
            self.stats['processing_time_total'] /
            self.stats['extractions_performed']
            if self.stats['extractions_performed'] > 0 else 0.0
        )

        return {
            **base_stats,
            **self.stats,
            'avg_processing_time': avg_processing_time,
            'avg_entities_per_extraction': (
                self.stats['entities_extracted'] /
                self.stats['extractions_performed']
                if self.stats['extractions_performed'] > 0 else 0.0
            )
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on entity extraction."""
        try:
            # Test extraction with sample text
            test_text = "John Smith works at OpenAI in San Francisco. Contact him at john@openai.com."
            result = await self.extract_entities(test_text)

            return {
                'status': 'healthy',
                'test_entities_found': len(result.entities),
                'methods_available': {
                    'spacy': self.spacy_processor.nlp is not None,
                    'transformers': self.transformer_processor.pipeline is not None,
                    'llm': True  # LLM is always available if provider is configured
                },
                'processing_time': result.processing_time,
                'stats': self.get_stats()
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'stats': self.get_stats()
            }


# Global entity extractor instance
_entity_extractor = None


async def get_entity_extractor() -> EntityExtractor:
    """Get the global entity extractor instance."""
    global _entity_extractor
    if _entity_extractor is None:
        _entity_extractor = EntityExtractor()
    return _entity_extractor
