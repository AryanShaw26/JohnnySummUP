from datetime import date, datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class WorkspaceFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_id: UUID
    document_id: UUID
    workspace: str
    finding_type: str
    title: str
    explanation: str
    why_it_matters: str | None = None
    review_priority: str
    source_page: int | None = None
    source_section: str | None = None
    source_excerpt: str | None = None
    metadata_json: dict[str, Any] | None = None
    is_reviewed: bool = False
    review_status: str = "pending"
    created_at: datetime


class WorkspaceAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    workspace: str
    version: int
    status: str
    extracted_text: str | None = None
    summary: str | None = None
    structured_data: dict[str, Any] | None = None
    key_points: list[Any] | None = None
    provider: str
    model_name: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    findings: list[WorkspaceFindingResponse] = []


class WorkspaceDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace: str
    document_type: str
    document_subtype: str | None = None
    label: str | None = None
    original_filename: str
    mime_type: str
    file_extension: str
    file_size_bytes: int
    document_date: date | None = None
    extraction_method: str | None = None
    page_count: int
    character_count: int
    status: str
    failure_code: str | None = None
    failure_message: str | None = None
    created_at: datetime
    updated_at: datetime
    analyses: list[WorkspaceAnalysisResponse] = []
    findings: list[WorkspaceFindingResponse] = []


class WorkspaceDocumentListResponse(BaseModel):
    items: list[WorkspaceDocumentResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class WorkspaceFindingUpdate(BaseModel):
    is_reviewed: bool | None = None
    review_status: str | None = None  # "pending", "reviewed", "dismissed"


class WorkspaceDocumentUpdate(BaseModel):
    document_subtype: str | None = None
    label: str | None = None


class WorkspaceOverviewResponse(BaseModel):
    workspace: str
    total_documents: int
    completed_documents: int
    failed_documents: int
    pending_documents: int
    subtypes_breakdown: dict[str, int]
    recent_documents: list[WorkspaceDocumentResponse]
    urgent_findings: list[WorkspaceFindingResponse]
    deadlines: list[WorkspaceFindingResponse]
