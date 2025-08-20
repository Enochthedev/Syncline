"""Contact dossier API endpoints."""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from api.dependencies import get_db
from api.auth.auth import get_current_active_user
from api.auth.rate_limiting import rate_limit
from api.auth.rbac import require_permission
from api.auth.models import User
from db.models.memory import ContactDossier

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contact-dossiers", tags=["Contact Dossiers"])


@router.get("/", summary="Get contact dossiers")
@rate_limit(requests_per_minute=30, requests_per_hour=500, per_user=True)
@require_permission("contact_dossiers", "read")
async def get_contact_dossiers(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get contact dossiers with optional filtering and pagination.

    Provides access to AI-generated contact dossiers with relationship insights,
    communication patterns, and suggested actions.
    """
    try:
        query = select(ContactDossier)

        # Apply user filter (default to current user if not specified and not admin)
        if user_id:
            if not current_user.is_superuser and str(current_user.id) != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: Can only access your own contact dossiers"
                )
            query = query.where(ContactDossier.user_id == UUID(user_id))
        else:
            # Default to current user's dossiers
            query = query.where(ContactDossier.user_id == current_user.id)

        # Apply tenant isolation
        if hasattr(current_user, 'tenant_id') and not current_user.is_superuser:
            # Additional tenant filtering would go here if needed
            pass

        # Apply pagination
        query = query.offset(offset).limit(limit)

        # Order by last updated
        query = query.order_by(desc(ContactDossier.last_updated))

        result = await db.execute(query)
        dossiers = result.scalars().all()

        return {
            "contact_dossiers": [
                {
                    "id": str(d.id),
                    "contact_id": str(d.contact_id),
                    "user_id": str(d.user_id),
                    "first_interaction": d.first_interaction.isoformat() if d.first_interaction else None,
                    "last_interaction": d.last_interaction.isoformat() if d.last_interaction else None,
                    "total_messages": d.total_messages,
                    "total_threads": d.total_threads,
                    "relationship_strength": d.relationship_strength,
                    "communication_style": d.communication_style,
                    "interaction_frequency": d.interaction_frequency,
                    "key_topics": d.key_topics,
                    "common_entities": d.common_entities,
                    "summary": d.summary,
                    "personality_insights": d.personality_insights,
                    "suggested_actions": d.suggested_actions,
                    "generated_at": d.generated_at.isoformat() if d.generated_at else None,
                    "last_updated": d.last_updated.isoformat() if d.last_updated else None
                }
                for d in dossiers
            ],
            "count": len(dossiers),
            "offset": offset,
            "limit": limit,
            "user_filter": user_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting contact dossiers: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get contact dossiers: {str(e)}")


@router.get("/{dossier_id}", summary="Get contact dossier by ID")
@rate_limit(requests_per_minute=60, requests_per_hour=1000, per_user=True)
@require_permission("contact_dossiers", "read")
async def get_contact_dossier(
    dossier_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get a specific contact dossier by ID.

    Returns detailed contact dossier information including relationship insights,
    communication patterns, and AI-generated recommendations.
    """
    try:
        result = await db.execute(
            select(ContactDossier).where(ContactDossier.id == UUID(dossier_id))
        )
        dossier = result.scalar_one_or_none()

        if not dossier:
            raise HTTPException(
                status_code=404, detail="Contact dossier not found")

        # Check access permissions
        if not current_user.is_superuser and dossier.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Can only access your own contact dossiers"
            )

        return {
            "id": str(dossier.id),
            "contact_id": str(dossier.contact_id),
            "user_id": str(dossier.user_id),
            "first_interaction": dossier.first_interaction.isoformat() if dossier.first_interaction else None,
            "last_interaction": dossier.last_interaction.isoformat() if dossier.last_interaction else None,
            "total_messages": dossier.total_messages,
            "total_threads": dossier.total_threads,
            "relationship_strength": dossier.relationship_strength,
            "communication_style": dossier.communication_style,
            "interaction_frequency": dossier.interaction_frequency,
            "key_topics": dossier.key_topics,
            "common_entities": dossier.common_entities,
            "summary": dossier.summary,
            "personality_insights": dossier.personality_insights,
            "suggested_actions": dossier.suggested_actions,
            "generated_at": dossier.generated_at.isoformat() if dossier.generated_at else None,
            "last_updated": dossier.last_updated.isoformat() if dossier.last_updated else None,
            "extra_metadata": dossier.extra_metadata
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting contact dossier {dossier_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get contact dossier: {str(e)}")


@router.get("/{dossier_id}/summary", summary="Get contact dossier summary")
@rate_limit(requests_per_minute=30, requests_per_hour=300, per_user=True)
@require_permission("contact_dossiers", "read")
async def get_contact_dossier_summary(
    dossier_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get a condensed summary of a contact dossier.

    Returns key insights and relationship information in a compact format
    suitable for quick reference or dashboard display.
    """
    try:
        result = await db.execute(
            select(ContactDossier).where(ContactDossier.id == UUID(dossier_id))
        )
        dossier = result.scalar_one_or_none()

        if not dossier:
            raise HTTPException(
                status_code=404, detail="Contact dossier not found")

        # Check access permissions
        if not current_user.is_superuser and dossier.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Can only access your own contact dossiers"
            )

        return {
            "id": str(dossier.id),
            "contact_id": str(dossier.contact_id),
            "relationship_strength": dossier.relationship_strength,
            "communication_style": dossier.communication_style,
            "interaction_frequency": dossier.interaction_frequency,
            "total_messages": dossier.total_messages,
            "total_threads": dossier.total_threads,
            # Top 5 topics
            "key_topics": dossier.key_topics[:5] if dossier.key_topics else [],
            "summary": dossier.summary,
            # Top 3 actions
            "top_suggested_actions": dossier.suggested_actions[:3] if dossier.suggested_actions else [],
            "last_interaction": dossier.last_interaction.isoformat() if dossier.last_interaction else None,
            "last_updated": dossier.last_updated.isoformat() if dossier.last_updated else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting contact dossier summary {dossier_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get contact dossier summary: {str(e)}")
