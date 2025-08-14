"""
Example service demonstrating event bus usage patterns.

This module shows how to integrate with the event bus for
message processing workflows.
"""

import asyncio
import logging
from typing import Dict, Any

from services.event_bus import EventBus, Event, ConsumerConfig, get_event_bus
from services.event_patterns import (
    EventFactory, StreamNames, ConsumerGroups, EventHandlers
)
from services.message_schema import RawMessage, Platform

logger = logging.getLogger(__name__)


class MessageProcessingService:
    """
    Example service that demonstrates event bus integration.

    This service shows how to:
    1. Publish events to the event bus
    2. Subscribe to events with consumer groups
    3. Handle events with proper error handling
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.processed_count = 0

    async def initialize(self) -> None:
        """Initialize the service and set up event subscriptions."""
        # Subscribe to raw message events
        raw_message_config = ConsumerConfig(
            group_name=ConsumerGroups.MESSAGE_NORMALIZERS,
            consumer_name="example_processor",
            stream_name=StreamNames.RAW_MESSAGES,
            batch_size=5,
            block_time=1000
        )

        await self.event_bus.subscribe(raw_message_config, self.handle_raw_message)

        # Subscribe to error events
        error_config = ConsumerConfig(
            group_name=ConsumerGroups.ERROR_HANDLERS,
            consumer_name="example_error_handler",
            stream_name=StreamNames.ERRORS,
            batch_size=10,
            block_time=2000
        )

        await self.event_bus.subscribe(error_config, EventHandlers.error_event_handler)

        logger.info("MessageProcessingService initialized")

    async def simulate_message_ingestion(self, platform: Platform, message_data: Dict[str, Any]) -> None:
        """
        Simulate ingesting a message from a platform.

        This demonstrates how a connector would publish raw message events.
        """
        # Create a raw message
        raw_message = RawMessage(
            platform=platform,
            platform_message_id=message_data.get('id', 'unknown'),
            raw_data=message_data
        )

        # Create and publish event
        event = EventFactory.create_message_received_event(
            raw_message,
            correlation_id=f"{platform.value}:{raw_message.platform_message_id}",
            source=f"{platform.value}_connector"
        )

        await self.event_bus.publish(StreamNames.RAW_MESSAGES, event)

        logger.info(
            f"Published raw message event for {platform.value} "
            f"message {raw_message.platform_message_id}"
        )

    async def handle_raw_message(self, event: Event) -> None:
        """
        Handle raw message events.

        This demonstrates how to process events and publish follow-up events.
        """
        try:
            logger.info(f"Processing raw message event: {event.id}")

            # Extract message data
            platform = Platform(event.data['platform'])
            platform_message_id = event.data['platform_message_id']
            raw_data = event.data['raw_data']

            # Simulate message processing
            await asyncio.sleep(0.1)  # Simulate processing time

            # Create processing results
            processing_results = {
                'normalized': True,
                'entities': [
                    {'type': 'person', 'value': 'John Doe', 'confidence': 0.95},
                    {'type': 'date', 'value': '2024-01-15', 'confidence': 0.88}
                ],
                'summary': 'Message processed successfully',
                'action_items': []
            }

            # Publish processed event
            processed_event = EventFactory.create_message_processed_event(
                message_id=f"{platform.value}:{platform_message_id}",
                processing_results=processing_results,
                correlation_id=event.correlation_id,
                source="example_processor"
            )

            await self.event_bus.publish(StreamNames.PROCESSED_MESSAGES, processed_event)

            self.processed_count += 1
            logger.info(
                f"Successfully processed message {platform_message_id}")

        except Exception as e:
            logger.error(f"Failed to process raw message event: {e}")

            # Publish error event
            error_event = EventFactory.create_error_event(
                error_type="message_processing_error",
                error_message=str(e),
                error_context={
                    'event_id': event.id,
                    'platform': event.data.get('platform'),
                    'message_id': event.data.get('platform_message_id'),
                    'severity': 'error'
                },
                correlation_id=event.correlation_id,
                source="example_processor"
            )

            await self.event_bus.publish(StreamNames.ERRORS, error_event)

    async def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            'processed_count': self.processed_count,
            'service_status': 'running'
        }


async def run_example():
    """
    Run the example service to demonstrate event bus functionality.

    This function shows a complete workflow:
    1. Initialize event bus
    2. Set up service with subscriptions
    3. Simulate message ingestion
    4. Process events
    5. Clean up
    """
    # Get event bus instance
    event_bus = await get_event_bus()

    # Create and initialize service
    service = MessageProcessingService(event_bus)
    await service.initialize()

    try:
        # Start consumers
        await event_bus.start_consumers()

        # Simulate some message ingestion
        test_messages = [
            {
                'platform': Platform.GMAIL,
                'data': {
                    'id': 'gmail_123',
                    'subject': 'Test Email',
                    'from': 'test@example.com',
                    'body': 'This is a test email from John Doe about the meeting on January 15th.'
                }
            },
            {
                'platform': Platform.SLACK,
                'data': {
                    'id': 'slack_456',
                    'channel': 'general',
                    'user': 'user123',
                    'text': 'Hey team, can we schedule a call for tomorrow?'
                }
            },
            {
                'platform': Platform.DISCORD,
                'data': {
                    'id': 'discord_789',
                    'channel_id': '123456789',
                    'author': {'id': '987654321', 'username': 'testuser'},
                    'content': 'Looking forward to the project demo next week!'
                }
            }
        ]

        # Publish test messages
        for msg in test_messages:
            await service.simulate_message_ingestion(msg['platform'], msg['data'])

        # Let the system process messages
        logger.info("Waiting for message processing...")
        await asyncio.sleep(2)

        # Check stats
        stats = await service.get_stats()
        logger.info(f"Processing stats: {stats}")

        # Publish a health check event
        health_event = EventFactory.create_health_check_event(
            component="example_service",
            status="healthy",
            details=stats,
            source="example_service"
        )

        await event_bus.publish(StreamNames.HEALTH_CHECKS, health_event)

        # Wait a bit more
        await asyncio.sleep(1)

        logger.info("Example completed successfully")

    finally:
        # Clean up
        await event_bus.stop_consumers()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run the example
    asyncio.run(run_example())
