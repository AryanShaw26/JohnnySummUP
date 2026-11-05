"""
ExtractedMeasurement model – ``extracted_measurements`` table.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.medical_document import MedicalDocument


class ExtractedMeasurement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "extracted_measurements"
    __table_args__ = (
        Index("ix_extracted_measurements_doc_param", "document_id", "parameter_code"),
        Index("ix_extracted_measurements_param_date", "parameter_code", "test_date"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("medical_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parameter_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    parameter_name_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    parameter_name_display: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    raw_value_text: Mapped[str] = mapped_column(String(120), nullable=False)
    numeric_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    qualitative_value: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    
    source_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    normalized_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    normalized_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    reference_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reference_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reference_text_raw: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    
    source_flag: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # HIGH, LOW, ABNORMAL, etc.
    calculated_range_status: Mapped[str] = mapped_column(
        String(30), default="unknown", nullable=False,
    )  # within_range, below_range, above_range, not_comparable, unknown
    
    test_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(20), default="unreviewed", nullable=False,
    )  # unreviewed, confirmed, corrected, needs_review, rejected
    
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_bbox: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, default=dict, nullable=True)

    # Relationships
    document: Mapped["MedicalDocument"] = relationship("MedicalDocument", back_populates="extracted_measurements")

    def __repr__(self) -> str:
        return f"<ExtractedMeasurement {self.parameter_name_raw}={self.raw_value_text} {self.source_unit}>"
