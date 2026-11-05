"""
Medical document request and response schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CapabilitiesData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    supportedMimeTypes: List[str]
    maxFileSizeBytes: int
    maxPages: int
    supportedDocumentTypes: List[str]


class DocumentCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    originalFilename: str
    mimeType: str
    fileSizeBytes: int
    documentType: str = "lab_report"
    documentTitle: Optional[str] = None
    testDate: Optional[str] = None


class DocumentUploadPendingData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    documentId: UUID
    status: str = "upload_pending"
    uploadEndpoint: str


class DocumentItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    originalFilename: str = Field(alias="original_filename")
    documentTitle: Optional[str] = Field(default=None, alias="document_title")
    documentType: str = Field(alias="document_type")
    testDate: Optional[datetime] = Field(default=None, alias="document_date")
    uploadedAt: datetime = Field(alias="created_at")
    processingStatus: str = Field(alias="status")
    pageCount: Optional[int] = Field(default=None, alias="page_count")
    measurementCount: int = 0
    findingCount: int = 0


class DocumentDetailData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    originalFilename: str
    documentTitle: Optional[str]
    documentType: str
    testDate: Optional[datetime]
    uploadedAt: datetime
    pageCount: Optional[int]
    providerName: Optional[str]
    facilityName: Optional[str]
    status: str
    summary: Optional[Dict[str, Any]] = None
    measurements: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    prescriptions: List[Dict[str, Any]] = []

