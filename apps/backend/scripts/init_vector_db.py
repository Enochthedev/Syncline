#!/usr/bin/env python3
"""
Vector Database Initialization Script

Initializes ChromaDB with default collections and settings.
Can be run standalone or imported as a module.

Usage:
    python scripts/init_vector_db.py [--reset] [--collection NAME]
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import settings
from services.vector_db.chroma_client import ChromaDBClient, get_chroma_client

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def init_vector_db(
    reset: bool = False,
    collection_name: str | None = None,
) -> bool:
    """
    Initialize the vector database.

    Args:
        reset: Whether to reset (delete all data) before initializing
        collection_name: Specific collection to create (creates default if None)

    Returns:
        True if successful
    """
    try:
        logger.info("=" * 60)
        logger.info("Vector Database Initialization")
        logger.info("=" * 60)

        # Get ChromaDB client
        client = get_chroma_client()

        logger.info(f"Persist directory: {client.persist_directory}")
        logger.info(f"Default collection: {client.collection_name}")
        logger.info(f"Distance function: {client.distance_function}")

        # Health check
        logger.info("\nPerforming health check...")
        if not client.health_check():
            logger.error("❌ ChromaDB health check failed")
            return False
        logger.info("✓ ChromaDB is accessible")

        # Reset if requested
        if reset:
            logger.warning("\n⚠️  Resetting ChromaDB (deleting all data)...")
            if client.reset():
                logger.info("✓ ChromaDB reset complete")
            else:
                logger.error("❌ Failed to reset ChromaDB")
                return False

        # List existing collections
        logger.info("\nExisting collections:")
        existing_collections = client.list_collections()
        if existing_collections:
            for col in existing_collections:
                count = client.count_documents(col)
                logger.info(f"  - {col} ({count} documents)")
        else:
            logger.info("  (none)")

        # Create collection(s)
        collections_to_create = []
        if collection_name:
            collections_to_create.append(collection_name)
        else:
            # Create default collections
            collections_to_create.extend(
                [
                    settings.CHROMA_COLLECTION_NAME,
                    f"{settings.CHROMA_COLLECTION_NAME}_threads",
                ]
            )

        logger.info("\nCreating collections...")
        for col_name in collections_to_create:
            collection = client.get_or_create_collection(
                name=col_name,
                metadata={
                    "description": f"Collection for {col_name}",
                    "created_by": "init_vector_db.py",
                },
            )
            count = client.count_documents(col_name)
            logger.info(f"✓ Collection '{col_name}' ready ({count} documents)")

        # Final status
        logger.info("\n" + "=" * 60)
        logger.info("✓ Vector database initialization complete")
        logger.info("=" * 60)

        # Summary
        all_collections = client.list_collections()
        total_docs = sum(client.count_documents(col) for col in all_collections)
        logger.info(f"\nSummary:")
        logger.info(f"  Collections: {len(all_collections)}")
        logger.info(f"  Total documents: {total_docs}")
        logger.info(f"  Persist directory: {client.persist_directory}")

        return True

    except Exception as e:
        logger.error(f"❌ Vector database initialization failed: {e}", exc_info=True)
        return False


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(description="Initialize ChromaDB vector database")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database (delete all data) before initializing",
    )
    parser.add_argument(
        "--collection",
        type=str,
        help="Specific collection name to create (creates defaults if not specified)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run initialization
    success = init_vector_db(
        reset=args.reset,
        collection_name=args.collection,
    )

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
