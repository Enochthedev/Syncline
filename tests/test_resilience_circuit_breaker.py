"""
Tests for Circuit Breaker implementation.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock

from services.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    CircuitBreakerError,
    CircuitBreakerTimeoutError,
    CircuitBreakerManager
)


@pytest.fixture
def circuit_breaker_config():
    """Circuit breaker configuration for testing."""
    return CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout_seconds=1,
        success_threshold=2,
        timeout_seconds=1.0
    )


@pytest.fixture
def circuit_breaker(circuit_breaker_config):
    """Circuit breaker instance for testing."""
    return CircuitBreaker(circuit_breaker_config, "test")


@pytest.mark.asyncio
async def test_circuit_breaker_closed_state(circuit_breaker):
    """Test circuit breaker in closed state."""
    assert circuit_breaker.state == CircuitBreakerState.CLOSED

    # Should allow execution
    result = await circuit_breaker.call(lambda: "success")
    assert result == "success"


@pytest.mark.asyncio
async def test_circuit_breaker_failure_threshold(circuit_breaker):
    """Test circuit breaker opening after failure threshold."""
    # Cause failures to reach threshold
    for i in range(3):
        with pytest.raises(ValueError):
            await circuit_breaker.call(lambda: exec('raise ValueError("test error")'))

    # Circuit breaker should now be open
    assert circuit_breaker.state == CircuitBreakerState.OPEN

    # Should block further requests
    with pytest.raises(CircuitBreakerError):
        await circuit_breaker.call(lambda: "should not execute")


@pytest.mark.asyncio
async def test_circuit_breaker_recovery(circuit_breaker):
    """Test circuit breaker recovery to closed state."""
    # Force circuit breaker to open
    for i in range(3):
        with pytest.raises(ValueError):
            await circuit_breaker.call(lambda: exec('raise ValueError("test error")'))

    assert circuit_breaker.state == CircuitBreakerState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(1.1)

    # Should transition to half-open and allow one request
    result = await circuit_breaker.call(lambda: "success")
    assert result == "success"
    assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

    # Another success should close the circuit
    result = await circuit_breaker.call(lambda: "success")
    assert result == "success"
    assert circuit_breaker.state == CircuitBreakerState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_failure(circuit_breaker):
    """Test circuit breaker failure in half-open state."""
    # Force to open state
    for i in range(3):
        with pytest.raises(ValueError):
            await circuit_breaker.call(lambda: exec('raise ValueError("test error")'))

    # Wait for recovery
    await asyncio.sleep(1.1)

    # Fail in half-open state
    with pytest.raises(ValueError):
        await circuit_breaker.call(lambda: exec('raise ValueError("test error")'))

    # Should go back to open
    assert circuit_breaker.state == CircuitBreakerState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_timeout():
    """Test circuit breaker timeout functionality."""
    config = CircuitBreakerConfig(timeout_seconds=0.1)
    cb = CircuitBreaker(config, "timeout_test")

    async def slow_function():
        await asyncio.sleep(0.2)
        return "should timeout"

    with pytest.raises(CircuitBreakerTimeoutError):
        await cb.call(slow_function)


@pytest.mark.asyncio
async def test_circuit_breaker_async_function(circuit_breaker):
    """Test circuit breaker with async functions."""
    async def async_success():
        return "async success"

    result = await circuit_breaker.call(async_success)
    assert result == "async success"

    async def async_failure():
        raise ValueError("async error")

    with pytest.raises(ValueError):
        await circuit_breaker.call(async_failure)


@pytest.mark.asyncio
async def test_circuit_breaker_sync_function(circuit_breaker):
    """Test circuit breaker with sync functions."""
    def sync_success():
        return "sync success"

    result = await circuit_breaker.call(sync_success)
    assert result == "sync success"

    def sync_failure():
        raise ValueError("sync error")

    with pytest.raises(ValueError):
        await circuit_breaker.call(sync_failure)


@pytest.mark.asyncio
async def test_circuit_breaker_ignored_exceptions():
    """Test circuit breaker with ignored exceptions."""
    config = CircuitBreakerConfig(
        failure_threshold=2,
        ignore_exception_types=(KeyError,)
    )
    cb = CircuitBreaker(config, "ignore_test")

    # KeyError should be ignored
    result = await cb.call(lambda: exec('raise KeyError("ignored")') or None)
    assert result is None
    assert cb.failure_count == 0

    # ValueError should count as failure
    with pytest.raises(ValueError):
        await cb.call(lambda: exec('raise ValueError("counted")'))
    assert cb.failure_count == 1


@pytest.mark.asyncio
async def test_circuit_breaker_stats(circuit_breaker):
    """Test circuit breaker statistics."""
    # Execute some operations
    await circuit_breaker.call(lambda: "success")

    try:
        await circuit_breaker.call(lambda: exec('raise ValueError("error")'))
    except ValueError:
        pass

    stats = circuit_breaker.get_stats()

    assert stats.state == CircuitBreakerState.CLOSED
    assert stats.total_requests == 2
    assert stats.total_successes == 1
    assert stats.total_failures == 1
    assert stats.failure_rate == 0.5


@pytest.mark.asyncio
async def test_circuit_breaker_reset(circuit_breaker):
    """Test circuit breaker manual reset."""
    # Force to open state
    for i in range(3):
        with pytest.raises(ValueError):
            await circuit_breaker.call(lambda: exec('raise ValueError("test error")'))

    assert circuit_breaker.state == CircuitBreakerState.OPEN

    # Reset manually
    await circuit_breaker.reset()
    assert circuit_breaker.state == CircuitBreakerState.CLOSED
    assert circuit_breaker.failure_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_force_open(circuit_breaker):
    """Test circuit breaker manual force open."""
    assert circuit_breaker.state == CircuitBreakerState.CLOSED

    await circuit_breaker.force_open()
    assert circuit_breaker.state == CircuitBreakerState.OPEN

    # Should block requests
    with pytest.raises(CircuitBreakerError):
        await circuit_breaker.call(lambda: "should not execute")


@pytest.mark.asyncio
async def test_circuit_breaker_manager():
    """Test circuit breaker manager."""
    manager = CircuitBreakerManager()

    # Get circuit breaker
    cb1 = await manager.get_circuit_breaker("test1")
    assert cb1.name == "test1"

    # Get same circuit breaker again
    cb2 = await manager.get_circuit_breaker("test1")
    assert cb1 is cb2

    # Get different circuit breaker
    cb3 = await manager.get_circuit_breaker("test2")
    assert cb3.name == "test2"
    assert cb3 is not cb1

    # List circuit breakers
    names = manager.list_circuit_breakers()
    assert "test1" in names
    assert "test2" in names

    # Remove circuit breaker
    removed = await manager.remove_circuit_breaker("test1")
    assert removed is True

    names = manager.list_circuit_breakers()
    assert "test1" not in names
    assert "test2" in names


@pytest.mark.asyncio
async def test_circuit_breaker_decorator():
    """Test circuit breaker decorator."""
    from services.resilience.circuit_breaker import circuit_breaker

    config = CircuitBreakerConfig(failure_threshold=2)

    @circuit_breaker("decorator_test", config)
    async def test_function(should_fail=False):
        if should_fail:
            raise ValueError("test error")
        return "success"

    # Should work normally
    result = await test_function()
    assert result == "success"

    # Cause failures
    for i in range(2):
        with pytest.raises(ValueError):
            await test_function(should_fail=True)

    # Should be blocked by circuit breaker
    with pytest.raises(CircuitBreakerError):
        await test_function()


@pytest.mark.asyncio
async def test_circuit_breaker_context_manager():
    """Test circuit breaker context manager."""
    from services.resilience.circuit_breaker import circuit_breaker_context

    config = CircuitBreakerConfig(failure_threshold=2)

    async with circuit_breaker_context("context_test", config) as cb:
        result = await cb.call(lambda: "success")
        assert result == "success"

        # Test failure
        with pytest.raises(ValueError):
            await cb.call(lambda: exec('raise ValueError("error")'))


@pytest.mark.asyncio
async def test_circuit_breaker_concurrent_access():
    """Test circuit breaker with concurrent access."""
    config = CircuitBreakerConfig(failure_threshold=5)
    cb = CircuitBreaker(config, "concurrent_test")

    async def worker(worker_id):
        try:
            return await cb.call(lambda: f"worker_{worker_id}")
        except Exception:
            return None

    # Run multiple workers concurrently
    tasks = [worker(i) for i in range(10)]
    results = await asyncio.gather(*tasks)

    # All should succeed
    assert all(result is not None for result in results)
    assert len(set(results)) == 10  # All unique results
