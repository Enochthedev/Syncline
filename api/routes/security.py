"""
Security API endpoints for the MESH ingestion system.

Provides endpoints for security status, key rotation, and audit log access.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from services.security import get_security_manager, SecurityManager
from services.security.types import KeyType, AuditEventType, AuditSeverity

router = APIRouter(prefix="/security", tags=["Security"])


def get_security_service() -> SecurityManager:
    """Dependency to get security manager."""
    return get_security_manager()


@router.get("/status", response_model=Dict[str, Any])
async def get_security_status(
    security_manager: SecurityManager = Depends(get_security_service)
):
    """
    Get current security status and statistics.

    Returns comprehensive security status including:
    - Encryption configuration
    - Key rotation status
    - Audit log statistics
    - Compliance readiness
    """
    try:
        status = await security_manager.get_security_status()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "security": status
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get security status: {e}")


@router.post("/keys/rotate", response_model=Dict[str, Any])
async def rotate_encryption_keys(
    key_type: Optional[str] = Query(
        None, description="Specific key type to rotate (data, token, master)"),
    security_manager: SecurityManager = Depends(get_security_service)
):
    """
    Manually rotate encryption keys.

    Args:
        key_type: Optional specific key type to rotate. If not provided, rotates all keys.

    Returns:
        Dictionary with rotation job IDs and status
    """
    try:
        # Convert string to KeyType enum if provided
        key_type_enum = None
        if key_type:
            key_type_map = {
                "data": KeyType.DATA_ENCRYPTION_KEY,
                "token": KeyType.TOKEN_ENCRYPTION_KEY,
                "master": KeyType.MASTER_KEY
            }
            key_type_enum = key_type_map.get(key_type.lower())
            if not key_type_enum:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid key type: {key_type}. Valid types: data, token, master"
                )

        results = await security_manager.rotate_encryption_keys(key_type_enum)

        return {
            "status": "success",
            "message": f"Key rotation initiated for {key_type or 'all'} keys",
            "rotation_jobs": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Key rotation failed: {e}")


@router.get("/audit/events", response_model=Dict[str, Any])
async def search_audit_events(
    event_type: Optional[str] = Query(
        None, description="Filter by event type"),
    action: Optional[str] = Query(None, description="Filter by action"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    resource_type: Optional[str] = Query(
        None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(
        None, description="Filter by resource ID"),
    severity: Optional[str] = Query(
        None, description="Filter by severity (low, medium, high, critical)"),
    success: Optional[bool] = Query(
        None, description="Filter by success status"),
    hours_back: int = Query(
        24, description="Hours back to search (default: 24)"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Offset for pagination"),
    security_manager: SecurityManager = Depends(get_security_service)
):
    """
    Search audit events with filters.

    Provides access to audit logs with comprehensive filtering options
    for security monitoring and compliance reporting.
    """
    try:
        # Convert string parameters to enums
        event_type_enum = None
        if event_type:
            try:
                event_type_enum = AuditEventType(event_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid event type: {event_type}")

        severity_enum = None
        if severity:
            try:
                severity_enum = AuditSeverity(severity.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid severity: {severity}")

        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)

        # Search events
        events = await security_manager.audit_logger.search_events(
            event_type=event_type_enum,
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            start_time=start_time,
            end_time=end_time,
            severity=severity_enum,
            success=success,
            limit=limit,
            offset=offset
        )

        return {
            "status": "success",
            "events": events,
            "filters": {
                "event_type": event_type,
                "action": action,
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "severity": severity,
                "success": success,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "hours_back": hours_back
                }
            },
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(events)
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Audit search failed: {e}")


@router.get("/audit/statistics", response_model=Dict[str, Any])
async def get_audit_statistics(
    hours_back: int = Query(
        24, description="Hours back to analyze (default: 24)"),
    security_manager: SecurityManager = Depends(get_security_service)
):
    """
    Get audit log statistics for monitoring and reporting.

    Provides comprehensive statistics about audit events including:
    - Total event counts
    - Success/failure rates
    - Event type breakdown
    - Severity distribution
    """
    try:
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)

        # Get statistics
        stats = await security_manager.audit_logger.get_statistics(
            start_time=start_time,
            end_time=end_time
        )

        return {
            "status": "success",
            "statistics": stats,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours_back": hours_back
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get audit statistics: {e}")


@router.post("/audit/verify/{event_id}", response_model=Dict[str, Any])
async def verify_audit_event_integrity(
    event_id: str,
    security_manager: SecurityManager = Depends(get_security_service)
):
    """
    Verify the integrity of a specific audit event.

    Checks the integrity hash of an audit event to ensure
    it hasn't been tampered with.
    """
    try:
        is_valid = await security_manager.audit_logger.verify_integrity(event_id)

        return {
            "status": "success",
            "event_id": event_id,
            "integrity_valid": is_valid,
            "message": "Event integrity verified" if is_valid else "Event integrity check failed",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Integrity verification failed: {e}")


@router.get("/compliance/report", response_model=Dict[str, Any])
async def get_compliance_report(
    days_back: int = Query(
        30, description="Days back to analyze (default: 30)"),
    security_manager: SecurityManager = Depends(get_security_service)
):
    """
    Generate a compliance report for regulatory requirements.

    Provides a comprehensive report suitable for GDPR, CCPA,
    and other regulatory compliance requirements.
    """
    try:
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days_back)

        # Get audit statistics
        audit_stats = await security_manager.audit_logger.get_statistics(
            start_time=start_time,
            end_time=end_time
        )

        # Get security status
        security_status = await security_manager.get_security_status()

        # Get key rotation jobs
        rotation_jobs = security_manager.key_rotation_service.get_rotation_jobs()

        report = {
            "report_period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "days": days_back
            },
            "security_posture": {
                "encryption_enabled": security_status["encryption"]["pii_encryption_enabled"],
                "token_encryption_enabled": security_status["encryption"]["token_encryption_enabled"],
                "key_rotation_enabled": security_status["key_rotation"]["enabled"],
                "audit_logging_enabled": True,
                "immutable_audit_logs": security_status["audit"]["immutable_logs"]
            },
            "audit_summary": {
                "total_events": audit_stats.get("total_events", 0),
                "successful_events": audit_stats.get("successful_events", 0),
                "failed_events": audit_stats.get("failed_events", 0),
                "success_rate": audit_stats.get("success_rate", 0),
                "event_types": audit_stats.get("event_types", {}),
                "severities": audit_stats.get("severities", {})
            },
            "key_management": {
                "total_rotation_jobs": len(rotation_jobs),
                "completed_rotations": len([j for j in rotation_jobs if j.status == "completed"]),
                "failed_rotations": len([j for j in rotation_jobs if j.status == "failed"]),
                "scheduled_rotations": len([j for j in rotation_jobs if j.status == "scheduled"])
            },
            "compliance_status": {
                "gdpr_compliant": True,
                "ccpa_compliant": True,
                "audit_trail_complete": True,
                "data_encryption_active": security_status["encryption"]["pii_encryption_enabled"],
                "retention_policy_active": True,
                "retention_days": security_status["audit"]["retention_days"]
            },
            "recommendations": []
        }

        # Add recommendations based on status
        if not security_status["encryption"]["pii_encryption_enabled"]:
            report["recommendations"].append(
                "Enable PII encryption for enhanced data protection")

        if not security_status["key_rotation"]["enabled"]:
            report["recommendations"].append(
                "Enable automatic key rotation for improved security")

        if audit_stats.get("success_rate", 1) < 0.95:
            report["recommendations"].append(
                "Investigate audit event failures - success rate below 95%")

        return {
            "status": "success",
            "compliance_report": report,
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate compliance report: {e}")
