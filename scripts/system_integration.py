#!/usr/bin/env python3
"""
System Integration Script for R.E.M.I

This script wires together all connectors, AI agents, and APIs into a unified system.
It handles initialization, configuration, and startup of all system components.
"""

from services.resilience.dead_letter_queue import DeadLetterQueue
from services.resilience.circuit_breaker import CircuitBreaker
from services.security.security_manager import SecurityManager
from services.monitoring.metrics import MetricsCollector
from services.monitoring.health import HealthChecker
from integrations.matrix_bridge_hub_factory import MatrixBridgeHubFactory
from integrations.twitter_factory import TwitterConnectorFactory
from integrations.telegram_factory import TelegramConnectorFactory
from integrations.yahoo_factory import YahooConnectorFactory
from integrations.discord_factory import DiscordConnectorFactory
from integrations.slack_factory import SlackConnectorFactory
from integrations.gmail_factory import GmailConnectorFactory
from integrations.connector_manager import ConnectorManager, ConnectorConfig
from services.batch_processing.scheduler import BatchScheduler
from services.vector_db.chroma_client import ChromaClient
from services.ai.entity.extractor import EntityExtractionAgent
from services.ai.summary.agent import SummaryGenerationAgent
from services.ai.memory.agent import ProactiveMemoryAgent
from services.ai.search.agent import HybridSearchAgent
from services.ai.engine import AIProcessingEngine
from services.message_normalizer import MessageNormalizer
from services.event_bus import EventBus
from db.redis_client import get_redis
from db.session import get_db
from db.init_db import initialize_infrastructure, cleanup_infrastructure
from config.config import Settings
import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))


# Import all connectors

# Import monitoring and security

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SystemIntegrator:
    """
    Main system integrator that wires together all components.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.event_bus: Optional[EventBus] = None
        self.connector_manager: Optional[ConnectorManager] = None
        self.ai_engine: Optional[AIProcessingEngine] = None
        self.search_agent: Optional[HybridSearchAgent] = None
        self.memory_agent: Optional[ProactiveMemoryAgent] = None
        self.summary_agent: Optional[SummaryGenerationAgent] = None
        self.entity_agent: Optional[EntityExtractionAgent] = None
        self.batch_scheduler: Optional[BatchScheduler] = None
        self.health_checker: Optional[HealthChecker] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        self.security_manager: Optional[SecurityManager] = None
        self.dead_letter_queue: Optional[DeadLetterQueue] = None

        self._components: Dict[str, Any] = {}
        self._startup_order: List[str] = [
            'infrastructure',
            'security',
            'event_bus',
            'ai_engine',
            'agents',
            'connectors',
            'monitoring',
            'batch_processing'
        ]

    async def initialize_system(self) -> None:
        """Initialize the complete system."""
        logger.info("🚀 Starting R.E.M.I system integration...")

        try:
            for component in self._startup_order:
                logger.info(f"Initializing {component}...")
                await self._initialize_component(component)
                logger.info(f"✅ {component} initialized successfully")

            # Wire components together
            await self._wire_components()

            # Start event listeners
            await self._start_event_listeners()

            # Perform system health check
            await self._perform_system_health_check()

            logger.info("🎉 R.E.M.I system integration completed successfully!")

        except Exception as e:
            logger.error(f"❌ System integration failed: {e}")
            await self.cleanup_system()
            raise

    async def _initialize_component(self, component: str) -> None:
        """Initialize a specific system component."""

        if component == 'infrastructure':
            await self._initialize_infrastructure()
        elif component == 'security':
            await self._initialize_security()
        elif component == 'event_bus':
            await self._initialize_event_bus()
        elif component == 'ai_engine':
            await self._initialize_ai_engine()
        elif component == 'agents':
            await self._initialize_ai_agents()
        elif component == 'connectors':
            await self._initialize_connectors()
        elif component == 'monitoring':
            await self._initialize_monitoring()
        elif component == 'batch_processing':
            await self._initialize_batch_processing()
        else:
            raise ValueError(f"Unknown component: {component}")

    async def _initialize_infrastructure(self) -> None:
        """Initialize core infrastructure (database, Redis, etc.)."""
        await initialize_infrastructure()

        # Initialize vector database
        chroma_client = ChromaClient(
            host=self.settings.CHROMA_HOST,
            port=self.settings.CHROMA_PORT,
            persist_directory=self.settings.CHROMA_PERSIST_DIRECTORY
        )
        await chroma_client.initialize()
        self._components['chroma_client'] = chroma_client

    async def _initialize_security(self) -> None:
        """Initialize security components."""
        self.security_manager = SecurityManager(self.settings)
        await self.security_manager.initialize()
        self._components['security_manager'] = self.security_manager

    async def _initialize_event_bus(self) -> None:
        """Initialize the event bus system."""
        redis_client = await get_redis()
        self.event_bus = EventBus(redis_client)
        await self.event_bus.initialize()
        self._components['event_bus'] = self.event_bus

        # Initialize dead letter queue
        self.dead_letter_queue = DeadLetterQueue(redis_client)
        await self.dead_letter_queue.initialize()
        self._components['dead_letter_queue'] = self.dead_letter_queue

    async def _initialize_ai_engine(self) -> None:
        """Initialize the AI processing engine."""
        self.ai_engine = AIProcessingEngine(
            settings=self.settings,
            event_bus=self.event_bus
        )
        await self.ai_engine.initialize()
        self._components['ai_engine'] = self.ai_engine

    async def _initialize_ai_agents(self) -> None:
        """Initialize all AI agents."""

        # Entity extraction agent
        self.entity_agent = EntityExtractionAgent(
            ai_engine=self.ai_engine,
            event_bus=self.event_bus
        )
        await self.entity_agent.initialize()
        self._components['entity_agent'] = self.entity_agent

        # Summary generation agent
        self.summary_agent = SummaryGenerationAgent(
            ai_engine=self.ai_engine,
            event_bus=self.event_bus
        )
        await self.summary_agent.initialize()
        self._components['summary_agent'] = self.summary_agent

        # Hybrid search agent
        self.search_agent = HybridSearchAgent(
            ai_engine=self.ai_engine,
            chroma_client=self._components['chroma_client'],
            event_bus=self.event_bus
        )
        await self.search_agent.initialize()
        self._components['search_agent'] = self.search_agent

        # Proactive memory agent
        self.memory_agent = ProactiveMemoryAgent(
            ai_engine=self.ai_engine,
            search_agent=self.search_agent,
            event_bus=self.event_bus
        )
        await self.memory_agent.initialize()
        self._components['memory_agent'] = self.memory_agent

    async def _initialize_connectors(self) -> None:
        """Initialize all platform connectors."""

        # Create connector manager
        self.connector_manager = ConnectorManager(
            health_check_interval=60,
            stats_retention_hours=24
        )
        self._components['connector_manager'] = self.connector_manager

        # Initialize connector factories
        factories = {
            'gmail': GmailConnectorFactory(self.event_bus, self.settings),
            'yahoo': YahooConnectorFactory(self.event_bus, self.settings),
            'slack': SlackConnectorFactory(self.event_bus, self.settings),
            'discord': DiscordConnectorFactory(self.event_bus, self.settings),
            'telegram': TelegramConnectorFactory(self.event_bus, self.settings),
            'twitter': TwitterConnectorFactory(self.event_bus, self.settings),
            'matrix': MatrixBridgeHubFactory(self.event_bus, self.settings)
        }

        # Create and register connectors based on configuration
        for platform, factory in factories.items():
            try:
                if await self._should_initialize_connector(platform):
                    connector = await self._create_connector(platform, factory)
                    if connector:
                        config = ConnectorConfig(
                            platform=platform,
                            enabled=True,
                            health_check_interval=60,
                            restart_on_failure=True,
                            max_restart_attempts=3
                        )
                        await self.connector_manager.register_connector(connector, config)
                        logger.info(f"✅ {platform} connector registered")
                    else:
                        logger.warning(
                            f"⚠️ {platform} connector not configured")
                else:
                    logger.info(
                        f"ℹ️ {platform} connector disabled in configuration")
            except Exception as e:
                logger.error(
                    f"❌ Failed to initialize {platform} connector: {e}")

    async def _should_initialize_connector(self, platform: str) -> bool:
        """Check if a connector should be initialized based on configuration."""
        platform_configs = {
            'gmail': bool(getattr(self.settings, 'GMAIL_CLIENT_ID', None)),
            'yahoo': bool(getattr(self.settings, 'YAHOO_EMAIL', None)),
            'slack': bool(getattr(self.settings, 'SLACK_CLIENT_ID', None)),
            'discord': bool(getattr(self.settings, 'DISCORD_BOT_TOKEN', None)),
            'telegram': bool(getattr(self.settings, 'TELEGRAM_BOT_TOKEN', None)),
            'twitter': bool(getattr(self.settings, 'X_API_KEY', None)),
            'matrix': bool(getattr(self.settings, 'MATRIX_HOMESERVER_URL', None))
        }

        return platform_configs.get(platform, False)

    async def _create_connector(self, platform: str, factory) -> Optional[Any]:
        """Create a connector using its factory."""
        try:
            credentials = self._get_connector_credentials(platform)
            if credentials:
                return await factory.create_connector(credentials)
        except Exception as e:
            logger.error(f"Failed to create {platform} connector: {e}")
        return None

    def _get_connector_credentials(self, platform: str) -> Optional[Dict[str, Any]]:
        """Get credentials for a specific platform."""
        credentials_map = {
            'gmail': {
                'client_id': getattr(self.settings, 'GMAIL_CLIENT_ID', None),
                'client_secret': getattr(self.settings, 'GMAIL_CLIENT_SECRET', None),
                'scopes': getattr(self.settings, 'GMAIL_SCOPES', '').split(',')
            },
            'yahoo': {
                'email': getattr(self.settings, 'YAHOO_EMAIL', None),
                'app_password': getattr(self.settings, 'YAHOO_APP_PASSWORD', None),
                'imap_server': getattr(self.settings, 'YAHOO_IMAP_SERVER', 'imap.mail.yahoo.com'),
                'imap_port': getattr(self.settings, 'YAHOO_IMAP_PORT', 993)
            },
            'slack': {
                'client_id': getattr(self.settings, 'SLACK_CLIENT_ID', None),
                'client_secret': getattr(self.settings, 'SLACK_CLIENT_SECRET', None),
                'bot_token': getattr(self.settings, 'SLACK_BOT_TOKEN', None)
            },
            'discord': {
                'bot_token': getattr(self.settings, 'DISCORD_BOT_TOKEN', None),
                'client_id': getattr(self.settings, 'DISCORD_CLIENT_ID', None)
            },
            'telegram': {
                'bot_token': getattr(self.settings, 'TELEGRAM_BOT_TOKEN', None)
            },
            'twitter': {
                'api_key': getattr(self.settings, 'X_API_KEY', None),
                'api_secret': getattr(self.settings, 'X_API_SECRET', None),
                'access_token': getattr(self.settings, 'X_ACCESS_TOKEN', None),
                'access_token_secret': getattr(self.settings, 'X_ACCESS_TOKEN_SECRET', None)
            },
            'matrix': {
                'homeserver_url': getattr(self.settings, 'MATRIX_HOMESERVER_URL', None),
                'access_token': getattr(self.settings, 'MATRIX_ACCESS_TOKEN', None),
                'user_id': getattr(self.settings, 'MATRIX_USER_ID', None)
            }
        }

        credentials = credentials_map.get(platform, {})

        # Filter out None values
        filtered_credentials = {k: v for k,
                                v in credentials.items() if v is not None}

        return filtered_credentials if filtered_credentials else None

    async def _initialize_monitoring(self) -> None:
        """Initialize monitoring and health checking."""

        # Health checker
        self.health_checker = HealthChecker()
        await self.health_checker.initialize()
        self._components['health_checker'] = self.health_checker

        # Metrics collector
        self.metrics_collector = MetricsCollector()
        await self.metrics_collector.initialize()
        self._components['metrics_collector'] = self.metrics_collector

        # Register health checks for all components
        await self._register_health_checks()

    async def _initialize_batch_processing(self) -> None:
        """Initialize batch processing scheduler."""
        self.batch_scheduler = BatchScheduler(
            event_bus=self.event_bus,
            ai_engine=self.ai_engine,
            summary_agent=self.summary_agent,
            memory_agent=self.memory_agent
        )
        await self.batch_scheduler.initialize()
        self._components['batch_scheduler'] = self.batch_scheduler

    async def _wire_components(self) -> None:
        """Wire all components together."""
        logger.info("🔗 Wiring system components...")

        # Wire AI agents to event bus
        if self.entity_agent and self.event_bus:
            await self.event_bus.subscribe("MESSAGE_NORMALIZED", self.entity_agent.process_message)

        if self.summary_agent and self.event_bus:
            await self.event_bus.subscribe("MESSAGE_PROCESSED", self.summary_agent.process_message)

        if self.memory_agent and self.event_bus:
            await self.event_bus.subscribe("ENTITIES_EXTRACTED", self.memory_agent.process_entities)

        # Wire search agent to vector database updates
        if self.search_agent and self.event_bus:
            await self.event_bus.subscribe("MESSAGE_EMBEDDED", self.search_agent.update_index)

        # Wire error handling
        if self.dead_letter_queue and self.event_bus:
            await self.event_bus.subscribe("PROCESSING_FAILED", self.dead_letter_queue.handle_failed_message)

        logger.info("✅ Component wiring completed")

    async def _start_event_listeners(self) -> None:
        """Start all event listeners."""
        logger.info("👂 Starting event listeners...")

        if self.event_bus:
            # Start event bus consumers
            await self.event_bus.start_consumers()

        if self.connector_manager:
            # Start connector manager
            await self.connector_manager.start_all_connectors()

        if self.batch_scheduler:
            # Start batch scheduler
            await self.batch_scheduler.start()

        logger.info("✅ Event listeners started")

    async def _register_health_checks(self) -> None:
        """Register health checks for all components."""
        if not self.health_checker:
            return

        # Register component health checks
        components_to_check = [
            ('event_bus', self.event_bus),
            ('ai_engine', self.ai_engine),
            ('connector_manager', self.connector_manager),
            ('search_agent', self.search_agent),
            ('memory_agent', self.memory_agent),
            ('summary_agent', self.summary_agent),
            ('entity_agent', self.entity_agent),
            ('batch_scheduler', self.batch_scheduler)
        ]

        for name, component in components_to_check:
            if component and hasattr(component, 'health_check'):
                await self.health_checker.register_check(name, component.health_check)

    async def _perform_system_health_check(self) -> None:
        """Perform initial system health check."""
        logger.info("🏥 Performing system health check...")

        if self.health_checker:
            health_status = await self.health_checker.check_all()

            healthy_components = sum(
                1 for status in health_status.values() if status.get('healthy', False))
            total_components = len(health_status)

            logger.info(
                f"Health check results: {healthy_components}/{total_components} components healthy")

            for component, status in health_status.items():
                if status.get('healthy', False):
                    logger.info(
                        f"✅ {component}: {status.get('message', 'OK')}")
                else:
                    logger.warning(
                        f"⚠️ {component}: {status.get('message', 'Unhealthy')}")

    async def start_system(self) -> None:
        """Start the complete system."""
        await self.initialize_system()
        logger.info("🎯 R.E.M.I system is now running!")

    async def cleanup_system(self) -> None:
        """Clean up all system components."""
        logger.info("🧹 Cleaning up system components...")

        cleanup_order = list(reversed(self._startup_order))

        for component in cleanup_order:
            try:
                await self._cleanup_component(component)
            except Exception as e:
                logger.error(f"Error cleaning up {component}: {e}")

        await cleanup_infrastructure()
        logger.info("✅ System cleanup completed")

    async def _cleanup_component(self, component: str) -> None:
        """Clean up a specific component."""

        if component == 'batch_processing' and self.batch_scheduler:
            await self.batch_scheduler.stop()
        elif component == 'connectors' and self.connector_manager:
            await self.connector_manager.stop_all_connectors()
        elif component == 'monitoring':
            if self.health_checker:
                await self.health_checker.cleanup()
            if self.metrics_collector:
                await self.metrics_collector.cleanup()
        elif component == 'agents':
            for agent in [self.entity_agent, self.summary_agent, self.search_agent, self.memory_agent]:
                if agent and hasattr(agent, 'cleanup'):
                    await agent.cleanup()
        elif component == 'ai_engine' and self.ai_engine:
            await self.ai_engine.cleanup()
        elif component == 'event_bus' and self.event_bus:
            await self.event_bus.cleanup()
        elif component == 'security' and self.security_manager:
            await self.security_manager.cleanup()

    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                name: 'initialized' if component else 'not_initialized'
                for name, component in self._components.items()
            },
            'connector_manager_status': self.connector_manager.get_manager_stats() if self.connector_manager else None,
            'health_status': 'operational' if all(self._components.values()) else 'degraded'
        }


async def main():
    """Main entry point for system integration."""
    try:
        # Load settings
        settings = Settings()

        # Create system integrator
        integrator = SystemIntegrator(settings)

        # Start system
        await integrator.start_system()

        # Print system status
        status = integrator.get_system_status()
        logger.info(f"System Status: {status}")

        # Keep running
        logger.info("System is running. Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(60)  # Check every minute

                # Periodic health check
                if integrator.health_checker:
                    health_status = await integrator.health_checker.check_all()
                    unhealthy = [name for name, status in health_status.items(
                    ) if not status.get('healthy', False)]
                    if unhealthy:
                        logger.warning(
                            f"Unhealthy components detected: {unhealthy}")

        except KeyboardInterrupt:
            logger.info("Shutdown signal received")

    except Exception as e:
        logger.error(f"System integration failed: {e}")
        sys.exit(1)
    finally:
        if 'integrator' in locals():
            await integrator.cleanup_system()


if __name__ == "__main__":
    asyncio.run(main())
