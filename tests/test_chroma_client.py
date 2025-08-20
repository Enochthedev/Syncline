"""
Unit tests for ChromaVectorDB client functionality.

Tests the core ChromaDB client operations including document storage,
retrieval, and collection management.
"""

import asyncio
import pytest
import pytest_asyncio
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import List
import uuid

from services.vector_db import (
    ChromaVectorDB, VectorDocument, VectorMetadata, VectorCollectionType,
    VectorSearchQuery
)


class TestChromaVectorDB:
    """Test suite for ChromaVectorDB functionality."""

    @pytest_asyncio.fixture
    async def temp_vector_db(self):
        """Create a temporary vector database for testing."""
        temp_dir = tempfile.mkdtemp()

        try:
            db = ChromaVectorDB(persist_directory=temp_dir)
            await db.initialize()
            yield db
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def sample_vector_document(self):
        """Create a sample vector document for testing."""
        return VectorDocument(
            id=f"test_{uuid.uuid4().hex[:8]}",
            text="This is a test message for vector database testing",
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5] * 77,  # 385 dimensions
            metadata=VectorMetadata(
                message_id="msg_123",
                thread_id="thread_456",
                platform="gmail",
                sender="test@example.com",
                timestamp=datetime.utcnow(),
                content_type="message",
                content_length=50
            ),
            collection=VectorCollectionType.MESSAGES
        )

    @pytest.fixture
    def sample_documents_batch(self):
        """Create a batch of sample documents for testing."""
        documents = []

        for i in range(10):
            doc = VectorDocument(
                id=f"batch_test_{i}_{uuid.uuid4().hex[:8]}",
                text=f"This is test message number {i} for batch testing",
                embedding=[0.1 * i, 0.2 * i, 0.3 * i, 0.4 * i, 0.5 * i] * 77,
                metadata=VectorMetadata(
                    message_id=f"msg_{i}",
                    thread_id=f"thread_{i % 3}",  # 3 different threads
                    platform="gmail" if i % 2 == 0 else "slack",
                    sender=f"user{i}@example.com",
                    timestamp=datetime.utcnow() - timedelta(hours=i),
                    content_type="message",
                    content_length=len(f"This is test message number {i}")
                ),
                collection=VectorCollectionType.MESSAGES
            )
            documents.append(doc)

        return documents

    @pytest.mark.asyncio
    async def test_vector_db_initialization(self, temp_vector_db):
        """Test vector database initialization."""
        db = temp_vector_db

        # Check that collections are initialized
        assert len(db._collections) == len(VectorCollectionType)

        # Check collection stats
        for collection_type in VectorCollectionType:
            stats = await db.get_collection_stats(collection_type)
            assert stats['document_count'] == 0
            assert stats['collection_type'] == collection_type.value

    @pytest.mark.asyncio
    async def test_store_single_document(self, temp_vector_db, sample_vector_document):
        """Test storing a single document."""
        db = temp_vector_db
        doc = sample_vector_document

        # Store document
        success = await db.store_document(doc)
        assert success is True

        # Verify document count
        stats = await db.get_collection_stats(VectorCollectionType.MESSAGES)
        assert stats['document_count'] == 1

    @pytest.mark.asyncio
    async def test_store_documents_batch(self, temp_vector_db, sample_documents_batch):
        """Test batch document storage."""
        db = temp_vector_db
        documents = sample_documents_batch

        # Store batch
        result = await db.store_documents_batch(documents)

        # Verify results
        assert result.operation_type == 'add'
        assert result.processed_count == len(documents)
        assert result.success_count == len(documents)
        assert result.error_count == 0
        assert result.success_rate == 1.0

        # Verify document count
        stats = await db.get_collection_stats(VectorCollectionType.MESSAGES)
        assert stats['document_count'] == len(documents)

    @pytest.mark.asyncio
    async def test_vector_similarity_search(self, temp_vector_db, sample_documents_batch):
        """Test vector similarity search."""
        db = temp_vector_db
        documents = sample_documents_batch

        # Store documents first
        await db.store_documents_batch(documents)

        # Create search query
        query = VectorSearchQuery(
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5] *
            77,  # Similar to first document
            collection=VectorCollectionType.MESSAGES,
            limit=5
        )

        # Perform search
        results = await db.search_similar(query)

        # Verify results
        assert len(results) > 0
        assert len(results) <= 5

        # Check result structure
        for result in results:
            assert result.id is not None
            assert result.text is not None
            assert result.metadata is not None
            assert 0.0 <= result.distance <= 2.0  # Cosine distance range
            assert 0.0 <= result.similarity_score <= 1.0

    @pytest.mark.asyncio
    async def test_metadata_filtering_search(self, temp_vector_db, sample_documents_batch):
        """Test search with metadata filtering."""
        db = temp_vector_db
        documents = sample_documents_batch

        # Store documents first
        await db.store_documents_batch(documents)

        # Search with platform filter
        query = VectorSearchQuery(
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5] * 77,
            collection=VectorCollectionType.MESSAGES,
            platform_filter="gmail",
            limit=10
        )

        results = await db.search_similar(query)

        # Verify all results are from Gmail
        for result in results:
            assert result.metadata.platform == "gmail"

        # Search with thread filter
        query_thread = VectorSearchQuery(
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5] * 77,
            collection=VectorCollectionType.MESSAGES,
            thread_filter="thread_0",
            limit=10
        )

        thread_results = await db.search_similar(query_thread)

        # Verify all results are from the same thread
        for result in thread_results:
            assert result.metadata.thread_id == "thread_0"

    @pytest.mark.asyncio
    async def test_metadata_only_search(self, temp_vector_db, sample_documents_batch):
        """Test metadata-only search without vector similarity."""
        db = temp_vector_db
        documents = sample_documents_batch

        # Store documents first
        await db.store_documents_batch(documents)

        # Search by metadata only
        results = await db.search_by_metadata(
            collection_type=VectorCollectionType.MESSAGES,
            metadata_filters={"platform": "slack"},
            limit=10
        )

        # Verify results
        assert len(results) > 0

        for result in results:
            assert result.metadata.platform == "slack"
            assert result.similarity_score == 1.0  # Perfect match for metadata search

    @pytest.mark.asyncio
    async def test_document_update(self, temp_vector_db, sample_vector_document):
        """Test document update functionality."""
        db = temp_vector_db
        doc = sample_vector_document

        # Store original document
        await db.store_document(doc)

        # Update document
        doc.text = "Updated test message content"
        doc.embedding = [0.9, 0.8, 0.7, 0.6, 0.5] * 77
        doc.metadata.content_length = len(doc.text)

        success = await db.update_document(doc)
        assert success is True

        # Verify update by searching
        query = VectorSearchQuery(
            embedding=doc.embedding,
            collection=VectorCollectionType.MESSAGES,
            limit=1
        )

        results = await db.search_similar(query)
        assert len(results) > 0
        assert results[0].text == "Updated test message content"

    @pytest.mark.asyncio
    async def test_document_deletion(self, temp_vector_db, sample_documents_batch):
        """Test document deletion functionality."""
        db = temp_vector_db
        documents = sample_documents_batch

        # Store documents first
        await db.store_documents_batch(documents)

        # Delete single document
        doc_to_delete = documents[0]
        success = await db.delete_document(doc_to_delete.id, VectorCollectionType.MESSAGES)
        assert success is True

        # Verify deletion
        stats = await db.get_collection_stats(VectorCollectionType.MESSAGES)
        assert stats['document_count'] == len(documents) - 1

        # Delete batch of documents
        ids_to_delete = [doc.id for doc in documents[1:4]]
        batch_result = await db.delete_documents_batch(ids_to_delete, VectorCollectionType.MESSAGES)

        assert batch_result.operation_type == 'delete'
        assert batch_result.success_count == len(ids_to_delete)
        assert batch_result.error_count == 0

        # Verify batch deletion
        final_stats = await db.get_collection_stats(VectorCollectionType.MESSAGES)
        expected_count = len(documents) - 1 - len(ids_to_delete)
        assert final_stats['document_count'] == expected_count

    @pytest.mark.asyncio
    async def test_health_check(self, temp_vector_db):
        """Test vector database health check."""
        db = temp_vector_db

        health_result = await db.health_check()

        assert health_result['status'] == 'healthy'
        assert health_result['store_test'] is True
        assert health_result['search_test'] is True
        assert health_result['collections_count'] == len(VectorCollectionType)
        assert 'stats' in health_result

    @pytest.mark.asyncio
    async def test_collection_reset(self, temp_vector_db, sample_documents_batch):
        """Test collection reset functionality."""
        db = temp_vector_db
        documents = sample_documents_batch

        # Store documents first
        await db.store_documents_batch(documents)

        # Verify documents are stored
        stats_before = await db.get_collection_stats(VectorCollectionType.MESSAGES)
        assert stats_before['document_count'] == len(documents)

        # Reset collection
        success = await db.reset_collection(VectorCollectionType.MESSAGES)
        assert success is True

        # Verify collection is empty
        stats_after = await db.get_collection_stats(VectorCollectionType.MESSAGES)
        assert stats_after['document_count'] == 0


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
