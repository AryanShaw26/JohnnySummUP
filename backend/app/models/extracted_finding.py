from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import Base


class ExtractedFinding(Base):
    __tablename__ = "extracted_findings"
    __table_args__ = (
        Index("ix_extracted_findings_user_doc", "user_id", "document_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("medical_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(60), nullable=True)
    reference_low: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    reference_high: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    reference_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    is_extracted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    document = relationship("MedicalDocument", back_populates="findings")
    analysis = relationship("DocumentAnalysis", back_populates="findings")
