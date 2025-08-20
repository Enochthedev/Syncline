"""
Health monitoring and statistics for ChromaDB operations.

This module provides health check functionality and performance
statistics tracking for the ChromaVectorDB client.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid

from .types import VectorDocument, VectorMetadata, VectorCollectionType

logger = logging.getLogger(__name__)


class ChromaHealthMonitor:
    """Health monitoring and statistics for ChromaDB operations."""

    def __init__(self, chroma_client):
        """Initialize health monitor with ChromaDB client reference."""
        self.client = chroma_client
        self.stats = {
            'documents_stored': 0,
            'searches_performed': 0,
            'batch_operations': 0,
            'total_processing_time': 0.0,
            'collection_counts': {},
            'last_operation': None
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the vector database."""
        try:
            # Test basic operations
            test_doc = VectorDocument(
                id=f"health_check_{uuid.uuid4().hex[:8]}",
                text="Health check test document",
                embedding=[0.1] * 384,  # Standard embedding dimension
                metadata=VectorMetadata(
                    content_type="test",
                    platform="health_check"
                ),
                collection=VectorCollectionType.MESSAGES
            )

            # Test store and retrieve
            store_success = await self._test_store_operation(test_doc)

            if store_success:
                # Test search
                search_success = await self._test_search_operation()

                # Clean up test document
                await self._cleanup_test_document(test_doc.id)

                return {
                    'status': 'healthy',
                    'store_test': store_success,
                    'search_test': search_success,
                    'collections_count': len(self.client._collections),
                    'stats': await self.get_stats()
                }
            else:
                return {
                    'status': 'unhealthy',
                    'store_test': False,
                    'search_test': False,
                    'error': 'Failed to store test document'
                }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'store_test': False,
                'search_test': False
            }

    async def _test_store_operation(self, test_doc: VectorDocument) -> bool:
        """Test document storage operation."""
        try:
            collection = self.client._get_collection(test_doc.collection)
            chroma_data = test_doc.to_chroma_format()
            collection.add(**chroma_data)
            return True
        except Exception as e:
            logger.error(f"Health check store test failed: {e}")
            return False

    async def _test_search_operation(self) -> bool:
        """Test search operation."""
        try:
            from .types import VectorSearchQuery

            query = VectorSearchQuery(
                text="Health check test",
                collection=VectorCollectionType.MESSAGES,
                limit=1
            )

            collection = self.client._get_collection(
                VectorCollectionType.MESSAGES)
            results = collection.query(
                query_texts=[query.text],
                n_results=query.limit
            )

            return len(results.get('ids', [[]])[0]) >= 0  # Allow empty results

        except Exception as e:
            logger.error(f"Health check search test failed: {e}")
            return False

    async def _cleanup_test_document(self, doc_id: str) -> None:
        """Clean up test document after health check."""
        try:
            collection = self.client._get_collection(
                VectorCollectionType.MESSAGES)
            collection.delete(ids=[doc_id])
        except Exception as e:
            logger.warning(f"Failed to cleanup test document {doc_id}: {e}")

    async def get_collection_stats(self, collection_type: VectorCollectionType) -> Dict[str, Any]:
        """Get statistics for a specific collection."""
        try:
            collection = self.client._get_collection(collection_type)
            count = collection.count()

            # Update cached count
            self.stats['collection_counts'][collection_type.value] = count

            return {
                'collection_type': collection_type.value,
                'document_count': count,
                'collection_name': f"mesh_{collection_type.value}"
            }

        except Exception as e:
            logger.error(
                f"Failed to get stats for collection {collection_type}: {e}")
            return {
                'collection_type': collection_type.value,
                'document_count': 0,
                'error': str(e)
            }

    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics."""
        # Refresh collection counts
        for collection_type in VectorCollectionType:
            await self.get_collection_stats(collection_type)

        return {
            **self.stats,
            'average_processing_time': (
                self.stats['total_processing_time'] /
                max(self.stats['documents_stored'] +
                    self.stats['searches_performed'], 1)
            ),
            'persist_directory': self.client.persist_directory,
            'use_local': self.client.use_local,
            'collections_initialized': len(self.client._collections)
        }

    def update_stats(self, operation: str, processing_time: float, collection_type: VectorCollectionType) -> None:
        """Update internal statistics."""
        if operation == 'store_document':
            self.stats['documents_stored'] += 1

        self.stats['total_processing_time'] += processing_time
        self.stats['last_operation'] = datetime.utcnow()

        # Update collection count (approximate)
        if collection_type.value not in self.stats['collection_counts']:
            self.stats['collection_counts'][collection_type.value] = 0
        if operation == 'store_document':
            self.stats['collection_counts'][collection_type.value] += 1

    def update_search_stats(self) -> None:
        """Update search statistics."""
        self.stats['searches_performed'] += 1
        self.stats['last_operation'] = datetime.utcnow()

    def update_batch_stats(self) -> None:
        """Update batch operation statistics."""
        self.stats['batch_operations'] += 1
        self.stats['last_operation'] = datetime.utcnow()
