"""Health check system for MESH components."""

import asyncio
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    response_time_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "response_time_ms": self.response_time_ms
        }


@dataclass
class HealthCheck:
    """Health check configuration."""
    name: str
    check_func: Callable[[], Awaitable[HealthCheckResult]]
    timeout_seconds: float = 5.0
    critical: bool = True
    tags: List[str] = field(default_factory=list)


class HealthChecker:
    """Centralized health checking system."""

    def __init__(self):
        """Initialize health checker."""
        self._checks: Dict[str, HealthCheck] = {}
        self._last_results: Dict[str, HealthCheckResult] = {}
        self._running = False

    def register_check(self, health_check: HealthCheck):
        """Register a health check."""
        self._checks[health_check.name] = health_check
        logger.info(f"Registered health check: {health_check.name}")

    def unregister_check(self, name: str):
        """Unregister a health check."""
        if name in self._checks:
            del self._checks[name]
            if name in self._last_results:
                del self._last_results[name]
            logger.info(f"Unregistered health check: {name}")

    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check."""
        if name not in self._checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check '{name}' not found"
            )

        check = self._checks[name]
        start_time = time.time()

        try:
            # Run the check with timeout
            result = await asyncio.wait_for(
                check.check_func(),
                timeout=check.timeout_seconds
            )
            result.response_time_ms = (time.time() - start_time) * 1000

        except asyncio.TimeoutError:
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {check.timeout_seconds}s",
                response_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000
            )
            logger.error(f"Health check '{name}' failed: {e}")

        # Cache the result
        self._last_results[name] = result
        return result

    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        if not self._checks:
            return {}

        # Run all checks concurrently
        tasks = [
            self.run_check(name) for name in self._checks.keys()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        check_results = {}
        for i, (name, result) in enumerate(zip(self._checks.keys(), results)):
            if isinstance(result, Exception):
                check_results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check exception: {str(result)}"
                )
            else:
                check_results[name] = result

        return check_results

    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        results = await self.run_all_checks()

        # Determine overall status
        overall_status = HealthStatus.HEALTHY
        critical_failures = []
        degraded_services = []

        for name, result in results.items():
            check = self._checks[name]

            if result.status == HealthStatus.UNHEALTHY:
                if check.critical:
                    overall_status = HealthStatus.UNHEALTHY
                    critical_failures.append(name)
                else:
                    if overall_status == HealthStatus.HEALTHY:
                        overall_status = HealthStatus.DEGRADED
                    degraded_services.append(name)

            elif result.status == HealthStatus.DEGRADED:
                if overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                degraded_services.append(name)

        # Calculate response times
        response_times = {
            name: result.response_time_ms
            for name, result in results.items()
            if result.response_time_ms is not None
        }

        avg_response_time = (
            sum(response_times.values()) / len(response_times)
            if response_times else 0
        )

        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {name: result.to_dict() for name, result in results.items()},
            "summary": {
                "total_checks": len(results),
                "healthy": sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY),
                "degraded": sum(1 for r in results.values() if r.status == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for r in results.values() if r.status == HealthStatus.UNHEALTHY),
                "critical_failures": critical_failures,
                "degraded_services": degraded_services,
                "average_response_time_ms": round(avg_response_time, 2)
            }
        }

    def get_cached_results(self) -> Dict[str, HealthCheckResult]:
        """Get cached health check results."""
        return self._last_results.copy()


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


# Built-in health checks
async def database_health_check() -> HealthCheckResult:
    """Check database connectivity."""
    try:
        from db.session import get_async_session

        async with get_async_session() as session:
            # Simple query to test connectivity
            result = await session.execute("SELECT 1")
            await result.fetchone()

        return HealthCheckResult(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Database connection successful",
            details={"type": "PostgreSQL"}
        )

    except Exception as e:
        return HealthCheckResult(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Database connection failed: {str(e)}",
            details={"error": str(e)}
        )


async def redis_health_check() -> HealthCheckResult:
    """Check Redis connectivity."""
    try:
        from db.redis_client import get_redis_client

        redis = await get_redis_client()
        await redis.ping()

        return HealthCheckResult(
            name="redis",
            status=HealthStatus.HEALTHY,
            message="Redis connection successful",
            details={"type": "Redis"}
        )

    except Exception as e:
        return HealthCheckResult(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Redis connection failed: {str(e)}",
            details={"error": str(e)}
        )


async def vector_db_health_check() -> HealthCheckResult:
    """Check vector database connectivity."""
    try:
        from services.vector_db.chroma_client import get_chroma_client

        client = await get_chroma_client()
        # Test basic operation
        collections = await client.list_collections()

        return HealthCheckResult(
            name="vector_db",
            status=HealthStatus.HEALTHY,
            message="Vector database connection successful",
            details={
                "type": "ChromaDB",
                "collections_count": len(collections)
            }
        )

    except Exception as e:
        return HealthCheckResult(
            name="vector_db",
            status=HealthStatus.UNHEALTHY,
            message=f"Vector database connection failed: {str(e)}",
            details={"error": str(e)}
        )


async def ai_engine_health_check() -> HealthCheckResult:
    """Check AI processing engine health."""
    try:
        from services.ai.engine import get_ai_processing_engine

        engine = await get_ai_processing_engine()
        health = await engine.health_check()

        if health.get("status") == "healthy":
            return HealthCheckResult(
                name="ai_engine",
                status=HealthStatus.HEALTHY,
                message="AI processing engine healthy",
                details=health
            )
        else:
            return HealthCheckResult(
                name="ai_engine",
                status=HealthStatus.DEGRADED,
                message="AI processing engine degraded",
                details=health
            )

    except Exception as e:
        return HealthCheckResult(
            name="ai_engine",
            status=HealthStatus.UNHEALTHY,
            message=f"AI engine health check failed: {str(e)}",
            details={"error": str(e)}
        )


def register_default_health_checks():
    """Register default health checks."""
    health_checker = get_health_checker()

    # Core infrastructure checks
    health_checker.register_check(HealthCheck(
        name="database",
        check_func=database_health_check,
        critical=True,
        tags=["infrastructure", "database"]
    ))

    health_checker.register_check(HealthCheck(
        name="redis",
        check_func=redis_health_check,
        critical=True,
        tags=["infrastructure", "cache"]
    ))

    health_checker.register_check(HealthCheck(
        name="vector_db",
        check_func=vector_db_health_check,
        critical=False,
        tags=["infrastructure", "ai"]
    ))

    health_checker.register_check(HealthCheck(
        name="ai_engine",
        check_func=ai_engine_health_check,
        critical=False,
        tags=["ai", "processing"]
    ))

    logger.info("Default health checks registered")
