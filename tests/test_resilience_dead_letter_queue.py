"""
Tests for Dead Letter Queue (DLQ) implementation.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from services.resilience.dead_letter_queue import (
    DeadLetterQueue,
    DLQMessage,
    DLQMessageStatus,
    DLQError
)


@pytest.fixture
async def mock_redis():
    """Mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.ping.return_value = True
    redis_mock.hset.return_value = True
    redis_mock.hget.return_value = None
    redis_mock.zadd.return_value = 1
    redis_mock.sadd.return_value = 1
    redis_mock.scard.return_value = 0
    redis_mock.zcard.return_value = 0
    redis_mock.zrange.return_value = []
    redis_mock.zrangebyscore.return_value = []
    redis_mock.zrem.return_value = 1
    redis_mock.srem.return_value = 1
    redis_mock.smembers.return_value = set()
    return redis_mock


@pytest.fixture
async def dlq(mock_redis):
    """DLQ instance with mocked Redis."""
    dlq = DeadLetterQueue(redis_client=mock_redis)
    await dlq.initialize()
    return dlq


@pytest.mark.asyncio
async def test_dlq_initialization(mock_redis):
    """Test DLQ initialization."""
    dlq = DeadLetterQueue(redis_client=mock_redis)
    await dlq.initialize()

    mock_redis.ping.assert_called_once()


@pytest.mark.asyncio
async def test_dlq_add_message(dlq, mock_redis):
    """Test adding a message to the DLQ."""
    event = {'id': 'test-event', 'type': 'test', 'data': {}}
    error = Exception("Test error")

    message_id = await dlq.add_message(event, error, max_retries=3)

    assert message_id is not None
    mock_redis.hset.assert_called()
    mock_redis.zadd.assert_called()
    mock_redis.sadd.assert_called()


@pytest.mark.asyncio
async def test_dlq_message_serialization():
    """Test DLQ message serialization."""
    message = DLQMessage(
        id="test-id",
        original_event={'test': 'data'},
        error_message="Test error",
        error_type="Exception",
        retry_count=1,
        max_retries=3,
        status=DLQMessageStatus.PENDING
    )

    # Test to_dict
    data = message.to_dict()
    assert data['id'] == "test-id"
    assert data['error_message'] == "Test error"
    assert data['status'] == "pending"

    # Test from_dict
    restored = DLQMessage.from_dict(data)
    assert restored.id == message.id
    assert restored.error_message == message.error_message
    assert restored.status == message.status


@pytest.mark.asyncio
async def test_dlq_poison_message_detection():
    """Test poison message detection."""
    message = DLQMessage(retry_count=5, max_retries=3)
    assert message.is_poison()

    message = DLQMessage(retry_count=2, max_retries=3)
    assert not message.is_poison()

    message = DLQMessage(status=DLQMessageStatus.POISON)
    assert message.is_poison()


@pytest.mark.asyncio
async def test_dlq_retry_message_success(dlq, mock_redis):
    """Test successful message retry."""
    # Mock getting message from Redis
    test_message = DLQMessage(
        id="test-id",
        original_event={'test': 'data'},
        error_message="Test error",
        retry_count=1,
        max_retries=3
    )

    import json
    mock_redis.hget.return_value = json.dumps(test_message.to_dict())

    # Mock handler that succeeds
    handler = AsyncMock()

    result = await dlq.retry_message("test-id", handler)

    assert result is True
    handler.assert_called_once_with(test_message.original_event)


@pytest.mark.asyncio
async def test_dlq_retry_message_failure(dlq, mock_redis):
    """Test failed message retry."""
    # Mock getting message from Redis
    test_message = DLQMessage(
        id="test-id",
        original_event={'test': 'data'},
        error_message="Test error",
        retry_count=1,
        max_retries=3
    )

    import json
    mock_redis.hget.return_value = json.dumps(test_message.to_dict())

    # Mock handler that fails
    handler = AsyncMock(side_effect=Exception("Handler failed"))

    result = await dlq.retry_message("test-id", handler)

    assert result is False
    handler.assert_called_once_with(test_message.original_event)


@pytest.mark.asyncio
async def test_dlq_retry_processor(dlq, mock_redis):
    """Test DLQ retry processor."""
    # Mock messages ready for retry
    mock_redis.zrangebyscore.return_value = [b"test-id-1", b"test-id-2"]

    # Mock getting messages
    test_message = DLQMessage(
        id="test-id-1",
        original_event={'test': 'data'},
        retry_count=1,
        max_retries=3
    )

    import json
    mock_redis.hget.return_value = json.dumps(test_message.to_dict())

    handler = AsyncMock()

    # Start processor
    await dlq.start_retry_processor(handler, check_interval=0.1)

    # Let it run briefly
    await asyncio.sleep(0.2)

    # Stop processor
    await dlq.stop_retry_processor()

    # Verify calls were made
    mock_redis.zrangebyscore.assert_called()


@pytest.mark.asyncio
async def test_dlq_statistics(dlq, mock_redis):
    """Test DLQ statistics."""
    # Mock Redis responses
    mock_redis.scard.return_value = 5
    mock_redis.zcard.return_value = 3
    mock_redis.zrange.return_value = [(b"test-id", 1234567890.0)]

    stats = await dlq.get_statistics()

    assert 'pending_count' in stats
    assert 'retry_queue_size' in stats
    assert 'processor_running' in stats
    assert stats['retry_queue_size'] == 3


@pytest.mark.asyncio
async def test_dlq_calculate_next_retry():
    """Test retry time calculation."""
    message = DLQMessage(retry_count=0)
    next_retry = message.calculate_next_retry(
        base_delay=60.0, max_delay=3600.0)

    # Should be approximately 60 seconds from now
    now = datetime.now(timezone.utc)
    delay = (next_retry - now).total_seconds()
    assert 55 <= delay <= 65  # Allow some variance

    # Test exponential backoff
    message = DLQMessage(retry_count=3)
    next_retry = message.calculate_next_retry(
        base_delay=60.0, max_delay=3600.0)

    delay = (next_retry - now).total_seconds()
    expected_delay = 60.0 * (2 ** 3)  # 480 seconds
    assert expected_delay - 10 <= delay <= expected_delay + 10


@pytest.mark.asyncio
async def test_dlq_error_handling(mock_redis):
    """Test DLQ error handling."""
    # Test initialization failure
    mock_redis.ping.side_effect = Exception("Redis connection failed")

    dlq = DeadLetterQueue(redis_client=mock_redis)

    with pytest.raises(DLQError):
        await dlq.initialize()


@pytest.mark.asyncio
async def test_dlq_context_manager():
    """Test DLQ context manager."""
    from services.resilience.dead_letter_queue import dlq_context

    # Mock the global DLQ
    with pytest.patch('services.resilience.dead_letter_queue.dead_letter_queue') as mock_dlq:
        mock_dlq.initialize = AsyncMock()
        mock_dlq.stop_retry_processor = AsyncMock()

        async with dlq_context() as dlq:
            assert dlq == mock_dlq
            mock_dlq.initialize.assert_called_once()

        mock_dlq.stop_retry_processor.assert_called_once()
