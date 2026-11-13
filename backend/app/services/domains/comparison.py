import difflib
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workspace_document import WorkspaceAnalysis, WorkspaceDocument


class DocumentComparisonService:
    @classmethod
    def compare_documents(
        cls, db: Session, doc_a_id: UUID, doc_b_id: UUID, user_id: UUID, workspace: str
    ) -> dict[str, Any]:
        """Compares two authorized documents within the same workspace."""
        doc_a = db.execute(
            select(WorkspaceDocument).where(
                WorkspaceDocument.id == doc_a_id,
                WorkspaceDocument.user_id == user_id,
                WorkspaceDocument.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        doc_b = db.execute(
            select(WorkspaceDocument).where(
                WorkspaceDocument.id == doc_b_id,
                WorkspaceDocument.user_id == user_id,
                WorkspaceDocument.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if not doc_a or not doc_b:
            raise ValueError("One or both documents not found or access denied.")

        # Latest analyses
        analysis_a = db.execute(
            select(WorkspaceAnalysis)
            .where(WorkspaceAnalysis.document_id == doc_a_id)
            .order_by(WorkspaceAnalysis.version.desc())
        ).scalar_one_or_none()

        analysis_b = db.execute(
            select(WorkspaceAnalysis)
            .where(WorkspaceAnalysis.document_id == doc_b_id)
            .order_by(WorkspaceAnalysis.version.desc())
        ).scalar_one_or_none()

        text_a = analysis_a.extracted_text if analysis_a else ""
        text_b = analysis_b.extracted_text if analysis_b else ""

        # Compute line diff
        diff = list(
            difflib.unified_diff(
                (text_a or "").splitlines(keepends=True),
                (text_b or "").splitlines(keepends=True),
                fromfile=doc_a.original_filename,
                tofile=doc_b.original_filename,
                n=3,
            )
        )

        additions = [line[1:].strip() for line in diff if line.startswith("+") and not line.startswith("+++")]
        deletions = [line[1:].strip() for line in diff if line.startswith("-") and not line.startswith("---")]

        # Structured differences
        data_a = (analysis_a.structured_data if analysis_a else {}) or {}
        data_b = (analysis_b.structured_data if analysis_b else {}) or {}

        field_changes: list[dict[str, Any]] = []
        all_keys = set(data_a.keys()).union(set(data_b.keys())) - {"findings", "disclaimer", "overview"}
        for k in sorted(all_keys):
            val_a = data_a.get(k)
            val_b = data_b.get(k)
            if val_a != val_b:
                field_changes.append({
                    "field": k,
                    "document_a_value": val_a,
                    "document_b_value": val_b,
                })

        return {
            "workspace": workspace,
            "document_a": {
                "id": str(doc_a.id),
                "filename": doc_a.original_filename,
                "document_type": doc_a.document_type,
                "document_subtype": doc_a.document_subtype,
                "created_at": doc_a.created_at.isoformat(),
                "summary": analysis_a.summary if analysis_a else None,
            },
            "document_b": {
                "id": str(doc_b.id),
                "filename": doc_b.original_filename,
                "document_type": doc_b.document_type,
                "document_subtype": doc_b.document_subtype,
                "created_at": doc_b.created_at.isoformat(),
                "summary": analysis_b.summary if analysis_b else None,
            },
            "summary_comparison": {
                "total_additions_count": len(additions),
                "total_deletions_count": len(deletions),
                "changed_fields_count": len(field_changes),
            },
            "field_changes": field_changes,
            "sample_additions": additions[:15],
            "sample_deletions": deletions[:15],
            "raw_diff": "".join(diff[:100]),
        }


document_comparison_service = DocumentComparisonService()
