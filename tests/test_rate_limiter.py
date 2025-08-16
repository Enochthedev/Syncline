"""
Unit tests for rate limiting utilities.

Tests rate limiting, exponential backoff, and circuit breaker
implementations for reliable API interactions.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from integrations.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    ExponentialBackoff,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    AdaptiveRateLimiter
)


class TestRateLimitConfig:
    """Test RateLimitConfig data class."""

    def test_rate_limit_config_creation(self):
        """Test RateLimitConfig creation."""
        config = RateLimitConfig(
            requests_per_second=5.0,
            burst_size=10,
            window_size_seconds=30
        )

        assert config.requests_per_second == 5.0
        assert config.burst_size == 10
        assert config.window_size_seconds == 30

    def test_rate_limit_config_defaults(self):
        """Test RateLimitConfig with default values."""
        config = RateLimitConfig()

        assert config.requests_per_second == 10.0
        assert config.burst_size == 20
        assert config.window_size_seconds == 60


class TestRateLimiter:
    """Test RateLimiter functionality."""

    @pytest.fixture
    def rate_limiter(self):
        """Rate limiter fixture with fast rate for testing."""
        config = RateLimitConfig(
            requests_per_second=10.0,
            burst_size=5
        )
        return RateLimiter(config)

    @pytest.mark.asyncio
    async def test_acquire_within_burst(self, rate_limiter):
        """Test acquiring tokens within burst limit."""
        start_time = time.time()

        # Should be able to acquire burst_size tokens immediately
        for _ in range(5):
            await rate_limiter.acquire()

        elapsed = time.time() - start_time
        # Should complete quickly (within burst)
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_acquire_exceeds_burst(self, rate_limiter):
        """Test acquiring tokens beyond burst limit."""
        # Exhaust burst tokens
        for _ in range(5):
            await rate_limiter.acquire()

        start_time = time.time()
        # This should wait for token refill
        await rate_limiter.acquire()
        elapsed = time.time() - start_time

        # Should have waited approximately 1/rate seconds
        assert elapsed >= 0.08  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens(self, rate_limiter):
        """Test acquiring multiple tokens at once."""
        start_time = time.time()
        await rate_limiter.acquire(3)
        elapsed = time.time() - start_time

        # Should complete quickly within burst
        assert elapsed < 0.1

        # Available tokens should be reduced (allow for small timing variations)
        available = rate_limiter.available_tokens()
        assert available <= 2.1  # Allow small tolerance for timing

    def test_available_tokens(self, rate_limiter):
        """Test available tokens calculation."""
        # Initially should have burst_size tokens
        available = rate_limiter.available_tokens()
        assert available == 5

    def test_token_refill(self, rate_limiter):
        """Test token bucket refill over time."""
        # Exhaust all tokens
        initial_available = rate_limiter.available_tokens()
        rate_limiter._tokens = 0
        rate_limiter._last_update = time.time() - 1.0  # 1 second ago

        # Check refill
        available = rate_limiter.available_tokens()
        # Should have refilled at rate (10 tokens/sec for 1 sec = 10 tokens)
        # But capped at burst_size (5)
        assert available == 5


class TestExponentialBackoff:
    """Test ExponentialBackoff functionality."""

    def test_exponential_backoff_creation(self):
        """Test ExponentialBackoff creation."""
        backoff = ExponentialBackoff(
            initial_delay=2.0,
            max_delay=120.0,
            multiplier=3.0,
            jitter=False
        )

        assert backoff.initial_delay == 2.0
        assert backoff.max_delay == 120.0
        assert backoff.multiplier == 3.0
        assert backoff.jitter is False
        assert backoff.attempt_count == 0

    def test_exponential_backoff_defaults(self):
        """Test ExponentialBackoff with default values."""
        backoff = ExponentialBackoff()

        assert backoff.initial_delay == 1.0
        assert backoff.max_delay == 60.0
        assert backoff.multiplier == 2.0
        assert backoff.jitter is True

    def test_next_delay_progression(self):
        """Test exponential delay progression."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            multiplier=2.0,
            jitter=False
        )

        # First attempt
        delay1 = backoff.next_delay()
        assert delay1 == 1.0
        assert backoff.attempt_count == 1

        # Second attempt
        delay2 = backoff.next_delay()
        assert delay2 == 2.0
        assert backoff.attempt_count == 2

        # Third attempt
        delay3 = backoff.next_delay()
        assert delay3 == 4.0
        assert backoff.attempt_count == 3

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        backoff = ExponentialBackoff(
            initial_delay=10.0,
            max_delay=15.0,
            multiplier=2.0,
            jitter=False
        )

        delay1 = backoff.next_delay()  # 10.0
        delay2 = backoff.next_delay()  # 15.0 (capped)
        delay3 = backoff.next_delay()  # 15.0 (capped)

        assert delay1 == 10.0
        assert delay2 == 15.0
        assert delay3 == 15.0

    def test_jitter(self):
        """Test jitter functionality."""
        backoff = ExponentialBackoff(
            initial_delay=10.0,
            jitter=True
        )

        delays = [backoff.next_delay() for _ in range(10)]

        # With jitter, delays should vary
        assert len(set(delays)) > 1  # Should have different values
        # All delays should be positive
        assert all(delay >= 0 for delay in delays)

    def test_reset(self):
        """Test backoff reset."""
        backoff = ExponentialBackoff(
            jitter=False)  # Disable jitter for predictable test

        # Make some attempts
        backoff.next_delay()
        backoff.next_delay()
        assert backoff.attempt_count == 2

        # Reset
        backoff.reset()
        assert backoff.attempt_count == 0

        # Next delay should be initial delay
        delay = backoff.next_delay()
        assert delay == 1.0


class TestCircuitBreakerConfig:
    """Test CircuitBreakerConfig data class."""

    def test_circuit_breaker_config_creation(self):
        """Test CircuitBreakerConfig creation."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout_seconds=30,
            success_threshold=2,
            timeout_seconds=10.0
        )

        assert config.failure_threshold == 3
        assert config.recovery_timeout_seconds == 30
        assert config.success_threshold == 2
        assert config.timeout_seconds == 10.0

    def test_circuit_breaker_config_defaults(self):
        """Test CircuitBreakerConfig with default values."""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.recovery_timeout_seconds == 60
        assert config.success_threshold == 3
        assert config.timeout_seconds == 30.0


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""

    @pytest.fixture
    def circuit_breaker(self):
        """Circuit breaker fixture with low thresholds for testing."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout_seconds=1,
            success_threshold=2
        )
        return CircuitBreaker(config)

    def test_circuit_breaker_initial_state(self, circuit_breaker):
        """Test circuit breaker initial state."""
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_can_execute_closed(self, circuit_breaker):
        """Test can_execute when circuit is closed."""
        can_execute = await circuit_breaker.can_execute()
        assert can_execute is True

    @pytest.mark.asyncio
    async def test_record_success_closed(self, circuit_breaker):
        """Test recording success when circuit is closed."""
        # Record some failures first
        await circuit_breaker.record_failure()
        assert circuit_breaker.failure_count == 1

        # Record success should reset failure count
        await circuit_breaker.record_success()
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_record_failure_opens_circuit(self, circuit_breaker):
        """Test that failures open the circuit."""
        # Record failures up to threshold
        await circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

        await circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        assert circuit_breaker.failure_count == 2

    @pytest.mark.asyncio
    async def test_can_execute_open(self, circuit_breaker):
        """Test can_execute when circuit is open."""
        # Open the circuit
        await circuit_breaker.record_failure()
        await circuit_breaker.record_failure()

        can_execute = await circuit_breaker.can_execute()
        assert can_execute is False

    @pytest.mark.asyncio
    async def test_recovery_timeout(self, circuit_breaker):
        """Test recovery timeout functionality."""
        # Open the circuit
        await circuit_breaker.record_failure()
        await circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Should transition to half-open
        can_execute = await circuit_breaker.can_execute()
        assert can_execute is True
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self, circuit_breaker):
        """Test that successes in half-open state close the circuit."""
        # Open the circuit and wait for recovery
        await circuit_breaker.record_failure()
        await circuit_breaker.record_failure()
        await asyncio.sleep(1.1)
        await circuit_breaker.can_execute()  # Transition to half-open

        # Record enough successes to close
        await circuit_breaker.record_success()
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

        await circuit_breaker.record_success()
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_failure_opens_circuit(self, circuit_breaker):
        """Test that failure in half-open state opens the circuit."""
        # Open the circuit and wait for recovery
        await circuit_breaker.record_failure()
        await circuit_breaker.record_failure()
        await asyncio.sleep(1.1)
        await circuit_breaker.can_execute()  # Transition to half-open

        # Record failure should open circuit again
        await circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitBreakerState.OPEN

    def test_get_stats(self, circuit_breaker):
        """Test getting circuit breaker statistics."""
        stats = circuit_breaker.get_stats()

        assert "state" in stats
        assert "failure_count" in stats
        assert "success_count" in stats
        assert "last_failure_time" in stats

        assert stats["state"] == CircuitBreakerState.CLOSED.value
        assert stats["failure_count"] == 0
        assert stats["success_count"] == 0
        assert stats["last_failure_time"] is None


class TestAdaptiveRateLimiter:
    """Test AdaptiveRateLimiter functionality."""

    @pytest.fixture
    def adaptive_limiter(self):
        """Adaptive rate limiter fixture."""
        return AdaptiveRateLimiter(
            initial_rate=10.0,
            min_rate=1.0,
            max_rate=50.0,
            adjustment_factor=0.2
        )

    def test_adaptive_rate_limiter_creation(self, adaptive_limiter):
        """Test AdaptiveRateLimiter creation."""
        assert adaptive_limiter.initial_rate == 10.0
        assert adaptive_limiter.min_rate == 1.0
        assert adaptive_limiter.max_rate == 50.0
        assert adaptive_limiter.adjustment_factor == 0.2
        assert adaptive_limiter.current_rate == 10.0

    @pytest.mark.asyncio
    async def test_acquire(self, adaptive_limiter):
        """Test basic acquire functionality."""
        start_time = time.time()
        await adaptive_limiter.acquire()
        elapsed = time.time() - start_time

        # Should complete quickly
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_record_response_time_good_performance(self, adaptive_limiter):
        """Test recording good response times."""
        initial_rate = adaptive_limiter.current_rate

        # Record good response times
        for _ in range(15):  # Need enough samples
            await adaptive_limiter.record_response_time(0.1)  # Fast response

        # Rate should increase or stay the same
        assert adaptive_limiter.current_rate >= initial_rate

    @pytest.mark.asyncio
    async def test_record_response_time_poor_performance(self, adaptive_limiter):
        """Test recording poor response times."""
        initial_rate = adaptive_limiter.current_rate

        # Record poor response times
        for _ in range(15):  # Need enough samples
            await adaptive_limiter.record_response_time(3.0)  # Slow response

        # Rate should decrease
        assert adaptive_limiter.current_rate < initial_rate

    @pytest.mark.asyncio
    async def test_record_error(self, adaptive_limiter):
        """Test recording errors."""
        initial_rate = adaptive_limiter.current_rate

        await adaptive_limiter.record_error()

        # Rate should decrease after error
        assert adaptive_limiter.current_rate < initial_rate

    @pytest.mark.asyncio
    async def test_rate_bounds(self, adaptive_limiter):
        """Test that rate stays within bounds."""
        # Record many errors to try to go below min
        for _ in range(10):
            await adaptive_limiter.record_error()

        assert adaptive_limiter.current_rate >= adaptive_limiter.min_rate

        # Reset and record many good responses to try to go above max
        adaptive_limiter._current_rate = adaptive_limiter.initial_rate
        adaptive_limiter._error_count = 0
        adaptive_limiter._success_count = 0

        for _ in range(20):
            await adaptive_limiter.record_response_time(0.01)

        assert adaptive_limiter.current_rate <= adaptive_limiter.max_rate

    def test_get_stats(self, adaptive_limiter):
        """Test getting adaptive rate limiter statistics."""
        stats = adaptive_limiter.get_stats()

        assert "current_rate" in stats
        assert "avg_response_time" in stats
        assert "error_rate" in stats
        assert "total_requests" in stats
        assert "available_tokens" in stats

        assert stats["current_rate"] == 10.0
        assert stats["avg_response_time"] == 0
        assert stats["error_rate"] == 0
        assert stats["total_requests"] == 0


if __name__ == "__main__":
    pytest.main([__file__])
