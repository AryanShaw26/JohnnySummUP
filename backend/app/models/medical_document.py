"""
MedicalDocument model – ``medical_documents`` table.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.annotation import DocumentAnnotation
    from app.models.export import GeneratedExport
    from app.models.finding import MedicalFinding
    from app.models.measurement import ExtractedMeasurement
    from app.models.prescription_item import PrescriptionItem
    from app.models.processing_job import ProcessingJob
    from app.models.summary import MedicalSummary
    from app.models.user import User


class MedicalDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "medical_documents"
    __table_args__ = (
        Index("ix_medical_documents_user_status", "user_id", "status"),
        Index("ix_medical_documents_user_doc_type", "user_id", "document_type"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    document_type: Mapped[str] = mapped_column(
        String(50), default="lab_report", nullable=False,
    )  # lab_report, prescription, imaging_report, discharge_summary, other
    status: Mapped[str] = mapped_column(
        String(30), default="uploaded", nullable=False,
    )  # uploaded, queued, processing, completed, needs_review, failed, deleted
    document_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    document_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    facility_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, default=dict, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="medical_documents")
    processing_jobs: Mapped[List["ProcessingJob"]] = relationship(
        "ProcessingJob", back_populates="document", cascade="all, delete-orphan",
    )
    extracted_measurements: Mapped[List["ExtractedMeasurement"]] = relationship(
        "ExtractedMeasurement", back_populates="document", cascade="all, delete-orphan",
    )
    summaries: Mapped[List["MedicalSummary"]] = relationship(
        "MedicalSummary", back_populates="document", cascade="all, delete-orphan",
    )
    findings: Mapped[List["MedicalFinding"]] = relationship(
        "MedicalFinding", back_populates="document", cascade="all, delete-orphan",
    )
    prescription_items: Mapped[List["PrescriptionItem"]] = relationship(
        "PrescriptionItem", back_populates="document", cascade="all, delete-orphan",
    )
    annotations: Mapped[List["DocumentAnnotation"]] = relationship(
        "DocumentAnnotation", back_populates="document", cascade="all, delete-orphan",
    )
    exports: Mapped[List["GeneratedExport"]] = relationship(
        "GeneratedExport", back_populates="document", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<MedicalDocument {self.original_filename}>"
