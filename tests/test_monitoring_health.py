"""Tests for monitoring health checks."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from services.monitoring.health import (
    HealthChecker, HealthCheck, HealthStatus, HealthCheckResult,
    get_health_checker, database_health_check, redis_health_check,
    vector_db_health_check, ai_engine_health_check, register_default_health_checks
)


class TestHealthCheckResult:
    """Test health check result functionality."""

    def test_health_check_result_creation(self):
        """Test creating health check results."""
        result = HealthCheckResult(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="All good",
            details={"key": "value"}
        )

        assert result.name == "test_check"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"
        assert result.details == {"key": "value"}
        assert isinstance(result.timestamp, datetime)

    def test_health_check_result_to_dict(self):
        """Test converting health check result to dictionary."""
        result = HealthCheckResult(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="All good",
            response_time_ms=123.45
        )

        result_dict = result.to_dict()

        assert result_dict["name"] == "test_check"
        assert result_dict["status"] == "healthy"
        assert result_dict["message"] == "All good"
        assert result_dict["response_time_ms"] == 123.45
        assert "timestamp" in result_dict


class TestHealthChecker:
    """Test health checker functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.health_checker = HealthChecker()

    @pytest.mark.asyncio
    async def test_register_and_run_check(self):
        """Test registering and running a health check."""
        # Create a mock health check
        async def mock_check():
            return HealthCheckResult(
                name="test_check",
                status=HealthStatus.HEALTHY,
                message="Test passed"
            )

        health_check = HealthCheck(
            name="test_check",
            check_func=mock_check,
            timeout_seconds=5.0,
            critical=True
        )

        # Register the check
        self.health_checker.register_check(health_check)

        # Run the check
        result = await self.health_checker.run_check("test_check")

        assert result.name == "test_check"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Test passed"
        assert result.response_time_ms is not None

    @pytest.mark.asyncio
    async def test_run_nonexistent_check(self):
        """Test running a check that doesn't exist."""
        result = await self.health_checker.run_check("nonexistent")

        assert result.name == "nonexistent"
        assert result.status == HealthStatus.UNKNOWN
        assert "not found" in result.message

    @pytest.mark.asyncio
    async def test_check_timeout(self):
        """Test health check timeout handling."""
        # Create a slow check that will timeout
        async def slow_check():
            await asyncio.sleep(2.0)  # Longer than timeout
            return HealthCheckResult(
                name="slow_check",
                status=HealthStatus.HEALTHY,
                message="Should not reach here"
            )

        health_check = HealthCheck(
            name="slow_check",
            check_func=slow_check,
            timeout_seconds=0.1,  # Very short timeout
            critical=True
        )

        self.health_checker.register_check(health_check)

        # Run the check
        result = await self.health_checker.run_check("slow_check")

        assert result.name == "slow_check"
        assert result.status == HealthStatus.UNHEALTHY
        assert "timed out" in result.message
        assert result.response_time_ms is not None

    @pytest.mark.asyncio
    async def test_check_exception_handling(self):
        """Test health check exception handling."""
        # Create a check that raises an exception
        async def failing_check():
            raise ValueError("Something went wrong")

        health_check = HealthCheck(
            name="failing_check",
            check_func=failing_check,
            timeout_seconds=5.0,
            critical=True
        )

        self.health_checker.register_check(health_check)

        # Run the check
        result = await self.health_checker.run_check("failing_check")

        assert result.name == "failing_check"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Something went wrong" in result.message
        assert result.response_time_ms is not None

    @pytest.mark.asyncio
    async def test_run_all_checks(self):
        """Test running all registered checks."""
        # Register multiple checks
        async def healthy_check():
            return HealthCheckResult("healthy", HealthStatus.HEALTHY, "OK")

        async def unhealthy_check():
            return HealthCheckResult("unhealthy", HealthStatus.UNHEALTHY, "Failed")

        self.health_checker.register_check(
            HealthCheck("healthy", healthy_check))
        self.health_checker.register_check(
            HealthCheck("unhealthy", unhealthy_check))

        # Run all checks
        results = await self.health_checker.run_all_checks()

        assert len(results) == 2
        assert "healthy" in results
        assert "unhealthy" in results
        assert results["healthy"].status == HealthStatus.HEALTHY
        assert results["unhealthy"].status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_get_system_health(self):
        """Test getting overall system health."""
        # Register checks with different statuses
        async def healthy_check():
            return HealthCheckResult("healthy", HealthStatus.HEALTHY, "OK")

        async def degraded_check():
            return HealthCheckResult("degraded", HealthStatus.DEGRADED, "Slow")

        async def unhealthy_critical_check():
            return HealthCheckResult("critical", HealthStatus.UNHEALTHY, "Failed")

        self.health_checker.register_check(HealthCheck(
            "healthy", healthy_check, critical=False))
        self.health_checker.register_check(HealthCheck(
            "degraded", degraded_check, critical=False))
        self.health_checker.register_check(HealthCheck(
            "critical", unhealthy_critical_check, critical=True))

        # Get system health
        system_health = await self.health_checker.get_system_health()

        assert system_health["status"] == "unhealthy"  # Critical failure
        assert "timestamp" in system_health
        assert "checks" in system_health
        assert "summary" in system_health

        summary = system_health["summary"]
        assert summary["total_checks"] == 3
        assert summary["healthy"] == 1
        assert summary["degraded"] == 1
        assert summary["unhealthy"] == 1
        assert "critical" in summary["critical_failures"]

    def test_unregister_check(self):
        """Test unregistering a health check."""
        # Register a check
        async def test_check():
            return HealthCheckResult("test", HealthStatus.HEALTHY, "OK")

        self.health_checker.register_check(HealthCheck("test", test_check))

        # Verify it's registered
        assert "test" in self.health_checker._checks

        # Unregister it
        self.health_checker.unregister_check("test")

        # Verify it's gone
        assert "test" not in self.health_checker._checks

    def test_get_cached_results(self):
        """Test getting cached health check results."""
        # Initially should be empty
        cached = self.health_checker.get_cached_results()
        assert len(cached) == 0

        # Add a cached result manually (simulating a previous check)
        result = HealthCheckResult("test", HealthStatus.HEALTHY, "OK")
        self.health_checker._last_results["test"] = result

        # Get cached results
        cached = self.health_checker.get_cached_results()
        assert len(cached) == 1
        assert "test" in cached
        assert cached["test"].status == HealthStatus.HEALTHY


class TestBuiltInHealthChecks:
    """Test built-in health check functions."""

    @pytest.mark.asyncio
    @patch('services.monitoring.health.get_async_session')
    async def test_database_health_check_success(self, mock_get_session):
        """Test successful database health check."""
        # Mock database session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = (1,)
        mock_session.execute.return_value = mock_result
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # Run health check
        result = await database_health_check()

        assert result.name == "database"
        assert result.status == HealthStatus.HEALTHY
        assert "successful" in result.message
        assert result.details["type"] == "PostgreSQL"

    @pytest.mark.asyncio
    @patch('services.monitoring.health.get_async_session')
    async def test_database_health_check_failure(self, mock_get_session):
        """Test failed database health check."""
        # Mock database session to raise exception
        mock_get_session.side_effect = Exception("Connection failed")

        # Run health check
        result = await database_health_check()

        assert result.name == "database"
        assert result.status == HealthStatus.UNHEALTHY
        assert "failed" in result.message
        assert "Connection failed" in result.details["error"]

    @pytest.mark.asyncio
    @patch('services.monitoring.health.get_redis_client')
    async def test_redis_health_check_success(self, mock_get_redis):
        """Test successful Redis health check."""
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_get_redis.return_value = mock_redis

        # Run health check
        result = await redis_health_check()

        assert result.name == "redis"
        assert result.status == HealthStatus.HEALTHY
        assert "successful" in result.message
        assert result.details["type"] == "Redis"

    @pytest.mark.asyncio
    @patch('services.monitoring.health.get_redis_client')
    async def test_redis_health_check_failure(self, mock_get_redis):
        """Test failed Redis health check."""
        # Mock Redis client to raise exception
        mock_get_redis.side_effect = Exception("Redis unavailable")

        # Run health check
        result = await redis_health_check()

        assert result.name == "redis"
        assert result.status == HealthStatus.UNHEALTHY
        assert "failed" in result.message
        assert "Redis unavailable" in result.details["error"]

    @pytest.mark.asyncio
    @patch('services.monitoring.health.get_chroma_client')
    async def test_vector_db_health_check_success(self, mock_get_chroma):
        """Test successful vector database health check."""
        # Mock ChromaDB client
        mock_client = AsyncMock()
        mock_client.list_collections.return_value = [
            "collection1", "collection2"]
        mock_get_chroma.return_value = mock_client

        # Run health check
        result = await vector_db_health_check()

        assert result.name == "vector_db"
        assert result.status == HealthStatus.HEALTHY
        assert "successful" in result.message
        assert result.details["type"] == "ChromaDB"
        assert result.details["collections_count"] == 2

    @pytest.mark.asyncio
    @patch('services.monitoring.health.get_chroma_client')
    async def test_vector_db_health_check_failure(self, mock_get_chroma):
        """Test failed vector database health check."""
        # Mock ChromaDB client to raise exception
        mock_get_chroma.side_effect = Exception("ChromaDB unavailable")

        # Run health check
        result = await vector_db_health_check()

        assert result.name == "vector_db"
        assert result.status == HealthStatus.UNHEALTHY
        assert "failed" in result.message
        assert "ChromaDB unavailable" in result.details["error"]

    @pytest.mark.asyncio
    @patch('services.monitoring.health.get_ai_processing_engine')
    async def test_ai_engine_health_check_success(self, mock_get_engine):
        """Test successful AI engine health check."""
        # Mock AI engine
        mock_engine = AsyncMock()
        mock_engine.health_check.return_value = {
            "status": "healthy",
            "models_loaded": 3,
            "memory_usage": "512MB"
        }
        mock_get_engine.return_value = mock_engine

        # Run health check
        result = await ai_engine_health_check()

        assert result.name == "ai_engine"
        assert result.status == HealthStatus.HEALTHY
        assert "healthy" in result.message
        assert result.details["models_loaded"] == 3

    @pytest.mark.asyncio
    @patch('services.monitoring.health.get_ai_processing_engine')
    async def test_ai_engine_health_check_degraded(self, mock_get_engine):
        """Test degraded AI engine health check."""
        # Mock AI engine with degraded status
        mock_engine = AsyncMock()
        mock_engine.health_check.return_value = {
            "status": "degraded",
            "models_loaded": 1,
            "issues": ["Model loading slow"]
        }
        mock_get_engine.return_value = mock_engine

        # Run health check
        result = await ai_engine_health_check()

        assert result.name == "ai_engine"
        assert result.status == HealthStatus.DEGRADED
        assert "degraded" in result.message
        assert result.details["models_loaded"] == 1


class TestHealthCheckerIntegration:
    """Test health checker integration functionality."""

    def test_global_health_checker(self):
        """Test global health checker singleton."""
        checker1 = get_health_checker()
        checker2 = get_health_checker()

        # Should be the same instance
        assert checker1 is checker2

    def test_register_default_health_checks(self):
        """Test registering default health checks."""
        health_checker = HealthChecker()

        # Should start empty
        assert len(health_checker._checks) == 0

        # Register default checks (we'll mock the global instance)
        with patch('services.monitoring.health.get_health_checker', return_value=health_checker):
            register_default_health_checks()

        # Should have registered checks
        assert len(health_checker._checks) > 0
        assert "database" in health_checker._checks
        assert "redis" in health_checker._checks
        assert "vector_db" in health_checker._checks
        assert "ai_engine" in health_checker._checks

        # Check that critical flags are set correctly
        assert health_checker._checks["database"].critical is True
        assert health_checker._checks["redis"].critical is True
        assert health_checker._checks["vector_db"].critical is False
        assert health_checker._checks["ai_engine"].critical is False

    @pytest.mark.asyncio
    async def test_health_check_with_tags(self):
        """Test health checks with tags."""
        health_checker = HealthChecker()

        async def test_check():
            return HealthCheckResult("test", HealthStatus.HEALTHY, "OK")

        # Register check with tags
        health_check = HealthCheck(
            name="test",
            check_func=test_check,
            tags=["infrastructure", "database"]
        )
        health_checker.register_check(health_check)

        # Verify tags are stored
        assert health_checker._checks["test"].tags == [
            "infrastructure", "database"]
