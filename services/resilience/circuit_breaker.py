"""
Enhanced Circuit Breaker implementation for fault tolerance.

This module provides circuit breaker patterns to prevent cascading failures
and enable graceful degradation of services.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 60
    success_threshold: int = 3  # For half-open state
    timeout_seconds: float = 30.0
    expected_exception_types: tuple = (Exception,)
    ignore_exception_types: tuple = ()


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, message: str, circuit_breaker: 'CircuitBreaker'):
        super().__init__(message)
        self.circuit_breaker = circuit_breaker


class CircuitBreakerTimeoutError(CircuitBreakerError):
    """Raised when operation times out."""
    pass


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    state: CircuitBreakerState
    failure_count: int
    success_count: int
    last_failure_time: Optional[datetime]
    last_success_time: Optional[datetime]
    total_requests: int
    total_failures: int
    total_successes: int
    uptime_seconds: float
    failure_rate: float


class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance.

    Prevents cascading failures by temporarily blocking requests
    when a service is failing consistently.
    """

    def __init__(self, config: CircuitBreakerConfig, name: str = "default"):
        self.config = config
        self.name = name
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._last_success_time: Optional[datetime] = None
        self._total_requests = 0
        self._total_failures = 0
        self._total_successes = 0
        self._start_time = datetime.now(timezone.utc)
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit breaker is open
            CircuitBreakerTimeoutError: If operation times out
        """
        async with self._lock:
            self._total_requests += 1

            # Check if we can execute
            if not await self._can_execute():
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is {self._state.value}",
                    self
                )

        try:
            # Execute with timeout
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout_seconds
                )
            else:
                result = func(*args, **kwargs)

            await self._record_success()
            return result

        except asyncio.TimeoutError:
            timeout_error = CircuitBreakerTimeoutError(
                f"Operation timed out after {self.config.timeout_seconds}s",
                self
            )
            await self._record_failure(timeout_error)
            raise timeout_error

        except Exception as e:
            # Check if this exception should be ignored
            if isinstance(e, self.config.ignore_exception_types):
                return None

            # Check if this is an expected exception type
            if isinstance(e, self.config.expected_exception_types):
                await self._record_failure(e)

            raise

    async def _can_execute(self) -> bool:
        """Check if request can be executed."""
        if self._state == CircuitBreakerState.CLOSED:
            return True

        elif self._state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if (self._last_failure_time and
                datetime.now(timezone.utc) - self._last_failure_time >=
                    timedelta(seconds=self.config.recovery_timeout_seconds)):
                self._state = CircuitBreakerState.HALF_OPEN
                self._success_count = 0
                logger.info(
                    f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                return True
            return False

        elif self._state == CircuitBreakerState.HALF_OPEN:
            return True

        return False

    async def _record_success(self) -> None:
        """Record a successful operation."""
        async with self._lock:
            self._total_successes += 1
            self._last_success_time = datetime.now(timezone.utc)

            if self._state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitBreakerState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info(
                        f"Circuit breaker '{self.name}' transitioning to CLOSED")

            elif self._state == CircuitBreakerState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    async def _record_failure(self, exception: Exception) -> None:
        """Record a failed operation."""
        async with self._lock:
            self._failure_count += 1
            self._total_failures += 1
            self._last_failure_time = datetime.now(timezone.utc)

            logger.warning(
                f"Circuit breaker '{self.name}' recorded failure: {exception}"
            )

            if self._state == CircuitBreakerState.HALF_OPEN:
                self._state = CircuitBreakerState.OPEN
                logger.warning(
                    f"Circuit breaker '{self.name}' transitioning to OPEN from HALF_OPEN"
                )

            elif (self._state == CircuitBreakerState.CLOSED and
                  self._failure_count >= self.config.failure_threshold):
                self._state = CircuitBreakerState.OPEN
                logger.warning(
                    f"Circuit breaker '{self.name}' OPEN after {self._failure_count} failures"
                )

    async def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        async with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            logger.info(
                f"Circuit breaker '{self.name}' manually reset to CLOSED")

    async def force_open(self) -> None:
        """Force the circuit breaker to open state."""
        async with self._lock:
            self._state = CircuitBreakerState.OPEN
            self._last_failure_time = datetime.now(timezone.utc)
            logger.warning(
                f"Circuit breaker '{self.name}' manually forced to OPEN")

    def get_stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics."""
        uptime = (datetime.now(timezone.utc) -
                  self._start_time).total_seconds()
        failure_rate = (
            self._total_failures / self._total_requests
            if self._total_requests > 0 else 0.0
        )

        return CircuitBreakerStats(
            state=self._state,
            failure_count=self._failure_count,
            success_count=self._success_count,
            last_failure_time=self._last_failure_time,
            last_success_time=self._last_success_time,
            total_requests=self._total_requests,
            total_failures=self._total_failures,
            total_successes=self._total_successes,
            uptime_seconds=uptime,
            failure_rate=failure_rate
        )


class CircuitBreakerManager:
    """Manager for multiple circuit breakers."""

    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_circuit_breaker(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        async with self._lock:
            if name not in self._circuit_breakers:
                if not config:
                    config = CircuitBreakerConfig()
                self._circuit_breakers[name] = CircuitBreaker(config, name)
                logger.info(f"Created circuit breaker '{name}'")

            return self._circuit_breakers[name]

    async def remove_circuit_breaker(self, name: str) -> bool:
        """Remove a circuit breaker."""
        async with self._lock:
            if name in self._circuit_breakers:
                del self._circuit_breakers[name]
                logger.info(f"Removed circuit breaker '{name}'")
                return True
            return False

    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        async with self._lock:
            for cb in self._circuit_breakers.values():
                await cb.reset()
            logger.info("Reset all circuit breakers")

    async def get_all_stats(self) -> Dict[str, CircuitBreakerStats]:
        """Get statistics for all circuit breakers."""
        stats = {}
        for name, cb in self._circuit_breakers.items():
            stats[name] = cb.get_stats()
        return stats

    def list_circuit_breakers(self) -> List[str]:
        """List all circuit breaker names."""
        return list(self._circuit_breakers.keys())


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()


async def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """Get a circuit breaker from the global manager."""
    return await circuit_breaker_manager.get_circuit_breaker(name, config)


@asynccontextmanager
async def circuit_breaker_context(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """Context manager for circuit breaker operations."""
    cb = await get_circuit_breaker(name, config)
    try:
        yield cb
    except CircuitBreakerError:
        # Circuit breaker errors should be handled by the caller
        raise
    except Exception as e:
        # Other exceptions are recorded as failures
        await cb._record_failure(e)
        raise


def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """Decorator for circuit breaker protection."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            cb = await get_circuit_breaker(name, config)
            return await cb.call(func, *args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in an event loop
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            async def async_call():
                cb = await get_circuit_breaker(name, config)
                return await cb.call(func, *args, **kwargs)

            return loop.run_until_complete(async_call())

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
