"""Monitoring and observability API endpoints."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Response, HTTPException, Depends
from fastapi.responses import PlainTextResponse

from services.monitoring.metrics import get_metrics_collector
from services.monitoring.health import get_health_checker
from services.monitoring.logging import get_correlation_id, log_api_request
import time

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/metrics", response_class=PlainTextResponse)
async def get_metrics():
    """
    Get Prometheus metrics.

    Returns metrics in Prometheus format for scraping.
    """
    start_time = time.time()

    try:
        metrics_collector = get_metrics_collector()
        metrics_data = metrics_collector.get_metrics()

        duration_ms = (time.time() - start_time) * 1000
        log_api_request(logger, "GET", "/monitoring/metrics", 200, duration_ms)

        return Response(
            content=metrics_data,
            media_type=metrics_collector.get_content_type()
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log_api_request(logger, "GET", "/monitoring/metrics", 500, duration_ms)
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Metrics collection failed: {str(e)}")


@router.get("/health")
async def get_health() -> Dict[str, Any]:
    """
    Get system health status.

    Returns comprehensive health information for all system components.
    """
    start_time = time.time()

    try:
        health_checker = get_health_checker()
        health_data = await health_checker.get_system_health()

        duration_ms = (time.time() - start_time) * 1000

        # Determine HTTP status code based on health
        status_code = 200
        if health_data["status"] == "unhealthy":
            status_code = 503
        elif health_data["status"] == "degraded":
            status_code = 200  # Still operational

        log_api_request(logger, "GET", "/monitoring/health",
                        status_code, duration_ms)

        return health_data

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log_api_request(logger, "GET", "/monitoring/health", 500, duration_ms)
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/health/{component}")
async def get_component_health(component: str) -> Dict[str, Any]:
    """
    Get health status for a specific component.

    Args:
        component: Name of the component to check

    Returns:
        Health status for the specified component
    """
    start_time = time.time()

    try:
        health_checker = get_health_checker()
        result = await health_checker.run_check(component)

        duration_ms = (time.time() - start_time) * 1000

        # Determine HTTP status code based on health
        status_code = 200
        if result.status.value == "unhealthy":
            status_code = 503
        elif result.status.value == "degraded":
            status_code = 200

        log_api_request(
            logger, "GET", f"/monitoring/health/{component}", status_code, duration_ms)

        return result.to_dict()

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log_api_request(
            logger, "GET", f"/monitoring/health/{component}", 500, duration_ms)
        logger.error(f"Component health check failed for {component}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed for {component}: {str(e)}"
        )


@router.get("/health/cached/all")
async def get_cached_health() -> Dict[str, Any]:
    """
    Get cached health check results.

    Returns the last known health status without running new checks.
    Useful for high-frequency monitoring without impacting system performance.
    """
    start_time = time.time()

    try:
        health_checker = get_health_checker()
        cached_results = health_checker.get_cached_results()

        duration_ms = (time.time() - start_time) * 1000
        log_api_request(
            logger, "GET", "/monitoring/health/cached/all", 200, duration_ms)

        return {
            "cached_results": {
                name: result.to_dict()
                for name, result in cached_results.items()
            },
            "total_checks": len(cached_results),
            "correlation_id": get_correlation_id()
        }

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log_api_request(
            logger, "GET", "/monitoring/health/cached/all", 500, duration_ms)
        logger.error(f"Failed to get cached health results: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cached health results: {str(e)}"
        )


@router.post("/health/refresh")
async def refresh_health_checks() -> Dict[str, Any]:
    """
    Refresh all health checks.

    Forces a refresh of all health check results and returns the updated status.
    """
    start_time = time.time()

    try:
        health_checker = get_health_checker()
        health_data = await health_checker.get_system_health()

        duration_ms = (time.time() - start_time) * 1000
        log_api_request(
            logger, "POST", "/monitoring/health/refresh", 200, duration_ms)

        return {
            **health_data,
            "refreshed": True,
            "correlation_id": get_correlation_id()
        }

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log_api_request(
            logger, "POST", "/monitoring/health/refresh", 500, duration_ms)
        logger.error(f"Health refresh failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Health refresh failed: {str(e)}"
        )


@router.get("/status")
async def get_system_status() -> Dict[str, Any]:
    """
    Get high-level system status.

    Returns a simplified status overview suitable for load balancers and uptime monitoring.
    """
    start_time = time.time()

    try:
        health_checker = get_health_checker()
        health_data = await health_checker.get_system_health()

        duration_ms = (time.time() - start_time) * 1000

        # Simplified status response
        status_response = {
            "status": health_data["status"],
            "timestamp": health_data["timestamp"],
            "version": "1.0.0",
            "uptime_seconds": duration_ms / 1000,  # Placeholder
            "correlation_id": get_correlation_id(),
            "summary": health_data["summary"]
        }

        status_code = 200
        if health_data["status"] == "unhealthy":
            status_code = 503

        log_api_request(logger, "GET", "/monitoring/status",
                        status_code, duration_ms)

        return status_response

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log_api_request(logger, "GET", "/monitoring/status", 500, duration_ms)
        logger.error(f"System status check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"System status check failed: {str(e)}"
        )
