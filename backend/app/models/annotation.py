"""
DocumentAnnotation model – ``document_annotations`` table.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.medical_document import MedicalDocument
    from app.models.user import User


class DocumentAnnotation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document_annotations"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("medical_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    annotation_type: Mapped[str] = mapped_column(
        String(50), default="user_note", nullable=False,
    )  # user_note, question_for_clinician, correction_note
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    document: Mapped["MedicalDocument"] = relationship("MedicalDocument", back_populates="annotations")

    def __repr__(self) -> str:
        return f"<DocumentAnnotation type={self.annotation_type}>"

