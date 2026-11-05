"""
PDF Report Export endpoints.
"""

from __future__ import annotations

import os
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.errors import ForbiddenError, NotFoundError
from app.models.export import GeneratedExport
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.export import ExportCreateRequest, ExportStatusData
from app.services.export_service import generate_document_pdf_summary

router = APIRouter()


@router.post("", response_model=ApiResponse[ExportStatusData], status_code=status.HTTP_202_ACCEPTED)
async def create_export(
    payload: ExportCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate downloadable PDF report summary.
    """
    if not payload.documentId:
        from app.core.errors import ValidationError
        raise ValidationError(message="documentId is required to generate a summary export.")

    export = await generate_document_pdf_summary(db, payload.documentId, current_user.id)

    return ApiResponse(
        data=ExportStatusData(
            exportId=export.id,
            status=export.status,
            downloadUrl=f"/api/v1/medical/exports/{export.id}/download",
        )
    )


@router.get("/{export_id}/download")
async def download_export(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download generated PDF summary file.
    """
    export = await db.get(GeneratedExport, export_id)
    if not export:
        raise NotFoundError(message="Export file not found.")

    if export.user_id != current_user.id:
        raise ForbiddenError(message="Access denied to this export.")

    if not os.path.exists(export.storage_path):
        raise NotFoundError(message="Export file missing on server.")

    return FileResponse(
        path=export.storage_path,
        media_type="application/pdf",
        filename=os.path.basename(export.storage_path),
    )

