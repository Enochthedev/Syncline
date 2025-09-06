"""API routes for contact insights and relationship analysis."""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db.session import get_db
from api.dependencies import get_current_user, get_tenant_context
from services.contacts.contact_manager import ContactManager
from services.contacts.contact_insights import ContactInsightsService
from services.contacts.relationship_analyzer import RelationshipAnalyzer
from db.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contacts", tags=["contact-insights"])


# Request/Response Models
class InsightFeedbackRequest(BaseModel):
    feedback: str  # 'helpful', 'not_helpful', 'incorrect'


class GenerateInsightsRequest(BaseModel):
    insight_types: Optional[List[str]] = None


class ExportInsightsRequest(BaseModel):
    format: str = "json"  # 'json', 'csv', 'pdf'


# Routes

@router.get("/{contact_id}/comprehensive-analysis")
async def get_comprehensive_analysis(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context=Depends(get_tenant_context)
):
    """Get comprehensive relationship analysis for a contact."""
    try:
        insights_service = ContactInsightsService(db)

        analysis = await insights_service.get_comprehensive_relationship_analysis(
            contact_id=contact_id,
            tenant_id=tenant_context.tenant_id,
            user_id=current_user.id
        )

        if not analysis:
            raise HTTPException(
                status_code=404, detail="Contact not found or no analysis available")

        return analysis

    except Exception as e:
        logger.error(
            f"Error getting comprehensive analysis for contact {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get comprehensive analysis")


@router.get("/{contact_id}/insights")
async def get_contact_insights(
    contact_id: UUID,
    refresh: bool = Query(False, description="Force refresh insights"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context=Depends(get_tenant_context)
):
    """Get AI-generated insights for a contact."""
    try:
        insights_service = ContactInsightsService(db)

        insights = await insights_service.get_contact_insights(
            contact_id=contact_id,
            tenant_id=tenant_context.tenant_id,
            user_id=current_user.id,
            refresh=refresh
        )

        return {"insights": insights}

    except Exception as e:
        logger.error(f"Error getting insights for contact {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get contact insights")


@router.get("/{contact_id}/timeline")
async def get_communication_timeline(
    contact_id: UUID,
    days_back: int = Query(365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context=Depends(get_tenant_context)
):
    """Get communication timeline with trend analysis."""
    try:
        relationship_analyzer = RelationshipAnalyzer(db)

        timeline_data = await relationship_analyzer.analyze_communication_timeline(
            contact_id=contact_id,
            tenant_id=tenant_context.tenant_id,
            user_id=current_user.id,
            days_back=days_back
        )

        return timeline_data

    except Exception as e:
        logger.error(f"Error getting timeline for contact {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get communication timeline")


@router.get("/{contact_id}/sentiment")
async def get_sentiment_analysis(
    contact_id: UUID,
    days_back: int = Query(90, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context=Depends(get_tenant_context)
):
    """Get sentiment analysis for communication with a contact."""
    try:
        relationship_analyzer = RelationshipAnalyzer(db)

        sentiment_data = await relationship_analyzer.analyze_sentiment_trends(
            contact_id=contact_id,
            tenant_id=tenant_context.tenant_id,
            user_id=current_user.id,
            days_back=days_back
        )

        return sentiment_data

    except Exception as e:
        logger.error(
            f"Error getting sentiment analysis for contact {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get sentiment analysis")


@router.get("/{contact_id}/network")
async def get_network_analysis(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context=Depends(get_tenant_context)
):
    """Get network analysis and mutual connections."""
    try:
        relationship_analyzer = RelationshipAnalyzer(db)

        network_data = await relationship_analyzer.analyze_mutual_connections(
            contact_id=contact_id,
            tenant_id=tenant_context.tenant_id,
            user_id=current_user.id
        )

        return network_data

    except Exception as e:
        logger.error(
            f"Error getting network analysis for contact {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get network analysis")


@router.get("/{contact_id}/heatmap")
async def get_interaction_heatmap(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context=Depends(get_tenant_context)
):
    """Get interaction frequency heatmap data."""
    try:
        insights_service = ContactInsightsService(db)

        heatmap_data = await insights_service.get_interaction_heatmap_data(
            contact_id=contact_id,
            tenant_id=tenant_context.tenant_id,
            user_id=current_user.id
        )

        return heatmap_data

    except Exception as e:
        logger.error(f"Error getting heatmap for contact {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get interaction heatmap")


@router.get("/{contact_id}/visualization/{viz_type}")
async def get_visualization_data(
    contact_id: UUID,
    viz_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context=Depends(get_tenant_context)
):
    """Get visualization data for different chart types."""
    try:
        insights_service = ContactInsightsService(db)

        if viz_type == "timeline":
            data = await insights_service.get_communication_timeline_visualization(
                contact_id=contact_id,
                tenant_id=tenant_context.tenant_id,
                user_id=current_user.id
            )
        elif viz_type == "sentiment":
            data = await insights_service.get_sentiment_trend_visualization(
                contact_id=contact_id,
                tenant_id=tenant_context.tenant_id,
                user_id=current_user.id
            )
        elif viz_type == "heatmap":
            data = await insights_service.get_interaction_heatmap_data(
                contact_id=contact_id,
                tenant_id=tenant_context.tenant_id,
                user_id=current_user.id
            )
        elif viz_type == "network":
            data = await insights_service.get_network_visualization_data(
                contact_id=contact_id,
                tenant_id=tenant_context.tenant_id,
                user_id=current_user.id
            )
        else:
            raise HTTPException(
                status_code=400, detail="Invalid visualization type")

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting {viz_type} visualization for contact {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get {viz_type} visualization")


@router.get("/{contact_id}/relationship-strength")
async def get_relationship_strength(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context=Depends(get_tenant_context)
):
    """Get detailed relationship strength calculation."""
    try:
        relationship_analyzer = RelationshipAnalyzer(db)

        strength_data = await relationship_analyzer.calculate_interaction_frequency_analysis(
            contact_id=contact_id,
            tenant_id=tenant_context.tenant_id,
            user_id=current_user.id
        )

        return strength_data

    except Exception as e:
        logger.error(
            f"Error getting relationship strength for contact {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get relationship strength")


@router.get("/{contact_id}/patterns")
async def get_communication_patterns(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context=Depends(get_tenant_context)
):
    """Get communication patterns analysis."""
    try:
        contact_manager = ContactManager(db)

        patterns = await contact_manager.get_communication_patterns(
            contact_id=contact_id,
            tenant_id=tenant_context.tenant_id,
            user_id=current_user.id
        )

        return patterns

    except Exception as e:
        logger.error(
            f"Error getting communication patterns for contact {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get communication patterns")


@router.post("/{contact_id}/insights/refresh")
async def refresh_contact_insights(
    contact_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context=Depends(get_tenant_context)
):
    """Refresh all insights for a contact."""
    try:
        insights_service = ContactInsightsService(db)

        # Run refresh in background
        background_tasks.add_task(
            insights_service.refresh_all_insights,
            contact_id,
            tenant_context.tenant_id,
            current_user.id
        )

        return {"message": "Insight refresh started", "status": "processing"}

    except Exception as e:
        logger.error(
            f"Error refreshing insights for contact {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to refresh insights")


@router.post("/{contact_id}/insights/generate")
async def generate_insights(
    contact_id: UUID,
    request: GenerateInsightsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context=Depends(get_tenant_context)
):
    """Generate specific types of insights on demand."""
    try:
        relationship_analyzer = RelationshipAnalyzer(db)

        insights = await relationship_analyzer.generate_relationship_insights(
            contact_id=contact_id,
            tenant_id=tenant_context.tenant_id,
            user_id=current_user.id
        )

        # Filter by requested types if specified
        if request.insight_types:
            insights = [
                insight for insight in insights
                if insight['type'] in request.insight_types
            ]

        return {"insights": insights}

    except Exception as e:
        logger.error(
            f"Error generating insights for contact {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate insights")


@router.post("/insights/{insight_id}/feedback")
async def submit_insight_feedback(
    insight_id: UUID,
    request: InsightFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit feedback for an insight."""
    try:
        from sqlalchemy import update
        from db.models.unified_contact import ContactInsight

        # Update insight with user feedback
        stmt = update(ContactInsight).where(
            ContactInsight.id == insight_id
        ).values(user_feedback=request.feedback)

        await db.execute(stmt)
        await db.commit()

        return {"message": "Feedback submitted successfully"}

    except Exception as e:
        logger.error(
            f"Error submitting feedback for insight {insight_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to submit feedback")


@router.get("/{contact_id}/insights/accuracy")
async def get_insight_accuracy_metrics(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context=Depends(get_tenant_context)
):
    """Get insight accuracy metrics based on user feedback."""
    try:
        insights_service = ContactInsightsService(db)

        accuracy_metrics = await insights_service.get_insight_accuracy_metrics(
            contact_id=contact_id,
            tenant_id=tenant_context.tenant_id,
            user_id=current_user.id
        )

        return accuracy_metrics

    except Exception as e:
        logger.error(
            f"Error getting accuracy metrics for contact {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get accuracy metrics")


@router.get("/insights/trending")
async def get_trending_insights(
    limit: int = Query(
        10, description="Number of trending insights to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context=Depends(get_tenant_context)
):
    """Get trending insights across all contacts."""
    try:
        # This would implement logic to find trending insights
        # For now, return empty list
        return {"insights": []}

    except Exception as e:
        logger.error(f"Error getting trending insights: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get trending insights")


@router.get("/insights/summary")
async def get_insights_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context=Depends(get_tenant_context)
):
    """Get insights summary for dashboard."""
    try:
        # This would implement logic to generate insights summary
        # For now, return basic structure
        return {
            "total_insights": 0,
            "recent_insights": 0,
            "accuracy_rate": 0.0,
            "top_insight_types": []
        }

    except Exception as e:
        logger.error(f"Error getting insights summary: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get insights summary")


@router.delete("/{contact_id}/insights/cache")
async def clear_insights_cache(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context=Depends(get_tenant_context)
):
    """Clear insights cache for a contact."""
    try:
        insights_service = ContactInsightsService(db)

        await insights_service.clear_insights_cache(contact_id)

        return {"message": "Cache cleared successfully"}

    except Exception as e:
        logger.error(f"Error clearing cache for contact {contact_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")


@router.get("/{contact_id}/insights/cache-status")
async def get_cache_status(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context=Depends(get_tenant_context)
):
    """Get cache status for contact insights."""
    try:
        # This would implement cache status checking
        # For now, return basic status
        return {
            "cached": False,
            "last_updated": None,
            "cache_size": 0
        }

    except Exception as e:
        logger.error(
            f"Error getting cache status for contact {contact_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get cache status")
