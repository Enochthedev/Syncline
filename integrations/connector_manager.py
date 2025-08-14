"""
Connector Manager for lifecycle management and health monitoring.

This module provides centralized management of platform connectors with
health monitoring, lifecycle management, and coordination.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum

from .base_connector import BaseConnector, ConnectorHealth, ConnectorStatus
from .rate_limiter import RateLimiter, CircuitBreaker, RateLimitConfig, CircuitBreakerConfig
from .token_manager import TokenManager

logger = logging.getLogger(__name__)


class ManagerStatus(Enum):
    """Connector manager status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ConnectorConfig:
    """Configuration for a platform connector."""
    platform: str
    enabled: bool = True
    rate_limit: Optional[RateLimitConfig] = None
    circuit_breaker: Optional[CircuitBreakerConfig] = None
    health_check_interval: int = 60  # seconds
    restart_on_failure: bool = True
    max_restart_attempts: int = 3
    restart_delay: int = 30  # seconds
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectorStats:
    """Statistics for a connector."""
    platform: str
    status: ConnectorStatus
    uptime_seconds: float
    error_count: int
    restart_count: int
    last_error: Optional[str]
    last_restart: Optional[datetime]
    health_checks_passed: int
    health_checks_failed: int
    rate_limit_stats: Dict[str, Any] = field(default_factory=dict)
    circuit_breaker_stats: Dict[str, Any] = field(default_factory=dict)


class ConnectorManager:
    """
    Manages lifecycle and health of platform connectors.

    Provides centralized management, monitoring, and coordination
    of all platform connectors with automatic restart and health monitoring.
    """

    def __init__(
        self,
        token_manager: Optional[TokenManager] = None,
        health_check_interval: int = 60,
        stats_retention_hours: int = 24
    ):
        self.token_manager = token_manager
        self.health_check_interval = health_check_interval
        self.stats_retention_hours = stats_retention_hours

        self._connectors: Dict[str, BaseConnector] = {}
        self._connector_configs: Dict[str, ConnectorConfig] = {}
        self._connector_stats: Dict[str, ConnectorStats] = {}
        self._restart_counts: Dict[str, int] = {}
        self._last_restarts: Dict[str, datetime] = {}

        self._status = ManagerStatus.STOPPED
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()

    @property
    def status(self) -> ManagerStatus:
        """Get manager status."""
        return self._status

    @property
    def is_running(self) -> bool:
        """Check if manager is running."""
        return self._running

    async def register_connector(
        self,
        connector: BaseConnector,
        config: Optional[ConnectorConfig] = None
    ) -> None:
        """Register a connector with the manager."""
        async with self._lock:
            platform = connector.platform

            if platform in self._connectors:
                logger.warning(
                    f"Connector for {platform} already registered, replacing")
                await self._stop_connector(platform)

            # Use provided config or create default
            if config is None:
                config = ConnectorConfig(
                    platform=platform,
                    rate_limit=RateLimitConfig(),
                    circuit_breaker=CircuitBreakerConfig()
                )

            # Set up rate limiter and circuit breaker
            if config.rate_limit:
                connector.rate_limiter = RateLimiter(config.rate_limit)

            if config.circuit_breaker:
                connector.circuit_breaker = CircuitBreaker(
                    config.circuit_breaker)

            # Set token manager
            if self.token_manager:
                connector.token_manager = self.token_manager

            self._connectors[platform] = connector
            self._connector_configs[platform] = config
            self._restart_counts[platform] = 0

            # Initialize stats
            self._connector_stats[platform] = ConnectorStats(
                platform=platform,
                status=ConnectorStatus.DISCONNECTED,
                uptime_seconds=0.0,
                error_count=0,
                restart_count=0,
                last_error=None,
                last_restart=None,
                health_checks_passed=0,
                health_checks_failed=0
            )

            logger.info(f"Registered connector for platform: {platform}")

    async def unregister_connector(self, platform: str) -> None:
        """Unregister a connector."""
        async with self._lock:
            if platform not in self._connectors:
                logger.warning(f"Connector for {platform} not registered")
                return

            await self._stop_connector(platform)

            del self._connectors[platform]
            del self._connector_configs[platform]
            del self._connector_stats[platform]
            self._restart_counts.pop(platform, None)
            self._last_restarts.pop(platform, None)

            logger.info(f"Unregistered connector for platform: {platform}")

    async def start_all_connectors(self) -> None:
        """Start all registered connectors."""
        if self._running:
            logger.warning("Connector manager already running")
            return

        self._status = ManagerStatus.STARTING
        logger.info("Starting connector manager")

        try:
            # Start enabled connectors
            start_tasks = []
            for platform, config in self._connector_configs.items():
                if config.enabled:
                    start_tasks.append(self._start_connector(platform))

            if start_tasks:
                await asyncio.gather(*start_tasks, return_exceptions=True)

            # Start health check task
            self._running = True
            self._health_check_task = asyncio.create_task(
                self._health_check_loop())

            self._status = ManagerStatus.RUNNING
            logger.info("Connector manager started successfully")

        except Exception as e:
            self._status = ManagerStatus.ERROR
            logger.error(f"Failed to start connector manager: {e}")
            raise

    async def stop_all_connectors(self) -> None:
        """Stop all connectors."""
        if not self._running:
            logger.warning("Connector manager not running")
            return

        self._status = ManagerStatus.STOPPING
        logger.info("Stopping connector manager")

        try:
            self._running = False

            # Cancel health check task
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
                self._health_check_task = None

            # Stop all connectors
            stop_tasks = []
            for platform in list(self._connectors.keys()):
                stop_tasks.append(self._stop_connector(platform))

            if stop_tasks:
                await asyncio.gather(*stop_tasks, return_exceptions=True)

            self._status = ManagerStatus.STOPPED
            logger.info("Connector manager stopped")

        except Exception as e:
            self._status = ManagerStatus.ERROR
            logger.error(f"Error stopping connector manager: {e}")
            raise

    async def start_connector(self, platform: str) -> None:
        """Start a specific connector."""
        async with self._lock:
            await self._start_connector(platform)

    async def stop_connector(self, platform: str) -> None:
        """Stop a specific connector."""
        async with self._lock:
            await self._stop_connector(platform)

    async def restart_connector(self, platform: str) -> None:
        """Restart a specific connector."""
        async with self._lock:
            await self._restart_connector(platform)

    async def get_connector_health(self, platform: Optional[str] = None) -> Dict[str, ConnectorHealth]:
        """Get health status for connectors."""
        if platform:
            if platform not in self._connectors:
                raise ValueError(f"Connector for {platform} not registered")
            return {platform: await self._connectors[platform].health_check()}

        # Get health for all connectors
        health_status = {}
        for platform, connector in self._connectors.items():
            try:
                health_status[platform] = await connector.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {platform}: {e}")
                health_status[platform] = ConnectorHealth(
                    status=ConnectorStatus.UNHEALTHY,
                    last_check=datetime.utcnow(),
                    error_count=1,
                    last_error=str(e)
                )

        return health_status

    async def get_connector_stats(self, platform: Optional[str] = None) -> Dict[str, ConnectorStats]:
        """Get statistics for connectors."""
        if platform:
            if platform not in self._connector_stats:
                raise ValueError(f"Stats for {platform} not available")
            return {platform: self._connector_stats[platform]}

        return dict(self._connector_stats)

    async def enable_connector(self, platform: str) -> None:
        """Enable a connector."""
        if platform not in self._connector_configs:
            raise ValueError(f"Connector for {platform} not registered")

        self._connector_configs[platform].enabled = True

        if self._running:
            await self.start_connector(platform)

    async def disable_connector(self, platform: str) -> None:
        """Disable a connector."""
        if platform not in self._connector_configs:
            raise ValueError(f"Connector for {platform} not registered")

        self._connector_configs[platform].enabled = False

        if self._running:
            await self.stop_connector(platform)

    async def _start_connector(self, platform: str) -> None:
        """Internal method to start a connector."""
        if platform not in self._connectors:
            logger.error(f"Connector for {platform} not registered")
            return

        connector = self._connectors[platform]
        config = self._connector_configs[platform]

        if not config.enabled:
            logger.debug(f"Connector for {platform} is disabled")
            return

        try:
            logger.info(f"Starting connector for {platform}")
            await connector.start()

            # Update stats
            stats = self._connector_stats[platform]
            stats.status = ConnectorStatus.HEALTHY

            logger.info(f"Connector for {platform} started successfully")

        except Exception as e:
            logger.error(f"Failed to start connector for {platform}: {e}")

            # Update stats
            stats = self._connector_stats[platform]
            stats.status = ConnectorStatus.UNHEALTHY
            stats.error_count += 1
            stats.last_error = str(e)

    async def _stop_connector(self, platform: str) -> None:
        """Internal method to stop a connector."""
        if platform not in self._connectors:
            return

        connector = self._connectors[platform]

        try:
            logger.info(f"Stopping connector for {platform}")
            await connector.stop()

            # Update stats
            stats = self._connector_stats[platform]
            stats.status = ConnectorStatus.DISCONNECTED

            logger.info(f"Connector for {platform} stopped")

        except Exception as e:
            logger.error(f"Error stopping connector for {platform}: {e}")

            # Update stats
            stats = self._connector_stats[platform]
            stats.error_count += 1
            stats.last_error = str(e)

    async def _restart_connector(self, platform: str) -> None:
        """Internal method to restart a connector."""
        config = self._connector_configs[platform]

        # Check restart limits
        restart_count = self._restart_counts.get(platform, 0)
        if restart_count >= config.max_restart_attempts:
            logger.error(f"Max restart attempts reached for {platform}")
            return

        # Check restart delay
        last_restart = self._last_restarts.get(platform)
        if last_restart:
            time_since_restart = datetime.utcnow() - last_restart
            if time_since_restart.total_seconds() < config.restart_delay:
                logger.debug(f"Restart delay not met for {platform}")
                return

        try:
            logger.info(f"Restarting connector for {platform}")

            await self._stop_connector(platform)
            await asyncio.sleep(1)  # Brief pause
            await self._start_connector(platform)

            # Update restart tracking
            self._restart_counts[platform] = restart_count + 1
            self._last_restarts[platform] = datetime.utcnow()

            # Update stats
            stats = self._connector_stats[platform]
            stats.restart_count += 1
            stats.last_restart = datetime.utcnow()

            logger.info(f"Connector for {platform} restarted successfully")

        except Exception as e:
            logger.error(f"Failed to restart connector for {platform}: {e}")

    async def _health_check_loop(self) -> None:
        """Background task for periodic health checks."""
        logger.info("Starting health check loop")

        while self._running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error

        logger.info("Health check loop stopped")

    async def _perform_health_checks(self) -> None:
        """Perform health checks on all connectors."""
        for platform, connector in self._connectors.items():
            config = self._connector_configs[platform]
            stats = self._connector_stats[platform]

            if not config.enabled:
                continue

            try:
                health = await connector.health_check()

                # Update stats
                stats.status = health.status
                stats.uptime_seconds = health.uptime_seconds
                stats.error_count = health.error_count
                stats.last_error = health.last_error

                if health.status == ConnectorStatus.HEALTHY:
                    stats.health_checks_passed += 1
                    # Reset restart count on successful health check
                    self._restart_counts[platform] = 0
                else:
                    stats.health_checks_failed += 1

                    # Restart on failure if configured
                    if (config.restart_on_failure and
                            health.status == ConnectorStatus.UNHEALTHY):
                        await self._restart_connector(platform)

                # Update rate limiter and circuit breaker stats
                if connector.rate_limiter and hasattr(connector.rate_limiter, 'get_stats'):
                    stats.rate_limit_stats = connector.rate_limiter.get_stats()

                if connector.circuit_breaker and hasattr(connector.circuit_breaker, 'get_stats'):
                    stats.circuit_breaker_stats = connector.circuit_breaker.get_stats()

            except Exception as e:
                logger.error(f"Health check failed for {platform}: {e}")
                stats.health_checks_failed += 1
                stats.error_count += 1
                stats.last_error = str(e)

    def get_manager_stats(self) -> Dict[str, Any]:
        """Get overall manager statistics."""
        total_connectors = len(self._connectors)
        enabled_connectors = sum(
            1 for config in self._connector_configs.values() if config.enabled)
        healthy_connectors = sum(
            1 for stats in self._connector_stats.values()
            if stats.status == ConnectorStatus.HEALTHY
        )

        return {
            "status": self._status.value,
            "total_connectors": total_connectors,
            "enabled_connectors": enabled_connectors,
            "healthy_connectors": healthy_connectors,
            "health_check_interval": self.health_check_interval,
            "uptime_seconds": (datetime.utcnow() - datetime.utcnow()).total_seconds() if self._running else 0
        }
