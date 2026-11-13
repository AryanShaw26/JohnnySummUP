from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import Base


class WorkspaceDocument(Base):
    __tablename__ = "workspace_documents"
    __table_args__ = (
        CheckConstraint("file_size_bytes > 0", name="ck_workspace_documents_positive_size"),
        Index("ix_workspace_documents_user_workspace", "user_id", "workspace"),
        Index("ix_workspace_documents_user_workspace_created", "user_id", "workspace", "created_at"),
        Index("ix_workspace_documents_user_status", "user_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(60), nullable=False)
    document_subtype: Mapped[str | None] = mapped_column(String(80), nullable=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(15), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    document_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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

    user = relationship("User", backref="workspace_documents")
    analyses = relationship(
        "WorkspaceAnalysis",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="desc(WorkspaceAnalysis.version)",
    )
    findings = relationship(
        "WorkspaceFinding",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class WorkspaceAnalysis(Base):
    __tablename__ = "workspace_analyses"
    __table_args__ = (
        UniqueConstraint("document_id", "version", name="uq_workspace_analyses_doc_version"),
        Index("ix_workspace_analyses_user_workspace", "user_id", "workspace"),
        Index("ix_workspace_analyses_doc_created", "document_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspace_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued")
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    key_points: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, default="gemini")
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    document = relationship("WorkspaceDocument", back_populates="analyses")
    findings = relationship("WorkspaceFinding", back_populates="analysis", cascade="all, delete-orphan")


class WorkspaceFinding(Base):
    __tablename__ = "workspace_findings"
    __table_args__ = (
        Index("ix_workspace_findings_user_workspace", "user_id", "workspace"),
        Index("ix_workspace_findings_doc", "document_id"),
        Index("ix_workspace_findings_type", "finding_type"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspace_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspace_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace: Mapped[str] = mapped_column(String(40), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_priority: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_section: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    document = relationship("WorkspaceDocument", back_populates="findings")
    analysis = relationship("WorkspaceAnalysis", back_populates="findings")
