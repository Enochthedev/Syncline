"""
Chaos engineering tests for system resilience and recovery.

These tests simulate various failure scenarios to validate the system's
ability to handle and recover from different types of failures.
"""

import asyncio
import pytest
import random
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from services.resilience import (
    DeadLetterQueue,
    CircuitBreaker,
    CircuitBreakerConfig,
    RetryHandler,
    RetryConfig,
    GracefulDegradationManager,
    ServiceStatus,
    DegradationLevel
)


class ChaosMonkey:
    """Chaos monkey for introducing random failures."""

    def __init__(self, failure_rate: float = 0.3):
        self.failure_rate = failure_rate
        self.failure_types = [
            ConnectionError,
            TimeoutError,
            ValueError,
            RuntimeError
        ]

    def should_fail(self) -> bool:
        """Determine if operation should fail."""
        return random.random() < self.failure_rate

    def get_random_error(self) -> Exception:
        """Get a random error type."""
        error_class = random.choice(self.failure_types)
        return error_class(f"Chaos monkey error: {error_class.__name__}")


@pytest.fixture
def chaos_monkey():
    """Chaos monkey fixture."""
    return ChaosMonkey(failure_rate=0.5)


@pytest.fixture
async def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = AsyncMock()
    redis_mock.ping.return_value = True
    redis_mock.hset.return_value = True
    redis_mock.hget.return_value = None
    redis_mock.zadd.return_value = 1
    redis_mock.sadd.return_value = 1
    redis_mock.scard.return_value = 0
    redis_mock.zcard.return_value = 0
    redis_mock.zrange.return_value = []
    redis_mock.zrangebyscore.return_value = []
    redis_mock.zrem.return_value = 1
    redis_mock.srem.return_value = 1
    redis_mock.smembers.return_value = set()
    return redis_mock


@pytest.mark.asyncio
async def test_chaos_circuit_breaker_resilience(chaos_monkey):
    """Test circuit breaker resilience under chaotic conditions."""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout_seconds=0.1,
        success_threshold=2
    )
    cb = CircuitBreaker(config, "chaos_test")

    success_count = 0
    failure_count = 0
    circuit_breaker_blocks = 0

    async def chaotic_operation():
        if chaos_monkey.should_fail():
            raise chaos_monkey.get_random_error()
        return "success"

    # Run many operations
    for i in range(100):
        try:
            result = await cb.call(chaotic_operation)
            if result == "success":
                success_count += 1
        except Exception as e:
            if "Circuit breaker" in str(e):
                circuit_breaker_blocks += 1
            else:
                failure_count += 1

        # Small delay to allow recovery
        if i % 10 == 0:
            await asyncio.sleep(0.01)

    # Verify circuit breaker protected the system
    assert circuit_breaker_blocks > 0, "Circuit breaker should have blocked some requests"
    assert success_count > 0, "Some operations should have succeeded"

    stats = cb.get_stats()
    print(
        f"Success: {success_count}, Failures: {failure_count}, CB Blocks: {circuit_breaker_blocks}")
    print(
        f"CB Stats: {stats.total_requests} requests, {stats.failure_rate:.2%} failure rate")


@pytest.mark.asyncio
async def test_chaos_retry_handler_resilience(chaos_monkey):
    """Test retry handler resilience under chaotic conditions."""
    config = RetryConfig(
        max_attempts=5,
        initial_delay=0.01,
        max_delay=0.1
    )
    handler = RetryHandler(config, "chaos_test")

    success_count = 0
    permanent_failures = 0

    async def chaotic_operation():
        # Simulate intermittent failures
        if chaos_monkey.should_fail():
            raise chaos_monkey.get_random_error()
        return "success"

    # Run operations
    for i in range(50):
        try:
            result = await handler.execute(chaotic_operation)
            if result == "success":
                success_count += 1
        except Exception:
            permanent_failures += 1

    # Verify retry handler improved success rate
    assert success_count > 0, "Some operations should have succeeded"

    stats = handler.get_stats()
    print(
        f"Success: {success_count}, Permanent failures: {permanent_failures}")
    print(
        f"Retry stats: {stats.total_attempts} attempts, {stats.successful_attempts} successes")


@pytest.mark.asyncio
async def test_chaos_dead_letter_queue_resilience(chaos_monkey, mock_redis):
    """Test DLQ resilience under chaotic conditions."""
    dlq = DeadLetterQueue(redis_client=mock_redis)
    await dlq.initialize()

    messages_added = 0
    processing_attempts = 0
    successful_retries = 0

    async def chaotic_handler(event):
        nonlocal processing_attempts
        processing_attempts += 1

        # Simulate processing failures
        if chaos_monkey.should_fail():
            raise chaos_monkey.get_random_error()
        return "processed"

    # Add messages to DLQ
    for i in range(20):
        event = {'id': f'event_{i}', 'data': f'test_data_{i}'}
        error = chaos_monkey.get_random_error()

        message_id = await dlq.add_message(event, error, max_retries=3)
        messages_added += 1

        # Simulate retry attempts
        if random.random() < 0.7:  # 70% chance of retry
            success = await dlq.retry_message(message_id, chaotic_handler)
            if success:
                successful_retries += 1

    assert messages_added == 20
    assert processing_attempts > 0
    print(
        f"Messages added: {messages_added}, Processing attempts: {processing_attempts}")
    print(f"Successful retries: {successful_retries}")


@pytest.mark.asyncio
async def test_chaos_graceful_degradation_resilience(chaos_monkey):
    """Test graceful degradation under chaotic conditions."""
    manager = GracefulDegradationManager()

    # Register a service with fallback
    async def fallback_handler(*args, **kwargs):
        return {"status": "degraded", "data": "fallback_data"}

    await manager.register_service(
        "chaotic_service",
        fallback_handler=fallback_handler
    )

    success_count = 0
    fallback_count = 0

    async def chaotic_primary_function():
        if chaos_monkey.should_fail():
            raise chaos_monkey.get_random_error()
        return {"status": "success", "data": "primary_data"}

    # Run operations
    for i in range(50):
        try:
            result = await manager.execute_with_fallback(
                "chaotic_service",
                chaotic_primary_function,
                cache_key=f"key_{i % 10}"  # Some cache reuse
            )

            if result.get("status") == "success":
                success_count += 1
            elif result.get("status") == "degraded":
                fallback_count += 1

        except Exception as e:
            print(f"Unexpected error: {e}")

    # Verify graceful degradation worked
    assert success_count + fallback_count > 0, "Should have some successful operations"
    assert fallback_count > 0, "Should have used fallback mechanisms"

    print(f"Primary success: {success_count}, Fallback used: {fallback_count}")


@pytest.mark.asyncio
async def test_chaos_combined_resilience_patterns(chaos_monkey, mock_redis):
    """Test combined resilience patterns under chaotic conditions."""
    # Set up all resilience components
    cb_config = CircuitBreakerConfig(
        failure_threshold=3, recovery_timeout_seconds=0.1)
    circuit_breaker = CircuitBreaker(cb_config, "combined_test")

    retry_config = RetryConfig(max_attempts=3, initial_delay=0.01)
    retry_handler = RetryHandler(retry_config, "combined_test")

    dlq = DeadLetterQueue(redis_client=mock_redis)
    await dlq.initialize()

    degradation_manager = GracefulDegradationManager()
    await degradation_manager.register_service(
        "combined_service",
        fallback_handler=lambda: {"status": "fallback", "data": None}
    )

    # Metrics
    total_operations = 100
    success_count = 0
    circuit_breaker_blocks = 0
    retry_exhausted = 0
    dlq_messages = 0
    fallback_used = 0

    async def chaotic_operation():
        """Simulate a chaotic external service call."""
        failure_chance = random.random()

        if failure_chance < 0.3:  # 30% immediate failure
            raise ConnectionError("Network failure")
        elif failure_chance < 0.5:  # 20% timeout
            await asyncio.sleep(0.01)  # Simulate slow response
            raise TimeoutError("Request timeout")
        elif failure_chance < 0.6:  # 10% server error
            raise RuntimeError("Server error")
        else:  # 40% success
            return {"status": "success", "data": "operation_result"}

    # Run operations with all resilience patterns
    for i in range(total_operations):
        try:
            # Layer 1: Circuit breaker protection
            result = await circuit_breaker.call(
                lambda: retry_handler.execute(
                    lambda: degradation_manager.execute_with_fallback(
                        "combined_service",
                        chaotic_operation,
                        cache_key=f"op_{i % 5}"
                    )
                )
            )

            if result.get("status") == "success":
                success_count += 1
            elif result.get("status") == "fallback":
                fallback_used += 1

        except Exception as e:
            error_type = type(e).__name__

            if "Circuit breaker" in str(e):
                circuit_breaker_blocks += 1
            elif "Max attempts" in str(e):
                retry_exhausted += 1
                # Add to DLQ
                await dlq.add_message(
                    {"operation_id": i, "type": "chaotic_operation"},
                    e,
                    max_retries=2
                )
                dlq_messages += 1
            else:
                print(f"Unexpected error type: {error_type}")

    # Verify system resilience
    total_handled = success_count + circuit_breaker_blocks + \
        retry_exhausted + fallback_used
    assert total_handled >= total_operations * \
        0.8, "Should handle at least 80% of operations"

    print(f"\n=== Chaos Engineering Results ===")
    print(f"Total operations: {total_operations}")
    print(
        f"Successful: {success_count} ({success_count/total_operations:.1%})")
    print(
        f"Circuit breaker blocks: {circuit_breaker_blocks} ({circuit_breaker_blocks/total_operations:.1%})")
    print(
        f"Retry exhausted: {retry_exhausted} ({retry_exhausted/total_operations:.1%})")
    print(
        f"Fallback used: {fallback_used} ({fallback_used/total_operations:.1%})")
    print(f"DLQ messages: {dlq_messages}")
    print(
        f"Total handled: {total_handled} ({total_handled/total_operations:.1%})")

    # Verify each component contributed
    assert success_count > 0, "Some operations should succeed"
    assert circuit_breaker_blocks > 0 or retry_exhausted > 0, "Resilience patterns should activate"


@pytest.mark.asyncio
async def test_chaos_network_partition_simulation():
    """Simulate network partition and test recovery."""
    network_available = True

    async def network_dependent_operation():
        if not network_available:
            raise ConnectionError("Network partition")
        return "network_success"

    cb_config = CircuitBreakerConfig(
        failure_threshold=2,
        recovery_timeout_seconds=0.1
    )
    circuit_breaker = CircuitBreaker(cb_config, "network_test")

    # Phase 1: Normal operation
    result = await circuit_breaker.call(network_dependent_operation)
    assert result == "network_success"

    # Phase 2: Network partition
    network_available = False

    # Should fail and open circuit breaker
    for _ in range(3):
        try:
            await circuit_breaker.call(network_dependent_operation)
        except (ConnectionError, Exception):
            pass

    # Circuit breaker should be open
    assert circuit_breaker.state.value == "open"

    # Phase 3: Network recovery
    network_available = True

    # Wait for recovery timeout
    await asyncio.sleep(0.15)

    # Should recover
    result = await circuit_breaker.call(network_dependent_operation)
    assert result == "network_success"


@pytest.mark.asyncio
async def test_chaos_memory_pressure_simulation():
    """Simulate memory pressure and test graceful degradation."""
    memory_pressure = False

    async def memory_intensive_operation():
        if memory_pressure:
            raise MemoryError("Out of memory")
        return "memory_success"

    async def lightweight_fallback():
        return {"status": "degraded", "message": "Using lightweight mode"}

    manager = GracefulDegradationManager()
    await manager.register_service(
        "memory_service",
        fallback_handler=lightweight_fallback
    )

    # Normal operation
    result = await manager.execute_with_fallback(
        "memory_service",
        memory_intensive_operation
    )
    assert result == "memory_success"

    # Memory pressure
    memory_pressure = True

    result = await manager.execute_with_fallback(
        "memory_service",
        memory_intensive_operation
    )
    assert result["status"] == "degraded"


@pytest.mark.asyncio
async def test_chaos_cascading_failure_prevention():
    """Test prevention of cascading failures."""
    service_states = {
        "service_a": True,
        "service_b": True,
        "service_c": True
    }

    circuit_breakers = {}

    async def create_service_call(service_name):
        async def service_call():
            if not service_states[service_name]:
                raise RuntimeError(f"{service_name} is down")
            return f"{service_name}_success"
        return service_call

    # Create circuit breakers for each service
    for service in service_states.keys():
        config = CircuitBreakerConfig(
            failure_threshold=2, recovery_timeout_seconds=0.1)
        circuit_breakers[service] = CircuitBreaker(config, service)

    # Simulate service A failure
    service_states["service_a"] = False

    # Service A should fail and open circuit breaker
    for _ in range(3):
        try:
            await circuit_breakers["service_a"].call(
                await create_service_call("service_a")
            )
        except Exception:
            pass

    # Service A circuit breaker should be open
    assert circuit_breakers["service_a"].state.value == "open"

    # Services B and C should still work
    result_b = await circuit_breakers["service_b"].call(
        await create_service_call("service_b")
    )
    result_c = await circuit_breakers["service_c"].call(
        await create_service_call("service_c")
    )

    assert result_b == "service_b_success"
    assert result_c == "service_c_success"

    # Verify isolation prevented cascading failure
    assert circuit_breakers["service_b"].state.value == "closed"
    assert circuit_breakers["service_c"].state.value == "closed"


@pytest.mark.asyncio
async def test_chaos_load_spike_handling():
    """Test handling of sudden load spikes."""
    from services.resilience.graceful_degradation import ServiceStatus

    current_load = 0
    max_capacity = 10

    async def load_sensitive_operation():
        nonlocal current_load
        current_load += 1

        try:
            if current_load > max_capacity:
                raise RuntimeError("System overloaded")

            # Simulate processing time
            await asyncio.sleep(0.01)
            return f"processed_request_{current_load}"
        finally:
            current_load -= 1

    manager = GracefulDegradationManager()

    # Simulate load spike with concurrent requests
    tasks = []
    for i in range(20):  # 2x capacity
        task = asyncio.create_task(
            manager.execute_with_fallback(
                "load_service",
                load_sensitive_operation,
                cache_key=f"request_{i}"
            )
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Count successful vs failed/degraded responses
    successes = sum(1 for r in results if isinstance(
        r, str) and "processed_request" in r)
    failures = sum(1 for r in results if isinstance(r, Exception))
    degraded = sum(1 for r in results if isinstance(
        r, dict) and r.get("status") == "degraded")

    print(
        f"Load spike results: {successes} success, {failures} failures, {degraded} degraded")

    # System should handle the load spike gracefully
    assert successes > 0, "Some requests should succeed"
    assert successes <= max_capacity * 1.5, "Should not exceed reasonable capacity"
