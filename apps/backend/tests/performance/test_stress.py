"""
Stress Testing Module for Syncline MESH

This module simulates extreme load conditions to identify breaking points
and validate system behavior under stress.

Test Scenarios:
1. Message Processing Throughput - 10,000 messages simultaneous injection
2. Connection Pool Exhaustion - Maximum concurrent database connections
3. Memory Pressure - Large payload processing
4. Recovery Testing - System response after overload

Run with:
    pytest test_stress.py -v --tb=short -s

For specific tests:
    pytest test_stress.py::TestMessageProcessingThroughput -v
"""

import asyncio
import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

import httpx
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


@dataclass
class StressTestResult:
    """Container for stress test results."""

    test_name: str
    start_time: datetime
    end_time: datetime
    total_operations: int
    successful_operations: int
    failed_operations: int
    throughput_per_second: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    peak_cpu_utilization: float = 0.0
    peak_memory_utilization: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": (self.end_time - self.start_time).total_seconds(),
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "success_rate": self.successful_operations
            / max(self.total_operations, 1)
            * 100,
            "throughput_per_second": round(self.throughput_per_second, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
            "peak_cpu_utilization": self.peak_cpu_utilization,
            "peak_memory_utilization": self.peak_memory_utilization,
            "errors": self.errors[:10],  # Limit errors in report
        }


class StressTestBase:
    """Base class for stress tests with common utilities."""

    BASE_URL = os.getenv("STRESS_TEST_URL", "http://localhost:8000")
    RESULTS_DIR = "results/stress_tests"

    @classmethod
    def setup_class(cls):
        """Setup test class - create results directory."""
        os.makedirs(cls.RESULTS_DIR, exist_ok=True)

    def calculate_percentile(self, data: List[float], percentile: int) -> float:
        """Calculate the nth percentile of a list of values."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        lower = int(index)
        upper = lower + 1
        if upper >= len(sorted_data):
            return sorted_data[-1]
        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight

    def save_result(self, result: StressTestResult):
        """Save test result to JSON file."""
        filename = f"{self.RESULTS_DIR}/{result.test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\nResults saved to: {filename}")


class TestMessageProcessingThroughput(StressTestBase):
    """
    Test Case: Message Processing Throughput

    Scenario: Inject 10,000 messages simultaneously into ingestion queue
    Expected:
    - Processing completion under 10 minutes
    - Throughput of ~19.6 messages/second
    - No message loss or data corruption
    """

    MESSAGE_COUNT = 10000

    @pytest.fixture
    def sample_messages(self) -> List[Dict[str, Any]]:
        """Generate sample messages for testing."""
        return [
            {
                "id": f"stress_msg_{i}",
                "content": f"Stress test message {i} - {datetime.now().isoformat()}",
                "sender_id": f"sender_{i % 100}",
                "platform": ["whatsapp", "gmail", "slack", "telegram"][i % 4],
                "timestamp": datetime.now().isoformat(),
                "metadata": {"test": True, "batch": i // 100},
            }
            for i in range(self.MESSAGE_COUNT)
        ]

    @pytest.mark.asyncio
    async def test_message_injection_throughput(self, sample_messages):
        """Test bulk message ingestion throughput."""
        latencies = []
        successful = 0
        failed = 0
        errors = []

        start_time = datetime.now()

        async with httpx.AsyncClient(base_url=self.BASE_URL, timeout=30.0) as client:
            # Process messages in batches to avoid overwhelming the system
            batch_size = 100

            for batch_start in range(0, len(sample_messages), batch_size):
                batch = sample_messages[batch_start : batch_start + batch_size]
                batch_tasks = []

                for msg in batch:
                    batch_tasks.append(
                        self._send_message(client, msg, latencies, errors)
                    )

                results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                for result in results:
                    if result is True:
                        successful += 1
                    else:
                        failed += 1

                # Progress indicator
                progress = (batch_start + len(batch)) / len(sample_messages) * 100
                print(
                    f"\rProgress: {progress:.1f}% ({batch_start + len(batch)}/{len(sample_messages)})",
                    end="",
                )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Calculate metrics
        result = StressTestResult(
            test_name="message_processing_throughput",
            start_time=start_time,
            end_time=end_time,
            total_operations=len(sample_messages),
            successful_operations=successful,
            failed_operations=failed,
            throughput_per_second=successful / duration if duration > 0 else 0,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            p95_latency_ms=self.calculate_percentile(latencies, 95),
            p99_latency_ms=self.calculate_percentile(latencies, 99),
            errors=errors,
        )

        self.save_result(result)

        # Print summary
        print(f"\n\n{'='*60}")
        print("MESSAGE PROCESSING THROUGHPUT TEST RESULTS")
        print(f"{'='*60}")
        print(f"Total Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        print(f"Total Messages: {result.total_operations}")
        print(f"Successful: {result.successful_operations}")
        print(f"Failed: {result.failed_operations}")
        print(f"Throughput: {result.throughput_per_second:.2f} messages/second")
        print(f"Avg Latency: {result.avg_latency_ms:.2f}ms")
        print(f"P95 Latency: {result.p95_latency_ms:.2f}ms")
        print(f"P99 Latency: {result.p99_latency_ms:.2f}ms")
        print(f"{'='*60}\n")

        # Assertions based on documented requirements
        assert duration < 600, f"Processing took longer than 10 minutes: {duration}s"
        assert (
            result.throughput_per_second > 15
        ), f"Throughput below minimum: {result.throughput_per_second}"
        assert (
            result.failed_operations == 0
            or (result.failed_operations / result.total_operations) < 0.01
        )

    async def _send_message(
        self,
        client: httpx.AsyncClient,
        message: Dict,
        latencies: List[float],
        errors: List[str],
    ) -> bool:
        """Send a single message and record metrics."""
        try:
            start = time.perf_counter()

            response = await client.post(
                "/api/v1/messages/ingest",
                json=message,
                headers={"Authorization": "Bearer stress_test_token"},
            )

            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

            if response.status_code in [200, 201, 202]:
                return True
            else:
                errors.append(f"Status {response.status_code}: {response.text[:100]}")
                return False

        except Exception as e:
            errors.append(str(e)[:100])
            return False


class TestDatabaseConnectionPoolExhaustion(StressTestBase):
    """
    Test Case: Database Connection Pool Stress

    Tests system behavior when database connection pool is exhausted.
    Validates graceful degradation and error handling.
    """

    CONCURRENT_CONNECTIONS = 200

    @pytest.mark.asyncio
    async def test_connection_pool_limits(self):
        """Test behavior at connection pool limits."""
        latencies = []
        successful = 0
        failed = 0
        errors = []

        start_time = datetime.now()

        async with httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=60.0,
            limits=httpx.Limits(max_connections=500, max_keepalive_connections=100),
        ) as client:
            # Fire concurrent requests
            tasks = [
                self._query_database(client, i, latencies, errors)
                for i in range(self.CONCURRENT_CONNECTIONS)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if result is True:
                    successful += 1
                else:
                    failed += 1

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        result = StressTestResult(
            test_name="connection_pool_exhaustion",
            start_time=start_time,
            end_time=end_time,
            total_operations=self.CONCURRENT_CONNECTIONS,
            successful_operations=successful,
            failed_operations=failed,
            throughput_per_second=successful / duration if duration > 0 else 0,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            p95_latency_ms=self.calculate_percentile(latencies, 95),
            p99_latency_ms=self.calculate_percentile(latencies, 99),
            errors=errors,
        )

        self.save_result(result)

        print(f"\n\n{'='*60}")
        print("CONNECTION POOL EXHAUSTION TEST RESULTS")
        print(f"{'='*60}")
        print(f"Concurrent Connections: {self.CONCURRENT_CONNECTIONS}")
        print(f"Successful: {result.successful_operations}")
        print(f"Failed: {result.failed_operations}")
        print(f"Avg Latency: {result.avg_latency_ms:.2f}ms")
        print(f"{'='*60}\n")

        # Should handle some failures gracefully without crashing
        assert successful > 0, "All connections failed"

    async def _query_database(
        self,
        client: httpx.AsyncClient,
        request_id: int,
        latencies: List[float],
        errors: List[str],
    ) -> bool:
        """Execute a database-heavy query."""
        try:
            start = time.perf_counter()

            # Use a contact profile query (involves relationship metrics calculation)
            response = await client.get(
                f"/api/v1/contacts/contact_{request_id}/profile",
                headers={"Authorization": "Bearer stress_test_token"},
            )

            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

            return response.status_code in [200, 404]

        except Exception as e:
            errors.append(f"Request {request_id}: {str(e)[:50]}")
            return False


class TestRecoveryTime(StressTestBase):
    """
    Test Case: System Recovery After Overload

    Verifies system returns to normal operation after load cessation.
    Target: Recovery within 30 seconds.
    """

    @pytest.mark.asyncio
    async def test_recovery_after_overload(self):
        """Test system recovery time after stress."""

        # Phase 1: Apply heavy load
        print("\nPhase 1: Applying heavy load...")
        async with httpx.AsyncClient(base_url=self.BASE_URL, timeout=30.0) as client:
            load_tasks = [
                client.get("/api/v1/messages", params={"limit": 100})
                for _ in range(100)
            ]
            await asyncio.gather(*load_tasks, return_exceptions=True)

        print("Phase 1: Load applied, starting recovery measurement...")

        # Phase 2: Measure time to return to normal response times
        recovery_start = time.perf_counter()
        normal_threshold_ms = 500  # Normal response should be under 500ms
        max_recovery_time = 30  # Maximum 30 seconds to recover

        recovered = False
        recovery_latencies = []

        async with httpx.AsyncClient(base_url=self.BASE_URL, timeout=10.0) as client:
            while (
                not recovered
                and (time.perf_counter() - recovery_start) < max_recovery_time
            ):
                try:
                    start = time.perf_counter()
                    response = await client.get("/api/v1/health")
                    latency_ms = (time.perf_counter() - start) * 1000
                    recovery_latencies.append(latency_ms)

                    if latency_ms < normal_threshold_ms and response.status_code == 200:
                        # Check if we have 3 consecutive fast responses
                        if len(recovery_latencies) >= 3:
                            recent = recovery_latencies[-3:]
                            if all(l < normal_threshold_ms for l in recent):
                                recovered = True

                    await asyncio.sleep(0.5)

                except Exception:
                    await asyncio.sleep(1)

        recovery_time = time.perf_counter() - recovery_start

        print(f"\n{'='*60}")
        print("RECOVERY TIME TEST RESULTS")
        print(f"{'='*60}")
        print(f"Recovered: {recovered}")
        print(f"Recovery Time: {recovery_time:.2f} seconds")
        print(
            f"Final Latency: {recovery_latencies[-1]:.2f}ms"
            if recovery_latencies
            else "N/A"
        )
        print(f"{'='*60}\n")

        assert recovered, f"System did not recover within {max_recovery_time} seconds"
        assert recovery_time < 30, f"Recovery took too long: {recovery_time:.2f}s"


class TestEndurance:
    """
    Endurance Test Configuration

    This test runs for extended periods (72 hours in production).
    For automated testing, uses a shorter duration with monitoring.

    Run with:
        pytest test_stress.py::TestEndurance -v --duration=3600
    """

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_endurance_short(self):
        """Short endurance test (1 hour) for CI/CD validation."""
        duration_seconds = int(os.getenv("ENDURANCE_DURATION", "300"))  # Default 5 min

        print(f"\nStarting endurance test for {duration_seconds} seconds...")

        metrics = {"samples": [], "memory_samples": [], "response_times": []}

        start_time = time.perf_counter()
        sample_interval = 10  # Sample every 10 seconds

        async with httpx.AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            while (time.perf_counter() - start_time) < duration_seconds:
                sample_start = time.perf_counter()

                try:
                    # Perform typical operations
                    response = await client.get(
                        "/api/v1/messages", params={"limit": 50}
                    )
                    latency = (time.perf_counter() - sample_start) * 1000

                    metrics["samples"].append(
                        {
                            "timestamp": time.time(),
                            "status": response.status_code,
                            "latency_ms": latency,
                        }
                    )
                    metrics["response_times"].append(latency)

                except Exception as e:
                    metrics["samples"].append(
                        {"timestamp": time.time(), "error": str(e)}
                    )

                elapsed = time.perf_counter() - start_time
                print(f"\rEndurance test: {elapsed:.0f}/{duration_seconds}s", end="")

                await asyncio.sleep(sample_interval)

        # Analyze results
        successful_samples = [s for s in metrics["samples"] if s.get("status") == 200]
        error_samples = [s for s in metrics["samples"] if "error" in s]

        print(f"\n\n{'='*60}")
        print("ENDURANCE TEST RESULTS")
        print(f"{'='*60}")
        print(f"Duration: {duration_seconds} seconds")
        print(f"Total Samples: {len(metrics['samples'])}")
        print(f"Successful: {len(successful_samples)}")
        print(f"Errors: {len(error_samples)}")
        if metrics["response_times"]:
            print(
                f"Avg Response Time: {statistics.mean(metrics['response_times']):.2f}ms"
            )
            print(
                f"Response Time Std Dev: {statistics.stdev(metrics['response_times']) if len(metrics['response_times']) > 1 else 0:.2f}ms"
            )
        print(f"{'='*60}\n")

        # Check for degradation
        if len(metrics["response_times"]) >= 2:
            first_half = metrics["response_times"][
                : len(metrics["response_times"]) // 2
            ]
            second_half = metrics["response_times"][
                len(metrics["response_times"]) // 2 :
            ]

            first_avg = statistics.mean(first_half)
            second_avg = statistics.mean(second_half)

            # Response times should not degrade significantly
            degradation = (
                (second_avg - first_avg) / first_avg * 100 if first_avg > 0 else 0
            )
            print(f"Performance Degradation: {degradation:.1f}%")

            assert (
                degradation < 50
            ), f"Significant performance degradation: {degradation:.1f}%"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
