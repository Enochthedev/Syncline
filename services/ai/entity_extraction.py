"""
Entity Extraction Agent for the MESH ingestion system.

This module provides backward compatibility imports for the entity extraction
functionality that has been reorganized into the services.ai.entity package.

For new code, use:
    from services.ai.entity import get_entity_extractor, ExtractedEntity, EntityConfidence

This file maintains backward compatibility for existing imports.
"""

# Import everything from the organized structure for backward compatibility
from .entity import (
    EntityExtractor,
    get_entity_extractor,
    ExtractedEntity,
    EntityConfidence,
    EntityExtractionResult,
    EntityExtractionError,
    EntityProcessor,
    EntityValidator,
    EntityNormalizer,
    EntityDeduplicator,
    EntityConfidenceCalculator
)

# Aliases for backward compatibility
EntityExtractionAgent = EntityExtractor


def get_entity_extraction_agent():
    """Get entity extraction agent (alias for get_entity_extractor)."""
    return get_entity_extractor()


def create_entity_extraction_agent():
    """Create entity extraction agent (alias for EntityExtractor)."""
    return EntityExtractor()


# Re-export all the main classes and functions
__all__ = [
    'EntityExtractor',
    'get_entity_extractor',
    'ExtractedEntity',
    'EntityConfidence',
    'EntityExtractionResult',
    'EntityExtractionError',
    'EntityProcessor',
    'EntityValidator',
    'EntityNormalizer',
    'EntityDeduplicator',
    'EntityConfidenceCalculator',
    'EntityExtractionAgent',
    'get_entity_extraction_agent',
    'create_entity_extraction_agent'
]
