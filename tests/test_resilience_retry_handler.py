"""
Tests for Retry Handler implementation.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock

from services.resilience.retry_handler import (
    RetryHandler,
    RetryConfig,
    RetryPolicy,
    JitterType,
    RetryError,
    MaxAttemptsExceededError,
    RetryTimeoutError,
    RetryManager,
    NETWORK_RETRY_CONFIG
)


@pytest.fixture
def retry_config():
    """Retry configuration for testing."""
    return RetryConfig(
        max_attempts=3,
        initial_delay=0.1,
        max_delay=1.0,
        multiplier=2.0,
        jitter_type=JitterType.NONE,  # No jitter for predictable tests
        policy=RetryPolicy.EXPONENTIAL_BACKOFF
    )


@pytest.fixture
def retry_handler(retry_config):
    """Retry handler instance for testing."""
    return RetryHandler(retry_config, "test")


@pytest.mark.asyncio
async def test_retry_handler_success_first_attempt(retry_handler):
    """Test successful execution on first attempt."""
    async def success_func():
        return "success"

    result = await retry_handler.execute(success_func)
    assert result == "success"

    stats = retry_handler.get_stats()
    assert stats.total_attempts == 1
    assert stats.successful_attempts == 1
    assert stats.failed_attempts == 0


@pytest.mark.asyncio
async def test_retry_handler_success_after_retries(retry_handler):
    """Test successful execution after retries."""
    call_count = 0

    async def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError(f"Attempt {call_count} failed")
        return "success"

    result = await retry_handler.execute(flaky_func)
    assert result == "success"
    assert call_count == 3

    stats = retry_handler.get_stats()
    assert stats.total_attempts == 3
    assert stats.successful_attempts == 1


@pytest.mark.asyncio
async def test_retry_handler_max_attempts_exceeded(retry_handler):
    """Test max attempts exceeded."""
    async def always_fail():
        raise ValueError("Always fails")

    with pytest.raises(MaxAttemptsExceededError) as exc_info:
        await retry_handler.execute(always_fail)

    assert exc_info.value.attempts == 3
    assert isinstance(exc_info.value.last_exception, ValueError)

    stats = retry_handler.get_stats()
    assert stats.total_attempts == 3
    assert stats.failed_attempts == 1


@pytest.mark.asyncio
async def test_retry_handler_non_retryable_exception():
    """Test non-retryable exceptions."""
    config = RetryConfig(
        max_attempts=3,
        retryable_exceptions=(ValueError,),
        non_retryable_exceptions=(KeyError,)
    )
    handler = RetryHandler(config, "test")

    async def non_retryable_error():
        raise KeyError("Non-retryable")

    # Should not retry KeyError
    with pytest.raises(KeyError):
        await handler.execute(non_retryable_error)

    stats = handler.get_stats()
    assert stats.total_attempts == 1


@pytest.mark.asyncio
async def test_retry_handler_exponential_backoff():
    """Test exponential backoff delay calculation."""
    config = RetryConfig(
        max_attempts=4,
        initial_delay=0.1,
        multiplier=2.0,
        jitter_type=JitterType.NONE
    )
    handler = RetryHandler(config, "test")

    # Test delay calculation
    assert handler._calculate_delay(0) == 0.1  # First retry
    assert handler._calculate_delay(1) == 0.2  # Second retry
    assert handler._calculate_delay(2) == 0.4  # Third retry


@pytest.mark.asyncio
async def test_retry_handler_linear_backoff():
    """Test linear backoff delay calculation."""
    config = RetryConfig(
        max_attempts=4,
        initial_delay=0.1,
        policy=RetryPolicy.LINEAR_BACKOFF,
        jitter_type=JitterType.NONE
    )
    handler = RetryHandler(config, "test")

    # Test delay calculation
    assert handler._calculate_delay(0) == 0.1  # 0.1 * (1 + 0)
    assert handler._calculate_delay(1) == 0.2  # 0.1 * (1 + 1)
    assert handler._calculate_delay(2) == 0.3  # 0.1 * (1 + 2)


@pytest.mark.asyncio
async def test_retry_handler_fixed_delay():
    """Test fixed delay policy."""
    config = RetryConfig(
        max_attempts=4,
        initial_delay=0.1,
        policy=RetryPolicy.FIXED_DELAY,
        jitter_type=JitterType.NONE
    )
    handler = RetryHandler(config, "test")

    # All delays should be the same
    assert handler._calculate_delay(0) == 0.1
    assert handler._calculate_delay(1) == 0.1
    assert handler._calculate_delay(2) == 0.1


@pytest.mark.asyncio
async def test_retry_handler_immediate_policy():
    """Test immediate retry policy."""
    config = RetryConfig(
        max_attempts=3,
        policy=RetryPolicy.IMMEDIATE,
        jitter_type=JitterType.NONE
    )
    handler = RetryHandler(config, "test")

    # All delays should be zero
    assert handler._calculate_delay(0) == 0.0
    assert handler._calculate_delay(1) == 0.0
    assert handler._calculate_delay(2) == 0.0


@pytest.mark.asyncio
async def test_retry_handler_max_delay_limit():
    """Test maximum delay limit."""
    config = RetryConfig(
        max_attempts=10,
        initial_delay=1.0,
        max_delay=2.0,
        multiplier=10.0,
        jitter_type=JitterType.NONE
    )
    handler = RetryHandler(config, "test")

    # Should be capped at max_delay
    delay = handler._calculate_delay(5)  # Would be 1.0 * 10^5 without limit
    assert delay == 2.0


@pytest.mark.asyncio
async def test_retry_handler_jitter_types():
    """Test different jitter types."""
    config = RetryConfig(
        initial_delay=1.0,
        jitter_type=JitterType.FULL
    )
    handler = RetryHandler(config, "test")

    # Full jitter should vary the delay
    delays = [handler._calculate_delay(0) for _ in range(10)]
    assert not all(d == delays[0] for d in delays)  # Should have variation

    # Equal jitter
    config.jitter_type = JitterType.EQUAL
    handler = RetryHandler(config, "test")
    delays = [handler._calculate_delay(0) for _ in range(10)]
    assert all(d >= 1.0 for d in delays)  # Should be >= base delay


@pytest.mark.asyncio
async def test_retry_handler_timeout_per_attempt():
    """Test per-attempt timeout."""
    config = RetryConfig(
        max_attempts=2,
        timeout_per_attempt=0.1
    )
    handler = RetryHandler(config, "test")

    async def slow_func():
        await asyncio.sleep(0.2)
        return "should timeout"

    with pytest.raises(MaxAttemptsExceededError):
        await handler.execute(slow_func)


@pytest.mark.asyncio
async def test_retry_handler_total_timeout():
    """Test total timeout."""
    config = RetryConfig(
        max_attempts=10,
        initial_delay=0.1,
        total_timeout=0.3
    )
    handler = RetryHandler(config, "test")

    async def always_fail():
        raise ValueError("Always fails")

    with pytest.raises(RetryTimeoutError):
        await handler.execute(always_fail)


@pytest.mark.asyncio
async def test_retry_handler_sync_function(retry_handler):
    """Test retry handler with sync functions."""
    call_count = 0

    def flaky_sync_func():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError(f"Attempt {call_count} failed")
        return "sync success"

    result = await retry_handler.execute(flaky_sync_func)
    assert result == "sync success"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_manager():
    """Test retry manager."""
    manager = RetryManager()

    # Get retry handler
    handler1 = await manager.get_retry_handler("test1")
    assert handler1.name == "test1"

    # Get same handler again
    handler2 = await manager.get_retry_handler("test1")
    assert handler1 is handler2

    # Get different handler
    handler3 = await manager.get_retry_handler("test2")
    assert handler3.name == "test2"
    assert handler3 is not handler1

    # List handlers
    names = manager.list_retry_handlers()
    assert "test1" in names
    assert "test2" in names

    # Remove handler
    removed = await manager.remove_retry_handler("test1")
    assert removed is True

    names = manager.list_retry_handlers()
    assert "test1" not in names


@pytest.mark.asyncio
async def test_retry_decorator():
    """Test retry decorator."""
    from services.resilience.retry_handler import retry

    config = RetryConfig(max_attempts=3, initial_delay=0.01)
    call_count = 0

    @retry("decorator_test", config)
    async def test_function(should_fail_count=0):
        nonlocal call_count
        call_count += 1
        if call_count <= should_fail_count:
            raise ValueError(f"Attempt {call_count} failed")
        return f"success on attempt {call_count}"

    # Should succeed on first attempt
    call_count = 0
    result = await test_function()
    assert result == "success on attempt 1"

    # Should succeed after retries
    call_count = 0
    result = await test_function(should_fail_count=2)
    assert result == "success on attempt 3"


@pytest.mark.asyncio
async def test_retry_context_manager():
    """Test retry context manager."""
    from services.resilience.retry_handler import retry_context

    config = RetryConfig(max_attempts=2, initial_delay=0.01)

    async with retry_context("context_test", config) as handler:
        result = await handler.execute(lambda: "success")
        assert result == "success"


@pytest.mark.asyncio
async def test_predefined_configs():
    """Test predefined retry configurations."""
    # Test network retry config
    handler = RetryHandler(NETWORK_RETRY_CONFIG, "network_test")

    # Should handle connection errors
    async def connection_error():
        raise ConnectionError("Network error")

    with pytest.raises(MaxAttemptsExceededError):
        await handler.execute(connection_error)

    # Should not retry ValueError (non-retryable)
    async def value_error():
        raise ValueError("Value error")

    with pytest.raises(ValueError):
        await handler.execute(value_error)


@pytest.mark.asyncio
async def test_retry_stats_tracking():
    """Test retry statistics tracking."""
    handler = RetryHandler(RetryConfig(
        max_attempts=3, initial_delay=0.01), "stats_test")

    # Successful operation
    await handler.execute(lambda: "success")

    # Failed operation
    try:
        await handler.execute(lambda: exec('raise ValueError("error")'))
    except MaxAttemptsExceededError:
        pass

    stats = handler.get_stats()
    assert stats.total_attempts == 4  # 1 + 3
    assert stats.successful_attempts == 1
    assert stats.failed_attempts == 1
    assert len(stats.attempts) == 4

    # Reset stats
    handler.reset_stats()
    stats = handler.get_stats()
    assert stats.total_attempts == 0
    assert len(stats.attempts) == 0
