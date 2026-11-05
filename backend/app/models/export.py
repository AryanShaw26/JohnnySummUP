"""
GeneratedExport model – ``generated_exports`` table.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.medical_document import MedicalDocument
    from app.models.user import User


class GeneratedExport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "generated_exports"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("medical_documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    export_type: Mapped[str] = mapped_column(
        String(50), default="single_report_summary", nullable=False,
    )  # single_report_summary, comparison_report, records_export
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="completed", nullable=False,
    )  # queued, generating, completed, failed, expired
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    document: Mapped[Optional["MedicalDocument"]] = relationship("MedicalDocument", back_populates="exports")

    def __repr__(self) -> str:
        return f"<GeneratedExport {self.export_type} status={self.status}>"

