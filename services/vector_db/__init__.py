"""
Vector database services for semantic search and embedding storage.

This package provides vector database integration using Chroma for storing
and retrieving message embeddings with metadata filtering capabilities.
"""

from .chroma_client import ChromaVectorDB, get_vector_db
from .types import VectorSearchResult, VectorDocument, VectorMetadata, VectorCollectionType, VectorSearchQuery
from .batch_processor import VectorBatchProcessor
from .batch_config import BatchProcessingConfig, BatchProcessingResult
from .integration import VectorIntegrationService, get_vector_integration_service

__all__ = [
    'ChromaVectorDB',
    'get_vector_db',
    'VectorSearchResult',
    'VectorDocument',
    'VectorMetadata',
    'VectorCollectionType',
    'VectorSearchQuery',
    'BatchProcessingConfig',
    'BatchProcessingResult',
    'VectorBatchProcessor',
    'VectorIntegrationService',
    'get_vector_integration_service'
]
