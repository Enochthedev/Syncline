"""Test script to verify core infrastructure setup."""

import asyncio
import logging
from db.init_db import initialize_infrastructure, cleanup_infrastructure
from db.session import get_db
from db.redis_client import get_redis
# Import all models to ensure they're loaded
from db.models.participant import Participant
from db.models.thread import Thread
from db.models.message import Message
from db.models.attachment import Attachment
from db.models.entity import Entity, MessageEntity
from db.models.summary import Summary
from sqlalchemy import text
import uuid
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_connection():
    """Test database connection and basic operations."""
    logger.info("Testing database connection...")

    try:
        async for session in get_db():
            # Test basic query
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
            logger.info("✓ Database connection successful")

            # Test table creation by checking if tables exist
            result = await session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            )
            tables = [row[0] for row in result.fetchall()]

            expected_tables = ['participants', 'threads', 'messages',
                               'entities', 'summaries', 'attachments', 'message_entities']
            for table in expected_tables:
                if table in tables:
                    logger.info(f"✓ Table '{table}' exists")
                else:
                    logger.warning(f"✗ Table '{table}' missing")

            break

    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        raise


async def test_redis_connection():
    """Test Redis connection."""
    logger.info("Testing Redis connection...")

    try:
        redis_client = await get_redis()

        # Test basic operations
        await redis_client.set("test_key", "test_value", ex=60)
        value = await redis_client.get("test_key")
        logger.info(f"Redis get result: {value} (type: {type(value)})")

        assert value == "test_value", f"Expected 'test_value', got '{value}'"

        # Clean up
        await redis_client.delete("test_key")

        logger.info("✓ Redis connection successful")

    except Exception as e:
        logger.error(f"✗ Redis connection failed: {e}")
        raise


async def test_model_creation():
    """Test creating model instances."""
    logger.info("Testing model creation...")

    try:
        async for session in get_db():
            # Clean up any existing test data first (in correct order due to foreign keys)
            await session.execute(text("DELETE FROM message_entities WHERE message_id IN (SELECT id FROM messages WHERE platform_message_id LIKE 'test_%')"))
            await session.execute(text("DELETE FROM attachments WHERE message_id IN (SELECT id FROM messages WHERE platform_message_id LIKE 'test_%')"))
            await session.execute(text("DELETE FROM messages WHERE platform_message_id LIKE 'test_%'"))
            await session.execute(text("DELETE FROM threads WHERE platform_thread_id LIKE 'test_%'"))
            await session.execute(text("DELETE FROM participants WHERE platform_user_id LIKE 'test_%'"))
            await session.commit()

            # Generate unique test identifiers
            import time
            timestamp = int(time.time())

            # Create a test participant
            participant = Participant(
                platform="gmail",
                platform_user_id=f"test_{timestamp}@example.com",
                display_name="Test User",
                email=f"test_{timestamp}@example.com"
            )
            session.add(participant)
            await session.flush()  # Get the ID

            # Create a test thread
            thread = Thread(
                platform="gmail",
                platform_thread_id=f"test_thread_{timestamp}",
                title="Test Thread",
                participants=[participant.id]
            )
            session.add(thread)
            await session.flush()

            # Create a test message
            message = Message(
                platform="gmail",
                platform_message_id=f"test_msg_{timestamp}",
                thread_id=thread.id,
                sender_id=participant.id,
                content_text="Test message content",
                timestamp=datetime.utcnow()
            )
            session.add(message)

            # Commit the transaction
            await session.commit()

            logger.info("✓ Model creation successful")
            logger.info(f"  - Created participant: {participant.id}")
            logger.info(f"  - Created thread: {thread.id}")
            logger.info(f"  - Created message: {message.id}")

            break

    except Exception as e:
        logger.error(f"✗ Model creation failed: {e}")
        raise


async def main():
    """Run all infrastructure tests."""
    logger.info("Starting infrastructure tests...")

    try:
        # Initialize infrastructure
        await initialize_infrastructure()

        # Run tests
        await test_database_connection()
        await test_redis_connection()
        await test_model_creation()

        logger.info("🎉 All infrastructure tests passed!")

    except Exception as e:
        logger.error(f"❌ Infrastructure tests failed: {e}")
        raise
    finally:
        # Cleanup
        await cleanup_infrastructure()

if __name__ == "__main__":
    asyncio.run(main())
