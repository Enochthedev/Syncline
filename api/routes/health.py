"""Health check and system status routes."""

import time
import logging
from fastapi import APIRouter
from typing import Dict, Any

from services.monitoring.health import get_health_checker
from services.monitoring.logging import log_api_request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", summary="Basic health check")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.

    Returns:
        Dict containing system status
    """
    start_time = time.time()

    try:
        health_checker = get_health_checker()
        health_data = await health_checker.get_system_health()

        # Simplified response for basic health check
        basic_status = {
            "status": health_data["status"],
            "timestamp": health_data["timestamp"],
            "database": "connected" if any(
                check["status"] == "healthy" and check["name"] == "database"
                for check in health_data["checks"].values()
            ) else "disconnected",
            "redis": "connected" if any(
                check["status"] == "healthy" and check["name"] == "redis"
                for check in health_data["checks"].values()
            ) else "disconnected"
        }

        duration_ms = (time.time() - start_time) * 1000
        log_api_request(logger, "GET", "/health/", 200, duration_ms)

        return basic_status

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log_api_request(logger, "GET", "/health/", 500, duration_ms)
        logger.error(f"Basic health check failed: {e}")

        return {
            "status": "unhealthy",
            "database": "unknown",
            "redis": "unknown",
            "error": str(e)
        }


@router.get("/detailed", summary="Detailed health check")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with more system information.

    Returns:
        Dict containing detailed system status
    """
    start_time = time.time()

    try:
        health_checker = get_health_checker()
        health_data = await health_checker.get_system_health()

        # Enhanced detailed response
        detailed_status = {
            "status": health_data["status"],
            "version": "1.0.0",
            "timestamp": health_data["timestamp"],
            "services": {},
            "features": {
                "message_ingestion": "enabled",
                "ai_processing": "enabled",
                "real_time_streaming": "enabled",
                "vector_search": "enabled",
                "multi_platform_connectors": "enabled"
            },
            "summary": health_data["summary"],
            "checks": health_data["checks"]
        }

        # Map health checks to services
        for check_name, check_result in health_data["checks"].items():
            if check_name == "database":
                detailed_status["services"]["database"] = {
                    "status": check_result["status"],
                    "type": "PostgreSQL",
                    "response_time_ms": check_result.get("response_time_ms")
                }
            elif check_name == "redis":
                detailed_status["services"]["redis"] = {
                    "status": check_result["status"],
                    "type": "Redis",
                    "response_time_ms": check_result.get("response_time_ms")
                }
            elif check_name == "vector_db":
                detailed_status["services"]["vector_db"] = {
                    "status": check_result["status"],
                    "type": "ChromaDB",
                    "response_time_ms": check_result.get("response_time_ms")
                }
            elif check_name == "ai_engine":
                detailed_status["services"]["ai_engine"] = {
                    "status": check_result["status"],
                    "type": "AI Processing Engine",
                    "response_time_ms": check_result.get("response_time_ms")
                }

        duration_ms = (time.time() - start_time) * 1000
        log_api_request(logger, "GET", "/health/detailed", 200, duration_ms)

        return detailed_status

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log_api_request(logger, "GET", "/health/detailed", 500, duration_ms)
        logger.error(f"Detailed health check failed: {e}")

        return {
            "status": "unhealthy",
            "version": "1.0.0",
            "services": {
                "database": {"status": "unknown", "type": "PostgreSQL"},
                "redis": {"status": "unknown", "type": "Redis"}
            },
            "features": {
                "message_ingestion": "unknown",
                "ai_processing": "unknown",
                "real_time_streaming": "unknown"
            },
            "error": str(e)
        }
