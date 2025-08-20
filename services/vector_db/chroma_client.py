"""
Chroma vector database client for embedding storage and retrieval.

This module provides a high-level interface to Chroma for storing message
embeddings with metadata and performing similarity searches.
"""

import logging
import os
from typing import Dict, List, Optional, Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from config.config import settings
from .types import VectorCollectionType, VectorSearchQuery, VectorDocument
from .chroma_health import ChromaHealthMonitor
from .chroma_operations import ChromaOperations

logger = logging.getLogger(__name__)


class ChromaVectorDB:
    """
    Chroma vector database client with async support and metadata filtering.

    Provides high-level operations for storing and retrieving embeddings
    with rich metadata support for the MESH ingestion system.
    """

    def __init__(
        self,
        persist_directory: str = "./vector_db",
        host: Optional[str] = None,
        port: Optional[int] = None,
        use_local: bool = True
    ):
        """
        Initialize Chroma client.

        Args:
            persist_directory: Local directory for persistent storage
            host: Chroma server host (for client mode)
            port: Chroma server port (for client mode)
            use_local: Whether to use local persistent client
        """
        self.persist_directory = persist_directory
        self.use_local = use_local
        self.host = host
        self.port = port

        self._client = None
        self._collections = {}

        # Initialize health monitor and operations
        self.health = ChromaHealthMonitor(self)
        self.operations = ChromaOperations(self, self.health)

        logger.info(
            f"ChromaVectorDB initialized with persist_directory: {persist_directory}")

    async def initialize(self) -> None:
        """Initialize the Chroma client and collections."""
        try:
            if self.use_local:
                # Create persistent directory if it doesn't exist
                os.makedirs(self.persist_directory, exist_ok=True)

                # Initialize persistent client
                self._client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
            else:
                # Initialize HTTP client for server mode
                self._client = chromadb.HttpClient(
                    host=self.host or "localhost",
                    port=self.port or 8000
                )

            # Initialize collections for each type
            await self._initialize_collections()

            logger.info("ChromaVectorDB client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize ChromaVectorDB: {e}")
            raise

    async def _initialize_collections(self) -> None:
        """Initialize collections for different document types."""
        for collection_type in VectorCollectionType:
            try:
                collection_name = f"mesh_{collection_type.value}"

                # Get or create collection
                collection = self._client.get_or_create_collection(
                    name=collection_name,
                    metadata={
                        "description": f"MESH {collection_type.value} embeddings"}
                )

                self._collections[collection_type] = collection

                # Update stats
                count = collection.count()
                self.health.stats['collection_counts'][collection_type.value] = count

                logger.info(
                    f"Initialized collection '{collection_name}' with {count} documents")

            except Exception as e:
                logger.error(
                    f"Failed to initialize collection {collection_type}: {e}")
                raise

    def _get_collection(self, collection_type: VectorCollectionType):
        """Get collection for the specified type."""
        if collection_type not in self._collections:
            raise ValueError(f"Collection {collection_type} not initialized")
        return self._collections[collection_type]

    # Delegate operations to the operations module
    async def store_document(self, document: VectorDocument) -> bool:
        """Store a single document in the vector database."""
        return await self.operations.store_document(document)

    async def store_documents_batch(self, documents: List[VectorDocument]):
        """Store multiple documents in batch."""
        return await self.operations.store_documents_batch(documents)

    async def search_similar(self, query: VectorSearchQuery, embedding: Optional[List[float]] = None):
        """Search for similar documents using vector similarity."""
        return await self.operations.search_similar(query, embedding)

    async def search_by_metadata(self, collection_type: VectorCollectionType, metadata_filters: Dict[str, Any], limit: int = 100):
        """Search documents by metadata only."""
        return await self.operations.search_by_metadata(collection_type, metadata_filters, limit)

    async def update_document(self, document: VectorDocument) -> bool:
        """Update an existing document."""
        return await self.operations.update_document(document)

    async def delete_document(self, document_id: str, collection_type: VectorCollectionType) -> bool:
        """Delete a document from the vector database."""
        return await self.operations.delete_document(document_id, collection_type)

    async def delete_documents_batch(self, document_ids: List[str], collection_type: VectorCollectionType):
        """Delete multiple documents in batch."""
        return await self.operations.delete_documents_batch(document_ids, collection_type)

    async def reset_collection(self, collection_type: VectorCollectionType) -> bool:
        """Reset (clear) a specific collection."""
        return await self.operations.reset_collection(collection_type)

    # Delegate health and stats to health monitor
    async def get_collection_stats(self, collection_type: VectorCollectionType) -> Dict[str, Any]:
        """Get statistics for a specific collection."""
        return await self.health.get_collection_stats(collection_type)

    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics."""
        return await self.health.get_stats()

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the vector database."""
        return await self.health.health_check()


# Global vector database instance
_vector_db_instance = None


async def get_vector_db() -> ChromaVectorDB:
    """Get the global vector database instance."""
    global _vector_db_instance

    if _vector_db_instance is None:
        _vector_db_instance = ChromaVectorDB()
        await _vector_db_instance.initialize()

    return _vector_db_instance
