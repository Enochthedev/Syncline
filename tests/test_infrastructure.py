"""
Tests for infrastructure setup and database connectivity.

Tests database connection, Redis connectivity, and model persistence.
"""

import pytest
import asyncio
from datetime import datetime
from sqlalchemy import text
import time

from db.session import get_db
from db.redis_client import get_redis
from db.models.participant import Participant
from db.models.thread import Thread
from db.models.message import Message
from db.models.attachment import Attachment
from db.models.entity import Entity, MessageEntity


class TestDatabaseConnection:
    """Test database connection and basic operations."""

    @pytest.mark.asyncio
    async def test_database_connection(self):
        """Test database connection and basic operations."""
        async for session in get_db():
            # Test basic query
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

            # Test table creation by checking if tables exist
            result = await session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            )
            tables = [row[0] for row in result.fetchall()]

            expected_tables = ['participants', 'threads', 'messages',
                               'entities', 'summaries', 'attachments', 'message_entities']
            for table in expected_tables:
                assert table in tables, f"Table '{table}' should exist"

            break


class TestRedisConnection:
    """Test Redis connection and operations."""

    @pytest.mark.asyncio
    async def test_redis_connection(self):
        """Test Redis connection."""
        try:
            redis_client = await get_redis()

            # Test basic operations
            await redis_client.set("test_key", "test_value", ex=60)
            value = await redis_client.get("test_key")

            assert value == "test_value"

            # Clean up
            await redis_client.delete("test_key")
        except RuntimeError as e:
            if "Redis client not initialized" in str(e):
                pytest.skip("Redis not initialized - skipping Redis tests")
            else:
                raise


class TestModelCreation:
    """Test creating and persisting model instances."""

    @pytest.mark.asyncio
    async def test_model_creation(self):
        """Test creating model instances."""
        async for session in get_db():
            # Generate unique test identifiers
            timestamp = int(time.time())

            # Clean up any existing test data first
            cleanup_queries = [
                "DELETE FROM message_entities WHERE message_id IN (SELECT id FROM messages WHERE platform_message_id LIKE 'test_%')",
                "DELETE FROM attachments WHERE message_id IN (SELECT id FROM messages WHERE platform_message_id LIKE 'test_%')",
                "DELETE FROM messages WHERE platform_message_id LIKE 'test_%'",
                "DELETE FROM threads WHERE platform_thread_id LIKE 'test_%'",
                "DELETE FROM participants WHERE platform_user_id LIKE 'test_%'"
            ]

            for query in cleanup_queries:
                await session.execute(text(query))
            await session.commit()

            # Create a test participant
            participant = Participant(
                platform="gmail",
                platform_user_id=f"test_{timestamp}@example.com",
                display_name="Test User",
                email=f"test_{timestamp}@example.com"
            )
            session.add(participant)
            await session.flush()

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

            # Verify creation
            assert participant.id is not None
            assert thread.id is not None
            assert message.id is not None

            break
