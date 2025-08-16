"""
AI services package for the MESH ingestion system.

This package contains all AI-related services including:
- AI processing engine
- PII redaction
- Embedding generation
- Base AI agent classes
"""

from .engine import AIProcessingEngine, get_ai_processing_engine
from .pii_redaction import PIIRedactionService, get_pii_redaction_service
from .embeddings import EmbeddingService, get_embedding_service
from .base import BaseAIAgent, AIProvider, agent_registry
from .detector import get_ai_detector, auto_configure_ai
from .providers import get_provider
from .entity_extraction import EntityExtractionAgent, get_entity_extraction_agent, create_entity_extraction_agent
from .summary import SummaryGenerationAgent, get_summary_generation_agent, create_summary_generation_agent

__all__ = [
    'AIProcessingEngine',
    'get_ai_processing_engine',
    'PIIRedactionService',
    'get_pii_redaction_service',
    'EmbeddingService',
    'get_embedding_service',
    'BaseAIAgent',
    'AIProvider',
    'agent_registry',
    'get_ai_detector',
    'auto_configure_ai',
    'get_provider',
    'EntityExtractionAgent',
    'get_entity_extraction_agent',
    'create_entity_extraction_agent',
    'SummaryGenerationAgent',
    'get_summary_generation_agent',
    'create_summary_generation_agent'
]
