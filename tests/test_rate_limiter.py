"""
Unit tests for rate limiting utilities.

Tests rate limiter, exponential backoff, circuit breaker,
and adaptive rate limiting functionality.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch

from integrations.rate_limiter import (
    RateLimiter,
    CircuitBreaker,
    ExponentialBackoff,
    AdaptiveRateLimiter,
    RateLimitConfig,
    CircuitBreakerConfig,
    CircuitBreakerState
)


class TestRateLimitConfig:
    """Test RateLimitConfig data class."""

    def test_default_config(self):
        """Test default rate limit configuration."""
        config = RateLimitConfig()

        assert config.requests_per_second == 10.0
        assert config.burst_size == 20
        assert config.window_size_seconds == 60

    def test_custom_config(self):
        """Test custom rate limit configuration."""
        config = RateLimitConfig(
            requests_per_second=5.0,
            burst_size=10,
            window_size_seconds=30
        )

        assert config.requests_per_second == 5.0
        assert config.burst_size == 10
        assert config.window_size_seconds == 30


class TestCircuitBreakerConfig:
    """Test CircuitBreakerConfig data class."""

    def test_default_config(self):
        """Test default circuit breaker configuration."""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.recovery_timeout_seconds == 60
        assert config.success_threshold == 3
        assert config.timeout_seconds == 30.0

    def test_custom_config(self):
        """Test custom circuit breaker configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout_seconds=30,
            success_threshold=2,
            timeout_seconds=15.0
        )

        assert config.failure_threshold == 3
        assert config.recovery_timeout_seconds == 30
        assert config.success_threshold == 2
        assert config.timeout_seconds == 15.0


class TestRateLimiter:
    """Test RateLimiter functionality."""

    @pytest.fixture
    def rate_limiter(self):
        """Rate limiter fixture."""
        config = RateLimitConfig(requests_per_second=10.0, burst_size=5)
        return RateLimiter(config)

    @pytest.mark.asyncio
    async def test_acquire_tokens_available(self, rate_limiter):
        """Test acquiring tokens when available."""
        # Should not block when tokens are available
        start_time = time.time()
        await rate_limiter.acquire(1)
        elapsed = time.time() - start_time

        assert elapsed < 0.1  # Should be nearly instantaneous

    @pytest.mark.asyncio
    async def test_acquire_tokens_burst(self, rate_limiter):
        """Test burst token acquisition."""
        # Should be able to acquire burst_size tokens quickly
        start_time = time.time()
        for _ in range(5):  # burst_size = 5
            await rate_limiter.acquire(1)
        elapsed = time.time() - start_time

        assert elapsed < 0.1  # Should be nearly instantaneous

    @pytest.mark.asyncio
    async def test_acquire_tokens_rate_limited(self, rate_limiter):
        """Test rate limiting when tokens exhausted."""
        # Exhaust burst tokens
        for _ in range(5):
            await rate_limiter.acquire(1)

        # Next acquisition should be rate limited
        start_time = time.time()
        await rate_limiter.acquire(1)
        elapsed = time.time() - start_time

        # Should wait approximately 1/10 second (10 req/s)
        assert 0.08 <= elapsed <= 0.15

    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens(self, rate_limiter):
        """Test acquiring multiple tokens at once."""
        start_time = time.time()
        await rate_limiter.acquire(3)
        elapsed = time.time() - start_time

        assert elapsed < 0.1  # Should be nearly instantaneous

    def test_available_tokens(self, rate_limiter):
        """Test available tokens calculation."""
        # Initially should have burst_size tokens
        available = rate_limiter.available_tokens()
        assert available == 5.0  # burst_size

    def test_available_tokens_after_time(self, rate_limiter):
        """Test available tokens after time passes."""
        # Consume all tokens
        rate_limiter._tokens = 0
        rate_limiter._last_update = time.time() - 1.0  # 1 second ago

        # Should have regenerated tokens
        available = rate_limiter.available_tokens()
        assert available == 5.0  # min(burst_size, 0 + 1.0 * 10.0) = 5.0


class TestExponentialBackoff:
    """Test ExponentialBackoff functionality."""

    def test_default_backoff(self):
        """Test default exponential backoff."""
        backoff = ExponentialBackoff()

        assert backoff.initial_delay == 1.0
        assert backoff.max_delay == 60.0
        assert backoff.multiplier == 2.0
        assert backoff.jitter is True
        assert backoff.attempt_count == 0

    def test_backoff_progression(self):
        """Test exponential backoff progression."""
        backoff = ExponentialBackoff(
            initial_delay=1.0, multiplier=2.0, jitter=False)

        delays = []
        for _ in range(5):
            delays.append(backoff.next_delay())

        # Should be: 1, 2, 4, 8, 16
        expected = [1.0, 2.0, 4.0, 8.0, 16.0]
        assert delays == expected

    def test_backoff_max_delay(self):
        """Test maximum delay limit."""
        backoff = ExponentialBackoff(
            initial_delay=10.0, max_delay=20.0, jitter=False)

        # Should cap at max_delay
        for _ in range(5):
            delay = backoff.next_delay()
            assert delay <= 20.0

    def test_backoff_with_jitter(self):
        """Test backoff with jitter."""
        backoff = ExponentialBackoff(initial_delay=4.0, jitter=True)

        delays = []
        for _ in range(10):
            delays.append(backoff.next_delay())

        # With jitter, delays should vary
        assert len(set(delays)) > 1  # Should have different values

    def test_backoff_reset(self):
        """Test backoff reset."""
        backoff = ExponentialBackoff()

        # Advance attempts
        backoff.next_delay()
        backoff.next_delay()
        assert backoff.attempt_count == 2

        # Reset
        backoff.reset()
        assert backoff.attempt_count == 0


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""

    @pytest.fixture
    def circuit_breaker(self):
        """Circuit breaker fixture."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout_seconds=1,  # Short timeout for testing
            success_threshold=2
        )
        return CircuitBreaker(config)

    @pytest.mark.asyncio
    async def test_initial_state_closed(self, circuit_breaker):
        """Test initial circuit breaker state."""
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert await circuit_breaker.can_execute() is True

    @pytest.mark.asyncio
    async def test_record_success_closed(self, circuit_breaker):
        """Test recording success in closed state."""
        await circuit_breaker.record_success()

        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_record_failure_closed(self, circuit_breaker):
        """Test recording failures in closed state."""
        # Record failures below threshold
        for _ in range(2):
            await circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 2

    @pytest.mark.asyncio
    async def test_transition_to_open(self, circuit_breaker):
        """Test transition from closed to open."""
        # Record failures to exceed threshold
        for _ in range(3):
            await circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitBreakerState.OPEN
        assert circuit_breaker.failure_count == 3
        assert await circuit_breaker.can_execute() is False

    @pytest.mark.asyncio
    async def test_transition_to_half_open(self, circuit_breaker):
        """Test transition from open to half-open."""
        # Trigger open state
        for _ in range(3):
            await circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Should transition to half-open
        assert await circuit_breaker.can_execute() is True
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_to_closed(self, circuit_breaker):
        """Test transition from half-open to closed."""
        # Get to half-open state
        for _ in range(3):
            await circuit_breaker.record_failure()
        await asyncio.sleep(1.1)
        await circuit_breaker.can_execute()  # Transition to half-open

        # Record enough successes
        for _ in range(2):  # success_threshold = 2
            await circuit_breaker.record_success()

        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_to_open(self, circuit_breaker):
        """Test transition from half-open back to open."""
        # Get to half-open state
        for _ in range(3):
            await circuit_breaker.record_failure()
        await asyncio.sleep(1.1)
        await circuit_breaker.can_execute()  # Transition to half-open

        # Record failure in half-open state
        await circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitBreakerState.OPEN

    def test_get_stats(self, circuit_breaker):
        """Test circuit breaker statistics."""
        stats = circuit_breaker.get_stats()

        assert "state" in stats
        assert "failure_count" in stats
        assert "success_count" in stats
        assert "last_failure_time" in stats

        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0
        assert stats["success_count"] == 0


class TestAdaptiveRateLimiter:
    """Test AdaptiveRateLimiter functionality."""

    @pytest.fixture
    def adaptive_limiter(self):
        """Adaptive rate limiter fixture."""
        return AdaptiveRateLimiter(
            initial_rate=10.0,
            min_rate=1.0,
            max_rate=20.0,
            adjustment_factor=0.2
        )

    @pytest.mark.asyncio
    async def test_initial_rate(self, adaptive_limiter):
        """Test initial rate setting."""
        assert adaptive_limiter.current_rate == 10.0

    @pytest.mark.asyncio
    async def test_acquire(self, adaptive_limiter):
        """Test token acquisition."""
        # Should not raise exception
        await adaptive_limiter.acquire()

    @pytest.mark.asyncio
    async def test_record_response_time_good(self, adaptive_limiter):
        """Test recording good response times."""
        initial_rate = adaptive_limiter.current_rate

        # Record good response times
        for _ in range(15):  # Need enough samples
            await adaptive_limiter.record_response_time(0.1)  # Fast response

        # Rate should increase or stay same
        assert adaptive_limiter.current_rate >= initial_rate

    @pytest.mark.asyncio
    async def test_record_response_time_slow(self, adaptive_limiter):
        """Test recording slow response times."""
        initial_rate = adaptive_limiter.current_rate

        # Record slow response times
        for _ in range(15):  # Need enough samples
            await adaptive_limiter.record_response_time(3.0)  # Slow response

        # Rate should decrease
        assert adaptive_limiter.current_rate < initial_rate

    @pytest.mark.asyncio
    async def test_record_error(self, adaptive_limiter):
        """Test recording errors."""
        initial_rate = adaptive_limiter.current_rate

        await adaptive_limiter.record_error()

        # Rate should decrease
        assert adaptive_limiter.current_rate < initial_rate

    @pytest.mark.asyncio
    async def test_rate_bounds(self, adaptive_limiter):
        """Test rate limiting bounds."""
        # Record many errors to try to go below min_rate
        for _ in range(10):
            await adaptive_limiter.record_error()

        assert adaptive_limiter.current_rate >= adaptive_limiter.min_rate

        # Reset and record many good responses to try to exceed max_rate
        adaptive_limiter._current_rate = adaptive_limiter.max_rate - 1
        for _ in range(20):
            await adaptive_limiter.record_response_time(0.1)

        assert adaptive_limiter.current_rate <= adaptive_limiter.max_rate

    def test_get_stats(self, adaptive_limiter):
        """Test adaptive rate limiter statistics."""
        stats = adaptive_limiter.get_stats()

        assert "current_rate" in stats
        assert "avg_response_time" in stats
        assert "error_rate" in stats
        assert "total_requests" in stats
        assert "available_tokens" in stats

        assert stats["current_rate"] == 10.0
        assert stats["total_requests"] == 0


if __name__ == "__main__":
    pytest.main([__file__])
