from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.abnormality_flag import AbnormalityFlag
from app.models.document_analysis import DocumentAnalysis
from app.models.extracted_finding import ExtractedFinding
from app.models.medical_document import MedicalDocument
from app.models.medical_measurement import MedicalMeasurement
from app.models.user import User
from app.schemas.medical import (
    AbnormalityFlagResponse,
    DocumentAnalysisResponse,
    DocumentListResponse,
    ExtractedFindingResponse,
    MedicalDocumentDetailResponse,
    MedicalDocumentResponse,
    MedicalMeasurementResponse,
    MedicalOverviewResponse,
    ParameterComparisonResponse,
    TimelineItem,
    TrendResponse,
)
from app.services.medical.analysis import analysis_service
from app.services.medical.analytics import analytics_service
from app.services.medical.documents import document_service
from app.services.medical.extraction import extraction_service
from app.services.medical.storage import storage_service

router = APIRouter(prefix="/medical", tags=["medical"])


# --- Overview ---

@router.get("/overview", response_model=MedicalOverviewResponse)
def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return analytics_service.get_overview(db, current_user.id)


# --- Documents ---

@router.post("/documents", response_model=MedicalDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    report_date: date | None = Form(None),
    provider: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = await document_service.create_document(
        db=db,
        upload=file,
        document_type=document_type,
        user_id=current_user.id,
        report_date=report_date,
        provider=provider,
    )
    latest_analysis = doc.analyses[0] if doc.analyses else None
    return MedicalDocumentResponse(
        id=doc.id,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        file_extension=doc.file_extension,
        file_size_bytes=doc.file_size_bytes,
        document_type=doc.document_type,
        report_date=doc.report_date,
        status=doc.status,
        failure_code=doc.failure_code,
        failure_message=doc.failure_message,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        latest_analysis=latest_analysis,  # type: ignore
    )


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    document_type: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    sort: str = Query("newest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs, total, total_pages = document_service.list_documents(
        db=db,
        user_id=current_user.id,
        document_type=document_type,
        status_filter=status,
        search=search,
        sort=sort,
        page=page,
        page_size=page_size,
    )

    items = []
    for d in docs:
        latest = d.analyses[0] if d.analyses else None
        items.append(
            MedicalDocumentResponse(
                id=d.id,
                original_filename=d.original_filename,
                mime_type=d.mime_type,
                file_extension=d.file_extension,
                file_size_bytes=d.file_size_bytes,
                document_type=d.document_type,
                report_date=d.report_date,
                status=d.status,
                failure_code=d.failure_code,
                failure_message=d.failure_message,
                created_at=d.created_at,
                updated_at=d.updated_at,
                latest_analysis=latest,  # type: ignore
            )
        )

    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/documents/{document_id}", response_model=MedicalDocumentDetailResponse)
def get_document_details(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = document_service.get_document(db, document_id, current_user.id)
    latest = doc.analyses[0] if doc.analyses else None

    analyses_resp = [DocumentAnalysisResponse.model_validate(a) for a in doc.analyses]
    findings_resp = [ExtractedFindingResponse.model_validate(f) for f in doc.findings]
    flags_resp = [
        AbnormalityFlagResponse(
            id=fl.id,
            document_id=fl.document_id,
            source_finding_id=fl.source_finding_id,
            measurement_id=fl.measurement_id,
            parameter_name=fl.parameter_name,
            observed_value=float(fl.observed_value) if fl.observed_value is not None else None,
            unit=fl.unit,
            reference_text=fl.reference_text,
            flag_type=fl.flag_type,
            severity=fl.severity,
            explanation=fl.explanation,
            created_at=fl.created_at,
            document_name=doc.original_filename,
            report_date=doc.report_date,
        )
        for fl in doc.flags
    ]
    meas_resp = [
        MedicalMeasurementResponse(
            id=m.id,
            document_id=m.document_id,
            source_finding_id=m.source_finding_id,
            parameter_name=m.parameter_name,
            parameter_code=m.parameter_code,
            numeric_value=float(m.numeric_value),
            unit=m.unit,
            report_date=m.report_date,
            reference_low=float(m.reference_low) if m.reference_low is not None else None,
            reference_high=float(m.reference_high) if m.reference_high is not None else None,
            reference_text=m.reference_text,
            created_at=m.created_at,
        )
        for m in doc.measurements
    ]

    return MedicalDocumentDetailResponse(
        id=doc.id,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        file_extension=doc.file_extension,
        file_size_bytes=doc.file_size_bytes,
        document_type=doc.document_type,
        report_date=doc.report_date,
        status=doc.status,
        failure_code=doc.failure_code,
        failure_message=doc.failure_message,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        latest_analysis=latest,  # type: ignore
        analyses=analyses_resp,
        findings=findings_resp,
        flags=flags_resp,
        measurements=meas_resp,
    )


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.get(MedicalDocument, document_id)
    if not doc or doc.user_id != current_user.id or doc.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or unauthorized",
        )

    file_path = storage_service.get_file_path(doc.storage_key, current_user.id)
    return FileResponse(
        path=file_path,
        media_type=doc.mime_type,
        filename=doc.original_filename,
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document_service.delete_document(db, document_id, current_user.id)


@router.get("/documents/{document_id}/status")
def get_document_status(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.get(MedicalDocument, document_id)
    if not doc or doc.user_id != current_user.id or doc.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return {
        "id": doc.id,
        "status": doc.status,
        "failure_code": doc.failure_code,
        "failure_message": doc.failure_message,
    }


# --- Analysis and Findings ---

@router.post("/documents/{document_id}/analyze", response_model=DocumentAnalysisResponse)
async def analyze_document(
    document_id: UUID,
    provider: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.get(MedicalDocument, document_id)
    if not doc or doc.user_id != current_user.id or doc.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    file_path = storage_service.get_file_path(doc.storage_key, current_user.id)

    extraction_result = extraction_service.extract_document(file_path, doc.mime_type)

    if extraction_result.status in ("corrupt", "encrypted", "unsupported") or not extraction_result.text.strip():
        doc.status = "failed"
        doc.failure_code = extraction_result.error_code or "extraction_failed"
        doc.failure_message = extraction_result.error_message or "We could not extract readable text from this document."
        db.commit()
        db.refresh(doc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=doc.failure_message,
        )

    extracted_text, _, _ = extraction_service.extract_text(file_path, doc.mime_type)
    image_data_url = (
        extraction_service.image_data_url(file_path, doc.mime_type)
        if doc.mime_type.startswith("image/")
        else None
    )
    extraction_result = extraction_service.extract_document(file_path, doc.mime_type)


    analysis = await analysis_service.run_analysis(
        db=db,
        document_id=doc.id,
        user_id=current_user.id,
        extracted_text=extraction_result.text,
        document_type=doc.document_type,


        image_data_url=image_data_url,
        requested_provider=provider,

    )
    return DocumentAnalysisResponse.model_validate(analysis)


@router.get("/documents/{document_id}/analyses", response_model=list[DocumentAnalysisResponse])
def get_document_analyses(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.get(MedicalDocument, document_id)
    if not doc or doc.user_id != current_user.id or doc.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    analyses = (
        db.execute(
            select(DocumentAnalysis)
            .where(DocumentAnalysis.document_id == document_id, DocumentAnalysis.user_id == current_user.id)
            .order_by(DocumentAnalysis.version.desc())
        )
        .scalars()
        .all()
    )
    return [DocumentAnalysisResponse.model_validate(a) for a in analyses]


@router.get("/analyses/{analysis_id}", response_model=DocumentAnalysisResponse)
def get_analysis_details(
    analysis_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analysis = db.get(DocumentAnalysis, analysis_id)
    if not analysis or analysis.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis record not found",
        )
    return DocumentAnalysisResponse.model_validate(analysis)


@router.get("/documents/{document_id}/findings", response_model=list[ExtractedFindingResponse])
def get_document_findings(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.get(MedicalDocument, document_id)
    if not doc or doc.user_id != current_user.id or doc.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    findings = (
        db.execute(
            select(ExtractedFinding)
            .where(ExtractedFinding.document_id == document_id, ExtractedFinding.user_id == current_user.id)
            .order_by(ExtractedFinding.category.asc(), ExtractedFinding.name.asc())
        )
        .scalars()
        .all()
    )
    return [ExtractedFindingResponse.model_validate(f) for f in findings]


@router.get("/flags", response_model=list[AbnormalityFlagResponse])
def list_abnormality_flags(
    document_id: UUID | None = Query(None),
    severity: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(AbnormalityFlag)
        .where(AbnormalityFlag.user_id == current_user.id)
        .order_by(AbnormalityFlag.created_at.desc())
        .options(joinedload(AbnormalityFlag.document))
    )

    if document_id:
        query = query.where(AbnormalityFlag.document_id == document_id)
    if severity and severity != "all":
        query = query.where(AbnormalityFlag.severity == severity)

    flags = db.execute(query).unique().scalars().all()
    return [
        AbnormalityFlagResponse(
            id=f.id,
            document_id=f.document_id,
            source_finding_id=f.source_finding_id,
            measurement_id=f.measurement_id,
            parameter_name=f.parameter_name,
            observed_value=float(f.observed_value) if f.observed_value is not None else None,
            unit=f.unit,
            reference_text=f.reference_text,
            flag_type=f.flag_type,
            severity=f.severity,
            explanation=f.explanation,
            created_at=f.created_at,
            document_name=f.document.original_filename if f.document else None,
            report_date=f.document.report_date if f.document else None,
        )
        for f in flags
    ]


@router.get("/flags/{flag_id}", response_model=AbnormalityFlagResponse)
def get_flag_details(
    flag_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    flag = (
        db.execute(
            select(AbnormalityFlag)
            .where(AbnormalityFlag.id == flag_id, AbnormalityFlag.user_id == current_user.id)
            .options(joinedload(AbnormalityFlag.document))
        )
        .unique()
        .scalar_one_or_none()
    )
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Abnormality flag not found",
        )
    return AbnormalityFlagResponse(
        id=flag.id,
        document_id=flag.document_id,
        source_finding_id=flag.source_finding_id,
        measurement_id=flag.measurement_id,
        parameter_name=flag.parameter_name,
        observed_value=float(flag.observed_value) if flag.observed_value is not None else None,
        unit=flag.unit,
        reference_text=flag.reference_text,
        flag_type=flag.flag_type,
        severity=flag.severity,
        explanation=flag.explanation,
        created_at=flag.created_at,
        document_name=flag.document.original_filename if flag.document else None,
        report_date=flag.document.report_date if flag.document else None,
    )


# --- Analytics ---

@router.get("/measurements", response_model=list[MedicalMeasurementResponse])
def list_measurements(
    parameter_name: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(MedicalMeasurement)
        .where(MedicalMeasurement.user_id == current_user.id)
        .order_by(MedicalMeasurement.report_date.desc(), MedicalMeasurement.created_at.desc())
    )
    if parameter_name:
        query = query.where(MedicalMeasurement.parameter_name == parameter_name)

    meas = db.execute(query).scalars().all()
    return [
        MedicalMeasurementResponse(
            id=m.id,
            document_id=m.document_id,
            source_finding_id=m.source_finding_id,
            parameter_name=m.parameter_name,
            parameter_code=m.parameter_code,
            numeric_value=float(m.numeric_value),
            unit=m.unit,
            report_date=m.report_date,
            reference_low=float(m.reference_low) if m.reference_low is not None else None,
            reference_high=float(m.reference_high) if m.reference_high is not None else None,
            reference_text=m.reference_text,
            created_at=m.created_at,
        )
        for m in meas
    ]


@router.get("/analytics/trends", response_model=TrendResponse)
def get_trends(
    parameter: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return analytics_service.get_health_trends(db, current_user.id, parameter)


@router.get("/analytics/comparison", response_model=ParameterComparisonResponse)
def get_parameter_comparison(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return analytics_service.get_parameter_comparison(db, current_user.id)


@router.get("/analytics/historical", response_model=ParameterComparisonResponse)
def get_historical_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return analytics_service.get_parameter_comparison(db, current_user.id)


# --- History ---

@router.get("/history/uploads", response_model=list[MedicalDocumentResponse])
def get_upload_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = (
        db.execute(
            select(MedicalDocument)
            .where(MedicalDocument.user_id == current_user.id, MedicalDocument.deleted_at.is_(None))
            .order_by(MedicalDocument.created_at.desc())
            .options(joinedload(MedicalDocument.analyses))
        )
        .unique()
        .scalars()
        .all()
    )
    items = []
    for d in docs:
        latest = d.analyses[0] if d.analyses else None
        items.append(
            MedicalDocumentResponse(
                id=d.id,
                original_filename=d.original_filename,
                mime_type=d.mime_type,
                file_extension=d.file_extension,
                file_size_bytes=d.file_size_bytes,
                document_type=d.document_type,
                report_date=d.report_date,
                status=d.status,
                failure_code=d.failure_code,
                failure_message=d.failure_message,
                created_at=d.created_at,
                updated_at=d.updated_at,
                latest_analysis=latest,  # type: ignore
            )
        )
    return items


@router.get("/history/summaries", response_model=list[DocumentAnalysisResponse])
def get_summary_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analyses = (
        db.execute(
            select(DocumentAnalysis)
            .where(
                DocumentAnalysis.user_id == current_user.id,
                DocumentAnalysis.status == "completed",
            )
            .order_by(DocumentAnalysis.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [DocumentAnalysisResponse.model_validate(a) for a in analyses]


@router.get("/history/timeline", response_model=list[TimelineItem])
def get_report_timeline(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return analytics_service.get_timeline(db, current_user.id)


# --- Diagnostics (Development / Admin) ---

@router.get("/diagnostics/provider")
def get_provider_diagnostics(
    current_user: User = Depends(get_current_user),
):
    """Returns provider configurations and key-present boolean without exposing secret values."""
    return analysis_service.get_provider_diagnostics()


@router.post("/diagnostics/test")
async def test_provider_connection(
    current_user: User = Depends(get_current_user),
):
    """Tests connectivity to Gemini using a minimal non-medical ping."""
    return await analysis_service.test_provider_connectivity()
