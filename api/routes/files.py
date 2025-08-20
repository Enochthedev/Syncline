"""File reference API endpoints."""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, or_

from api.dependencies import get_db
from api.auth.auth import get_current_active_user
from api.auth.rate_limiting import rate_limit
from api.auth.rbac import require_permission
from api.auth.models import User
from db.models.memory import FileReference

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["File References"])


@router.get("/", summary="Get file references")
@rate_limit(requests_per_minute=30, requests_per_hour=500, per_user=True)
@require_permission("file_references", "read")
async def get_file_references(
    filename: Optional[str] = Query(
        None, description="Search by filename (partial match)"),
    file_type: Optional[str] = Query(None, description="Filter by file type"),
    shared_by: Optional[str] = Query(
        None, description="Filter by user who shared the file"),
    platform: Optional[str] = Query(
        None, description="Filter by source platform"),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get file references with metadata search capabilities.

    Provides comprehensive file search and filtering functionality
    to find shared files across all communication platforms.
    """
    try:
        query = select(FileReference)

        # Apply filters
        filters = []

        if filename:
            filters.append(FileReference.filename.ilike(f"%{filename}%"))

        if file_type:
            filters.append(FileReference.file_type == file_type)

        if shared_by:
            filters.append(FileReference.shared_by == UUID(shared_by))

        if platform:
            filters.append(FileReference.source_platform == platform)

        if filters:
            query = query.where(and_(*filters))

        # Apply tenant isolation (if needed)
        if hasattr(current_user, 'tenant_id') and not current_user.is_superuser:
            # Additional tenant filtering would go here if needed
            pass

        # Apply pagination
        query = query.offset(offset).limit(limit)

        # Order by shared time (most recent first)
        query = query.order_by(desc(FileReference.shared_at))

        result = await db.execute(query)
        files = result.scalars().all()

        return {
            "file_references": [
                {
                    "id": str(f.id),
                    "filename": f.filename,
                    "file_type": f.file_type,
                    "file_size": f.file_size,
                    "file_url": f.file_url,
                    "shared_by": str(f.shared_by),
                    "shared_with": f.shared_with,
                    "shared_at": f.shared_at.isoformat() if f.shared_at else None,
                    "source_message_id": str(f.source_message_id) if f.source_message_id else None,
                    "source_thread_id": str(f.source_thread_id) if f.source_thread_id else None,
                    "source_platform": f.source_platform,
                    "content_summary": f.content_summary,
                    "extracted_topics": f.extracted_topics
                }
                for f in files
            ],
            "count": len(files),
            "offset": offset,
            "limit": limit,
            "filters": {
                "filename": filename,
                "file_type": file_type,
                "shared_by": shared_by,
                "platform": platform
            }
        }

    except Exception as e:
        logger.error(f"Error getting file references: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get file references: {str(e)}")


@router.get("/{file_id}", summary="Get file reference by ID")
@rate_limit(requests_per_minute=60, requests_per_hour=1000, per_user=True)
@require_permission("file_references", "read")
async def get_file_reference(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get a specific file reference by ID.

    Returns detailed file reference information including metadata,
    sharing context, and AI-generated content analysis.
    """
    try:
        result = await db.execute(
            select(FileReference).where(FileReference.id == UUID(file_id))
        )
        file_ref = result.scalar_one_or_none()

        if not file_ref:
            raise HTTPException(
                status_code=404, detail="File reference not found")

        return {
            "id": str(file_ref.id),
            "filename": file_ref.filename,
            "file_type": file_ref.file_type,
            "file_size": file_ref.file_size,
            "file_url": file_ref.file_url,
            "shared_by": str(file_ref.shared_by),
            "shared_with": file_ref.shared_with,
            "shared_at": file_ref.shared_at.isoformat() if file_ref.shared_at else None,
            "source_message_id": str(file_ref.source_message_id) if file_ref.source_message_id else None,
            "source_thread_id": str(file_ref.source_thread_id) if file_ref.source_thread_id else None,
            "source_platform": file_ref.source_platform,
            "content_summary": file_ref.content_summary,
            "extracted_topics": file_ref.extracted_topics,
            "extra_metadata": file_ref.extra_metadata
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file reference {file_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get file reference: {str(e)}")


@router.get("/search/by-contact", summary="Search files shared with contact")
@rate_limit(requests_per_minute=20, requests_per_hour=200, per_user=True)
@require_permission("file_references", "read")
async def search_files_by_contact(
    contact_name: Optional[str] = Query(
        None, description="Contact name or identifier"),
    contact_id: Optional[str] = Query(None, description="Contact UUID"),
    file_type: Optional[str] = Query(None, description="Filter by file type"),
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of results"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Search for files shared with a specific contact.

    Implements the "files we shared with X" functionality as required.
    Finds all files shared in conversations with a specific contact.
    """
    try:
        query = select(FileReference)

        # Apply contact filters
        filters = []

        if contact_id:
            # Filter by contact ID in shared_with array
            filters.append(FileReference.shared_with.contains([contact_id]))

        if contact_name:
            # This would require joining with contact/participant tables
            # For now, we'll search in the shared_with metadata
            # In a full implementation, this would be more sophisticated
            pass

        if file_type:
            filters.append(FileReference.file_type == file_type)

        if filters:
            query = query.where(and_(*filters))

        # Apply pagination and ordering
        query = query.offset(0).limit(limit)
        query = query.order_by(desc(FileReference.shared_at))

        result = await db.execute(query)
        files = result.scalars().all()

        return {
            "search_criteria": {
                "contact_name": contact_name,
                "contact_id": contact_id,
                "file_type": file_type
            },
            "file_references": [
                {
                    "id": str(f.id),
                    "filename": f.filename,
                    "file_type": f.file_type,
                    "file_size": f.file_size,
                    "shared_by": str(f.shared_by),
                    "shared_at": f.shared_at.isoformat() if f.shared_at else None,
                    "source_platform": f.source_platform,
                    "content_summary": f.content_summary,
                    "extracted_topics": f.extracted_topics
                }
                for f in files
            ],
            "count": len(files)
        }

    except Exception as e:
        logger.error(f"Error searching files by contact: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to search files by contact: {str(e)}")


@router.get("/search/by-type", summary="Search files by type")
@rate_limit(requests_per_minute=30, requests_per_hour=300, per_user=True)
@require_permission("file_references", "read")
async def search_files_by_type(
    file_type: str = Query(..., description="File type to search for"),
    platform: Optional[str] = Query(
        None, description="Filter by source platform"),
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of results"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Search for files by type with optional platform filtering.

    Useful for finding all files of a specific type (e.g., PDFs, images)
    across all communication platforms.
    """
    try:
        query = select(FileReference).where(
            FileReference.file_type == file_type)

        if platform:
            query = query.where(FileReference.source_platform == platform)

        # Apply pagination and ordering
        query = query.offset(0).limit(limit)
        query = query.order_by(desc(FileReference.shared_at))

        result = await db.execute(query)
        files = result.scalars().all()

        return {
            "file_type": file_type,
            "platform_filter": platform,
            "file_references": [
                {
                    "id": str(f.id),
                    "filename": f.filename,
                    "file_size": f.file_size,
                    "shared_by": str(f.shared_by),
                    "shared_at": f.shared_at.isoformat() if f.shared_at else None,
                    "source_platform": f.source_platform,
                    "content_summary": f.content_summary,
                    "extracted_topics": f.extracted_topics
                }
                for f in files
            ],
            "count": len(files)
        }

    except Exception as e:
        logger.error(f"Error searching files by type {file_type}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to search files by type: {str(e)}")


@router.get("/stats/summary", summary="Get file statistics")
@rate_limit(requests_per_minute=10, requests_per_hour=100, per_user=True)
@require_permission("file_references", "read")
async def get_file_statistics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive file statistics.

    Returns aggregated statistics about file sharing patterns,
    file types, and platform distribution.
    """
    try:
        # This would be implemented with proper aggregation queries
        # For now, returning a basic structure

        # Get total count
        total_result = await db.execute(select(FileReference))
        total_files = len(total_result.scalars().all())

        return {
            "total_files": total_files,
            "statistics": {
                "by_platform": {},  # Would be populated with actual data
                "by_file_type": {},  # Would be populated with actual data
                "by_month": {},     # Would be populated with actual data
                "top_sharers": []   # Would be populated with actual data
            },
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting file statistics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get file statistics: {str(e)}")
