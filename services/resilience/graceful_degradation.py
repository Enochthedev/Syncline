"""
Graceful degradation strategies for partial system failures.

This module provides mechanisms to gracefully handle partial system failures
by falling back to alternative implementations or cached data.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceStatus(Enum):
    """Service status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


class DegradationLevel(Enum):
    """Levels of service degradation."""
    NONE = "none"           # Full functionality
    MINOR = "minor"         # Some features disabled
    MAJOR = "major"         # Core features only
    CRITICAL = "critical"   # Emergency mode only


@dataclass
class ServiceHealth:
    """Health information for a service."""
    name: str
    status: ServiceStatus
    degradation_level: DegradationLevel = DegradationLevel.NONE
    last_check: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))
    error_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FallbackConfig:
    """Configuration for fallback behavior."""
    enabled: bool = True
    cache_ttl_seconds: int = 300
    max_cache_size: int = 1000
    fallback_timeout_seconds: float = 5.0
    health_check_interval_seconds: int = 60


class GracefulDegradationError(Exception):
    """Base exception for graceful degradation."""
    pass


class FallbackExecutionError(GracefulDegradationError):
    """Raised when fallback execution fails."""
    pass


class GracefulDegradationManager:
    """
    Manager for graceful degradation strategies.

    Provides fallback mechanisms, caching, and service health monitoring
    to maintain system functionality during partial failures.
    """

    def __init__(self, config: FallbackConfig = None):
        self.config = config or FallbackConfig()
        self._services: Dict[str, ServiceHealth] = {}
        self._fallback_cache: Dict[str, Dict[str, Any]] = {}
        self._fallback_handlers: Dict[str, Callable] = {}
        self._health_check_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def register_service(
        self,
        name: str,
        health_check: Optional[Callable[[], bool]] = None,
        fallback_handler: Optional[Callable[..., Any]] = None
    ) -> None:
        """Register a service for monitoring and fallback."""
        async with self._lock:
            self._services[name] = ServiceHealth(
                name=name,
                status=ServiceStatus.HEALTHY
            )

            if fallback_handler:
                self._fallback_handlers[name] = fallback_handler

            if health_check:
                # Start health check task
                task = asyncio.create_task(
                    self._health_check_loop(name, health_check)
                )
                self._health_check_tasks[name] = task

            logger.info(
                f"Registered service '{name}' for graceful degradation")

    async def unregister_service(self, name: str) -> None:
        """Unregister a service."""
        async with self._lock:
            # Stop health check task
            if name in self._health_check_tasks:
                self._health_check_tasks[name].cancel()
                del self._health_check_tasks[name]

            # Clean up
            self._services.pop(name, None)
            self._fallback_handlers.pop(name, None)
            self._fallback_cache.pop(name, None)

            logger.info(f"Unregistered service '{name}'")

    async def execute_with_fallback(
        self,
        service_name: str,
        primary_func: Callable[..., T],
        cache_key: Optional[str] = None,
        *args,
        **kwargs
    ) -> T:
        """
        Execute a function with fallback support.

        Args:
            service_name: Name of the service
            primary_func: Primary function to execute
            cache_key: Key for caching results
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result or fallback result
        """
        service = self._services.get(service_name)
        if not service:
            # Service not registered, execute normally
            if asyncio.iscoroutinefunction(primary_func):
                return await primary_func(*args, **kwargs)
            else:
                return primary_func(*args, **kwargs)

        try:
            # Try primary function if service is healthy or degraded
            if service.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]:
                if asyncio.iscoroutinefunction(primary_func):
                    result = await primary_func(*args, **kwargs)
                else:
                    result = primary_func(*args, **kwargs)

                # Cache successful result
                if cache_key and self.config.enabled:
                    await self._cache_result(service_name, cache_key, result)

                # Record success
                await self._record_success(service_name)
                return result

        except Exception as e:
            logger.warning(
                f"Primary function failed for service '{service_name}': {e}")
            await self._record_failure(service_name, e)

        # Try fallback strategies
        return await self._execute_fallback(service_name, cache_key, *args, **kwargs)

    async def _execute_fallback(
        self,
        service_name: str,
        cache_key: Optional[str],
        *args,
        **kwargs
    ) -> Any:
        """Execute fallback strategies."""
        # Strategy 1: Try cached result
        if cache_key:
            cached_result = await self._get_cached_result(service_name, cache_key)
            if cached_result is not None:
                logger.info(
                    f"Using cached result for service '{service_name}'")
                return cached_result

        # Strategy 2: Try registered fallback handler
        if service_name in self._fallback_handlers:
            try:
                fallback_func = self._fallback_handlers[service_name]

                if asyncio.iscoroutinefunction(fallback_func):
                    result = await asyncio.wait_for(
                        fallback_func(*args, **kwargs),
                        timeout=self.config.fallback_timeout_seconds
                    )
                else:
                    result = fallback_func(*args, **kwargs)

                logger.info(
                    f"Used fallback handler for service '{service_name}'")
                return result

            except Exception as e:
                logger.error(
                    f"Fallback handler failed for service '{service_name}': {e}")

        # Strategy 3: Return degraded response
        degraded_response = await self._get_degraded_response(service_name)
        if degraded_response is not None:
            logger.info(
                f"Using degraded response for service '{service_name}'")
            return degraded_response

        # All fallback strategies failed
        raise FallbackExecutionError(
            f"All fallback strategies failed for service '{service_name}'"
        )

    async def _cache_result(
        self,
        service_name: str,
        cache_key: str,
        result: Any
    ) -> None:
        """Cache a result for fallback use."""
        if service_name not in self._fallback_cache:
            self._fallback_cache[service_name] = {}

        cache = self._fallback_cache[service_name]

        # Implement simple LRU eviction
        if len(cache) >= self.config.max_cache_size:
            # Remove oldest entry
            oldest_key = next(iter(cache))
            del cache[oldest_key]

        cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now(timezone.utc),
            'ttl': self.config.cache_ttl_seconds
        }

    async def _get_cached_result(
        self,
        service_name: str,
        cache_key: str
    ) -> Any:
        """Get a cached result if available and not expired."""
        if service_name not in self._fallback_cache:
            return None

        cache = self._fallback_cache[service_name]
        if cache_key not in cache:
            return None

        cached_entry = cache[cache_key]

        # Check if expired
        age = (datetime.now(timezone.utc) -
               cached_entry['timestamp']).total_seconds()
        if age > cached_entry['ttl']:
            del cache[cache_key]
            return None

        return cached_entry['result']

    async def _get_degraded_response(self, service_name: str) -> Any:
        """Get a degraded response for the service."""
        service = self._services.get(service_name)
        if not service:
            return None

        # Return different responses based on degradation level
        if service.degradation_level == DegradationLevel.MINOR:
            return {
                'status': 'degraded',
                'message': 'Service is running with limited functionality',
                'data': None
            }
        elif service.degradation_level == DegradationLevel.MAJOR:
            return {
                'status': 'limited',
                'message': 'Service is running in emergency mode',
                'data': None
            }
        elif service.degradation_level == DegradationLevel.CRITICAL:
            return {
                'status': 'unavailable',
                'message': 'Service is temporarily unavailable',
                'data': None
            }

        return None

    async def _record_success(self, service_name: str) -> None:
        """Record a successful operation."""
        async with self._lock:
            service = self._services.get(service_name)
            if service:
                # Reset error count on success
                service.error_count = 0
                service.last_error = None

                # Improve status if degraded
                if service.status == ServiceStatus.DEGRADED:
                    service.status = ServiceStatus.HEALTHY
                    service.degradation_level = DegradationLevel.NONE
                    logger.info(
                        f"Service '{service_name}' recovered to healthy status")

    async def _record_failure(self, service_name: str, error: Exception) -> None:
        """Record a failed operation."""
        async with self._lock:
            service = self._services.get(service_name)
            if service:
                service.error_count += 1
                service.last_error = str(error)
                service.last_check = datetime.now(timezone.utc)

                # Update status based on error count
                if service.error_count >= 10:
                    service.status = ServiceStatus.OFFLINE
                    service.degradation_level = DegradationLevel.CRITICAL
                elif service.error_count >= 5:
                    service.status = ServiceStatus.UNHEALTHY
                    service.degradation_level = DegradationLevel.MAJOR
                elif service.error_count >= 2:
                    service.status = ServiceStatus.DEGRADED
                    service.degradation_level = DegradationLevel.MINOR

                logger.warning(
                    f"Service '{service_name}' status: {service.status.value}, "
                    f"errors: {service.error_count}"
                )

    async def _health_check_loop(
        self,
        service_name: str,
        health_check: Callable[[], bool]
    ) -> None:
        """Run periodic health checks for a service."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval_seconds)

                # Perform health check
                is_healthy = health_check()

                async with self._lock:
                    service = self._services.get(service_name)
                    if service:
                        service.last_check = datetime.now(timezone.utc)

                        if is_healthy:
                            await self._record_success(service_name)
                        else:
                            await self._record_failure(
                                service_name,
                                Exception("Health check failed")
                            )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Health check error for service '{service_name}': {e}")

    async def get_service_health(self, service_name: str) -> Optional[ServiceHealth]:
        """Get health information for a service."""
        return self._services.get(service_name)

    async def get_all_service_health(self) -> Dict[str, ServiceHealth]:
        """Get health information for all services."""
        return self._services.copy()

    async def force_degradation(
        self,
        service_name: str,
        level: DegradationLevel
    ) -> bool:
        """Force a service to a specific degradation level."""
        async with self._lock:
            service = self._services.get(service_name)
            if service:
                service.degradation_level = level

                # Update status based on degradation level
                if level == DegradationLevel.NONE:
                    service.status = ServiceStatus.HEALTHY
                elif level == DegradationLevel.MINOR:
                    service.status = ServiceStatus.DEGRADED
                elif level == DegradationLevel.MAJOR:
                    service.status = ServiceStatus.UNHEALTHY
                elif level == DegradationLevel.CRITICAL:
                    service.status = ServiceStatus.OFFLINE

                logger.info(
                    f"Forced service '{service_name}' to degradation level: {level.value}"
                )
                return True

        return False

    async def clear_cache(self, service_name: Optional[str] = None) -> None:
        """Clear cache for a service or all services."""
        if service_name:
            self._fallback_cache.pop(service_name, None)
            logger.info(f"Cleared cache for service '{service_name}'")
        else:
            self._fallback_cache.clear()
            logger.info("Cleared all service caches")

    async def shutdown(self) -> None:
        """Shutdown the graceful degradation manager."""
        # Cancel all health check tasks
        for task in self._health_check_tasks.values():
            task.cancel()

        # Wait for tasks to complete
        if self._health_check_tasks:
            await asyncio.gather(
                *self._health_check_tasks.values(),
                return_exceptions=True
            )

        self._health_check_tasks.clear()
        logger.info("Graceful degradation manager shutdown complete")


# Global graceful degradation manager
graceful_degradation_manager = GracefulDegradationManager()


async def get_graceful_degradation_manager() -> GracefulDegradationManager:
    """Get the global graceful degradation manager."""
    return graceful_degradation_manager


@asynccontextmanager
async def graceful_degradation_context(
    service_name: str,
    primary_func: Callable,
    cache_key: Optional[str] = None
):
    """Context manager for graceful degradation."""
    manager = await get_graceful_degradation_manager()
    try:
        yield lambda *args, **kwargs: manager.execute_with_fallback(
            service_name, primary_func, cache_key, *args, **kwargs
        )
    except Exception:
        raise


def with_graceful_degradation(
    service_name: str,
    cache_key: Optional[str] = None,
    fallback_handler: Optional[Callable] = None
):
    """Decorator for graceful degradation."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            manager = await get_graceful_degradation_manager()

            # Register fallback handler if provided
            if fallback_handler:
                await manager.register_service(
                    service_name,
                    fallback_handler=fallback_handler
                )

            return await manager.execute_with_fallback(
                service_name, func, cache_key, *args, **kwargs
            )

        def sync_wrapper(*args, **kwargs):
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            async def async_call():
                manager = await get_graceful_degradation_manager()

                if fallback_handler:
                    await manager.register_service(
                        service_name,
                        fallback_handler=fallback_handler
                    )

                return await manager.execute_with_fallback(
                    service_name, func, cache_key, *args, **kwargs
                )

            return loop.run_until_complete(async_call())

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
