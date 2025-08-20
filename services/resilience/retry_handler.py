"""
Retry handler with exponential backoff for transient failures.

This module provides sophisticated retry mechanisms with exponential backoff,
jitter, and configurable retry policies for different types of failures.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryPolicy(Enum):
    """Retry policy types."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"


class JitterType(Enum):
    """Jitter types for retry delays."""
    NONE = "none"
    FULL = "full"          # ±50% of delay
    EQUAL = "equal"        # +50% of delay
    DECORRELATED = "decorrelated"  # Decorrelated jitter


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter_type: JitterType = JitterType.FULL
    policy: RetryPolicy = RetryPolicy.EXPONENTIAL_BACKOFF
    retryable_exceptions: tuple = (Exception,)
    non_retryable_exceptions: tuple = ()
    timeout_per_attempt: Optional[float] = None
    total_timeout: Optional[float] = None


class RetryError(Exception):
    """Base exception for retry operations."""

    def __init__(self, message: str, attempts: int, last_exception: Exception):
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception


class RetryTimeoutError(RetryError):
    """Raised when total retry timeout is exceeded."""
    pass


class MaxAttemptsExceededError(RetryError):
    """Raised when maximum retry attempts are exceeded."""
    pass


@dataclass
class RetryAttempt:
    """Information about a retry attempt."""
    attempt_number: int
    delay: float
    exception: Optional[Exception] = None
    start_time: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    success: bool = False

    @property
    def duration(self) -> Optional[float]:
        """Get attempt duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


@dataclass
class RetryStats:
    """Statistics for retry operations."""
    total_attempts: int
    successful_attempts: int
    failed_attempts: int
    total_delay: float
    total_duration: float
    attempts: List[RetryAttempt] = field(default_factory=list)


class RetryHandler:
    """
    Sophisticated retry handler with exponential backoff.

    Provides configurable retry policies, jitter, timeouts, and
    detailed statistics for retry operations.
    """

    def __init__(self, config: RetryConfig, name: str = "default"):
        self.config = config
        self.name = name
        self._stats = RetryStats(0, 0, 0, 0.0, 0.0)

    async def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function with retry logic.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            RetryTimeoutError: If total timeout is exceeded
            MaxAttemptsExceededError: If max attempts are exceeded
        """
        start_time = datetime.now(timezone.utc)
        attempts = []
        last_exception = None

        for attempt_num in range(1, self.config.max_attempts + 1):
            # Check total timeout
            if self.config.total_timeout:
                elapsed = (datetime.now(timezone.utc) -
                           start_time).total_seconds()
                if elapsed >= self.config.total_timeout:
                    raise RetryTimeoutError(
                        f"Total timeout of {self.config.total_timeout}s exceeded",
                        attempt_num - 1,
                        last_exception or Exception("Timeout")
                    )

            # Calculate delay for this attempt
            delay = self._calculate_delay(attempt_num - 1)

            attempt = RetryAttempt(
                attempt_number=attempt_num,
                delay=delay
            )
            attempts.append(attempt)

            # Wait before attempt (except for first attempt)
            if attempt_num > 1:
                logger.debug(
                    f"Retry {self.name}: Waiting {delay:.2f}s before attempt {attempt_num}"
                )
                await asyncio.sleep(delay)
                self._stats.total_delay += delay

            try:
                # Execute with per-attempt timeout
                if self.config.timeout_per_attempt:
                    if asyncio.iscoroutinefunction(func):
                        result = await asyncio.wait_for(
                            func(*args, **kwargs),
                            timeout=self.config.timeout_per_attempt
                        )
                    else:
                        result = func(*args, **kwargs)
                else:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)

                # Success!
                attempt.end_time = datetime.now(timezone.utc)
                attempt.success = True

                self._update_stats(attempts, True)

                logger.debug(
                    f"Retry {self.name}: Success on attempt {attempt_num}"
                )

                return result

            except Exception as e:
                attempt.end_time = datetime.now(timezone.utc)
                attempt.exception = e
                last_exception = e

                # Check if this exception is retryable
                if not self._is_retryable_exception(e):
                    logger.debug(
                        f"Retry {self.name}: Non-retryable exception: {e}"
                    )
                    self._update_stats(attempts, False)
                    raise

                logger.warning(
                    f"Retry {self.name}: Attempt {attempt_num} failed: {e}"
                )

                # If this was the last attempt, raise the exception
                if attempt_num >= self.config.max_attempts:
                    break

        # All attempts failed
        self._update_stats(attempts, False)

        raise MaxAttemptsExceededError(
            f"Max attempts ({self.config.max_attempts}) exceeded for {self.name}",
            len(attempts),
            last_exception
        )

    def _calculate_delay(self, attempt_number: int) -> float:
        """Calculate delay for the given attempt number."""
        if self.config.policy == RetryPolicy.EXPONENTIAL_BACKOFF:
            delay = self.config.initial_delay * \
                (self.config.multiplier ** attempt_number)
        elif self.config.policy == RetryPolicy.LINEAR_BACKOFF:
            delay = self.config.initial_delay * (1 + attempt_number)
        elif self.config.policy == RetryPolicy.FIXED_DELAY:
            delay = self.config.initial_delay
        elif self.config.policy == RetryPolicy.IMMEDIATE:
            delay = 0.0
        else:
            delay = self.config.initial_delay

        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)

        # Apply jitter
        delay = self._apply_jitter(delay, attempt_number)

        return max(0.0, delay)

    def _apply_jitter(self, delay: float, attempt_number: int) -> float:
        """Apply jitter to the delay."""
        if self.config.jitter_type == JitterType.NONE:
            return delay

        elif self.config.jitter_type == JitterType.FULL:
            # ±50% jitter
            jitter_amount = delay * 0.5
            return delay + random.uniform(-jitter_amount, jitter_amount)

        elif self.config.jitter_type == JitterType.EQUAL:
            # +50% jitter
            jitter_amount = delay * 0.5
            return delay + random.uniform(0, jitter_amount)

        elif self.config.jitter_type == JitterType.DECORRELATED:
            # Decorrelated jitter
            if attempt_number == 0:
                return delay
            else:
                return random.uniform(self.config.initial_delay, delay * 3)

        return delay

    def _is_retryable_exception(self, exception: Exception) -> bool:
        """Check if an exception is retryable."""
        # Check non-retryable exceptions first
        if isinstance(exception, self.config.non_retryable_exceptions):
            return False

        # Check retryable exceptions
        return isinstance(exception, self.config.retryable_exceptions)

    def _update_stats(self, attempts: List[RetryAttempt], success: bool) -> None:
        """Update retry statistics."""
        self._stats.total_attempts += len(attempts)
        if success:
            self._stats.successful_attempts += 1
        else:
            self._stats.failed_attempts += 1

        # Calculate total duration
        if attempts:
            start_time = attempts[0].start_time
            end_time = attempts[-1].end_time or datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            self._stats.total_duration += duration

        self._stats.attempts.extend(attempts)

    def get_stats(self) -> RetryStats:
        """Get retry statistics."""
        return self._stats

    def reset_stats(self) -> None:
        """Reset retry statistics."""
        self._stats = RetryStats(0, 0, 0, 0.0, 0.0)


class RetryManager:
    """Manager for multiple retry handlers."""

    def __init__(self):
        self._retry_handlers: Dict[str, RetryHandler] = {}
        self._lock = asyncio.Lock()

    async def get_retry_handler(
        self,
        name: str,
        config: Optional[RetryConfig] = None
    ) -> RetryHandler:
        """Get or create a retry handler."""
        async with self._lock:
            if name not in self._retry_handlers:
                if not config:
                    config = RetryConfig()
                self._retry_handlers[name] = RetryHandler(config, name)
                logger.info(f"Created retry handler '{name}'")

            return self._retry_handlers[name]

    async def remove_retry_handler(self, name: str) -> bool:
        """Remove a retry handler."""
        async with self._lock:
            if name in self._retry_handlers:
                del self._retry_handlers[name]
                logger.info(f"Removed retry handler '{name}'")
                return True
            return False

    async def get_all_stats(self) -> Dict[str, RetryStats]:
        """Get statistics for all retry handlers."""
        stats = {}
        for name, handler in self._retry_handlers.items():
            stats[name] = handler.get_stats()
        return stats

    def list_retry_handlers(self) -> List[str]:
        """List all retry handler names."""
        return list(self._retry_handlers.keys())


# Global retry manager
retry_manager = RetryManager()


async def get_retry_handler(
    name: str,
    config: Optional[RetryConfig] = None
) -> RetryHandler:
    """Get a retry handler from the global manager."""
    return await retry_manager.get_retry_handler(name, config)


@asynccontextmanager
async def retry_context(
    name: str,
    config: Optional[RetryConfig] = None
):
    """Context manager for retry operations."""
    handler = await get_retry_handler(name, config)
    try:
        yield handler
    except (RetryTimeoutError, MaxAttemptsExceededError):
        # Retry errors should be handled by the caller
        raise


def retry(
    name: str,
    config: Optional[RetryConfig] = None
):
    """Decorator for retry protection."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            handler = await get_retry_handler(name, config)
            return await handler.execute(func, *args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in an event loop
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            async def async_call():
                handler = await get_retry_handler(name, config)
                return await handler.execute(func, *args, **kwargs)

            return loop.run_until_complete(async_call())

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Predefined retry configurations for common scenarios
NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    max_delay=30.0,
    multiplier=2.0,
    jitter_type=JitterType.FULL,
    policy=RetryPolicy.EXPONENTIAL_BACKOFF,
    retryable_exceptions=(
        ConnectionError,
        TimeoutError,
        OSError,
    ),
    non_retryable_exceptions=(
        ValueError,
        TypeError,
        KeyError,
    ),
    timeout_per_attempt=30.0,
    total_timeout=300.0
)

DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=0.5,
    max_delay=10.0,
    multiplier=2.0,
    jitter_type=JitterType.EQUAL,
    policy=RetryPolicy.EXPONENTIAL_BACKOFF,
    timeout_per_attempt=10.0,
    total_timeout=60.0
)

API_RETRY_CONFIG = RetryConfig(
    max_attempts=4,
    initial_delay=2.0,
    max_delay=60.0,
    multiplier=1.5,
    jitter_type=JitterType.DECORRELATED,
    policy=RetryPolicy.EXPONENTIAL_BACKOFF,
    timeout_per_attempt=30.0,
    total_timeout=180.0
)
