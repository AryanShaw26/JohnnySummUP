"""
Medical finding schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FindingEvidenceItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    documentId: Optional[str] = None
    page: Optional[int] = None
    snippet: Optional[str] = None
    measurementId: Optional[str] = None


class FindingResponseData(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    documentId: UUID = Field(alias="document_id")
    measurementId: Optional[UUID] = Field(default=None, alias="measurement_id")
    findingType: str = Field(alias="finding_type")
    title: str
    explanation: str
    ruleCode: Optional[str] = Field(default=None, alias="rule_code")
    evidence: List[FindingEvidenceItem] = Field(default_factory=list)
    reviewStatus: str = Field(alias="review_status")
    createdAt: datetime = Field(alias="created_at")

