"""
Prescription schemas.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PrescriptionItemData(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    documentId: UUID = Field(alias="document_id")
    medicineNameRaw: str = Field(alias="medicine_name_raw")
    strengthText: Optional[str] = Field(default=None, alias="strength_text")
    doseText: Optional[str] = Field(default=None, alias="dose_text")
    routeText: Optional[str] = Field(default=None, alias="route_text")
    frequencyText: Optional[str] = Field(default=None, alias="frequency_text")
    durationText: Optional[str] = Field(default=None, alias="duration_text")
    instructionsText: Optional[str] = Field(default=None, alias="instructions_text")
    confidence: Optional[float] = None
    reviewStatus: str = Field(alias="review_status")
    sourcePage: Optional[int] = Field(default=None, alias="source_page")
    sourceSnippet: Optional[str] = Field(default=None, alias="source_snippet")

