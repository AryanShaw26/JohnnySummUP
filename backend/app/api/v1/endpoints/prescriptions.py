"""
Prescriptions endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.errors import NotFoundError
from app.models.medical_document import MedicalDocument
from app.models.prescription_item import PrescriptionItem
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.prescription import PrescriptionItemData

router = APIRouter()


@router.get("", response_model=ApiResponse[List[Dict[str, Any]]])
async def list_prescriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List extracted prescription items across user documents.
    """
    stmt = (
        select(PrescriptionItem, MedicalDocument.document_title, MedicalDocument.original_filename, MedicalDocument.document_date)
        .join(MedicalDocument, PrescriptionItem.document_id == MedicalDocument.id)
        .where(
            MedicalDocument.user_id == current_user.id,
            MedicalDocument.deleted_at.is_(None),
        )
        .order_by(desc(PrescriptionItem.created_at))
    )
    res = await db.execute(stmt)
    rows = res.all()

    items = []
    for rx, title, orig_name, date_val in rows:
        items.append({
            "id": str(rx.id),
            "documentId": str(rx.document_id),
            "documentTitle": title or orig_name,
            "date": date_val.strftime("%Y-%m-%d") if date_val else "Not stated",
            "medicineName": rx.medicine_name_raw,
            "strength": rx.strength_text,
            "dose": rx.dose_text,
            "frequency": rx.frequency_text,
            "duration": rx.duration_text,
            "instructions": rx.instructions_text,
            "confidence": rx.confidence,
            "reviewStatus": rx.review_status,
            "sourceSnippet": rx.source_snippet,
            "sourcePage": rx.source_page,
        })

    return ApiResponse(data=items)

