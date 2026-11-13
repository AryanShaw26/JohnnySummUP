import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workspace_document import (
    WorkspaceAnalysis,
    WorkspaceDocument,
    WorkspaceFinding,
)
from app.services.ai.gemini_service import GeminiServiceError, gemini_workspace_service
from app.services.documents.classification import document_classifier, normalize_workspace
from app.services.documents.extraction.router import extraction_router
from app.services.documents.storage import workspace_storage_service

logger = logging.getLogger("johnnysummup.orchestrator")


class WorkspaceDocumentOrchestrator:
    @classmethod
    async def ingest_document(
        cls,
        db: Session,
        user_id: UUID,
        workspace: str,
        upload: UploadFile,
        document_subtype: str | None = None,
        label: str | None = None,
        mock_ai_response: dict[str, Any] | None = None,
    ) -> WorkspaceDocument:
        """Ingests, stores, extracts, classifies, and triggers AI analysis for a document."""
        norm_workspace = normalize_workspace(workspace)

        # 1. Validation and Storage
        stored_filename, storage_key, file_size, mime_type, ext = await workspace_storage_service.save_upload(
            upload, user_id
        )

        doc = WorkspaceDocument(
            user_id=user_id,
            workspace=norm_workspace,
            document_type=norm_workspace,
            document_subtype=document_subtype,
            label=label or upload.filename,
            original_filename=upload.filename or "document",
            stored_filename=stored_filename,
            storage_key=storage_key,
            mime_type=mime_type,
            file_extension=ext,
            file_size_bytes=file_size,
            status="stored",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # 2. Process extraction and analysis
        await cls.process_document(db, doc.id, user_id, mock_ai_response=mock_ai_response)
        db.refresh(doc)
        return doc

    @classmethod
    async def process_document(
        cls,
        db: Session,
        document_id: UUID,
        user_id: UUID,
        mock_ai_response: dict[str, Any] | None = None,
    ) -> WorkspaceDocument:
        """Executes extraction, classification, Gemini analysis, and persistence."""
        doc = db.execute(
            select(WorkspaceDocument).where(
                WorkspaceDocument.id == document_id,
                WorkspaceDocument.user_id == user_id,
                WorkspaceDocument.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if not doc:
            raise ValueError("Document not found or access denied")

        # 1. Extraction stage
        doc.status = "extracting"
        db.commit()

        file_path = workspace_storage_service.get_file_path(doc.storage_key, user_id)
        extract_res = extraction_router.extract_document(file_path, doc.mime_type)

        doc.extraction_method = extract_res.extraction_method
        doc.page_count = max(1, extract_res.page_count)
        doc.character_count = extract_res.total_characters

        if extract_res.status in ("failed", "corrupt", "unsupported", "no_readable_text") or not extract_res.text.strip():
            doc.status = "failed"
            doc.failure_code = extract_res.error_code or "NO_READABLE_TEXT"
            doc.failure_message = extract_res.error_message or "We could not extract readable text from this document."
            db.commit()
            db.refresh(doc)
            return doc

        doc.status = "extracted"
        db.commit()

        # 2. Classification stage
        doc.status = "classifying"
        db.commit()

        classification = document_classifier.classify(
            doc.workspace, extract_res.text, doc.document_subtype
        )
        if not doc.document_subtype or doc.document_subtype == "other":
            doc.document_subtype = classification.suggested_subtype

        # 3. Create analysis record
        next_version = (
            db.execute(
                select(WorkspaceAnalysis.version)
                .where(WorkspaceAnalysis.document_id == doc.id)
                .order_by(WorkspaceAnalysis.version.desc())
            ).scalars().first()
            or 0
        ) + 1

        analysis = WorkspaceAnalysis(
            document_id=doc.id,
            user_id=user_id,
            workspace=doc.workspace,
            version=next_version,
            status="analyzing",
            extracted_text=extract_res.text,
            started_at=datetime.now(timezone.utc),
        )
        db.add(analysis)
        doc.status = "analyzing"
        db.commit()
        db.refresh(analysis)

        # 4. AI Analysis stage
        try:
            if mock_ai_response is not None:
                ai_data = mock_ai_response
            else:
                ai_data = await gemini_workspace_service.analyze_workspace_document(
                    workspace=doc.workspace,
                    document_text=extract_res.text,
                    document_subtype=doc.document_subtype,
                )

            # 5. Persist analysis and findings atomically
            analysis.status = "completed"
            analysis.summary = ai_data.get("summary")
            analysis.structured_data = ai_data.get("structured_data")
            analysis.key_points = ai_data.get("key_points", [])
            analysis.provider = ai_data.get("provider", "gemini")
            analysis.model_name = ai_data.get("model_name")
            analysis.completed_at = datetime.now(timezone.utc)

            # Persist findings
            findings_data = ai_data.get("findings", [])
            for f in findings_data:
                finding = WorkspaceFinding(
                    analysis_id=analysis.id,
                    document_id=doc.id,
                    user_id=user_id,
                    workspace=doc.workspace,
                    finding_type=f.get("finding_type", "general"),
                    title=f.get("title", "Finding"),
                    explanation=f.get("explanation", ""),
                    why_it_matters=f.get("why_it_matters"),
                    review_priority=f.get("review_priority", "info"),
                    source_page=f.get("source_page"),
                    source_section=f.get("source_section"),
                    source_excerpt=f.get("source_excerpt"),
                    metadata_json=f.get("metadata_json"),
                )
                db.add(finding)

            doc.status = "completed"
            doc.failure_code = None
            doc.failure_message = None
            db.commit()
            db.refresh(doc)

        except GeminiServiceError as g_err:
            logger.error("orchestrator_gemini_error doc_id=%s code=%s msg=%s", doc.id, g_err.error_code, g_err.user_message)
            analysis.status = "failed"
            analysis.error_code = g_err.error_code
            analysis.error_message = g_err.user_message
            doc.status = "failed"
            doc.failure_code = g_err.error_code
            doc.failure_message = g_err.user_message
            db.commit()

        except Exception as exc:
            logger.exception("orchestrator_unexpected_error doc_id=%s exc=%s", doc.id, exc)
            analysis.status = "failed"
            analysis.error_code = "analysis_failed"
            analysis.error_message = f"Document analysis failed: {exc}"
            doc.status = "failed"
            doc.failure_code = "analysis_failed"
            doc.failure_message = "Document analysis could not be completed."
            db.commit()

        return doc


workspace_orchestrator = WorkspaceDocumentOrchestrator()
