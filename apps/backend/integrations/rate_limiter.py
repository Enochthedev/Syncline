"""
Rate Limiter for Platform API Requests

Provides rate limiting with:
- Token bucket algorithm
- Platform-specific rate limits
- Exponential backoff for retries
- Request queuing
"""

import asyncio
import logging
import random
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine, Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================


class RateLimitConfig(BaseModel):
    """Rate limit configuration for a platform."""

    requests_per_minute: int = Field(
        default=60, description="Maximum requests per minute"
    )
    requests_per_hour: Optional[int] = Field(
        default=None, description="Maximum requests per hour (optional)"
    )
    requests_per_day: Optional[int] = Field(
        default=None, description="Maximum requests per day (optional)"
    )
    burst_size: int = Field(default=10, description="Maximum burst size")
    retry_after_seconds: int = Field(
        default=60, description="Default retry delay when rate limited"
    )


class RateLimitState(BaseModel):
    """Current state of rate limiter."""

    tokens_available: int = Field(description="Available request tokens")
    last_refill: datetime = Field(description="Last token refill time")
    requests_this_minute: int = Field(
        default=0, description="Requests in current minute"
    )
    requests_this_hour: int = Field(default=0, description="Requests in current hour")
    requests_this_day: int = Field(default=0, description="Requests in current day")
    minute_reset_at: datetime = Field(description="Minute window reset time")
    hour_reset_at: Optional[datetime] = Field(
        default=None, description="Hour window reset time"
    )
    day_reset_at: Optional[datetime] = Field(
        default=None, description="Day window reset time"
    )


# =============================================================================
# Rate Limiter
# =============================================================================


class RateLimiter:
    """
    Token bucket rate limiter with multiple time windows.

    Supports:
    - Per-minute, per-hour, and per-day limits
    - Burst capacity
    - Automatic token refill
    - Request queuing
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config

        # Token bucket state
        self._tokens = config.burst_size
        self._last_refill = datetime.utcnow()

        # Request counters
        self._requests_this_minute = 0
        self._requests_this_hour = 0
        self._requests_this_day = 0

        # Time window tracking
        self._minute_reset_at = datetime.utcnow() + timedelta(minutes=1)
        self._hour_reset_at = datetime.utcnow() + timedelta(hours=1)
        self._day_reset_at = datetime.utcnow() + timedelta(days=1)

        # Request queue
        self._queue: deque = deque()

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def acquire(self, wait: bool = True) -> bool:
        """
        Acquire permission to make a request.

        Args:
            wait: If True, wait for token availability. If False, return immediately.

        Returns:
            True if request can proceed, False if rate limited (when wait=False)
        """
        async with self._lock:
            # Refill tokens
            await self._refill_tokens()

            # Reset time windows if needed
            self._reset_windows()

            # Check all rate limits
            if not self._can_make_request():
                if not wait:
                    return False

                # Calculate wait time
                wait_time = self._calculate_wait_time()
                logger.info(f"Rate limited. Waiting {wait_time:.2f} seconds...")

                # Wait outside the lock
                async with self._lock:
                    pass

                await asyncio.sleep(wait_time)

                # Try again after waiting
                return await self.acquire(wait=True)

            # Consume token and increment counters
            self._tokens -= 1
            self._requests_this_minute += 1
            self._requests_this_hour += 1
            self._requests_this_day += 1

            return True

    async def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = datetime.utcnow()
        elapsed = (now - self._last_refill).total_seconds()

        # Refill rate: requests_per_minute / 60 tokens per second
        refill_rate = self.config.requests_per_minute / 60.0
        tokens_to_add = int(elapsed * refill_rate)

        if tokens_to_add > 0:
            self._tokens = min(self._tokens + tokens_to_add, self.config.burst_size)
            self._last_refill = now

    def _reset_windows(self) -> None:
        """Reset time windows if they have expired."""
        now = datetime.utcnow()

        # Reset minute window
        if now >= self._minute_reset_at:
            self._requests_this_minute = 0
            self._minute_reset_at = now + timedelta(minutes=1)

        # Reset hour window
        if self.config.requests_per_hour and now >= self._hour_reset_at:
            self._requests_this_hour = 0
            self._hour_reset_at = now + timedelta(hours=1)

        # Reset day window
        if self.config.requests_per_day and now >= self._day_reset_at:
            self._requests_this_day = 0
            self._day_reset_at = now + timedelta(days=1)

    def _can_make_request(self) -> bool:
        """Check if a request can be made within all rate limits."""
        # Check token availability
        if self._tokens <= 0:
            return False

        # Check per-minute limit
        if self._requests_this_minute >= self.config.requests_per_minute:
            return False

        # Check per-hour limit
        if (
            self.config.requests_per_hour
            and self._requests_this_hour >= self.config.requests_per_hour
        ):
            return False

        # Check per-day limit
        if (
            self.config.requests_per_day
            and self._requests_this_day >= self.config.requests_per_day
        ):
            return False

        return True

    def _calculate_wait_time(self) -> float:
        """Calculate how long to wait before next request."""
        now = datetime.utcnow()
        wait_times = []

        # Wait for token refill
        if self._tokens <= 0:
            seconds_per_token = 60.0 / self.config.requests_per_minute
            wait_times.append(seconds_per_token)

        # Wait for minute window reset
        if self._requests_this_minute >= self.config.requests_per_minute:
            wait_times.append((self._minute_reset_at - now).total_seconds())

        # Wait for hour window reset
        if (
            self.config.requests_per_hour
            and self._requests_this_hour >= self.config.requests_per_hour
        ):
            wait_times.append((self._hour_reset_at - now).total_seconds())

        # Wait for day window reset
        if (
            self.config.requests_per_day
            and self._requests_this_day >= self.config.requests_per_day
        ):
            wait_times.append((self._day_reset_at - now).total_seconds())

        # Return minimum wait time (or default)
        return (
            max(min(wait_times), 0.1) if wait_times else self.config.retry_after_seconds
        )

    async def get_state(self) -> RateLimitState:
        """
        Get current rate limiter state.

        Returns:
            Current state snapshot
        """
        async with self._lock:
            await self._refill_tokens()
            self._reset_windows()

            return RateLimitState(
                tokens_available=self._tokens,
                last_refill=self._last_refill,
                requests_this_minute=self._requests_this_minute,
                requests_this_hour=self._requests_this_hour,
                requests_this_day=self._requests_this_day,
                minute_reset_at=self._minute_reset_at,
                hour_reset_at=self._hour_reset_at,
                day_reset_at=self._day_reset_at,
            )

    def reset(self) -> None:
        """Reset rate limiter state."""
        self._tokens = self.config.burst_size
        self._last_refill = datetime.utcnow()
        self._requests_this_minute = 0
        self._requests_this_hour = 0
        self._requests_this_day = 0
        self._minute_reset_at = datetime.utcnow() + timedelta(minutes=1)
        self._hour_reset_at = datetime.utcnow() + timedelta(hours=1)
        self._day_reset_at = datetime.utcnow() + timedelta(days=1)


# =============================================================================
# Platform-Specific Rate Limit Configurations
# =============================================================================

PLATFORM_RATE_LIMITS: Dict[str, RateLimitConfig] = {
    "gmail": RateLimitConfig(
        requests_per_minute=250,
        requests_per_day=1_000_000_000,  # 1 billion per day
        burst_size=50,
    ),
    "slack": RateLimitConfig(
        requests_per_minute=60,
        burst_size=20,
    ),
    "discord": RateLimitConfig(
        requests_per_minute=50,
        burst_size=10,
    ),
    "whatsapp": RateLimitConfig(
        requests_per_minute=80,
        requests_per_hour=1000,
        burst_size=20,
    ),
    "twitter": RateLimitConfig(
        requests_per_minute=15,
        requests_per_hour=180,
        burst_size=5,
    ),
    "telegram": RateLimitConfig(
        requests_per_minute=30,
        burst_size=10,
    ),
}


def get_rate_limiter(platform: str) -> RateLimiter:
    """
    Get a rate limiter for a specific platform.

    Args:
        platform: Platform name (gmail, slack, etc.)

    Returns:
        Configured RateLimiter instance
    """
    config = PLATFORM_RATE_LIMITS.get(
        platform.lower(), RateLimitConfig()  # Default config
    )
    return RateLimiter(config)


# =============================================================================
# Exponential Backoff Utility
# =============================================================================


class ExponentialBackoff:
    """
    Exponential backoff calculator for retry logic.

    Implements exponential backoff with jitter to prevent thundering herd.
    """

    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize exponential backoff.

        Args:
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential calculation
            jitter: Whether to add random jitter
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self._attempt = 0

    def calculate_delay(self, attempt: Optional[int] = None) -> float:
        """
        Calculate delay for a given attempt.

        Args:
            attempt: Retry attempt number (uses internal counter if None)

        Returns:
            Delay in seconds
        """
        if attempt is None:
            attempt = self._attempt
            self._attempt += 1

        # Calculate exponential delay
        delay = min(self.base_delay * (self.exponential_base**attempt), self.max_delay)

        # Add jitter if enabled
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)

        return delay

    def reset(self) -> None:
        """Reset attempt counter."""
        self._attempt = 0

    @property
    def attempt(self) -> int:
        """Get current attempt number."""
        return self._attempt


async def retry_with_backoff(
    func: Callable[..., Coroutine[Any, Any, Any]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
) -> Any:
    """
    Retry a function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback called on each retry

    Returns:
        Result of successful function call

    Raises:
        Last exception if all retries fail
    """
    backoff = ExponentialBackoff(
        base_delay=base_delay,
        max_delay=max_delay,
    )

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except exceptions as e:
            last_exception = e

            if attempt >= max_retries:
                logger.error(
                    f"All {max_retries} retry attempts failed: {e}", exc_info=True
                )
                raise

            delay = backoff.calculate_delay()

            logger.warning(
                f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                f"Retrying in {delay:.2f}s..."
            )

            if on_retry:
                on_retry(e, attempt, delay)

            await asyncio.sleep(delay)

    # Should never reach here, but just in case
    if last_exception:
        raise last_exception


# =============================================================================
# Request Queue Manager
# =============================================================================


class RequestQueue:
    """
    Queue manager for rate-limited requests.

    Manages a queue of pending requests with priority support.
    """

    def __init__(self, rate_limiter: RateLimiter):
        """
        Initialize request queue.

        Args:
            rate_limiter: Rate limiter to use for request throttling
        """
        self.rate_limiter = rate_limiter
        self._queue: deque = deque()
        self._processing = False
        self._lock = asyncio.Lock()

    async def enqueue(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        priority: int = 0,
    ) -> Any:
        """
        Enqueue a request for execution.

        Args:
            func: Async function to execute
            priority: Request priority (higher = more important)

        Returns:
            Result of function execution
        """
        # Create future for result
        future = asyncio.Future()

        # Add to queue with priority
        async with self._lock:
            self._queue.append((priority, func, future))
            # Sort by priority (descending)
            self._queue = deque(sorted(self._queue, key=lambda x: x[0], reverse=True))

        # Start processing if not already running
        if not self._processing:
            asyncio.create_task(self._process_queue())

        # Wait for result
        return await future

    async def _process_queue(self) -> None:
        """Process queued requests with rate limiting."""
        if self._processing:
            return

        self._processing = True

        try:
            while True:
                async with self._lock:
                    if not self._queue:
                        break

                    priority, func, future = self._queue.popleft()

                # Wait for rate limit
                await self.rate_limiter.acquire(wait=True)

                # Execute request
                try:
                    result = await func()
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)

        finally:
            self._processing = False

    def size(self) -> int:
        """Get current queue size."""
        return len(self._queue)

    def clear(self) -> None:
        """Clear all pending requests."""
        self._queue.clear()


# Export public API
__all__ = [
    "RateLimiter",
    "RateLimitConfig",
    "RateLimitState",
    "ExponentialBackoff",
    "RequestQueue",
    "retry_with_backoff",
    "get_rate_limiter",
    "PLATFORM_RATE_LIMITS",
]
