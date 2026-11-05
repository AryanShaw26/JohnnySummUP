"""
Extracted measurement schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReferenceRangeData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    low: Optional[float] = None
    high: Optional[float] = None
    rawText: Optional[str] = None


class SourceLocationData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    page: Optional[int] = None
    snippet: Optional[str] = None
    boundingBox: Optional[dict] = None


class MeasurementResponseData(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    documentId: UUID = Field(alias="document_id")
    parameterCode: Optional[str] = Field(default=None, alias="parameter_code")
    parameterName: str = Field(alias="parameter_name_raw")
    parameterDisplayName: Optional[str] = Field(default=None, alias="parameter_name_display")
    rawValueText: str = Field(alias="raw_value_text")
    numericValue: Optional[str] = None  # String for precision safety
    sourceUnit: Optional[str] = Field(default=None, alias="source_unit")
    referenceRange: Optional[ReferenceRangeData] = None
    sourceFlag: Optional[str] = Field(default=None, alias="source_flag")
    calculatedRangeStatus: str = Field(alias="calculated_range_status")
    testDate: Optional[datetime] = Field(default=None, alias="test_date")
    confidence: Optional[float] = None
    reviewStatus: str = Field(alias="review_status")
    source: Optional[SourceLocationData] = None

