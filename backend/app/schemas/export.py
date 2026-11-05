"""
Export schemas.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExportCreateRequest(BaseModel):
    documentId: Optional[UUID] = None
    exportType: str = "single_report_summary"


class ExportStatusData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    exportId: UUID
    status: str
    downloadUrl: Optional[str] = None

