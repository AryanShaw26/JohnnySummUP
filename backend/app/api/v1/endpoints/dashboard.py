"""
Medical Overview Dashboard endpoints.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.analytics import DashboardOverviewData
from app.schemas.common import ApiResponse
from app.services.analytics_service import get_dashboard_overview

router = APIRouter()


@router.get("", response_model=ApiResponse[Dict[str, Any]])
@router.get("/stats", response_model=ApiResponse[Dict[str, Any]])
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns counts, recent records, recent evidence-grounded findings,
    and tracked parameter previews. NO health score is calculated.
    """
    data = await get_dashboard_overview(db, current_user.id)
    return ApiResponse(data=data)

