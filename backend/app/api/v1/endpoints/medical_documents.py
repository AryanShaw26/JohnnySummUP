"""
Medical document upload, retrieval, and management endpoints.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationInfo
from app.schemas.medical_document import (
    DocumentCreateRequest,
    DocumentDetailData,
    DocumentItemResponse,
    DocumentUploadPendingData,
)
from app.services.document_service import (
    delete_document,
    get_document_for_user,
    list_documents_for_user,
    process_document_upload,
)

router = APIRouter()


@router.post("/upload", response_model=ApiResponse[Dict[str, Any]], status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("lab_report"),
    document_title: Optional[str] = Form(None),
    test_date: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Direct multipart document upload (PDF or images). Enqueues processing.
    """
    doc, job = await process_document_upload(
        db=db,
        user_id=current_user.id,
        file=file,
        document_type=document_type,
        document_title=document_title,
        test_date=test_date,
    )

    return ApiResponse(
        data={
            "documentId": str(doc.id),
            "jobId": str(job.id),
            "status": doc.status,
            "originalFilename": doc.original_filename,
            "documentTitle": doc.document_title,
            "documentType": doc.document_type,
            "fileSizeBytes": doc.file_size_bytes,
        }
    )


@router.get("", response_model=PaginatedResponse[DocumentItemResponse])
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    document_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List user-owned documents with pagination, search, and type filters.
    """
    items, total = await list_documents_for_user(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        search=search,
        document_type=document_type,
        status=status,
    )

    total_pages = max(1, (total + page_size - 1) // page_size)
    return PaginatedResponse(
        data=[DocumentItemResponse.model_validate(item) for item in items],
        pagination=PaginationInfo(
            page=page,
            pageSize=page_size,
            totalItems=total,
            totalPages=total_pages,
        ),
    )


@router.get("/{document_id}", response_model=ApiResponse[DocumentDetailData])
async def get_document_detail(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get complete details of a report including summary, measurements, and findings.
    """
    doc = await get_document_for_user(db, document_id, current_user.id)

    summary_dict = None
    if doc.summaries:
        s = doc.summaries[0]
        summary_dict = {
            "id": str(s.id),
            "summaryText": s.summary_text,
            "structuredSummary": s.structured_summary,
            "modelProvider": s.model_provider,
            "validationStatus": s.validation_status,
            "createdAt": s.created_at.isoformat() if s.created_at else None,
        }

    measurements_list = []
    for m in doc.extracted_measurements:
        measurements_list.append({
            "id": str(m.id),
            "documentId": str(m.document_id),
            "parameterCode": m.parameter_code,
            "parameterName": m.parameter_name_raw,
            "parameterDisplayName": m.parameter_name_display,
            "rawValueText": m.raw_value_text,
            "numericValue": str(m.numeric_value) if m.numeric_value is not None else None,
            "sourceUnit": m.source_unit,
            "referenceRange": {
                "low": m.reference_low,
                "high": m.reference_high,
                "rawText": m.reference_text_raw,
            },
            "sourceFlag": m.source_flag,
            "calculatedRangeStatus": m.calculated_range_status,
            "testDate": m.test_date.isoformat() if m.test_date else None,
            "confidence": m.confidence,
            "reviewStatus": m.review_status,
            "source": {
                "page": m.source_page,
                "snippet": m.source_snippet,
            },
        })

    findings_list = []
    for f in doc.findings:
        findings_list.append({
            "id": str(f.id),
            "documentId": str(f.document_id),
            "measurementId": str(f.measurement_id) if f.measurement_id else None,
            "findingType": f.finding_type,
            "title": f.title,
            "explanation": f.explanation,
            "ruleCode": f.rule_code,
            "evidence": f.evidence_reference or [],
            "reviewStatus": f.review_status,
            "createdAt": f.created_at.isoformat() if f.created_at else None,
        })

    prescriptions_list = []
    for rx in doc.prescription_items:
        prescriptions_list.append({
            "id": str(rx.id),
            "documentId": str(rx.document_id),
            "medicineNameRaw": rx.medicine_name_raw,
            "strengthText": rx.strength_text,
            "doseText": rx.dose_text,
            "routeText": rx.route_text,
            "frequencyText": rx.frequency_text,
            "durationText": rx.duration_text,
            "instructionsText": rx.instructions_text,
            "confidence": rx.confidence,
            "reviewStatus": rx.review_status,
            "sourcePage": rx.source_page,
            "sourceSnippet": rx.source_snippet,
        })

    return ApiResponse(
        data=DocumentDetailData(
            id=doc.id,
            originalFilename=doc.original_filename,
            documentTitle=doc.document_title or doc.original_filename,
            documentType=doc.document_type,
            testDate=doc.document_date,
            uploadedAt=doc.created_at,
            pageCount=doc.page_count,
            providerName=doc.provider_name,
            facilityName=doc.facility_name,
            status=doc.status,
            summary=summary_dict,
            measurements=measurements_list,
            findings=findings_list,
            prescriptions=prescriptions_list,
        )
    )


@router.get("/{document_id}/file")
async def get_document_source_file(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream the original uploaded file securely with ownership authorization.
    """
    doc = await get_document_for_user(db, document_id, current_user.id)
    if not os.path.exists(doc.storage_path):
        from app.core.errors import NotFoundError
        raise NotFoundError(message="Source file not found on storage server.")

    return FileResponse(
        path=doc.storage_path,
        media_type=doc.mime_type,
        filename=doc.original_filename,
    )


@router.delete("/{document_id}", response_model=ApiResponse[Dict[str, str]])
async def delete_user_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently delete a document and its extracted findings and files.
    """
    await delete_document(db, document_id, current_user.id)
    return ApiResponse(data={"message": "Document deleted successfully."})

