from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import Base


class MedicalMeasurement(Base):
    __tablename__ = "medical_measurements"
    __table_args__ = (
        Index("ix_medical_measurements_user_param_date", "user_id", "parameter_name", "report_date"),
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
        index=True,
    )
    parameter_name: Mapped[str] = mapped_column(String(160), nullable=False)
    parameter_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    numeric_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(60), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    reference_low: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    reference_high: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    reference_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    document = relationship("MedicalDocument", back_populates="measurements")
    source_finding = relationship("ExtractedFinding")
