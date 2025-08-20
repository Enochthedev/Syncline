#!/usr/bin/env python3
"""
Vector Database Management Script

This script provides utilities for managing the vector database including
initialization, batch processing, health checks, and maintenance operations.
"""

from services.vector_db import get_vector_db, VectorBatchProcessor, BatchProcessingConfig
from services.vector_db.types import VectorCollectionType
from config.config import settings
import asyncio
import argparse
import logging
import sys
from datetime import datetime, timedelta
from typing import Optional
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def initialize_vector_db():
    """Initialize the vector database and collections."""
    try:
        logger.info("Initializing vector database...")

        vector_db = await get_vector_db()

        # Perform health check
        health_result = await vector_db.health_check()

        if health_result['status'] == 'healthy':
            logger.info("Vector database initialized successfully")

            # Print collection stats
            for collection_type in VectorCollectionType:
                stats = await vector_db.get_collection_stats(collection_type)
                logger.info(
                    f"Collection {collection_type.value}: {stats['document_count']} documents")

            return True
        else:
            logger.error(
                f"Vector database health check failed: {health_result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        logger.error(f"Failed to initialize vector database: {e}")
        return False


async def process_historical_messages(limit: Optional[int] = None, batch_size: int = 100):
    """Process historical messages for embedding generation."""
    try:
        logger.info(
            f"Starting historical message processing (limit: {limit}, batch_size: {batch_size})")

        # Configure batch processor
        config = BatchProcessingConfig(
            batch_size=batch_size,
            max_concurrent_batches=3,
            embedding_batch_size=50,
            progress_callback=lambda processed, total: logger.info(
                f"Progress: {processed}/{total} messages processed")
        )

        processor = VectorBatchProcessor(config)
        await processor.initialize()

        # Process messages
        result = await processor.process_historical_messages(limit=limit)

        # Print results
        logger.info(f"Processing completed:")
        logger.info(f"  Total items: {result.total_items}")
        logger.info(f"  Processed: {result.processed_items}")
        logger.info(f"  Successful: {result.successful_items}")
        logger.info(f"  Failed: {result.failed_items}")
        logger.info(f"  Success rate: {result.success_rate:.2%}")
        logger.info(f"  Processing time: {result.processing_time:.2f}s")

        if result.errors:
            logger.warning(f"Errors encountered: {len(result.errors)}")
            for error in result.errors[:5]:  # Show first 5 errors
                logger.warning(f"  - {error}")

        return result.success_rate > 0.8  # Consider successful if >80% success rate

    except Exception as e:
        logger.error(f"Historical message processing failed: {e}")
        return False


async def process_summaries(summary_type: Optional[str] = None, limit: Optional[int] = None):
    """Process summaries for embedding generation."""
    try:
        logger.info(
            f"Processing summaries (type: {summary_type}, limit: {limit})")

        processor = VectorBatchProcessor()
        await processor.initialize()

        result = await processor.process_summaries_batch(summary_type=summary_type, limit=limit)

        logger.info(f"Summary processing completed:")
        logger.info(f"  Total items: {result.total_items}")
        logger.info(f"  Successful: {result.successful_items}")
        logger.info(f"  Failed: {result.failed_items}")
        logger.info(f"  Success rate: {result.success_rate:.2%}")

        return result.success_rate > 0.8

    except Exception as e:
        logger.error(f"Summary processing failed: {e}")
        return False


async def process_entities(entity_type: Optional[str] = None, limit: Optional[int] = None):
    """Process entities for embedding generation."""
    try:
        logger.info(
            f"Processing entities (type: {entity_type}, limit: {limit})")

        processor = VectorBatchProcessor()
        await processor.initialize()

        result = await processor.process_entities_batch(entity_type=entity_type, limit=limit)

        logger.info(f"Entity processing completed:")
        logger.info(f"  Total items: {result.total_items}")
        logger.info(f"  Successful: {result.successful_items}")
        logger.info(f"  Failed: {result.failed_items}")
        logger.info(f"  Success rate: {result.success_rate:.2%}")

        return result.success_rate > 0.8

    except Exception as e:
        logger.error(f"Entity processing failed: {e}")
        return False


async def health_check():
    """Perform comprehensive health check."""
    try:
        logger.info("Performing vector database health check...")

        vector_db = await get_vector_db()
        health_result = await vector_db.health_check()

        logger.info(f"Health check status: {health_result['status']}")

        if health_result['status'] == 'healthy':
            logger.info("✓ Store test: Passed")
            logger.info("✓ Search test: Passed")

            # Get detailed stats
            stats = await vector_db.get_stats()
            logger.info(f"Database statistics:")
            logger.info(
                f"  Collections initialized: {stats['collections_initialized']}")
            logger.info(
                f"  Total documents stored: {stats['documents_stored']}")
            logger.info(
                f"  Total searches performed: {stats['searches_performed']}")
            logger.info(
                f"  Average processing time: {stats['average_processing_time']:.3f}s")

            # Collection counts
            for collection_type in VectorCollectionType:
                collection_stats = await vector_db.get_collection_stats(collection_type)
                logger.info(
                    f"  {collection_type.value}: {collection_stats['document_count']} documents")

            return True
        else:
            logger.error(
                f"✗ Health check failed: {health_result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False


async def reset_collections(collection_types: Optional[list] = None):
    """Reset (clear) specified collections."""
    try:
        vector_db = await get_vector_db()

        collections_to_reset = collection_types or [
            ct.value for ct in VectorCollectionType]

        logger.warning(f"Resetting collections: {collections_to_reset}")
        logger.warning(
            "This will permanently delete all data in these collections!")

        # Confirm in interactive mode
        if sys.stdin.isatty():
            response = input("Are you sure you want to continue? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Operation cancelled")
                return False

        success_count = 0

        for collection_name in collections_to_reset:
            try:
                collection_type = VectorCollectionType(collection_name)
                success = await vector_db.reset_collection(collection_type)

                if success:
                    logger.info(f"✓ Reset collection: {collection_name}")
                    success_count += 1
                else:
                    logger.error(
                        f"✗ Failed to reset collection: {collection_name}")

            except ValueError:
                logger.error(f"✗ Invalid collection type: {collection_name}")

        logger.info(
            f"Reset completed: {success_count}/{len(collections_to_reset)} collections")
        return success_count == len(collections_to_reset)

    except Exception as e:
        logger.error(f"Collection reset failed: {e}")
        return False


async def search_test(query_text: str, collection: str = "messages", limit: int = 5):
    """Test vector search functionality."""
    try:
        logger.info(f"Testing search with query: '{query_text}'")

        from services.vector_db.types import VectorSearchQuery
        from services.ai.embeddings import get_embedding_service

        # Get embedding for query
        embedding_service = await get_embedding_service()
        embedding_result = await embedding_service.generate_embedding(query_text)

        # Perform search
        vector_db = await get_vector_db()

        query = VectorSearchQuery(
            text=query_text,
            collection=VectorCollectionType(collection),
            limit=limit
        )

        results = await vector_db.search_similar(query, embedding_result.embedding)

        logger.info(f"Search completed: {len(results)} results found")

        for i, result in enumerate(results):
            logger.info(f"Result {i+1}:")
            logger.info(f"  ID: {result.id}")
            logger.info(f"  Similarity: {result.similarity_score:.3f}")
            logger.info(f"  Text: {result.text[:100]}...")
            logger.info(f"  Platform: {result.metadata.platform}")
            logger.info(f"  Timestamp: {result.metadata.timestamp}")

        return len(results) > 0

    except Exception as e:
        logger.error(f"Search test failed: {e}")
        return False


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Vector Database Management Tool")

    subparsers = parser.add_subparsers(
        dest='command', help='Available commands')

    # Initialize command
    init_parser = subparsers.add_parser(
        'init', help='Initialize vector database')

    # Process messages command
    process_parser = subparsers.add_parser(
        'process-messages', help='Process historical messages')
    process_parser.add_argument(
        '--limit', type=int, help='Maximum number of messages to process')
    process_parser.add_argument(
        '--batch-size', type=int, default=100, help='Batch size for processing')

    # Process summaries command
    summaries_parser = subparsers.add_parser(
        'process-summaries', help='Process summaries')
    summaries_parser.add_argument('--type', help='Summary type to process')
    summaries_parser.add_argument(
        '--limit', type=int, help='Maximum number of summaries to process')

    # Process entities command
    entities_parser = subparsers.add_parser(
        'process-entities', help='Process entities')
    entities_parser.add_argument('--type', help='Entity type to process')
    entities_parser.add_argument(
        '--limit', type=int, help='Maximum number of entities to process')

    # Health check command
    health_parser = subparsers.add_parser(
        'health', help='Perform health check')

    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset collections')
    reset_parser.add_argument(
        '--collections', nargs='+', help='Collections to reset')

    # Search test command
    search_parser = subparsers.add_parser(
        'search', help='Test search functionality')
    search_parser.add_argument('query', help='Search query text')
    search_parser.add_argument(
        '--collection', default='messages', help='Collection to search')
    search_parser.add_argument(
        '--limit', type=int, default=5, help='Number of results to return')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Run the appropriate command
    async def run_command():
        try:
            if args.command == 'init':
                success = await initialize_vector_db()
            elif args.command == 'process-messages':
                success = await process_historical_messages(args.limit, args.batch_size)
            elif args.command == 'process-summaries':
                success = await process_summaries(args.type, args.limit)
            elif args.command == 'process-entities':
                success = await process_entities(args.type, args.limit)
            elif args.command == 'health':
                success = await health_check()
            elif args.command == 'reset':
                success = await reset_collections(args.collections)
            elif args.command == 'search':
                success = await search_test(args.query, args.collection, args.limit)
            else:
                logger.error(f"Unknown command: {args.command}")
                success = False

            if success:
                logger.info("Command completed successfully")
                sys.exit(0)
            else:
                logger.error("Command failed")
                sys.exit(1)

        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            sys.exit(1)

    # Run the async command
    asyncio.run(run_command())


if __name__ == "__main__":
    main()
