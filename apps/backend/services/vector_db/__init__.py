"""
Vector Database Services Package

Provides vector database capabilities for semantic search:
- ChromaDB integration with local persistence
- Collection management
- Vector storage and retrieval
- Similarity search
"""

from .chroma_client import (
    ChromaDBClient,
    get_chroma_client,
)

__all__ = [
    "ChromaDBClient",
    "get_chroma_client",
]
