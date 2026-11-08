from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import Base


class AbnormalityFlag(Base):
    __tablename__ = "abnormality_flags"
    __table_args__ = (
        Index("ix_abnormality_flags_user_created", "user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("medical_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_finding_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("extracted_findings.id", ondelete="SET NULL"),
        nullable=True,
    )
    measurement_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("medical_measurements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parameter_name: Mapped[str] = mapped_column(String(160), nullable=False)
    observed_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(60), nullable=True)
    reference_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    flag_type: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="review")
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    document = relationship("MedicalDocument", back_populates="flags")
    source_finding = relationship("ExtractedFinding")
    measurement = relationship("MedicalMeasurement")
