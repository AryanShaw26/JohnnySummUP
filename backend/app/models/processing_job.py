"""
ProcessingJob model – ``processing_jobs`` table.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.medical_document import MedicalDocument


class ProcessingJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        Index("ix_processing_jobs_doc_status", "document_id", "status"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("medical_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(
        String(50), default="ocr_extract_analyse", nullable=False,
    )  # ocr_extract_analyse, regenerate_summary, generate_export
    status: Mapped[str] = mapped_column(
        String(30), default="queued", nullable=False,
    )  # queued, processing, completed, needs_review, failed, cancelled
    stage: Mapped[str] = mapped_column(
        String(50), default="queued", nullable=False,
    )  # validation, text_acquisition, extraction, rule_evaluation, summarization, completed
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(64), default="1.0.0", nullable=False)
    provider_metadata: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    error_message_safe: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    document: Mapped["MedicalDocument"] = relationship("MedicalDocument", back_populates="processing_jobs")

    def __repr__(self) -> str:
        return f"<ProcessingJob {self.job_type} status={self.status}>"
