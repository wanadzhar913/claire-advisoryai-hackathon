"""Financial insights API endpoints."""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, ConfigDict, Field

from backend.core.auth import get_current_user
from backend.models.user import User
from backend.services.db.postgres_connector import database_service
from backend.services.ai_agent.transaction_analyzer import transaction_analyzer

router = APIRouter()


class InsightResponse(BaseModel):
    """Financial insight response model."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    user_id: int
    file_id: Optional[str] = None
    insight_type: str
    title: str
    description: str
    icon: str
    severity: Optional[str] = None
    insight_metadata: Optional[dict] = Field(default=None, alias="metadata")
    created_at: Optional[str] = None


class InsightsListResponse(BaseModel):
    """Response model for listing insights."""
    insights: List[InsightResponse]
    patterns: List[InsightResponse]
    alerts: List[InsightResponse]
    recommendations: List[InsightResponse]
    count: int


class AnalyzeResponse(BaseModel):
    """Response model for analyze endpoint."""
    message: str
    insights_generated: int
    patterns_count: int
    alerts_count: int
    recommendations_count: int


@router.get("", tags=["Insights"], response_model=InsightsListResponse)
async def get_insights(
    current_user: User = Depends(get_current_user),
    insight_type: Optional[str] = Query(
        default=None, 
        pattern="^(pattern|alert|recommendation)$",
        description="Filter by insight type"
    ),
    file_id: Optional[str] = Query(default=None, description="Filter by file ID"),
    start_date: Optional[date] = Query(default=None, description="Filter insights for this transaction date range (inclusive)"),
    end_date: Optional[date] = Query(default=None, description="Filter insights for this transaction date range (inclusive)"),
    limit: Optional[int] = Query(default=50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Results to skip"),
) -> InsightsListResponse:
    """Get financial insights for the current user.
    
    Returns insights grouped by type (patterns, alerts, recommendations).
    
    Args:
        current_user: Authenticated user (from Clerk JWT)
        insight_type: Optional filter by insight type
        file_id: Optional filter by file ID
        start_date: Optional filter by start date (insights related to transactions from this date)
        end_date: Optional filter by end date (insights related to transactions up to this date)
        limit: Maximum number of results
        offset: Number of results to skip
        
    Returns:
        InsightsListResponse: Grouped insights
    """
    user_id = current_user.id
    
    try:
        if (start_date is None) != (end_date is None):
            raise HTTPException(
                status_code=400,
                detail="Both start_date and end_date must be provided together, or neither",
            )
        if start_date and end_date and end_date < start_date:
            raise HTTPException(status_code=400, detail="end_date must be >= start_date")

        fetch_limit = 200 if (start_date and end_date) and limit is not None else limit
        fetch_offset = 0 if (start_date and end_date) else offset
        insights = database_service.get_user_insights(
            user_id=user_id,
            insight_type=insight_type,
            file_id=file_id,
            limit=fetch_limit,
            offset=fetch_offset,
            order_desc=True,
        )

        if start_date and end_date:
            req_start = start_date.isoformat()
            req_end = end_date.isoformat()

            def _overlaps(i: object) -> bool:
                meta = getattr(i, "insight_metadata", None) or {}
                tr = meta.get("time_range") or meta.get("observed_time_range") or {}
                s = tr.get("start")
                e = tr.get("end")
                if not s or not e:
                    return False
                # overlap inclusive: not (e < req_start or s > req_end)
                return not (e < req_start or s > req_end)

            insights = [i for i in insights if _overlaps(i)]
            insights = insights[offset: offset + (limit or 50)]
        
        # Convert to response models and group by type
        all_insights = []
        patterns = []
        alerts = []
        recommendations = []
        
        for insight in insights:
            response = InsightResponse(
                id=insight.id,
                user_id=insight.user_id,
                file_id=insight.file_id,
                insight_type=insight.insight_type,
                title=insight.title,
                description=insight.description,
                icon=insight.icon,
                severity=insight.severity,
                insight_metadata=insight.insight_metadata,
                created_at=insight.created_at.isoformat() if insight.created_at else None,
            )
            all_insights.append(response)
            
            if insight.insight_type == "pattern":
                patterns.append(response)
            elif insight.insight_type == "alert":
                alerts.append(response)
            elif insight.insight_type == "recommendation":
                recommendations.append(response)
        
        return InsightsListResponse(
            insights=all_insights,
            patterns=patterns,
            alerts=alerts,
            recommendations=recommendations,
            count=len(all_insights),
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch insights: {str(e)}"
        )


@router.post("/analyze", tags=["Insights"], response_model=AnalyzeResponse)
async def analyze_transactions(
    current_user: User = Depends(get_current_user),
    file_id: Optional[str] = Query(default=None, description="Analyze specific file only"),
    start_date: Optional[date] = Query(default=None, description="Analyze transactions from this date onwards (inclusive)"),
    end_date: Optional[date] = Query(default=None, description="Analyze transactions up to this date (inclusive)"),
    background_tasks: BackgroundTasks = None,
) -> AnalyzeResponse:
    """Trigger AI analysis of user's transactions.
    
    This endpoint runs the LangGraph agent to analyze transactions and generate
    new insights (patterns, alerts, recommendations).
    
    Args:
        current_user: Authenticated user (from Clerk JWT)
        file_id: Optional file ID to analyze specific upload only
        
    Returns:
        AnalyzeResponse: Summary of generated insights
    """
    user_id = current_user.id
    
    try:
        if (start_date is None) != (end_date is None):
            raise HTTPException(
                status_code=400,
                detail="Both start_date and end_date must be provided together, or neither",
            )
        if start_date and end_date and end_date < start_date:
            raise HTTPException(status_code=400, detail="end_date must be >= start_date")
        if file_id is None and start_date is None and end_date is None:
            raise HTTPException(
                status_code=400,
                detail="Provide either file_id, or (start_date and end_date)",
            )

        # Run the analysis
        insights = transaction_analyzer.analyze(
            user_id=user_id,
            file_id=file_id,
            start_date=start_date,
            end_date=end_date,
        )
        
        # Count by type
        patterns_count = sum(1 for i in insights if i.insight_type == "pattern")
        alerts_count = sum(1 for i in insights if i.insight_type == "alert")
        recommendations_count = sum(1 for i in insights if i.insight_type == "recommendation")
        
        return AnalyzeResponse(
            message="Analysis completed successfully",
            insights_generated=len(insights),
            patterns_count=patterns_count,
            alerts_count=alerts_count,
            recommendations_count=recommendations_count,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze transactions: {str(e)}"
        )


@router.delete("", tags=["Insights"])
async def delete_insights(
    current_user: User = Depends(get_current_user),
    file_id: Optional[str] = Query(default=None, description="Delete insights for specific file only"),
) -> dict:
    """Delete financial insights for the current user.
    
    Args:
        current_user: Authenticated user (from Clerk JWT)
        file_id: Optional file ID to delete insights for specific upload only
        
    Returns:
        dict: Deletion result
    """
    user_id = current_user.id
    
    try:
        deleted_count = database_service.delete_user_insights(
            user_id=user_id,
            file_id=file_id,
        )
        
        return {
            "message": "Insights deleted successfully",
            "deleted_count": deleted_count,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete insights: {str(e)}"
        )
