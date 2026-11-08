from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import Base


class MedicalDocument(Base):
    __tablename__ = "medical_documents"
    __table_args__ = (
        CheckConstraint("file_size_bytes > 0", name="ck_medical_documents_positive_size"),
        Index("ix_medical_documents_user_created", "user_id", "created_at"),
        Index("ix_medical_documents_user_type_created", "user_id", "document_type", "created_at"),
        Index("ix_medical_documents_user_status", "user_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(15), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    report_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="uploaded")
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="medical_documents")
    analyses = relationship(
        "DocumentAnalysis",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="desc(DocumentAnalysis.version)",
    )
    findings = relationship(
        "ExtractedFinding",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    measurements = relationship(
        "MedicalMeasurement",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    flags = relationship(
        "AbnormalityFlag",
        back_populates="document",
        cascade="all, delete-orphan",
    )
