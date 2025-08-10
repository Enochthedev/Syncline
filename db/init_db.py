"""Database initialization utilities."""

import asyncio
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from config.config import settings
from db.redis_client import initialize_redis, close_redis

logger = logging.getLogger(__name__)

async def create_database_if_not_exists():
    """Create the database if it doesn't exist."""
    # Parse the database URL to get connection details
    db_url = settings.DATABASE_URL
    
    # Extract database name from URL
    if "postgresql+asyncpg://" in db_url:
        # Split URL to get database name
        parts = db_url.split("/")
        db_name = parts[-1]
        base_url = "/".join(parts[:-1]) + "/postgres"  # Connect to postgres db first
        
        # Create engine to connect to postgres database
        engine = create_async_engine(base_url, isolation_level="AUTOCOMMIT")
        
        try:
            async with engine.begin() as conn:
                # Check if database exists
                result = await conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                    {"db_name": db_name}
                )
                
                if not result.fetchone():
                    # Create database
                    await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                    logger.info(f"Created database: {db_name}")
                else:
                    logger.info(f"Database {db_name} already exists")
                    
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            raise
        finally:
            await engine.dispose()

async def initialize_infrastructure():
    """Initialize all infrastructure components."""
    logger.info("Initializing infrastructure...")
    
    try:
        # Create database if needed
        await create_database_if_not_exists()
        
        # Initialize Redis connection
        await initialize_redis()
        logger.info("Redis connection initialized")
        
        logger.info("Infrastructure initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize infrastructure: {e}")
        raise

async def cleanup_infrastructure():
    """Cleanup infrastructure connections."""
    logger.info("Cleaning up infrastructure...")
    
    try:
        await close_redis()
        logger.info("Infrastructure cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during infrastructure cleanup: {e}")

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Run initialization
    asyncio.run(initialize_infrastructure())