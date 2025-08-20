"""
CRUD operations for ChromaDB vector database.

This module provides create, read, update, and delete operations
for vector documents in ChromaDB collections.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from .types import (
    VectorDocument, VectorSearchResult, VectorSearchQuery,
    VectorCollectionType, VectorBatchResult
)

logger = logging.getLogger(__name__)


class ChromaOperations:
    """CRUD operations for ChromaDB collections."""

    def __init__(self, chroma_client, health_monitor):
        """Initialize operations with ChromaDB client and health monitor."""
        self.client = chroma_client
        self.health = health_monitor

    async def store_document(self, document: VectorDocument) -> bool:
        """Store a single document in the vector database."""
        try:
            start_time = datetime.utcnow()

            collection = self.client._get_collection(document.collection)

            # Convert document to Chroma format
            chroma_data = document.to_chroma_format()

            # Add to collection
            collection.add(**chroma_data)

            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self.health.update_stats(
                'store_document', processing_time, document.collection)

            logger.debug(
                f"Stored document {document.id} in collection {document.collection.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to store document {document.id}: {e}")
            return False

    async def store_documents_batch(self, documents: List[VectorDocument]) -> VectorBatchResult:
        """Store multiple documents in batch."""
        start_time = datetime.utcnow()

        if not documents:
            return VectorBatchResult(
                operation_type='add',
                collection=VectorCollectionType.MESSAGES,
                processed_count=0,
                success_count=0,
                error_count=0
            )

        # Group documents by collection
        collections_data = {}
        for doc in documents:
            if doc.collection not in collections_data:
                collections_data[doc.collection] = {
                    'ids': [],
                    'documents': [],
                    'embeddings': [],
                    'metadatas': []
                }

            collections_data[doc.collection]['ids'].append(doc.id)
            collections_data[doc.collection]['documents'].append(doc.text)
            collections_data[doc.collection]['embeddings'].append(
                doc.embedding)
            collections_data[doc.collection]['metadatas'].append(
                doc.metadata.to_dict())

        success_count = 0
        error_count = 0
        errors = []

        # Process each collection
        for collection_type, data in collections_data.items():
            try:
                collection = self.client._get_collection(collection_type)
                collection.add(**data)
                success_count += len(data['ids'])

                logger.debug(
                    f"Stored {len(data['ids'])} documents in collection {collection_type.value}")

            except Exception as e:
                error_count += len(data['ids'])
                error_msg = f"Failed to store batch in collection {collection_type.value}: {e}"
                errors.append(error_msg)
                logger.error(error_msg)

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        # Update statistics
        self.health.update_batch_stats()
        self.health.stats['documents_stored'] += success_count
        self.health.stats['total_processing_time'] += processing_time

        result = VectorBatchResult(
            operation_type='add',
            collection=documents[0].collection if documents else VectorCollectionType.MESSAGES,
            processed_count=len(documents),
            success_count=success_count,
            error_count=error_count,
            errors=errors,
            processing_time=processing_time
        )

        logger.info(
            f"Batch store completed: {success_count}/{len(documents)} successful")
        return result

    async def search_similar(
        self,
        query: VectorSearchQuery,
        embedding: Optional[List[float]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar documents using vector similarity."""
        try:
            start_time = datetime.utcnow()

            collection = self.client._get_collection(query.collection)

            # Prepare query parameters
            query_params = {
                'n_results': query.limit
            }

            # Add query embedding or text
            if embedding:
                query_params['query_embeddings'] = [embedding]
            elif query.text:
                query_params['query_texts'] = [query.text]
            else:
                raise ValueError(
                    "Either text or embedding must be provided for search")

            # Add metadata filters
            where_clause = query.build_where_clause()
            if where_clause:
                query_params['where'] = where_clause

            # Perform search
            results = collection.query(**query_params)

            # Convert results to VectorSearchResult objects
            search_results = []

            if results['ids'] and results['ids'][0]:  # Check if we have results
                for i in range(len(results['ids'][0])):
                    result = VectorSearchResult.from_chroma_result(
                        doc_id=results['ids'][0][i],
                        document=results['documents'][0][i],
                        metadata=results['metadatas'][0][i],
                        distance=results['distances'][0][i]
                    )
                    search_results.append(result)

            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self.health.update_search_stats()
            self.health.stats['total_processing_time'] += processing_time

            logger.debug(
                f"Search completed: {len(search_results)} results in {processing_time:.3f}s")
            return search_results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def search_by_metadata(
        self,
        collection_type: VectorCollectionType,
        metadata_filters: Dict[str, Any],
        limit: int = 100
    ) -> List[VectorSearchResult]:
        """Search documents by metadata only (no vector similarity)."""
        try:
            collection = self.client._get_collection(collection_type)

            results = collection.get(
                where=metadata_filters,
                limit=limit,
                include=['documents', 'metadatas']
            )

            # Convert to VectorSearchResult objects (without distance/similarity)
            search_results = []

            if results['ids']:
                for i in range(len(results['ids'])):
                    from .types import VectorMetadata
                    result = VectorSearchResult(
                        id=results['ids'][i],
                        text=results['documents'][i] if results['documents'] else "",
                        metadata=VectorMetadata.from_dict(
                            results['metadatas'][i]),
                        distance=0.0,  # No distance for metadata-only search
                        similarity_score=1.0  # Perfect match for metadata search
                    )
                    search_results.append(result)

            logger.debug(
                f"Metadata search completed: {len(search_results)} results")
            return search_results

        except Exception as e:
            logger.error(f"Metadata search failed: {e}")
            return []

    async def update_document(self, document: VectorDocument) -> bool:
        """Update an existing document in the vector database."""
        try:
            collection = self.client._get_collection(document.collection)

            # Chroma update operation
            collection.update(
                ids=[document.id],
                documents=[document.text],
                embeddings=[document.embedding],
                metadatas=[document.metadata.to_dict()]
            )

            logger.debug(
                f"Updated document {document.id} in collection {document.collection.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to update document {document.id}: {e}")
            return False

    async def delete_document(self, document_id: str, collection_type: VectorCollectionType) -> bool:
        """Delete a document from the vector database."""
        try:
            collection = self.client._get_collection(collection_type)
            collection.delete(ids=[document_id])

            logger.debug(
                f"Deleted document {document_id} from collection {collection_type.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False

    async def delete_documents_batch(
        self,
        document_ids: List[str],
        collection_type: VectorCollectionType
    ) -> VectorBatchResult:
        """Delete multiple documents in batch."""
        start_time = datetime.utcnow()

        try:
            collection = self.client._get_collection(collection_type)
            collection.delete(ids=document_ids)

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            result = VectorBatchResult(
                operation_type='delete',
                collection=collection_type,
                processed_count=len(document_ids),
                success_count=len(document_ids),
                error_count=0,
                processing_time=processing_time
            )

            logger.info(
                f"Batch delete completed: {len(document_ids)} documents deleted")
            return result

        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()

            result = VectorBatchResult(
                operation_type='delete',
                collection=collection_type,
                processed_count=len(document_ids),
                success_count=0,
                error_count=len(document_ids),
                errors=[str(e)],
                processing_time=processing_time
            )

            logger.error(f"Batch delete failed: {e}")
            return result

    async def reset_collection(self, collection_type: VectorCollectionType) -> bool:
        """Reset (clear) a specific collection."""
        try:
            collection_name = f"mesh_{collection_type.value}"

            # Delete existing collection
            self.client._client.delete_collection(name=collection_name)

            # Recreate collection
            collection = self.client._client.create_collection(
                name=collection_name,
                metadata={
                    "description": f"MESH {collection_type.value} embeddings"}
            )

            self.client._collections[collection_type] = collection
            self.health.stats['collection_counts'][collection_type.value] = 0

            logger.info(f"Reset collection {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to reset collection {collection_type}: {e}")
            return False
