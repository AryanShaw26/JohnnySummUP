"""
Analytics, dashboard stats, and trends schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.medical_document import DocumentItemResponse


class TrackedParameterPreview(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    parameterCode: str
    displayName: str
    category: str
    unit: str
    readingCount: int
    latestValue: str
    latestStatus: str
    latestDate: Optional[datetime] = None


class DashboardOverviewData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reportCount: int
    analysedCount: int
    needsReviewCount: int
    trackedParameterCount: int
    recentDocuments: List[DocumentItemResponse]
    recentFindings: List[Dict[str, Any]]
    trackedParameterPreviews: List[TrackedParameterPreview]


class TrendPointData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    measurementId: UUID
    documentId: UUID
    documentTitle: Optional[str] = None
    testDate: str
    value: float
    rawValue: str
    unit: str
    referenceLow: Optional[float] = None
    referenceHigh: Optional[float] = None
    calculatedRangeStatus: str
    reviewStatus: str


class TrendResponseData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    parameterCode: str
    displayName: str
    unit: str
    comparabilityStatus: str  # comparable, insufficient_data, incompatible_units, needs_review
    explanation: str
    points: List[TrendPointData]


class ComparisonRequest(BaseModel):
    documentIds: List[UUID]
    parameterCodes: Optional[List[str]] = None


class AlignedMeasurementRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    parameterCode: Optional[str]
    parameterName: str
    unit: Optional[str]
    valuesByDocument: Dict[str, Dict[str, Any]]  # docId -> { value, status, refRange, date }

