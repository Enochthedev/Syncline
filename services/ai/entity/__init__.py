"""
Entity extraction services.

This package contains all entity extraction functionality including
NER models, entity types, and extraction pipelines.
"""

from .extractor import EntityExtractor, get_entity_extractor
from .types import ExtractedEntity, EntityConfidence, EntityRelation, EntityExtractionResult, EntityExtractionError
from .processors import SpacyProcessor, TransformerProcessor, LLMProcessor

# Add aliases for backward compatibility
EntityProcessor = SpacyProcessor
EntityValidator = SpacyProcessor  # Placeholder
EntityNormalizer = SpacyProcessor  # Placeholder
EntityDeduplicator = SpacyProcessor  # Placeholder
EntityConfidenceCalculator = SpacyProcessor  # Placeholder

__all__ = [
    'EntityExtractor',
    'get_entity_extractor',
    'ExtractedEntity',
    'EntityConfidence',
    'EntityRelation',
    'EntityExtractionResult',
    'EntityExtractionError',
    'SpacyProcessor',
    'TransformerProcessor',
    'LLMProcessor',
    'EntityProcessor',
    'EntityValidator',
    'EntityNormalizer',
    'EntityDeduplicator',
    'EntityConfidenceCalculator'
]
