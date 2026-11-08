from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MedicalDocumentBase(BaseModel):
    original_filename: str
    document_type: str
    report_date: date | None = None


class DocumentAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    version: int
    status: str
    extracted_text: str | None = None
    summary: str | None = None
    key_points: list[Any] | dict[str, Any] | None = None
    provider: str | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class ExtractedFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_id: UUID
    document_id: UUID
    category: str
    finding_type: str
    name: str
    value_text: str | None = None
    numeric_value: float | None = None
    unit: str | None = None
    reference_low: float | None = None
    reference_high: float | None = None
    reference_text: str | None = None
    source_page: int | None = None
    source_excerpt: str | None = None
    confidence: float | None = None
    is_extracted: bool = True
    created_at: datetime


class MedicalMeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    source_finding_id: UUID | None = None
    parameter_name: str
    parameter_code: str | None = None
    numeric_value: float
    unit: str
    report_date: date
    reference_low: float | None = None
    reference_high: float | None = None
    reference_text: str | None = None
    created_at: datetime


class AbnormalityFlagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    source_finding_id: UUID | None = None
    measurement_id: UUID | None = None
    parameter_name: str
    observed_value: float | None = None
    unit: str | None = None
    reference_text: str | None = None
    flag_type: str
    severity: str
    explanation: str | None = None
    created_at: datetime
    document_name: str | None = None
    report_date: date | None = None


class MedicalDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    mime_type: str
    file_extension: str
    file_size_bytes: int
    document_type: str
    report_date: date | None = None
    status: str
    failure_code: str | None = None
    failure_message: str | None = None
    created_at: datetime
    updated_at: datetime
    latest_analysis: DocumentAnalysisResponse | None = None


class MedicalDocumentDetailResponse(MedicalDocumentResponse):
    analyses: list[DocumentAnalysisResponse] = Field(default_factory=list)
    findings: list[ExtractedFindingResponse] = Field(default_factory=list)
    flags: list[AbnormalityFlagResponse] = Field(default_factory=list)
    measurements: list[MedicalMeasurementResponse] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    items: list[MedicalDocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MedicalOverviewResponse(BaseModel):
    total_reports: int
    prescriptions_count: int
    lab_reports_count: int
    important_findings_count: int
    recent_reports: list[MedicalDocumentResponse]
    important_findings: list[AbnormalityFlagResponse]


class TrendPoint(BaseModel):
    date: date
    value: float
    unit: str
    document_id: UUID
    document_name: str
    is_abnormal: bool = False


class TrendResponse(BaseModel):
    parameter_name: str
    unit: str
    reference_range: str | None = None
    current_value: float | None = None
    previous_value: float | None = None
    change: float | None = None
    status: str = "normal"  # normal, high, low, review
    points: list[TrendPoint]
    available_parameters: list[str] = Field(default_factory=list)


class ParameterComparisonRow(BaseModel):
    parameter_name: str
    unit: str
    reference_range: str | None = None
    values_by_date: dict[str, float | None]
    trend_direction: str  # up, down, stable, unknown


class ParameterComparisonResponse(BaseModel):
    report_dates: list[str]
    rows: list[ParameterComparisonRow]


class TimelineItem(BaseModel):
    document_id: UUID
    report_name: str
    report_date: date
    document_type: str
    status: str
    key_measurements: list[dict[str, Any]] = Field(default_factory=list)
    flag_count: int = 0
