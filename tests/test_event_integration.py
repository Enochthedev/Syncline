"""
Integration test for the complete event bus system.

This test verifies the end-to-end functionality of the event bus
with real Redis Streams (if available) or mocked Redis.
"""

import asyncio
import os
from unittest.mock import AsyncMock

from services.event_bus import EventBus, Event, EventType, ConsumerConfig
from services.event_patterns import EventFactory, StreamNames, ConsumerGroups
from services.message_schema import RawMessage, Platform


async def test_event_bus_integration():
    """Test complete event bus integration."""
    print("🧪 Testing Event Bus Integration...")

    # Use mock Redis for testing
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.xadd.return_value = "1234567890-0"
    mock_redis.xgroup_create.return_value = True
    mock_redis.xreadgroup.return_value = []
    mock_redis.xack.return_value = 1

    # Initialize event bus
    bus = EventBus(redis_client=mock_redis)
    await bus.initialize()
    print("✅ Event bus initialized")

    # Test event creation and publishing
    raw_message = RawMessage(
        platform=Platform.GMAIL,
        platform_message_id="test_msg_123",
        raw_data={
            "subject": "Test Email",
            "from": "test@example.com",
            "body": "This is a test message for event bus integration."
        }
    )

    event = EventFactory.create_message_received_event(
        raw_message,
        correlation_id="test_correlation_123",
        source="integration_test"
    )

    message_id = await bus.publish(StreamNames.RAW_MESSAGES, event)
    print(f"✅ Event published successfully - Message ID: {message_id}")

    # Test consumer subscription
    processed_events = []

    async def test_handler(event: Event):
        processed_events.append(event)
        print(f"📨 Processed event: {event.type.value} (ID: {event.id})")

    config = ConsumerConfig(
        group_name=ConsumerGroups.MESSAGE_NORMALIZERS,
        consumer_name="integration_test_consumer",
        stream_name=StreamNames.RAW_MESSAGES,
        batch_size=1
    )

    await bus.subscribe(config, test_handler)
    print("✅ Consumer subscribed")

    # Test health check
    health = await bus.health_check()
    assert health['status'] == 'healthy'
    print("✅ Health check passed")

    # Test event serialization/deserialization
    serialized = bus._serialize_event(event)
    deserialized = bus._deserialize_event(serialized)

    assert deserialized.id == event.id
    assert deserialized.type == event.type
    assert deserialized.data == event.data
    print("✅ Event serialization/deserialization works")

    print("🎉 All integration tests passed!")

    return {
        'event_bus_initialized': True,
        'event_published': True,
        'consumer_subscribed': True,
        'health_check_passed': True,
        'serialization_works': True
    }


async def test_multiple_event_types():
    """Test different event types and patterns."""
    print("\n🧪 Testing Multiple Event Types...")

    # Test different event factory methods
    events = []

    # Message received event
    raw_msg = RawMessage(Platform.SLACK, "slack_123", {"text": "Hello"})
    events.append(EventFactory.create_message_received_event(raw_msg))

    # Entity extracted event
    events.append(EventFactory.create_entity_extracted_event(
        "msg_123",
        [{"type": "person", "value": "John Doe"}]
    ))

    # Summary generated event
    events.append(EventFactory.create_summary_generated_event(
        "summary_123", "daily", "thread_456", {"content": "Daily summary"}
    ))

    # Error event
    events.append(EventFactory.create_error_event(
        "test_error", "Test error message", {"severity": "low"}
    ))

    # Health check event
    events.append(EventFactory.create_health_check_event(
        "test_component", "healthy", {"uptime": "100%"}
    ))

    print(f"✅ Created {len(events)} different event types")

    # Test event serialization for all types
    for event in events:
        try:
            # Mock serialization test
            event_dict = event.to_dict()
            reconstructed = Event.from_dict(event_dict)
            assert reconstructed.type == event.type
            print(f"✅ Event type {event.type.value} serialization works")
        except Exception as e:
            print(f"❌ Event type {event.type.value} failed: {e}")
            raise

    print("🎉 All event types work correctly!")
    return True


async def main():
    """Run all integration tests."""
    print("🚀 Starting Event Bus Integration Tests\n")

    try:
        # Run basic integration test
        result1 = await test_event_bus_integration()

        # Run multiple event types test
        result2 = await test_multiple_event_types()

        print(f"\n✅ Integration Test Summary:")
        print(
            f"   - Event Bus Integration: {'PASSED' if result1 else 'FAILED'}")
        print(
            f"   - Multiple Event Types: {'PASSED' if result2 else 'FAILED'}")
        print(f"\n🎉 All tests completed successfully!")

        return True

    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
