"""
Medical document service: upload, storage, ownership verification,
and document lifecycle management.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai_pipeline.orchestrator import run_pipeline_for_document
from app.core.config import settings
from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.models.finding import MedicalFinding
from app.models.measurement import ExtractedMeasurement
from app.models.medical_document import MedicalDocument
from app.models.prescription_item import PrescriptionItem
from app.models.processing_job import ProcessingJob
from app.models.summary import MedicalSummary


async def process_document_upload(
    db: AsyncSession,
    user_id: UUID,
    file: UploadFile,
    document_type: str = "lab_report",
    document_title: Optional[str] = None,
    test_date: Optional[str] = None,
) -> Tuple[MedicalDocument, ProcessingJob]:
    """
    Saves uploaded file to disk and enqueues the AI pipeline asynchronously.
    """
    # 1. Validation
    filename = file.filename or "medical_document.pdf"
    content_type = file.content_type or "application/pdf"

    if content_type not in settings.ALLOWED_MIME_TYPES:
        raise ValidationError(
            message=f"Unsupported file type '{content_type}'. Supported: {settings.ALLOWED_MIME_TYPES}"
        )

    # 2. Store file securely
    doc_id = uuid.uuid4()
    ext = Path(filename).suffix or ".pdf"
    safe_filename = f"{doc_id}{ext}"
    storage_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    sha256 = hashlib.sha256()
    size_bytes = 0

    with open(storage_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            size_bytes += len(chunk)
            if size_bytes > settings.MAX_FILE_SIZE_BYTES:
                buffer.close()
                if os.path.exists(storage_path):
                    os.remove(storage_path)
                raise ValidationError(message="File size exceeds maximum allowed limit (20MB).")
            sha256.update(chunk)
            buffer.write(chunk)

    parsed_date = None
    if test_date:
        try:
            from dateutil import parser
            parsed_date = parser.parse(test_date)
        except Exception:
            pass

    # 3. Create database records
    doc = MedicalDocument(
        id=doc_id,
        user_id=user_id,
        original_filename=filename,
        storage_path=storage_path,
        file_size_bytes=size_bytes,
        mime_type=content_type,
        document_type=document_type,
        document_title=document_title or filename,
        document_date=parsed_date,
        status="queued",
        checksum_sha256=sha256.hexdigest(),
    )
    db.add(doc)
    await db.flush()

    job = ProcessingJob(
        document_id=doc.id,
        job_type="ocr_extract_analyse",
        status="queued",
        stage="queued",
        progress_percent=0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(doc)
    await db.refresh(job)

    # 4. Trigger asynchronous background task
    asyncio.create_task(run_pipeline_for_document(doc.id, job.id))

    return doc, job


async def get_document_for_user(
    db: AsyncSession,
    document_id: UUID,
    user_id: UUID,
) -> MedicalDocument:
    """
    Enforces server-side ownership authorization.
    """
    query = (
        select(MedicalDocument)
        .where(MedicalDocument.id == document_id)
        .options(
            selectinload(MedicalDocument.extracted_measurements),
            selectinload(MedicalDocument.findings),
            selectinload(MedicalDocument.summaries),
            selectinload(MedicalDocument.prescription_items),
            selectinload(MedicalDocument.processing_jobs),
        )
    )
    res = await db.execute(query)
    doc = res.scalar_one_or_none()

    if not doc:
        raise NotFoundError(message="Document not found.")

    if doc.user_id != user_id:
        raise ForbiddenError(message="Access denied to this document.")

    return doc


async def list_documents_for_user(
    db: AsyncSession,
    user_id: UUID,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    document_type: Optional[str] = None,
    status: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Lists documents for user with counts and filters.
    """
    stmt = select(MedicalDocument).where(
        MedicalDocument.user_id == user_id,
        MedicalDocument.deleted_at.is_(None),
    )

    if document_type:
        stmt = stmt.where(MedicalDocument.document_type == document_type)
    if status:
        stmt = stmt.where(MedicalDocument.status == status)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            (MedicalDocument.original_filename.ilike(pattern))
            | (MedicalDocument.document_title.ilike(pattern))
            | (MedicalDocument.facility_name.ilike(pattern))
        )

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_stmt)
    total_count = total_res.scalar() or 0

    # Paged query
    stmt = (
        stmt.order_by(desc(MedicalDocument.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(
            selectinload(MedicalDocument.extracted_measurements),
            selectinload(MedicalDocument.findings),
        )
    )
    res = await db.execute(stmt)
    docs = res.scalars().all()

    items: List[Dict[str, Any]] = []
    for d in docs:
        items.append({
            "id": d.id,
            "original_filename": d.original_filename,
            "document_title": d.document_title or d.original_filename,
            "document_type": d.document_type,
            "document_date": d.document_date,
            "created_at": d.created_at,
            "status": d.status,
            "page_count": d.page_count,
            "measurementCount": len(d.extracted_measurements),
            "findingCount": len(d.findings),
        })

    return items, total_count


async def delete_document(
    db: AsyncSession,
    document_id: UUID,
    user_id: UUID,
) -> None:
    """
    Safely deletes document and its stored files.
    """
    doc = await get_document_for_user(db, document_id, user_id)

    # Delete disk file
    if os.path.exists(doc.storage_path):
        try:
            os.remove(doc.storage_path)
        except Exception:
            pass

    await db.delete(doc)
    await db.commit()

