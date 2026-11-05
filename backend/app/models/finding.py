"""
MedicalFinding model – ``medical_findings`` table.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.medical_document import MedicalDocument


class MedicalFinding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "medical_findings"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("medical_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    measurement_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("extracted_measurements.id", ondelete="SET NULL"),
        nullable=True,
    )
    finding_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )  # below_report_range, above_report_range, source_flagged, needs_review, notable_change, document_observation
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    rule_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    evidence_reference: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(20), default="unreviewed", nullable=False,
    )  # unreviewed, reviewed, dismissed, needs_review

    # Relationships
    document: Mapped["MedicalDocument"] = relationship("MedicalDocument", back_populates="findings")

    def __repr__(self) -> str:
        return f"<MedicalFinding {self.title}>"
