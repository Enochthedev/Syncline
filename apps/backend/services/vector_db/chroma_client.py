"""
ChromaDB Client

Provides vector database functionality using ChromaDB:
- Collection management
- Vector storage and retrieval
- Similarity search
- Local persistence
"""

import logging
from pathlib import Path
from typing import Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from pydantic import BaseModel, Field

from config.config import settings

logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """Result from a similarity search."""
    id: str
    document: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    distance: float
    score: float  # Similarity score (1 - distance for cosine)


class ChromaDBClient:
    """
    ChromaDB client for vector storage and similarity search.
    
    Provides a high-level interface for:
    - Creating and managing collections
    - Adding documents with embeddings
    - Performing similarity searches
    - Managing persistence
    """
    
    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
        distance_function: Optional[str] = None,
    ):
        """
        Initialize ChromaDB client.
        
        Args:
            persist_directory: Directory for persistent storage
            collection_name: Default collection name
            distance_function: Distance metric ('cosine', 'l2', 'ip')
        """
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIRECTORY
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self.distance_function = distance_function or settings.CHROMA_DISTANCE_FUNCTION
        
        # Ensure persist directory exists
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self._client: Optional[chromadb.Client] = None
        self._collections: dict[str, chromadb.Collection] = {}
        
        logger.info(
            f"Initialized ChromaDB client with persistence at {self.persist_directory}"
        )
    
    def _get_client(self) -> chromadb.Client:
        """Get or create ChromaDB client."""
        if self._client is None:
            chroma_settings = ChromaSettings(
                persist_directory=self.persist_directory,
                anonymized_telemetry=False,
            )
            self._client = chromadb.Client(chroma_settings)
            logger.debug("Created ChromaDB client")
        return self._client
    
    def get_or_create_collection(
        self,
        name: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        embedding_function: Optional[Any] = None,
    ) -> chromadb.Collection:
        """
        Get or create a collection.
        
        Args:
            name: Collection name (uses default if not specified)
            metadata: Collection metadata
            embedding_function: Custom embedding function
            
        Returns:
            ChromaDB collection
        """
        name = name or self.collection_name
        
        # Return cached collection if available
        if name in self._collections:
            return self._collections[name]
        
        client = self._get_client()
        
        # Prepare collection metadata
        collection_metadata = metadata or {}
        collection_metadata["hnsw:space"] = self.distance_function
        
        # Get or create collection
        collection = client.get_or_create_collection(
            name=name,
            metadata=collection_metadata,
            embedding_function=embedding_function,
        )
        
        # Cache the collection
        self._collections[name] = collection
        
        logger.info(f"Got or created collection: {name}")
        return collection
    
    def list_collections(self) -> list[str]:
        """
        List all collections.
        
        Returns:
            List of collection names
        """
        client = self._get_client()
        collections = client.list_collections()
        return [col.name for col in collections]
    
    def delete_collection(self, name: str) -> bool:
        """
        Delete a collection.
        
        Args:
            name: Collection name
            
        Returns:
            True if successful
        """
        try:
            client = self._get_client()
            client.delete_collection(name=name)
            
            # Remove from cache
            if name in self._collections:
                del self._collections[name]
            
            logger.info(f"Deleted collection: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection {name}: {e}")
            return False
    
    def add_documents(
        self,
        documents: list[str],
        ids: list[str],
        metadatas: Optional[list[dict[str, Any]]] = None,
        embeddings: Optional[list[list[float]]] = None,
        collection_name: Optional[str] = None,
    ) -> bool:
        """
        Add documents to a collection.
        
        Args:
            documents: List of document texts
            ids: List of document IDs
            metadatas: Optional list of metadata dicts
            embeddings: Optional pre-computed embeddings
            collection_name: Collection name (uses default if not specified)
            
        Returns:
            True if successful
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            
            # Prepare arguments
            add_kwargs = {
                "documents": documents,
                "ids": ids,
            }
            
            if metadatas:
                add_kwargs["metadatas"] = metadatas
            
            if embeddings:
                add_kwargs["embeddings"] = embeddings
            
            # Add to collection
            collection.add(**add_kwargs)
            
            logger.debug(f"Added {len(documents)} documents to collection")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return False
    
    def update_documents(
        self,
        ids: list[str],
        documents: Optional[list[str]] = None,
        metadatas: Optional[list[dict[str, Any]]] = None,
        embeddings: Optional[list[list[float]]] = None,
        collection_name: Optional[str] = None,
    ) -> bool:
        """
        Update existing documents.
        
        Args:
            ids: List of document IDs to update
            documents: Optional updated document texts
            metadatas: Optional updated metadata
            embeddings: Optional updated embeddings
            collection_name: Collection name
            
        Returns:
            True if successful
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            
            # Prepare arguments
            update_kwargs = {"ids": ids}
            
            if documents:
                update_kwargs["documents"] = documents
            
            if metadatas:
                update_kwargs["metadatas"] = metadatas
            
            if embeddings:
                update_kwargs["embeddings"] = embeddings
            
            # Update in collection
            collection.update(**update_kwargs)
            
            logger.debug(f"Updated {len(ids)} documents in collection")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update documents: {e}")
            return False
    
    def delete_documents(
        self,
        ids: list[str],
        collection_name: Optional[str] = None,
    ) -> bool:
        """
        Delete documents from a collection.
        
        Args:
            ids: List of document IDs to delete
            collection_name: Collection name
            
        Returns:
            True if successful
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            collection.delete(ids=ids)
            
            logger.debug(f"Deleted {len(ids)} documents from collection")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return False
    
    def query(
        self,
        query_texts: Optional[list[str]] = None,
        query_embeddings: Optional[list[list[float]]] = None,
        n_results: int = 10,
        where: Optional[dict[str, Any]] = None,
        where_document: Optional[dict[str, Any]] = None,
        collection_name: Optional[str] = None,
    ) -> list[SearchResult]:
        """
        Query the collection for similar documents.
        
        Args:
            query_texts: Query texts (will be embedded)
            query_embeddings: Pre-computed query embeddings
            n_results: Number of results to return
            where: Metadata filter
            where_document: Document content filter
            collection_name: Collection name
            
        Returns:
            List of search results
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            
            # Prepare query arguments
            query_kwargs = {"n_results": n_results}
            
            if query_texts:
                query_kwargs["query_texts"] = query_texts
            elif query_embeddings:
                query_kwargs["query_embeddings"] = query_embeddings
            else:
                raise ValueError("Must provide either query_texts or query_embeddings")
            
            if where:
                query_kwargs["where"] = where
            
            if where_document:
                query_kwargs["where_document"] = where_document
            
            # Execute query
            results = collection.query(**query_kwargs)
            
            # Parse results into SearchResult objects
            search_results = []
            
            # ChromaDB returns results as lists of lists (one per query)
            # We'll flatten for single query case
            for i in range(len(results["ids"][0])):
                result = SearchResult(
                    id=results["ids"][0][i],
                    document=results["documents"][0][i],
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    distance=results["distances"][0][i] if results["distances"] else 0.0,
                    score=1.0 - results["distances"][0][i] if results["distances"] else 1.0,
                )
                search_results.append(result)
            
            logger.debug(f"Query returned {len(search_results)} results")
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to query collection: {e}")
            return []
    
    def get_documents(
        self,
        ids: Optional[list[str]] = None,
        where: Optional[dict[str, Any]] = None,
        limit: Optional[int] = None,
        collection_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get documents from collection.
        
        Args:
            ids: Specific document IDs to retrieve
            where: Metadata filter
            limit: Maximum number of documents
            collection_name: Collection name
            
        Returns:
            Dictionary with ids, documents, metadatas, embeddings
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            
            # Prepare get arguments
            get_kwargs = {}
            
            if ids:
                get_kwargs["ids"] = ids
            
            if where:
                get_kwargs["where"] = where
            
            if limit:
                get_kwargs["limit"] = limit
            
            # Get documents
            results = collection.get(**get_kwargs)
            
            logger.debug(f"Retrieved {len(results['ids'])} documents")
            return results
            
        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            return {"ids": [], "documents": [], "metadatas": [], "embeddings": []}
    
    def count_documents(self, collection_name: Optional[str] = None) -> int:
        """
        Count documents in a collection.
        
        Args:
            collection_name: Collection name
            
        Returns:
            Number of documents
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            count = collection.count()
            logger.debug(f"Collection has {count} documents")
            return count
        except Exception as e:
            logger.error(f"Failed to count documents: {e}")
            return 0
    
    def health_check(self) -> bool:
        """
        Check if ChromaDB is accessible.
        
        Returns:
            True if healthy
        """
        try:
            client = self._get_client()
            # Try to list collections as a health check
            client.list_collections()
            logger.debug("ChromaDB health check passed")
            return True
        except Exception as e:
            logger.warning(f"ChromaDB health check failed: {e}")
            return False
    
    def reset(self) -> bool:
        """
        Reset the ChromaDB client (clear all collections).
        
        WARNING: This deletes all data!
        
        Returns:
            True if successful
        """
        try:
            client = self._get_client()
            client.reset()
            self._collections.clear()
            logger.warning("ChromaDB reset - all collections deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to reset ChromaDB: {e}")
            return False


# Global client instance
_chroma_client: Optional[ChromaDBClient] = None


def get_chroma_client() -> ChromaDBClient:
    """
    Get the global ChromaDB client instance.
    
    Returns:
        ChromaDB client
    """
    global _chroma_client
    
    if _chroma_client is None:
        _chroma_client = ChromaDBClient()
    
    return _chroma_client


__all__ = [
    "ChromaDBClient",
    "SearchResult",
    "get_chroma_client",
]
