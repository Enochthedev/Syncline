"""Contact intelligence API endpoints."""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from api.dependencies import get_db
from api.auth.auth import get_current_active_user
from api.auth.rate_limiting import rate_limit
from api.auth.rbac import require_permission
from api.auth.models import User
from services.contacts.contact_manager import ContactManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contacts", tags=["Contact Intelligence"])


# Pydantic models for request/response
class ContactIdentityCreate(BaseModel):
    platform: str = Field(...,
                          description="Platform name (e.g., 'gmail', 'slack')")
    platform_user_id: str = Field(..., description="Platform-specific user ID")
    platform_handle: Optional[str] = Field(
        None, description="Platform handle/username")
    display_name: Optional[str] = Field(
        None, description="Display name on platform")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    profile_url: Optional[str] = Field(None, description="Profile URL")
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")
    is_verified: bool = Field(
        False, description="Whether identity is verified")
    platform_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Platform-specific metadata")


class ContactCreate(BaseModel):
    primary_name: str = Field(..., description="Primary contact name")
    display_name: Optional[str] = Field(None, description="Display name")
    primary_email: Optional[str] = Field(
        None, description="Primary email address")
    primary_phone: Optional[str] = Field(
        None, description="Primary phone number")
    profile_photo_url: Optional[str] = Field(
        None, description="Profile photo URL")
    identities: List[ContactIdentityCreate] = Field(
        ..., description="Platform identities")
    custom_notes: Optional[str] = Field(None, description="Custom notes")
    tags: List[str] = Field(default_factory=list, description="Contact tags")
    is_favorite: bool = Field(False, description="Whether contact is favorite")
    notification_enabled: bool = Field(
        True, description="Enable notifications")
    preferred_communication_platform: Optional[str] = Field(
        None, description="Preferred platform")
    extra_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata")


class ContactUpdate(BaseModel):
    primary_name: Optional[str] = Field(
        None, description="Primary contact name")
    display_name: Optional[str] = Field(None, description="Display name")
    primary_email: Optional[str] = Field(
        None, description="Primary email address")
    primary_phone: Optional[str] = Field(
        None, description="Primary phone number")
    profile_photo_url: Optional[str] = Field(
        None, description="Profile photo URL")
    custom_notes: Optional[str] = Field(None, description="Custom notes")
    tags: Optional[List[str]] = Field(None, description="Contact tags")
    is_favorite: Optional[bool] = Field(
        None, description="Whether contact is favorite")
    is_archived: Optional[bool] = Field(
        None, description="Whether contact is archived")


class ContactPreferencesUpdate(BaseModel):
    notification_enabled: Optional[bool] = Field(
        None, description="Enable notifications")
    preferred_communication_platform: Optional[str] = Field(
        None, description="Preferred platform")
    reminder_frequency: Optional[str] = Field(
        None, description="Reminder frequency")
    share_presence: Optional[bool] = Field(
        None, description="Share presence status")
    share_read_receipts: Optional[bool] = Field(
        None, description="Share read receipts")
    auto_reply_enabled: Optional[bool] = Field(
        None, description="Enable auto-reply")
    auto_reply_message: Optional[str] = Field(
        None, description="Auto-reply message")


class ContactMergeRequest(BaseModel):
    primary_contact_id: str = Field(...,
                                    description="ID of primary contact to keep")
    duplicate_contact_ids: List[str] = Field(
        ..., description="IDs of duplicate contacts to merge")


class ContactSearchFilters(BaseModel):
    platforms: Optional[List[str]] = Field(
        None, description="Filter by platforms")
    is_favorite: Optional[bool] = Field(
        None, description="Filter by favorite status")
    relationship_strength_min: Optional[float] = Field(
        None, description="Minimum relationship strength")
    communication_frequency: Optional[List[str]] = Field(
        None, description="Communication frequency categories")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    last_interaction_days: Optional[int] = Field(
        None, description="Days since last interaction")


@router.get("/search", summary="Search contacts")
@rate_limit(requests_per_minute=60, requests_per_hour=1000, per_user=True)
@require_permission("contacts", "read")
async def search_contacts(
    q: str = Query("", description="Search query"),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    platforms: Optional[str] = Query(
        None, description="Comma-separated list of platforms"),
    is_favorite: Optional[bool] = Query(
        None, description="Filter by favorite status"),
    relationship_strength_min: Optional[float] = Query(
        None, ge=0.0, le=1.0, description="Minimum relationship strength"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Search contacts with intelligent fuzzy matching and filtering.

    Supports searching by:
    - Name (fuzzy matching)
    - Email address
    - Phone number
    - Platform handles
    """
    try:
        contact_manager = ContactManager(db)

        # Build filters
        filters = {}
        if platforms:
            filters["platforms"] = [p.strip() for p in platforms.split(",")]
        if is_favorite is not None:
            filters["is_favorite"] = is_favorite
        if relationship_strength_min is not None:
            filters["relationship_strength_min"] = relationship_strength_min

        # Get tenant_id from user (assuming it's available)
        tenant_id = getattr(current_user, 'tenant_id', current_user.id)

        contacts = await contact_manager.search_contacts(
            query=q,
            tenant_id=tenant_id,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
            filters=filters
        )

        # Convert to response format
        contact_data = []
        for contact in contacts:
            contact_dict = {
                "id": str(contact.id),
                "primary_name": contact.primary_name,
                "display_name": contact.display_name,
                "primary_email": contact.primary_email,
                "primary_phone": contact.primary_phone,
                "profile_photo_url": contact.profile_photo_url,
                "last_interaction": contact.last_interaction.isoformat() if contact.last_interaction else None,
                "total_messages": contact.total_messages,
                "total_threads": contact.total_threads,
                "platforms": contact.platforms,
                "preferred_platform": contact.preferred_platform,
                "relationship_strength": contact.relationship_strength,
                "communication_frequency": contact.communication_frequency,
                "is_favorite": contact.is_favorite,
                "is_archived": contact.is_archived,
                "tags": contact.tags,
                "identities": [
                    {
                        "platform": identity.platform,
                        "platform_user_id": identity.platform_user_id,
                        "platform_handle": identity.platform_handle,
                        "display_name": identity.display_name,
                        "email": identity.email,
                        "phone": identity.phone,
                        "is_verified": identity.is_verified
                    }
                    for identity in contact.identities
                ],
                "created_at": contact.created_at.isoformat() if contact.created_at else None,
                "updated_at": contact.updated_at.isoformat() if contact.updated_at else None
            }
            contact_data.append(contact_dict)

        return {
            "contacts": contact_data,
            "count": len(contact_data),
            "offset": offset,
            "limit": limit,
            "query": q,
            "filters": filters
        }

    except Exception as e:
        logger.error(f"Error searching contacts: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to search contacts: {str(e)}")


@router.get("/{contact_id}", summary="Get contact by ID")
@rate_limit(requests_per_minute=120, requests_per_hour=2000, per_user=True)
@require_permission("contacts", "read")
async def get_contact(
    contact_id: str,
    include_insights: bool = Query(
        True, description="Include AI-generated insights"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get detailed contact information by ID."""
    try:
        contact_manager = ContactManager(db)
        tenant_id = getattr(current_user, 'tenant_id', current_user.id)

        contact = await contact_manager.get_contact(
            contact_id=UUID(contact_id),
            tenant_id=tenant_id,
            user_id=current_user.id,
            include_insights=include_insights
        )

        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")

        # Build response
        contact_dict = {
            "id": str(contact.id),
            "primary_name": contact.primary_name,
            "display_name": contact.display_name,
            "primary_email": contact.primary_email,
            "primary_phone": contact.primary_phone,
            "profile_photo_url": contact.profile_photo_url,
            "first_interaction": contact.first_interaction.isoformat() if contact.first_interaction else None,
            "last_interaction": contact.last_interaction.isoformat() if contact.last_interaction else None,
            "total_messages": contact.total_messages,
            "total_threads": contact.total_threads,
            "platforms": contact.platforms,
            "preferred_platform": contact.preferred_platform,
            "relationship_strength": contact.relationship_strength,
            "communication_frequency": contact.communication_frequency,
            "response_time_avg": contact.response_time_avg,
            "sentiment_score": contact.sentiment_score,
            "top_topics": contact.top_topics,
            "common_entities": contact.common_entities,
            "shared_interests": contact.shared_interests,
            "mutual_contacts": contact.mutual_contacts,
            "interaction_patterns": contact.interaction_patterns,
            "custom_notes": contact.custom_notes,
            "tags": contact.tags,
            "is_favorite": contact.is_favorite,
            "is_archived": contact.is_archived,
            "notification_preferences": contact.notification_preferences,
            "identities": [
                {
                    "id": str(identity.id),
                    "platform": identity.platform,
                    "platform_user_id": identity.platform_user_id,
                    "platform_handle": identity.platform_handle,
                    "display_name": identity.display_name,
                    "email": identity.email,
                    "phone": identity.phone,
                    "profile_url": identity.profile_url,
                    "avatar_url": identity.avatar_url,
                    "is_verified": identity.is_verified,
                    "is_active": identity.is_active,
                    "last_seen": identity.last_seen.isoformat() if identity.last_seen else None,
                    "platform_metadata": identity.platform_metadata
                }
                for identity in contact.identities
            ],
            "created_at": contact.created_at.isoformat() if contact.created_at else None,
            "updated_at": contact.updated_at.isoformat() if contact.updated_at else None,
            "last_sync_at": contact.last_sync_at.isoformat() if contact.last_sync_at else None,
            "extra_metadata": contact.extra_metadata
        }

        # Add insights if requested and available
        if include_insights and hasattr(contact, 'insights') and contact.insights:
            contact_dict["insights"] = [
                {
                    "id": str(insight.id),
                    "insight_type": insight.insight_type,
                    "title": insight.title,
                    "description": insight.description,
                    "confidence_score": insight.confidence_score,
                    "supporting_data": insight.supporting_data,
                    "suggested_actions": insight.suggested_actions,
                    "generated_at": insight.generated_at.isoformat() if insight.generated_at else None,
                    "expires_at": insight.expires_at.isoformat() if insight.expires_at else None,
                    "is_active": insight.is_active,
                    "user_feedback": insight.user_feedback
                }
                for insight in contact.insights if insight.is_active
            ]

        # Add preferences if available
        if hasattr(contact, 'preferences') and contact.preferences:
            prefs = contact.preferences[0] if contact.preferences else None
            if prefs:
                contact_dict["preferences"] = {
                    "notification_enabled": prefs.notification_enabled,
                    "preferred_communication_platform": prefs.preferred_communication_platform,
                    "reminder_frequency": prefs.reminder_frequency,
                    "custom_ringtone": prefs.custom_ringtone,
                    "custom_notification_sound": prefs.custom_notification_sound,
                    "share_presence": prefs.share_presence,
                    "share_read_receipts": prefs.share_read_receipts,
                    "auto_reply_enabled": prefs.auto_reply_enabled,
                    "auto_reply_message": prefs.auto_reply_message
                }

        return contact_dict

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting contact {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get contact: {str(e)}")


@router.post("/", summary="Create new contact")
@rate_limit(requests_per_minute=30, requests_per_hour=200, per_user=True)
@require_permission("contacts", "create")
async def create_contact(
    contact_data: ContactCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new unified contact with platform identities."""
    try:
        contact_manager = ContactManager(db)
        tenant_id = getattr(current_user, 'tenant_id', current_user.id)

        # Convert identities to dict format
        identities = [identity.dict() for identity in contact_data.identities]

        contact = await contact_manager.create_contact(
            tenant_id=tenant_id,
            user_id=current_user.id,
            primary_name=contact_data.primary_name,
            identities=identities,
            display_name=contact_data.display_name,
            primary_email=contact_data.primary_email,
            primary_phone=contact_data.primary_phone,
            profile_photo_url=contact_data.profile_photo_url,
            custom_notes=contact_data.custom_notes,
            tags=contact_data.tags,
            is_favorite=contact_data.is_favorite,
            notification_enabled=contact_data.notification_enabled,
            preferred_communication_platform=contact_data.preferred_communication_platform,
            extra_metadata=contact_data.extra_metadata
        )

        return {
            "id": str(contact.id),
            "primary_name": contact.primary_name,
            "display_name": contact.display_name,
            "primary_email": contact.primary_email,
            "is_favorite": contact.is_favorite,
            "created_at": contact.created_at.isoformat() if contact.created_at else None,
            "message": "Contact created successfully"
        }

    except Exception as e:
        logger.error(f"Error creating contact: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create contact: {str(e)}")


@router.put("/{contact_id}", summary="Update contact")
@rate_limit(requests_per_minute=60, requests_per_hour=500, per_user=True)
@require_permission("contacts", "update")
async def update_contact(
    contact_id: str,
    contact_updates: ContactUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Update contact information."""
    try:
        contact_manager = ContactManager(db)
        tenant_id = getattr(current_user, 'tenant_id', current_user.id)

        # Filter out None values
        updates = {k: v for k, v in contact_updates.dict().items()
                   if v is not None}

        contact = await contact_manager.update_contact(
            contact_id=UUID(contact_id),
            tenant_id=tenant_id,
            user_id=current_user.id,
            updates=updates
        )

        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")

        return {
            "id": str(contact.id),
            "primary_name": contact.primary_name,
            "display_name": contact.display_name,
            "updated_at": contact.updated_at.isoformat() if contact.updated_at else None,
            "message": "Contact updated successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating contact {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update contact: {str(e)}")


@router.post("/{contact_id}/merge", summary="Merge duplicate contacts")
@rate_limit(requests_per_minute=10, requests_per_hour=50, per_user=True)
@require_permission("contacts", "update")
async def merge_contacts(
    contact_id: str,
    merge_request: ContactMergeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Merge duplicate contacts into a primary contact."""
    try:
        contact_manager = ContactManager(db)
        tenant_id = getattr(current_user, 'tenant_id', current_user.id)

        # Validate that contact_id matches primary_contact_id
        if contact_id != merge_request.primary_contact_id:
            raise HTTPException(
                status_code=400,
                detail="Contact ID in URL must match primary_contact_id in request body"
            )

        duplicate_ids = [UUID(id_str)
                         for id_str in merge_request.duplicate_contact_ids]

        merged_contact = await contact_manager.merge_contacts(
            primary_id=UUID(merge_request.primary_contact_id),
            duplicate_ids=duplicate_ids,
            tenant_id=tenant_id,
            user_id=current_user.id
        )

        return {
            "id": str(merged_contact.id),
            "primary_name": merged_contact.primary_name,
            "total_messages": merged_contact.total_messages,
            "total_threads": merged_contact.total_threads,
            "platforms": merged_contact.platforms,
            "merged_contacts": len(duplicate_ids),
            "updated_at": merged_contact.updated_at.isoformat() if merged_contact.updated_at else None,
            "message": f"Successfully merged {len(duplicate_ids)} contacts"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error merging contacts: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to merge contacts: {str(e)}")


@router.get("/{contact_id}/insights", summary="Get contact insights")
@rate_limit(requests_per_minute=60, requests_per_hour=500, per_user=True)
@require_permission("contacts", "read")
async def get_contact_insights(
    contact_id: str,
    refresh: bool = Query(False, description="Force refresh insights"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get AI-generated insights for a contact."""
    try:
        contact_manager = ContactManager(db)
        tenant_id = getattr(current_user, 'tenant_id', current_user.id)

        insights = await contact_manager.get_contact_insights(
            contact_id=UUID(contact_id),
            tenant_id=tenant_id,
            user_id=current_user.id
        )

        return {
            "contact_id": contact_id,
            "insights": [
                {
                    "id": str(insight.id),
                    "insight_type": insight.insight_type,
                    "title": insight.title,
                    "description": insight.description,
                    "confidence_score": insight.confidence_score,
                    "supporting_data": insight.supporting_data,
                    "suggested_actions": insight.suggested_actions,
                    "generated_at": insight.generated_at.isoformat() if insight.generated_at else None,
                    "expires_at": insight.expires_at.isoformat() if insight.expires_at else None,
                    "is_active": insight.is_active,
                    "user_feedback": insight.user_feedback
                }
                for insight in insights if insight.is_active
            ],
            "count": len([i for i in insights if i.is_active])
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting contact insights for {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get contact insights: {str(e)}")


@router.get("/", summary="List contacts")
@rate_limit(requests_per_minute=60, requests_per_hour=1000, per_user=True)
@require_permission("contacts", "read")
async def list_contacts(
    limit: int = Query(
        50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    favorites_only: bool = Query(
        False, description="Show only favorite contacts"),
    recent_days: Optional[int] = Query(
        None, ge=1, le=365, description="Show contacts from last N days"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """List contacts with optional filtering."""
    try:
        contact_manager = ContactManager(db)
        tenant_id = getattr(current_user, 'tenant_id', current_user.id)

        if favorites_only:
            contacts = await contact_manager.get_favorite_contacts(
                tenant_id=tenant_id,
                user_id=current_user.id,
                limit=limit
            )
        elif recent_days:
            contacts = await contact_manager.get_recent_contacts(
                tenant_id=tenant_id,
                user_id=current_user.id,
                days=recent_days,
                limit=limit
            )
        elif platform:
            contacts = await contact_manager.get_contacts_by_platform(
                platform=platform,
                tenant_id=tenant_id,
                user_id=current_user.id,
                limit=limit
            )
        else:
            # Default search with empty query
            contacts = await contact_manager.search_contacts(
                query="",
                tenant_id=tenant_id,
                user_id=current_user.id,
                limit=limit,
                offset=offset
            )

        # Convert to response format
        contact_data = []
        for contact in contacts:
            contact_dict = {
                "id": str(contact.id),
                "primary_name": contact.primary_name,
                "display_name": contact.display_name,
                "primary_email": contact.primary_email,
                "profile_photo_url": contact.profile_photo_url,
                "last_interaction": contact.last_interaction.isoformat() if contact.last_interaction else None,
                "total_messages": contact.total_messages,
                "platforms": contact.platforms,
                "relationship_strength": contact.relationship_strength,
                "communication_frequency": contact.communication_frequency,
                "is_favorite": contact.is_favorite,
                "tags": contact.tags
            }
            contact_data.append(contact_dict)

        return {
            "contacts": contact_data,
            "count": len(contact_data),
            "offset": offset,
            "limit": limit,
            "filters": {
                "favorites_only": favorites_only,
                "recent_days": recent_days,
                "platform": platform
            }
        }

    except Exception as e:
        logger.error(f"Error listing contacts: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list contacts: {str(e)}")


@router.get("/statistics", summary="Get contact statistics")
@rate_limit(requests_per_minute=30, requests_per_hour=200, per_user=True)
@require_permission("contacts", "read")
async def get_contact_statistics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get contact statistics and analytics."""
    try:
        contact_manager = ContactManager(db)
        tenant_id = getattr(current_user, 'tenant_id', current_user.id)

        stats = await contact_manager.get_contact_statistics(
            tenant_id=tenant_id,
            user_id=current_user.id
        )

        return stats

    except Exception as e:
        logger.error(f"Error getting contact statistics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get contact statistics: {str(e)}")
