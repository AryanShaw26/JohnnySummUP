"""
MedicalSummary model – ``medical_summaries`` table.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Float, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.medical_document import MedicalDocument


class MedicalSummary(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "medical_summaries"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("medical_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary_type: Mapped[str] = mapped_column(
        String(50), default="document_summary", nullable=False,
    )  # document_summary, section_summary, comparison_summary
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_summary: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    model_provider: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(64), default="v1.0", nullable=True)
    pipeline_version: Mapped[Optional[str]] = mapped_column(String(64), default="1.0.0", nullable=True)
    validation_status: Mapped[str] = mapped_column(
        String(20), default="passed", nullable=False,
    )  # pending, passed, needs_review, rejected
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    document: Mapped["MedicalDocument"] = relationship("MedicalDocument", back_populates="summaries")

    def __repr__(self) -> str:
        return f"<MedicalSummary type={self.summary_type}>"
