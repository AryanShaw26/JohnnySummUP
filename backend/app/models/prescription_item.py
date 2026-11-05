"""
PrescriptionItem model – ``prescription_items`` table.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.medical_document import MedicalDocument


class PrescriptionItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "prescription_items"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("medical_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    medicine_name_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    medicine_name_normalized: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    strength_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dose_text: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    route_text: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    frequency_text: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    duration_text: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    instructions_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(20), default="unreviewed", nullable=False,
    )  # unreviewed, confirmed, corrected, needs_review
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    document: Mapped["MedicalDocument"] = relationship("MedicalDocument", back_populates="prescription_items")

    def __repr__(self) -> str:
        return f"<PrescriptionItem {self.medicine_name_raw}>"

