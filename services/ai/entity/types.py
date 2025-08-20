"""
Entity extraction type definitions.

This module contains all data structures and enums used for
entity extraction and relationship mapping.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from enum import Enum

from db.models.entity import EntityType


class EntityConfidence(str, Enum):
    """Entity confidence levels."""
    HIGH = "high"      # 0.8+
    MEDIUM = "medium"  # 0.5-0.8
    LOW = "low"        # 0.2-0.5
    VERY_LOW = "very_low"  # <0.2


@dataclass
class ExtractedEntity:
    """Represents an extracted entity with metadata."""
    type: EntityType
    value: str
    normalized_value: Optional[str] = None
    confidence: float = 0.0
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    source_method: str = "unknown"  # spacy, transformers, llm
    context: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def get_confidence_level(self) -> EntityConfidence:
        """Get confidence level enum based on score."""
        if self.confidence >= 0.8:
            return EntityConfidence.HIGH
        elif self.confidence >= 0.5:
            return EntityConfidence.MEDIUM
        elif self.confidence >= 0.2:
            return EntityConfidence.LOW
        else:
            return EntityConfidence.VERY_LOW

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'type': self.type.value,
            'value': self.value,
            'normalized_value': self.normalized_value,
            'confidence': self.confidence,
            'start_position': self.start_position,
            'end_position': self.end_position,
            'source_method': self.source_method,
            'context': self.context,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class EntityRelation:
    """Represents a relationship between entities."""
    source_entity: ExtractedEntity
    target_entity: ExtractedEntity
    relation_type: str
    confidence: float = 0.0
    context: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'source_entity': self.source_entity.to_dict(),
            'target_entity': self.target_entity.to_dict(),
            'relation_type': self.relation_type,
            'confidence': self.confidence,
            'context': self.context,
            'metadata': self.metadata
        }


@dataclass
class ExtractionResult:
    """Result of entity extraction process."""
    entities: List[ExtractedEntity] = field(default_factory=list)
    relations: List[EntityRelation] = field(default_factory=list)
    processing_time: float = 0.0
    methods_used: List[str] = field(default_factory=list)
    confidence_stats: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_entities_by_type(self, entity_type: EntityType) -> List[ExtractedEntity]:
        """Get entities filtered by type."""
        return [e for e in self.entities if e.type == entity_type]

    def get_high_confidence_entities(self) -> List[ExtractedEntity]:
        """Get entities with high confidence."""
        return [e for e in self.entities if e.confidence >= 0.8]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'entities': [e.to_dict() for e in self.entities],
            'relations': [r.to_dict() for r in self.relations],
            'processing_time': self.processing_time,
            'methods_used': self.methods_used,
            'confidence_stats': self.confidence_stats,
            'metadata': self.metadata
        }


# Alias for backward compatibility
EntityExtractionResult = ExtractionResult


class EntityExtractionError(Exception):
    """Exception raised during entity extraction."""

    def __init__(self, message: str, entity_type: Optional[str] = None, source_method: Optional[str] = None):
        super().__init__(message)
        self.entity_type = entity_type
        self.source_method = source_method
