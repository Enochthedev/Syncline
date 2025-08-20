"""
Batch processing utilities for vector database operations.

This module provides efficient batch processing for large-scale embedding
operations, including historical message processing and bulk updates.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from services.ai.embeddings import get_embedding_service

from .chroma_client import get_vector_db
from .batch_config import BatchProcessingConfig, BatchProcessingResult, BatchOperationStats
from .batch_operations import BatchOperationHandler, BatchDataFetcher

logger = logging.getLogger(__name__)


class VectorBatchProcessor:
    """
    Batch processor for vector database operations.

    Handles large-scale processing of messages, summaries, and entities
    for embedding generation and vector storage.
    """

    def __init__(self, config: Optional[BatchProcessingConfig] = None):
        """Initialize batch processor with configuration."""
        self.config = config or BatchProcessingConfig()
        self.embedding_service = None
        self.vector_db = None

        # Processing statistics
        self.stats = BatchOperationStats()

        logger.info(
            f"VectorBatchProcessor initialized with batch_size={self.config.batch_size}")

    async def initialize(self) -> None:
        """Initialize required services."""
        self.embedding_service = await get_embedding_service()
        self.vector_db = await get_vector_db()

        # Initialize operation handler and data fetcher
        self.operation_handler = BatchOperationHandler(
            self.config, self.embedding_service, self.vector_db
        )
        self.data_fetcher = BatchDataFetcher(self.config)

        logger.info("VectorBatchProcessor services initialized")

    async def process_historical_messages(
        self,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> BatchProcessingResult:
        """Process historical messages for embedding generation and storage."""
        start_time = datetime.utcnow()

        try:
            # Get messages from database
            messages = await self.data_fetcher.fetch_messages_batch(limit, offset)
            total_messages = len(messages)

            if total_messages == 0:
                return BatchProcessingResult(
                    operation_type='process_historical_messages',
                    total_items=0,
                    processed_items=0,
                    successful_items=0,
                    failed_items=0,
                    processing_time=0.0
                )

            logger.info(f"Processing {total_messages} historical messages")

            # Process in batches with concurrent execution
            processed_count, successful_count, failed_count, errors, batch_results = \
                await self._process_messages_concurrently(messages)

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            # Update statistics
            self.stats.update_stats(
                len(batch_results), processed_count, processing_time)

            result = BatchProcessingResult(
                operation_type='process_historical_messages',
                total_items=total_messages,
                processed_items=processed_count,
                successful_items=successful_count,
                failed_items=failed_count,
                processing_time=processing_time,
                errors=errors,
                batch_results=batch_results
            )

            logger.info(
                f"Historical message processing completed: "
                f"{successful_count}/{total_messages} successful in {processing_time:.2f}s"
            )

            return result

        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Historical message processing failed: {e}")

            return BatchProcessingResult(
                operation_type='process_historical_messages',
                total_items=0,
                processed_items=0,
                successful_items=0,
                failed_items=0,
                processing_time=processing_time,
                errors=[str(e)]
            )

    async def _process_messages_concurrently(self, messages):
        """Process messages in concurrent batches."""
        processed_count = 0
        successful_count = 0
        failed_count = 0
        errors = []
        batch_results = []

        # Create semaphore for concurrent processing
        semaphore = asyncio.Semaphore(self.config.max_concurrent_batches)

        async def process_batch(batch_messages):
            async with semaphore:
                return await self.operation_handler.process_message_batch(batch_messages)

        # Process messages in batches
        tasks = []
        for i in range(0, len(messages), self.config.batch_size):
            batch = messages[i:i + self.config.batch_size]
            task = process_batch(batch)
            tasks.append(task)

        # Execute batches with progress tracking
        for i, task in enumerate(asyncio.as_completed(tasks)):
            try:
                result = await task
                batch_results.append(result)

                processed_count += result.processed_count
                successful_count += result.success_count
                failed_count += result.error_count
                errors.extend(result.errors)

                # Progress callback
                if self.config.progress_callback:
                    self.config.progress_callback(
                        processed_count, len(messages))

                logger.debug(
                    f"Completed batch {i+1}/{len(tasks)}: {result.success_count}/{result.processed_count} successful")

            except Exception as e:
                error_msg = f"Batch processing failed: {e}"
                errors.append(error_msg)
                logger.error(error_msg)

        return processed_count, successful_count, failed_count, errors, batch_results

    async def process_summaries_batch(
        self,
        summary_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> BatchProcessingResult:
        """Process summaries for embedding generation and storage."""
        start_time = datetime.utcnow()

        try:
            # Fetch summaries from database
            summaries = await self.data_fetcher.fetch_summaries_batch(summary_type, limit)
            total_summaries = len(summaries)

            if total_summaries == 0:
                return self._empty_result('process_summaries', 0.0)

            logger.info(f"Processing {total_summaries} summaries")

            # Convert summaries to vector documents
            vector_documents = await self.operation_handler.process_summaries_to_vectors(summaries)

            # Store in vector database
            if vector_documents:
                batch_result = await self.vector_db.store_documents_batch(vector_documents)
                processing_time = (datetime.utcnow() -
                                   start_time).total_seconds()

                return BatchProcessingResult(
                    operation_type='process_summaries',
                    total_items=total_summaries,
                    processed_items=len(vector_documents),
                    successful_items=batch_result.success_count,
                    failed_items=batch_result.error_count,
                    processing_time=processing_time,
                    errors=batch_result.errors,
                    batch_results=[batch_result]
                )
            else:
                processing_time = (datetime.utcnow() -
                                   start_time).total_seconds()
                return self._failed_result('process_summaries', total_summaries, processing_time, ["No summaries could be processed"])

        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Summary batch processing failed: {e}")
            return self._failed_result('process_summaries', 0, processing_time, [str(e)])

    async def process_entities_batch(
        self,
        entity_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> BatchProcessingResult:
        """Process entities for embedding generation and storage."""
        start_time = datetime.utcnow()

        try:
            # Fetch entities from database
            entities = await self.data_fetcher.fetch_entities_batch(entity_type, limit)
            total_entities = len(entities)

            if total_entities == 0:
                return self._empty_result('process_entities', 0.0)

            logger.info(f"Processing {total_entities} entities")

            # Convert entities to vector documents
            vector_documents = await self.operation_handler.process_entities_to_vectors(entities)

            # Store in vector database
            if vector_documents:
                batch_result = await self.vector_db.store_documents_batch(vector_documents)
                processing_time = (datetime.utcnow() -
                                   start_time).total_seconds()

                return BatchProcessingResult(
                    operation_type='process_entities',
                    total_items=total_entities,
                    processed_items=len(vector_documents),
                    successful_items=batch_result.success_count,
                    failed_items=batch_result.error_count,
                    processing_time=processing_time,
                    errors=batch_result.errors,
                    batch_results=[batch_result]
                )
            else:
                processing_time = (datetime.utcnow() -
                                   start_time).total_seconds()
                return self._failed_result('process_entities', total_entities, processing_time, ["No entities could be processed"])

        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Entity batch processing failed: {e}")
            return self._failed_result('process_entities', 0, processing_time, [str(e)])

    def _empty_result(self, operation_type: str, processing_time: float) -> BatchProcessingResult:
        """Create empty result for operations with no items."""
        return BatchProcessingResult(
            operation_type=operation_type,
            total_items=0,
            processed_items=0,
            successful_items=0,
            failed_items=0,
            processing_time=processing_time
        )

    def _failed_result(self, operation_type: str, total_items: int, processing_time: float, errors: List[str]) -> BatchProcessingResult:
        """Create failed result for operations with errors."""
        return BatchProcessingResult(
            operation_type=operation_type,
            total_items=total_items,
            processed_items=0,
            successful_items=0,
            failed_items=total_items,
            processing_time=processing_time,
            errors=errors
        )

    async def get_stats(self) -> Dict[str, Any]:
        """Get batch processor statistics."""
        return {
            **self.stats.to_dict(),
            'config': {
                'batch_size': self.config.batch_size,
                'max_concurrent_batches': self.config.max_concurrent_batches,
                'embedding_batch_size': self.config.embedding_batch_size,
                'retry_attempts': self.config.retry_attempts
            }
        }
