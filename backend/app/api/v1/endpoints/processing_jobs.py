"""
Processing jobs endpoints for polling status and retries.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_pipeline.orchestrator import run_pipeline_for_document
from app.core.dependencies import get_current_user, get_db
from app.core.errors import ForbiddenError, NotFoundError
from app.models.medical_document import MedicalDocument
from app.models.processing_job import ProcessingJob
from app.models.user import User
from app.schemas.common import ApiResponse

router = APIRouter()


@router.get("/{job_id}", response_model=ApiResponse[Dict[str, Any]])
async def get_job_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get job progress, stage, and safe messages.
    """
    stmt = (
        select(ProcessingJob)
        .join(MedicalDocument, ProcessingJob.document_id == MedicalDocument.id)
        .where(ProcessingJob.id == job_id)
    )
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()

    if not job:
        raise NotFoundError(message="Processing job not found.")

    doc = await db.get(MedicalDocument, job.document_id)
    if not doc or doc.user_id != current_user.id:
        raise ForbiddenError(message="Access denied to this job.")

    return ApiResponse(
        data={
            "jobId": str(job.id),
            "documentId": str(job.document_id),
            "status": job.status,
            "stage": job.stage,
            "progressPercent": job.progress_percent,
            "safeMessage": job.error_message_safe or f"Processing stage: {job.stage.replace('_', ' ').title()}",
            "retryable": job.status == "failed",
            "updatedAt": job.updated_at.isoformat() if job.updated_at else None,
        }
    )


@router.post("/{job_id}/retry", response_model=ApiResponse[Dict[str, Any]])
async def retry_failed_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retry a failed processing job.
    """
    job = await db.get(ProcessingJob, job_id)
    if not job:
        raise NotFoundError(message="Processing job not found.")

    doc = await db.get(MedicalDocument, job.document_id)
    if not doc or doc.user_id != current_user.id:
        raise ForbiddenError(message="Access denied to this job.")

    job.status = "queued"
    job.stage = "queued"
    job.progress_percent = 0
    job.attempt_count += 1
    doc.status = "queued"
    await db.commit()

    asyncio.create_task(run_pipeline_for_document(doc.id, job.id))

    return ApiResponse(
        data={
            "jobId": str(job.id),
            "documentId": str(doc.id),
            "status": job.status,
        }
    )

