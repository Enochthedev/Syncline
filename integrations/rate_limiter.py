"""
Rate limiting utilities with exponential backoff and circuit breaker patterns.

This module provides rate limiting, exponential backoff, and circuit breaker
implementations for reliable API interactions.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, Optional
from collections import deque

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_second: float = 10.0
    burst_size: int = 20
    window_size_seconds: int = 60


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 60
    success_threshold: int = 3  # For half-open state
    timeout_seconds: float = 30.0


class RateLimiter:
    """
    Token bucket rate limiter with burst support.

    Implements a token bucket algorithm that allows for burst traffic
    while maintaining an average rate limit.
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._tokens = float(config.burst_size)
        self._last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens from the bucket, waiting if necessary."""
        async with self._lock:
            now = time.time()

            # Add tokens based on elapsed time
            elapsed = now - self._last_update
            self._tokens = min(
                self.config.burst_size,
                self._tokens + elapsed * self.config.requests_per_second
            )
            self._last_update = now

            # Wait if not enough tokens
            if self._tokens < tokens:
                wait_time = (tokens - self._tokens) / \
                    self.config.requests_per_second
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self._tokens = 0
            else:
                self._tokens -= tokens

    def available_tokens(self) -> float:
        """Get number of available tokens."""
        now = time.time()
        elapsed = now - self._last_update
        return min(
            self.config.burst_size,
            self._tokens + elapsed * self.config.requests_per_second
        )


class ExponentialBackoff:
    """
    Exponential backoff utility for retry logic.

    Implements exponential backoff with jitter to avoid thundering herd problems.
    """

    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: bool = True
    ):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self._attempt = 0

    def next_delay(self) -> float:
        """Calculate next delay with exponential backoff."""
        delay = min(
            self.initial_delay * (self.multiplier ** self._attempt),
            self.max_delay
        )

        if self.jitter:
            # Add jitter (±25% of delay)
            import random
            jitter_amount = delay * 0.25
            delay += random.uniform(-jitter_amount, jitter_amount)

        self._attempt += 1
        return max(0, delay)

    def reset(self) -> None:
        """Reset backoff state."""
        self._attempt = 0

    @property
    def attempt_count(self) -> int:
        """Get current attempt count."""
        return self._attempt


class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance.

    Prevents cascading failures by temporarily blocking requests
    when a service is failing consistently.
    """

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    async def can_execute(self) -> bool:
        """Check if request can be executed."""
        async with self._lock:
            if self._state == CircuitBreakerState.CLOSED:
                return True

            elif self._state == CircuitBreakerState.OPEN:
                # Check if recovery timeout has passed
                if (self._last_failure_time and
                    datetime.now(timezone.utc) - self._last_failure_time >=
                        timedelta(seconds=self.config.recovery_timeout_seconds)):
                    self._state = CircuitBreakerState.HALF_OPEN
                    self._success_count = 0
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                    return True
                return False

            elif self._state == CircuitBreakerState.HALF_OPEN:
                return True

            return False

    async def record_success(self) -> None:
        """Record a successful operation."""
        async with self._lock:
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitBreakerState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info("Circuit breaker transitioning to CLOSED")

            elif self._state == CircuitBreakerState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    async def record_failure(self) -> None:
        """Record a failed operation."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now(timezone.utc)

            if self._state == CircuitBreakerState.HALF_OPEN:
                self._state = CircuitBreakerState.OPEN
                logger.warning(
                    "Circuit breaker transitioning to OPEN from HALF_OPEN")

            elif (self._state == CircuitBreakerState.CLOSED and
                  self._failure_count >= self.config.failure_threshold):
                self._state = CircuitBreakerState.OPEN
                logger.warning(
                    f"Circuit breaker OPEN after {self._failure_count} failures")

    def get_stats(self) -> Dict[str, any]:
        """Get circuit breaker statistics."""
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None
        }


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts based on response times and errors.

    Automatically reduces rate when detecting high latency or errors,
    and gradually increases when service is healthy.
    """

    def __init__(
        self,
        initial_rate: float = 10.0,
        min_rate: float = 1.0,
        max_rate: float = 100.0,
        adjustment_factor: float = 0.1
    ):
        self.initial_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.adjustment_factor = adjustment_factor

        self._current_rate = initial_rate
        self._response_times = deque(maxlen=100)
        self._error_count = 0
        self._success_count = 0
        self._lock = asyncio.Lock()

        # Create underlying rate limiter
        self._rate_limiter = RateLimiter(RateLimitConfig(
            requests_per_second=self._current_rate,
            burst_size=int(self._current_rate * 2)
        ))

    async def acquire(self) -> None:
        """Acquire permission to make request."""
        await self._rate_limiter.acquire()

    async def record_response_time(self, response_time: float) -> None:
        """Record response time for adaptive adjustment."""
        async with self._lock:
            self._response_times.append(response_time)
            self._success_count += 1

            # Adjust rate based on performance
            await self._adjust_rate()

    async def record_error(self) -> None:
        """Record error for adaptive adjustment."""
        async with self._lock:
            self._error_count += 1

            # Reduce rate on errors
            new_rate = max(
                self.min_rate,
                self._current_rate * (1 - self.adjustment_factor * 2)
            )
            await self._update_rate(new_rate)

    async def _adjust_rate(self) -> None:
        """Adjust rate based on recent performance."""
        if len(self._response_times) < 10:
            return

        # Calculate average response time
        avg_response_time = sum(self._response_times) / \
            len(self._response_times)

        # Calculate error rate
        total_requests = self._success_count + self._error_count
        error_rate = self._error_count / total_requests if total_requests > 0 else 0

        # Adjust rate based on performance
        if avg_response_time > 2.0 or error_rate > 0.1:  # High latency or errors
            new_rate = max(
                self.min_rate,
                self._current_rate * (1 - self.adjustment_factor)
            )
        elif avg_response_time < 0.5 and error_rate < 0.01:  # Good performance
            new_rate = min(
                self.max_rate,
                self._current_rate * (1 + self.adjustment_factor)
            )
        else:
            return  # No adjustment needed

        await self._update_rate(new_rate)

    async def _update_rate(self, new_rate: float) -> None:
        """Update the underlying rate limiter."""
        if abs(new_rate - self._current_rate) > 0.1:  # Only update if significant change
            self._current_rate = new_rate
            self._rate_limiter = RateLimiter(RateLimitConfig(
                requests_per_second=new_rate,
                burst_size=int(new_rate * 2)
            ))
            logger.debug(f"Adjusted rate limit to {new_rate:.2f} req/s")

    @property
    def current_rate(self) -> float:
        """Get current rate limit."""
        return self._current_rate

    def get_stats(self) -> Dict[str, any]:
        """Get rate limiter statistics."""
        avg_response_time = (
            sum(self._response_times) / len(self._response_times)
            if self._response_times else 0
        )

        total_requests = self._success_count + self._error_count
        error_rate = self._error_count / total_requests if total_requests > 0 else 0

        return {
            "current_rate": self._current_rate,
            "avg_response_time": avg_response_time,
            "error_rate": error_rate,
            "total_requests": total_requests,
            "available_tokens": self._rate_limiter.available_tokens()
        }
