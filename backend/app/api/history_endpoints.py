"""History management endpoints."""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
import logging
import json

from app.models.schemas import (
    HistoryResponse,
    HistoryItem,
    HistoryStats,
    DeleteResponse
)
from app.models.user import UserResponse
from app.services.auth import get_current_user
from app.models.database import history_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/history", response_model=HistoryResponse)
async def get_comparison_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    website_url: Optional[str] = None,
    project_name: Optional[str] = None,
    status: Optional[str] = None,
    current_user: Optional[UserResponse] = Depends(get_current_user)
) -> HistoryResponse:
    """
    Get comparison history with optional filters.
    Only returns comparisons belonging to the current user.
    """
    user_id = current_user.id if current_user else None
    
    items = history_db.get_history(
        limit=limit,
        offset=offset,
        website_url=website_url,
        project_name=project_name,
        status=status,
        user_id=user_id
    )
    
    history_items = []
    for item in items:
        history_items.append(HistoryItem(
            id=item["id"],
            job_id=item["job_id"],
            figma_url=item.get("figma_url"),
            website_url=item["website_url"],
            viewport_name=item.get("viewport_name", "desktop"),
            viewport_width=item.get("viewport_width", 1920),
            viewport_height=item.get("viewport_height", 1080),
            match_score=item.get("match_score", 0.0),
            total_differences=item.get("total_differences", 0),
            critical_count=item.get("critical_count", 0),
            warning_count=item.get("warning_count", 0),
            info_count=item.get("info_count", 0),
            status=item.get("status", "pending"),
            project_name=item.get("project_name"),
            tags=json.loads(item["tags"]) if item.get("tags") else None,
            created_at=item["created_at"],
            completed_at=item.get("completed_at")
        ))
    
    return HistoryResponse(
        items=history_items,
        total=len(history_items),
        page=(offset // limit) + 1,
        limit=limit
    )


@router.get("/history/stats", response_model=HistoryStats)
async def get_history_stats(
    current_user: Optional[UserResponse] = Depends(get_current_user)
) -> HistoryStats:
    """Get overall statistics for comparison history (user-specific)."""
    user_id = current_user.id if current_user else None
    stats = history_db.get_stats(user_id=user_id)
    return HistoryStats(
        total_comparisons=stats.get("total_comparisons", 0) or 0,
        avg_match_score=stats.get("avg_match_score", 0.0) or 0.0,
        total_differences_found=stats.get("total_differences_found", 0) or 0,
        unique_websites=stats.get("unique_websites", 0) or 0
    )


@router.delete("/history/{job_id}", response_model=DeleteResponse)
async def delete_history_item(
    job_id: str,
    current_user: Optional[UserResponse] = Depends(get_current_user)
) -> DeleteResponse:
    """Delete a comparison from history (only if owned by user)."""
    user_id = current_user.id if current_user else None
    deleted = history_db.delete_comparison(job_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="History item not found")
    return DeleteResponse(message=f"History item {job_id} deleted successfully")


@router.delete("/history", response_model=DeleteResponse)
async def delete_all_history(
    current_user: Optional[UserResponse] = Depends(get_current_user)
) -> DeleteResponse:
    """Delete all comparison history for the current user."""
    user_id = current_user.id if current_user else None
    count = history_db.delete_all(user_id=user_id)
    return DeleteResponse(message=f"Deleted {count} history items")
