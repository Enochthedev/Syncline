"""
Integration tests for the EventBus service.

Tests event flow, message delivery guarantees, and consumer group functionality.
"""

import asyncio
import pytest
import pytest_asyncio
import uuid
from datetime import datetime
from typing import List
from unittest.mock import AsyncMock, MagicMock

from services.event_bus import (
    EventBus, Event, EventType, EventPriority, ConsumerConfig,
    EventBusError, EventPublishError, EventSerializationError
)


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock = AsyncMock()
    mock.ping.return_value = True
    mock.xadd.return_value = "1234567890-0"
    mock.xgroup_create.return_value = True
    mock.xreadgroup.return_value = []
    mock.xack.return_value = 1
    mock.xinfo_stream.return_value = {"length": 0}
    mock.xinfo_groups.return_value = []
    return mock


@pytest_asyncio.fixture
async def event_bus(mock_redis):
    """Event bus instance for testing."""
    bus = EventBus(redis_client=mock_redis)
    await bus.initialize()
    return bus


@pytest.fixture
def sample_event():
    """Sample event for testing."""
    return Event(
        id="test-event-123",
        type=EventType.MESSAGE_RECEIVED,
        data={"message": "test message", "platform": "gmail"},
        metadata={"source": "test"},
        timestamp=datetime.utcnow(),
        priority=EventPriority.NORMAL,
        correlation_id="corr-123",
        source="test-service"
    )


class TestEvent:
    """Test Event data structure."""

    def test_event_creation(self):
        """Test event creation with defaults."""
        event = Event()

        assert event.id is not None
        assert event.type == EventType.MESSAGE_RECEIVED
        assert event.data == {}
        assert event.metadata == {}
        assert isinstance(event.timestamp, datetime)
        assert event.priority == EventPriority.NORMAL
        assert event.correlation_id is None
        assert event.source is None

    def test_event_to_dict(self, sample_event):
        """Test event serialization to dictionary."""
        event_dict = sample_event.to_dict()

        assert event_dict['id'] == "test-event-123"
        assert event_dict['type'] == EventType.MESSAGE_RECEIVED.value
        assert event_dict['data'] == {
            "message": "test message", "platform": "gmail"}
        assert event_dict['metadata'] == {"source": "test"}
        assert event_dict['priority'] == EventPriority.NORMAL.value
        assert event_dict['correlation_id'] == "corr-123"
        assert event_dict['source'] == "test-service"
        assert 'timestamp' in event_dict

    def test_event_from_dict(self, sample_event):
        """Test event deserialization from dictionary."""
        event_dict = sample_event.to_dict()
        reconstructed = Event.from_dict(event_dict)

        assert reconstructed.id == sample_event.id
        assert reconstructed.type == sample_event.type
        assert reconstructed.data == sample_event.data
        assert reconstructed.metadata == sample_event.metadata
        assert reconstructed.priority == sample_event.priority
        assert reconstructed.correlation_id == sample_event.correlation_id
        assert reconstructed.source == sample_event.source


class TestEventBus:
    """Test EventBus functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_redis):
        """Test event bus initialization."""
        bus = EventBus(redis_client=mock_redis)
        await bus.initialize()

        mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialization_failure(self):
        """Test event bus initialization failure."""
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Connection failed")

        bus = EventBus(redis_client=mock_redis)

        with pytest.raises(EventBusError):
            await bus.initialize()

    @pytest.mark.asyncio
    async def test_publish_event(self, event_bus, mock_redis, sample_event):
        """Test event publishing."""
        stream_name = "test-stream"

        message_id = await event_bus.publish(stream_name, sample_event)

        assert message_id == "1234567890-0"
        mock_redis.xadd.assert_called_once()

        # Verify the call arguments
        call_args = mock_redis.xadd.call_args
        assert call_args[0][0] == stream_name
        assert 'fields' in call_args[1]
        assert 'maxlen' in call_args[1]
        assert call_args[1]['approximate'] is True

    @pytest.mark.asyncio
    async def test_publish_event_failure(self, event_bus, mock_redis, sample_event):
        """Test event publishing failure."""
        mock_redis.xadd.side_effect = Exception("Redis error")

        with pytest.raises(EventPublishError):
            await event_bus.publish("test-stream", sample_event)

    @pytest.mark.asyncio
    async def test_create_consumer_group(self, event_bus, mock_redis):
        """Test consumer group creation."""
        stream_name = "test-stream"
        group_name = "test-group"

        result = await event_bus.create_consumer_group(stream_name, group_name)

        assert result is True
        mock_redis.xgroup_create.assert_called_once_with(
            stream_name, group_name, "0", mkstream=True
        )

    @pytest.mark.asyncio
    async def test_create_existing_consumer_group(self, event_bus, mock_redis):
        """Test creating an already existing consumer group."""
        from redis import ResponseError

        mock_redis.xgroup_create.side_effect = ResponseError(
            "BUSYGROUP Consumer Group name already exists")

        result = await event_bus.create_consumer_group("test-stream", "test-group")

        assert result is False

    @pytest.mark.asyncio
    async def test_subscribe_consumer(self, event_bus, mock_redis):
        """Test consumer subscription."""
        config = ConsumerConfig(
            group_name="test-group",
            consumer_name="test-consumer",
            stream_name="test-stream",
            batch_size=5
        )

        handler = AsyncMock()

        await event_bus.subscribe(config, handler)

        consumer_key = f"{config.group_name}:{config.consumer_name}"
        assert consumer_key in event_bus._consumers
        assert event_bus._consumers[consumer_key]['config'] == config
        assert event_bus._consumers[consumer_key]['handler'] == handler
        assert event_bus._consumers[consumer_key]['running'] is False

    @pytest.mark.asyncio
    async def test_event_serialization(self, event_bus, sample_event):
        """Test event serialization for Redis."""
        serialized = event_bus._serialize_event(sample_event)

        assert isinstance(serialized, dict)
        assert all(isinstance(v, str) for v in serialized.values())
        assert serialized['id'] == sample_event.id
        assert serialized['type'] == sample_event.type.value

        # JSON fields should be serialized as JSON strings
        import json
        assert json.loads(serialized['data']) == sample_event.data
        assert json.loads(serialized['metadata']) == sample_event.metadata

    @pytest.mark.asyncio
    async def test_event_deserialization(self, event_bus, sample_event):
        """Test event deserialization from Redis."""
        # First serialize
        serialized = event_bus._serialize_event(sample_event)

        # Then deserialize
        deserialized = event_bus._deserialize_event(serialized)

        assert deserialized.id == sample_event.id
        assert deserialized.type == sample_event.type
        assert deserialized.data == sample_event.data
        assert deserialized.metadata == sample_event.metadata
        assert deserialized.priority == sample_event.priority
        assert deserialized.correlation_id == sample_event.correlation_id
        assert deserialized.source == sample_event.source

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, event_bus, mock_redis):
        """Test health check when system is healthy."""
        health = await event_bus.health_check()

        assert health['status'] == 'healthy'
        assert health['redis_connected'] is True
        assert health['consumers_running'] is False
        assert health['consumer_count'] == 0
        assert health['active_tasks'] == 0
        assert 'consumers' in health

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, event_bus, mock_redis):
        """Test health check when Redis is down."""
        mock_redis.ping.side_effect = Exception("Connection failed")

        health = await event_bus.health_check()

        assert health['status'] == 'unhealthy'
        assert health['redis_connected'] is False
        assert 'error' in health


class TestConsumerIntegration:
    """Test consumer integration and message processing."""

    @pytest.mark.asyncio
    async def test_consumer_message_processing(self, event_bus, mock_redis, sample_event):
        """Test end-to-end message processing."""
        # Setup mock Redis to return a message
        serialized_event = event_bus._serialize_event(sample_event)
        mock_redis.xreadgroup.return_value = [
            ("test-stream", [("1234567890-0", serialized_event)])
        ]

        # Setup consumer
        config = ConsumerConfig(
            group_name="test-group",
            consumer_name="test-consumer",
            stream_name="test-stream",
            batch_size=1,
            block_time=100
        )

        processed_events = []

        async def test_handler(event: Event):
            processed_events.append(event)

        await event_bus.subscribe(config, test_handler)

        # Start consumers briefly
        await event_bus.start_consumers()
        await asyncio.sleep(0.1)  # Let it process
        await event_bus.stop_consumers()

        # Verify message was processed
        assert len(processed_events) == 1
        processed_event = processed_events[0]
        assert processed_event.id == sample_event.id
        assert processed_event.type == sample_event.type
        assert processed_event.data == sample_event.data

    @pytest.mark.asyncio
    async def test_consumer_error_handling(self, event_bus, mock_redis, sample_event):
        """Test consumer error handling."""
        # Setup mock Redis to return a message
        serialized_event = event_bus._serialize_event(sample_event)
        mock_redis.xreadgroup.return_value = [
            ("test-stream", [("1234567890-0", serialized_event)])
        ]

        # Setup consumer with failing handler
        config = ConsumerConfig(
            group_name="test-group",
            consumer_name="test-consumer",
            stream_name="test-stream",
            batch_size=1,
            block_time=100
        )

        async def failing_handler(event: Event):
            raise Exception("Handler failed")

        await event_bus.subscribe(config, failing_handler)

        # Start consumers briefly
        await event_bus.start_consumers()
        await asyncio.sleep(0.1)  # Let it process
        await event_bus.stop_consumers()

        # Verify message was still acknowledged (to prevent infinite retries)
        mock_redis.xack.assert_called()

    @pytest.mark.asyncio
    async def test_multiple_consumers(self, event_bus, mock_redis):
        """Test multiple consumers on different streams."""
        # Setup two consumers
        config1 = ConsumerConfig(
            group_name="group1",
            consumer_name="consumer1",
            stream_name="stream1"
        )

        config2 = ConsumerConfig(
            group_name="group2",
            consumer_name="consumer2",
            stream_name="stream2"
        )

        handler1 = AsyncMock()
        handler2 = AsyncMock()

        await event_bus.subscribe(config1, handler1)
        await event_bus.subscribe(config2, handler2)

        assert len(event_bus._consumers) == 2
        assert "group1:consumer1" in event_bus._consumers
        assert "group2:consumer2" in event_bus._consumers


class TestEventBusContext:
    """Test event bus context manager."""

    @pytest.mark.asyncio
    async def test_event_bus_context(self, mock_redis):
        """Test event bus context manager."""
        from services.event_bus import event_bus_context

        # Mock the global event bus
        import services.event_bus
        original_event_bus = services.event_bus.event_bus
        test_bus = EventBus(redis_client=mock_redis)
        services.event_bus.event_bus = test_bus

        try:
            async with event_bus_context() as bus:
                assert isinstance(bus, EventBus)
                mock_redis.ping.assert_called()
        finally:
            # Restore original event bus
            services.event_bus.event_bus = original_event_bus


class TestConsumerConfig:
    """Test ConsumerConfig data structure."""

    def test_consumer_config_defaults(self):
        """Test consumer config with default values."""
        config = ConsumerConfig(
            group_name="test-group",
            consumer_name="test-consumer",
            stream_name="test-stream"
        )

        assert config.group_name == "test-group"
        assert config.consumer_name == "test-consumer"
        assert config.stream_name == "test-stream"
        assert config.batch_size == 10
        assert config.block_time == 1000
        assert config.auto_ack is True
        assert config.max_retries == 3
        assert config.retry_delay == 1.0

    def test_consumer_config_custom_values(self):
        """Test consumer config with custom values."""
        config = ConsumerConfig(
            group_name="custom-group",
            consumer_name="custom-consumer",
            stream_name="custom-stream",
            batch_size=50,
            block_time=5000,
            auto_ack=False,
            max_retries=5,
            retry_delay=2.5
        )

        assert config.batch_size == 50
        assert config.block_time == 5000
        assert config.auto_ack is False
        assert config.max_retries == 5
        assert config.retry_delay == 2.5


if __name__ == "__main__":
    pytest.main([__file__])
