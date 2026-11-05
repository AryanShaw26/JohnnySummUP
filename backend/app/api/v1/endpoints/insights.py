"""
AI Insights endpoints for evidence-grounded findings.
"""

from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.finding import MedicalFinding
from app.models.medical_document import MedicalDocument
from app.models.user import User
from app.schemas.common import ApiResponse

router = APIRouter()


@router.get("", response_model=ApiResponse[List[Dict[str, Any]]])
async def list_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List user-visible evidence-linked findings categorized by status.
    """
    stmt = (
        select(MedicalFinding, MedicalDocument.document_title, MedicalDocument.original_filename)
        .join(MedicalDocument, MedicalFinding.document_id == MedicalDocument.id)
        .where(
            MedicalDocument.user_id == current_user.id,
            MedicalDocument.deleted_at.is_(None),
        )
        .order_by(desc(MedicalFinding.created_at))
    )
    res = await db.execute(stmt)
    rows = res.all()

    items = []
    for f, title, orig_name in rows:
        items.append({
            "id": str(f.id),
            "documentId": str(f.document_id),
            "documentTitle": title or orig_name,
            "findingType": f.finding_type,
            "title": f.title,
            "explanation": f.explanation,
            "ruleCode": f.rule_code,
            "evidence": f.evidence_reference or [],
            "reviewStatus": f.review_status,
            "createdAt": f.created_at.isoformat() if f.created_at else None,
        })

    return ApiResponse(data=items)

