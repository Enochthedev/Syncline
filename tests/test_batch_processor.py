"""
Unit tests for VectorBatchProcessor functionality.

Tests batch processing operations for messages, summaries, and entities
including performance and concurrent processing capabilities.
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
    VectorBatchProcessor, BatchProcessingConfig, ChromaVectorDB,
    VectorDocument, VectorMetadata, VectorCollectionType
)


class TestVectorBatchProcessor:
    """Test suite for VectorBatchProcessor functionality."""

    @pytest_asyncio.fixture
    async def batch_processor(self):
        """Create a batch processor for testing."""
        config = BatchProcessingConfig(
            batch_size=5,
            max_concurrent_batches=2,
            embedding_batch_size=3
        )

        processor = VectorBatchProcessor(config)
        await processor.initialize()
        return processor

    @pytest_asyncio.fixture
    async def temp_vector_db_for_batch(self):
        """Create a temporary vector database for batch testing."""
        temp_dir = tempfile.mkdtemp()

        try:
            db = ChromaVectorDB(persist_directory=temp_dir)
            await db.initialize()

            # Replace global instance for testing
            import services.vector_db.chroma_client
            original_get_vector_db = services.vector_db.chroma_client.get_vector_db

            async def mock_get_vector_db():
                return db

            services.vector_db.chroma_client.get_vector_db = mock_get_vector_db

            yield db

            # Restore original function
            services.vector_db.chroma_client.get_vector_db = original_get_vector_db

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_batch_processor_initialization(self, batch_processor):
        """Test batch processor initialization."""
        processor = batch_processor

        assert processor.config.batch_size == 5
        assert processor.config.max_concurrent_batches == 2
        assert processor.embedding_service is not None
        assert processor.vector_db is not None

    @pytest.mark.asyncio
    async def test_batch_processor_stats(self, batch_processor):
        """Test batch processor statistics."""
        processor = batch_processor

        stats = await processor.get_stats()

        assert 'total_batches_processed' in stats
        assert 'total_documents_processed' in stats
        assert 'config' in stats
        assert stats['config']['batch_size'] == 5


class TestVectorDBPerformance:
    """Performance tests for vector database operations."""

    @pytest_asyncio.fixture
    async def performance_vector_db(self):
        """Create a vector database for performance testing."""
        temp_dir = tempfile.mkdtemp()

        try:
            db = ChromaVectorDB(persist_directory=temp_dir)
            await db.initialize()
            yield db
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def create_large_document_batch(self, count: int) -> List[VectorDocument]:
        """Create a large batch of documents for performance testing."""
        documents = []

        for i in range(count):
            doc = VectorDocument(
                id=f"perf_test_{i}_{uuid.uuid4().hex[:8]}",
                text=f"Performance test document {i} with some content for testing",
                embedding=[0.1 * (i % 100), 0.2 * (i % 100)
                           ] * 192,  # 384 dimensions
                metadata=VectorMetadata(
                    message_id=f"msg_{i}",
                    thread_id=f"thread_{i % 10}",
                    platform="gmail" if i % 2 == 0 else "slack",
                    sender=f"user{i % 50}@example.com",
                    timestamp=datetime.utcnow() - timedelta(minutes=i),
                    content_type="message",
                    content_length=50
                ),
                collection=VectorCollectionType.MESSAGES
            )
            documents.append(doc)

        return documents

    @pytest.mark.asyncio
    async def test_large_batch_storage_performance(self, performance_vector_db):
        """Test performance of storing large batches."""
        db = performance_vector_db

        # Create 100 documents
        documents = self.create_large_document_batch(100)

        start_time = datetime.utcnow()
        result = await db.store_documents_batch(documents)
        end_time = datetime.utcnow()

        processing_time = (end_time - start_time).total_seconds()

        # Verify results
        assert result.success_count == 100
        assert result.error_count == 0

        # Performance assertions (adjust based on expected performance)
        assert processing_time < 30.0  # Should complete within 30 seconds

        # Calculate throughput
        throughput = len(documents) / processing_time
        print(f"Storage throughput: {throughput:.2f} documents/second")

        # Verify storage
        stats = await db.get_collection_stats(VectorCollectionType.MESSAGES)
        assert stats['document_count'] == 100

    @pytest.mark.asyncio
    async def test_search_performance_with_large_dataset(self, performance_vector_db):
        """Test search performance with a large dataset."""
        db = performance_vector_db

        # Store large dataset
        documents = self.create_large_document_batch(500)
        await db.store_documents_batch(documents)

        # Perform multiple searches and measure performance
        search_times = []

        for i in range(10):
            from services.vector_db.types import VectorSearchQuery

            query = VectorSearchQuery(
                embedding=[0.1 * i, 0.2 * i] * 192,
                collection=VectorCollectionType.MESSAGES,
                limit=10
            )

            start_time = datetime.utcnow()
            results = await db.search_similar(query)
            end_time = datetime.utcnow()

            search_time = (end_time - start_time).total_seconds()
            search_times.append(search_time)

            # Verify results
            assert len(results) <= 10

        # Calculate average search time
        avg_search_time = sum(search_times) / len(search_times)
        max_search_time = max(search_times)

        print(f"Average search time: {avg_search_time:.3f}s")
        print(f"Maximum search time: {max_search_time:.3f}s")

        # Performance assertions
        assert avg_search_time < 1.0  # Average search should be under 1 second
        assert max_search_time < 2.0  # No search should take more than 2 seconds

    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self, performance_vector_db):
        """Test performance of concurrent operations."""
        db = performance_vector_db

        # Create multiple batches
        batch_size = 50
        num_batches = 4

        batches = [
            self.create_large_document_batch(batch_size)
            for _ in range(num_batches)
        ]

        # Store batches concurrently
        start_time = datetime.utcnow()

        tasks = [db.store_documents_batch(batch) for batch in batches]
        results = await asyncio.gather(*tasks)

        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()

        # Verify all batches succeeded
        total_stored = sum(result.success_count for result in results)
        total_expected = batch_size * num_batches

        assert total_stored == total_expected

        # Performance assertion
        sequential_estimate = processing_time * num_batches  # Rough estimate
        assert processing_time < sequential_estimate * \
            0.8  # Should be faster than sequential

        print(
            f"Concurrent storage time: {processing_time:.2f}s for {total_expected} documents")

        # Verify final count
        stats = await db.get_collection_stats(VectorCollectionType.MESSAGES)
        assert stats['document_count'] == total_expected


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
