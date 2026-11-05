"""
Health Analytics endpoints for parameters, trends, and comparisons.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_pipeline.parameter_catalog import PARAMETER_CATALOG
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.analytics import ComparisonRequest, TrendResponseData
from app.schemas.common import ApiResponse
from app.services.analytics_service import compare_documents, get_parameter_trends

router = APIRouter()


@router.get("/parameters", response_model=ApiResponse[List[Dict[str, str]]])
async def list_available_parameters():
    """
    List all supported canonical parameters available for trend tracking.
    """
    params = [
        {
            "parameterCode": p.parameter_code,
            "displayName": p.canonical_name,
            "category": p.category,
            "supportedUnits": ", ".join(p.supported_units),
        }
        for p in PARAMETER_CATALOG.values()
    ]
    return ApiResponse(data=params)


@router.get("/trends", response_model=ApiResponse[Dict[str, Any]])
@router.get("/metrics", response_model=ApiResponse[Dict[str, Any]])
async def get_trends(
    parameterCode: Optional[str] = Query(None, alias="parameterCode"),
    metric_name: Optional[str] = Query(None, alias="metric_name"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve chronological trend points with comparability evaluation.
    """
    code = parameterCode or metric_name or "hemoglobin"
    data = await get_parameter_trends(db, current_user.id, code.lower())
    return ApiResponse(data=data)


@router.post("/compare", response_model=ApiResponse[Dict[str, Any]])
async def compare_reports(
    payload: ComparisonRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Side-by-side comparison of 2 or more reports.
    """
    data = await compare_documents(db, current_user.id, payload.documentIds)
    return ApiResponse(data=data)

