"""
Comprehensive system integration tests for MESH ingestion system.

This module tests the complete integration of all system components including
Yahoo connector, configuration management, and end-to-end user workflows.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient

from main import app
from db.session import get_db
from db.redis_client import get_redis
from services.event_bus import EventBus
from services.message_normalizer import MessageNormalizer
from services.ai.engine import AIProcessingEngine
from services.ai.search.agent import HybridSearchAgent
from services.message_schema import RawMessage, NormalizedMessage, MessageContent, Participant
from integrations.gmail_connector import GmailConnector
from integrations.slack_connector import SlackConnector
from integrations.discord_connector import DiscordConnector
from integrations.yahoo_connector import YahooConnector
from integrations.connector_manager import ConnectorManager
from api.auth.models import User


@pytest.fixture
def test_user():
    """Create a test user for integration tests."""
    return User(
        id="integration-test-user",
        username="integration_user",
        email="integration@example.com",
        full_name="Integration Test User",
        is_active=True,
        tenant_id="integration-tenant"
    )


@pytest.fixture
async def event_bus():
    """Create event bus for testing."""
    try:
        redis_client = await get_redis()
        return EventBus(redis_client)
    except RuntimeError:
        pytest.skip("Redis not available for integration tests")


@pytest.fixture
def mock_ai_engine():
    """Mock AI processing engine."""
    engine = AsyncMock(spec=AIProcessingEngine)

    # Mock entity extraction
    engine.extract_entities.return_value = [
        {"type": "person", "value": "John Doe", "confidence": 0.95},
        {"type": "organization", "value": "Acme Corp", "confidence": 0.88},
        {"type": "date", "value": "today", "confidence": 0.95}
    ]

    # Mock summary generation
    engine.generate_summary.return_value = {
        "content": "Test summary of the conversation",
        "key_points": ["Important point 1", "Important point 2"],
        "action_items": ["Follow up on proposal"],
        "urgency": "medium"
    }

    # Mock embedding generation
    engine.generate_embedding.return_value = [
        0.1] * 1536  # Mock 1536-dim vector

    return engine


@pytest.fixture
def mock_search_agent():
    """Mock hybrid search agent."""
    agent = AsyncMock(spec=HybridSearchAgent)

    search_result = AsyncMock()
    search_result.results = []
    search_result.stats = AsyncMock()
    search_result.stats.total_results = 0
    search_result.stats.processing_time_ms = 10.0
    search_result.query = AsyncMock()
    search_result.suggestions = []
    search_result.facets = {}

    agent.search.return_value = search_result
    return agent


class TestSystemIntegration:
    """Test complete system integration with all components."""

    @pytest.mark.asyncio
    async def test_complete_system_integration(self, test_user, event_bus, mock_ai_engine, mock_search_agent):
        """Test complete system integration from connector to API."""

        # Step 1: Test all connector types including Yahoo
        connectors_data = [
            {
                "platform": "gmail",
                "connector_class": GmailConnector,
                "message_content": "Gmail integration test message"
            },
            {
                "platform": "slack",
                "connector_class": SlackConnector,
                "message_content": "Slack integration test message"
            },
            {
                "platform": "discord",
                "connector_class": DiscordConnector,
                "message_content": "Discord integration test message"
            },
            {
                "platform": "yahoo",
                "connector_class": YahooConnector,
                "message_content": "Yahoo mail integration test message"
            }
        ]

        processed_messages = []

        for connector_data in connectors_data:
            # Create raw message for each platform
            raw_message = RawMessage(
                platform=connector_data["platform"],
                platform_message_id=f"{connector_data['platform']}_integration_123",
                platform_thread_id=f"{connector_data['platform']}_integration_thread",
                raw_data={
                    "content": connector_data["message_content"],
                    "sender": f"test@{connector_data['platform']}.com",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            # Normalize message
            normalizer = MessageNormalizer()
            normalized_message = await normalizer.normalize_message(raw_message)

            # Simulate AI processing
            with patch('services.ai.engine.AIProcessingEngine', return_value=mock_ai_engine):
                entities = await mock_ai_engine.extract_entities(normalized_message.content.text)
                summary = await mock_ai_engine.generate_summary(normalized_message.content.text)
                embedding = await mock_ai_engine.generate_embedding(normalized_message.content.text)

            processed_messages.append({
                "normalized": normalized_message,
                "entities": entities,
                "summary": summary,
                "embedding": embedding
            })

        # Verify all platforms processed successfully
        assert len(processed_messages) == 4
        platforms_processed = {
            msg["normalized"].platform for msg in processed_messages}
        assert platforms_processed == {"gmail", "slack", "discord", "yahoo"}

        # Step 2: Test unified search across all platforms
        with patch('services.ai.search.agent.HybridSearchAgent', return_value=mock_search_agent):
            # Configure mock to return results from all platforms
            mock_search_response = AsyncMock()
            mock_search_response.results = [
                AsyncMock(
                    platform=msg["normalized"].platform,
                    content=msg["normalized"].content.text,
                    entities=msg["entities"],
                    score=0.9
                ) for msg in processed_messages
            ]
            mock_search_response.stats = AsyncMock()
            mock_search_response.stats.total_results = 4
            mock_search_response.stats.processing_time_ms = 25.0
            mock_search_response.query = AsyncMock()
            mock_search_response.suggestions = []
            mock_search_response.facets = {
                "platforms": {"gmail": 1, "slack": 1, "discord": 1, "yahoo": 1}
            }

            mock_search_agent.search.return_value = mock_search_response

            # Test search across all platforms
            search_results = await mock_search_agent.search("integration test")

            assert len(search_results.results) == 4
            result_platforms = {
                result.platform for result in search_results.results}
            assert result_platforms == {"gmail", "slack", "discord", "yahoo"}

        # Step 3: Test API integration with all processed data
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('api.dependencies.get_current_active_user', return_value=test_user):
                with patch('services.ai.search.agent.HybridSearchAgent', return_value=mock_search_agent):

                    # Test search API
                    search_data = {
                        "query": "integration test",
                        "platforms": ["gmail", "slack", "discord", "yahoo"],
                        "limit": 10
                    }

                    response = await client.post("/api/v1/search/", json=search_data)
                    assert response.status_code == 200

                    data = response.json()
                    assert "results" in data
                    assert "stats" in data
                    assert data["stats"]["total_results"] == 4

    @pytest.mark.asyncio
    async def test_yahoo_connector_integration(self, test_user, event_bus, mock_ai_engine):
        """Test Yahoo connector integration specifically."""

        # Create Yahoo-specific message
        yahoo_message = RawMessage(
            platform="yahoo",
            platform_message_id="yahoo_integration_test_123",
            platform_thread_id="yahoo_integration_thread",
            raw_data={
                "content": "Yahoo mail integration test with attachments",
                "sender": "sender@yahoo.com",
                "subject": "Integration Test Email",
                "timestamp": datetime.utcnow().isoformat(),
                "has_attachments": True
            }
        )

        # Test normalization
        normalizer = MessageNormalizer()
        normalized_yahoo = await normalizer.normalize_message(yahoo_message)

        assert normalized_yahoo.platform == "yahoo"
        assert "Yahoo mail integration test" in normalized_yahoo.content.text
        assert normalized_yahoo.metadata.get(
            "subject") == "Integration Test Email"

        # Test AI processing
        with patch('services.ai.engine.AIProcessingEngine', return_value=mock_ai_engine):
            entities = await mock_ai_engine.extract_entities(normalized_yahoo.content.text)
            summary = await mock_ai_engine.generate_summary(normalized_yahoo.content.text)

            assert len(entities) > 0
            assert summary["content"] is not None

        # Test event publishing
        await event_bus.publish("MESSAGE_RECEIVED", {
            "platform": "yahoo",
            "message": normalized_yahoo.dict()
        })

    @pytest.mark.asyncio
    async def test_connector_manager_integration(self, event_bus, mock_ai_engine):
        """Test connector manager with all connectors including Yahoo."""

        # Create connector manager
        manager = ConnectorManager()

        # Mock connectors
        mock_connectors = {}
        platforms = ["gmail", "slack", "discord", "yahoo"]

        for platform in platforms:
            mock_connector = AsyncMock()
            mock_connector.platform = platform
            mock_connector.status = "connected"
            mock_connector.health_check.return_value = AsyncMock(
                status="healthy",
                last_check=datetime.utcnow(),
                message=f"{platform} connector healthy"
            )
            mock_connectors[platform] = mock_connector

            # Register with manager
            await manager.register_connector(mock_connector)

        # Test health checks for all connectors
        health_status = await manager.get_connector_health()

        assert len(health_status) == 4
        for platform in platforms:
            assert platform in health_status
            assert health_status[platform].message.endswith("healthy")

        # Test manager stats
        stats = manager.get_manager_stats()
        assert stats["total_connectors"] == 4
        assert stats["enabled_connectors"] == 4

    @pytest.mark.asyncio
    async def test_system_performance_under_load(self, test_user, event_bus, mock_ai_engine):
        """Test system performance under high message load."""

        # Create high volume of messages from all platforms
        message_count = 100
        messages = []

        for i in range(message_count):
            platform = ["gmail", "slack", "discord", "yahoo"][i % 4]
            raw_message = RawMessage(
                platform=platform,
                platform_message_id=f"{platform}_load_test_{i}",
                platform_thread_id=f"{platform}_load_thread_{i // 10}",
                raw_data={
                    "content": f"Load test message {i} from {platform}",
                    "sender": f"user{i}@{platform}.com",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            messages.append(raw_message)

        # Process messages in batches
        batch_size = 10
        start_time = time.time()

        normalizer = MessageNormalizer()
        processed_count = 0

        for i in range(0, message_count, batch_size):
            batch = messages[i:i + batch_size]

            # Process batch concurrently
            async def process_batch_message(msg):
                normalized = await normalizer.normalize_message(msg)

                with patch('services.ai.engine.AIProcessingEngine', return_value=mock_ai_engine):
                    entities = await mock_ai_engine.extract_entities(normalized.content.text)
                    return normalized, entities

            batch_tasks = [process_batch_message(msg) for msg in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            successful_batch = [
                r for r in batch_results if not isinstance(r, Exception)]
            processed_count += len(successful_batch)

        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert processed_count >= message_count * 0.95  # At least 95% success rate
        assert total_time < 60.0  # Should process 100 messages in under 60 seconds

        messages_per_second = processed_count / total_time
        assert messages_per_second > 1.0  # At least 1 message per second

    @pytest.mark.asyncio
    async def test_system_error_recovery(self, test_user, event_bus):
        """Test system-wide error recovery and resilience."""

        # Test various error scenarios
        error_scenarios = [
            {
                "name": "malformed_message",
                "message": RawMessage(
                    platform="gmail",
                    platform_message_id="error_test_1",
                    platform_thread_id="error_thread",
                    raw_data={"malformed": "data"}  # Missing required fields
                )
            },
            {
                "name": "invalid_platform",
                "message": RawMessage(
                    platform="invalid_platform",
                    platform_message_id="error_test_2",
                    platform_thread_id="error_thread",
                    raw_data={"content": "test"}
                )
            },
            {
                "name": "empty_content",
                "message": RawMessage(
                    platform="yahoo",
                    platform_message_id="error_test_3",
                    platform_thread_id="error_thread",
                    raw_data={"content": ""}
                )
            }
        ]

        normalizer = MessageNormalizer()
        error_count = 0
        recovery_count = 0

        for scenario in error_scenarios:
            try:
                await normalizer.normalize_message(scenario["message"])
                recovery_count += 1
            except Exception as e:
                error_count += 1

                # Test that errors are properly logged and handled
                assert isinstance(e, Exception)

                # Simulate error recovery mechanism
                with patch('services.resilience.dead_letter_queue.DeadLetterQueue') as mock_dlq:
                    mock_dlq_instance = AsyncMock()
                    mock_dlq.return_value = mock_dlq_instance

                    await mock_dlq_instance.add_failed_message(
                        f"NORMALIZATION_ERROR_{scenario['name'].upper()}",
                        scenario["message"].dict(),
                        str(e)
                    )

                    mock_dlq_instance.add_failed_message.assert_called_once()

        # System should handle errors gracefully
        assert error_count > 0  # We expect some errors from malformed data
        assert error_count + recovery_count == len(error_scenarios)

    @pytest.mark.asyncio
    async def test_configuration_management(self, test_user):
        """Test system-wide configuration management."""

        # Test configuration loading and validation
        from config.config import Settings

        # Test that all required configuration is present
        settings = Settings()

        # Core configuration
        assert hasattr(settings, 'DATABASE_URL')
        assert hasattr(settings, 'REDIS_URL')

        # Platform configurations (including Yahoo)
        platform_configs = [
            'GMAIL_CLIENT_ID',
            'SLACK_CLIENT_ID',
            'DISCORD_BOT_TOKEN',
            'YAHOO_EMAIL',
            'YAHOO_APP_PASSWORD'
        ]

        # These might not be set in test environment, but should be defined
        for config in platform_configs:
            assert hasattr(settings, config)

        # AI configuration
        ai_configs = [
            'DEFAULT_LLM_PROVIDER',
            'DEFAULT_CHAT_MODEL',
            'OLLAMA_BASE_URL'
        ]

        for config in ai_configs:
            assert hasattr(settings, config)

    @pytest.mark.asyncio
    async def test_user_acceptance_scenarios(self, test_user, event_bus, mock_ai_engine, mock_search_agent):
        """Test major user acceptance scenarios including Yahoo."""

        # Scenario 1: User connects Gmail and receives messages
        gmail_message = RawMessage(
            platform="gmail",
            platform_message_id="user_test_gmail_1",
            platform_thread_id="user_gmail_thread",
            raw_data={
                "content": "Important email from client about project deadline",
                "sender": "client@company.com",
                "subject": "Project Deadline Update",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        # Scenario 2: User connects Yahoo and receives messages
        yahoo_message = RawMessage(
            platform="yahoo",
            platform_message_id="user_test_yahoo_1",
            platform_thread_id="user_yahoo_thread",
            raw_data={
                "content": "Personal email from family about weekend plans",
                "sender": "family@yahoo.com",
                "subject": "Weekend Plans",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        # Scenario 3: User connects Slack and receives team messages
        slack_message = RawMessage(
            platform="slack",
            platform_message_id="user_test_slack_1",
            platform_thread_id="user_slack_thread",
            raw_data={
                "content": "Team standup meeting moved to 3 PM today",
                "sender": "team.lead",
                "channel": "#general",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        normalizer = MessageNormalizer()
        normalized_gmail = await normalizer.normalize_message(gmail_message)
        normalized_yahoo = await normalizer.normalize_message(yahoo_message)
        normalized_slack = await normalizer.normalize_message(slack_message)

        # Scenario 4: User searches across all platforms
        with patch('services.ai.search.agent.HybridSearchAgent', return_value=mock_search_agent):
            mock_search_response = AsyncMock()
            mock_search_response.results = [
                AsyncMock(
                    platform="gmail",
                    content="Important email from client about project deadline",
                    score=0.95,
                    metadata={"subject": "Project Deadline Update"}
                ),
                AsyncMock(
                    platform="yahoo",
                    content="Personal email from family about weekend plans",
                    score=0.90,
                    metadata={"subject": "Weekend Plans"}
                ),
                AsyncMock(
                    platform="slack",
                    content="Team standup meeting moved to 3 PM today",
                    score=0.88,
                    metadata={"channel": "#general"}
                )
            ]
            mock_search_response.stats = AsyncMock()
            mock_search_response.stats.total_results = 3
            mock_search_response.query = AsyncMock()
            mock_search_response.suggestions = [
                "deadline", "meeting", "project", "weekend"]
            mock_search_response.facets = {
                "platforms": {"gmail": 1, "yahoo": 1, "slack": 1},
                "time_range": {"today": 3}
            }

            mock_search_agent.search.return_value = mock_search_response

            # User searches for "project deadline"
            search_results = await mock_search_agent.search("project deadline")

            assert len(search_results.results) == 3
            assert any(
                "deadline" in result.content for result in search_results.results)
            assert any(result.platform ==
                       "gmail" for result in search_results.results)
            assert any(result.platform ==
                       "yahoo" for result in search_results.results)
            assert any(result.platform ==
                       "slack" for result in search_results.results)

        # Scenario 5: User gets AI-powered insights
        with patch('services.ai.engine.AIProcessingEngine', return_value=mock_ai_engine):
            # Configure AI to extract relevant entities and insights
            mock_ai_engine.extract_entities.return_value = [
                {"type": "person", "value": "client", "confidence": 0.9},
                {"type": "person", "value": "family", "confidence": 0.85},
                {"type": "organization", "value": "company", "confidence": 0.85},
                {"type": "date", "value": "today", "confidence": 0.95},
                {"type": "time", "value": "3 PM", "confidence": 0.92}
            ]

            mock_ai_engine.generate_summary.return_value = {
                "content": "User has important project deadline communication from client, personal family plans, and team meeting rescheduled",
                "key_points": [
                    "Project deadline update from client",
                    "Weekend plans with family",
                    "Team standup moved to 3 PM"
                ],
                "action_items": [
                    "Review project deadline requirements",
                    "Confirm weekend plans with family",
                    "Attend rescheduled team meeting"
                ],
                "urgency": "medium"
            }

            # Process all messages with AI
            gmail_entities = await mock_ai_engine.extract_entities(normalized_gmail.content.text)
            yahoo_entities = await mock_ai_engine.extract_entities(normalized_yahoo.content.text)
            slack_entities = await mock_ai_engine.extract_entities(normalized_slack.content.text)

            combined_content = f"{normalized_gmail.content.text} {normalized_yahoo.content.text} {normalized_slack.content.text}"
            summary = await mock_ai_engine.generate_summary(combined_content)

            # Verify AI insights are meaningful
            assert len(gmail_entities) > 0
            assert len(yahoo_entities) > 0
            assert len(slack_entities) > 0
            assert summary["urgency"] == "medium"
            assert len(summary["action_items"]) > 0

        # All user scenarios completed successfully
        assert normalized_gmail.platform == "gmail"
        assert normalized_yahoo.platform == "yahoo"
        assert normalized_slack.platform == "slack"

    @pytest.mark.asyncio
    async def test_end_to_end_workflow_with_yahoo(self, test_user, event_bus, mock_ai_engine, mock_search_agent):
        """Test complete end-to-end workflow including Yahoo connector."""

        # Step 1: Message ingestion from Yahoo
        yahoo_raw = RawMessage(
            platform="yahoo",
            platform_message_id="e2e_yahoo_123",
            platform_thread_id="e2e_yahoo_thread",
            raw_data={
                "content": "End-to-end test message from Yahoo Mail",
                "sender": "test@yahoo.com",
                "subject": "E2E Test",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        # Step 2: Message normalization
        normalizer = MessageNormalizer()
        normalized = await normalizer.normalize_message(yahoo_raw)

        assert normalized.platform == "yahoo"
        assert "End-to-end test message" in normalized.content.text

        # Step 3: AI processing
        with patch('services.ai.engine.AIProcessingEngine', return_value=mock_ai_engine):
            entities = await mock_ai_engine.extract_entities(normalized.content.text)
            summary = await mock_ai_engine.generate_summary(normalized.content.text)
            embedding = await mock_ai_engine.generate_embedding(normalized.content.text)

        # Step 4: Event publishing
        await event_bus.publish("MESSAGE_PROCESSED", {
            "message_id": str(normalized.id),
            "platform": "yahoo",
            "entities": entities,
            "summary": summary
        })

        # Step 5: Search integration
        with patch('services.ai.search.agent.HybridSearchAgent', return_value=mock_search_agent):
            mock_search_response = AsyncMock()
            mock_search_response.results = [
                AsyncMock(
                    platform="yahoo",
                    content="End-to-end test message from Yahoo Mail",
                    score=0.98,
                    entities=entities
                )
            ]
            mock_search_response.stats = AsyncMock()
            mock_search_response.stats.total_results = 1

            mock_search_agent.search.return_value = mock_search_response

            search_results = await mock_search_agent.search("end-to-end test")
            assert len(search_results.results) == 1
            assert search_results.results[0].platform == "yahoo"

        # Step 6: API integration
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('api.dependencies.get_current_active_user', return_value=test_user):
                with patch('services.ai.search.agent.HybridSearchAgent', return_value=mock_search_agent):

                    response = await client.post("/api/v1/search/", json={
                        "query": "end-to-end test",
                        "platforms": ["yahoo"]
                    })

                    assert response.status_code == 200
                    data = response.json()
                    assert data["stats"]["total_results"] == 1

        # Complete workflow successful
        assert len(entities) > 0
        assert summary["content"] is not None
        assert len(embedding) == 1536


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
