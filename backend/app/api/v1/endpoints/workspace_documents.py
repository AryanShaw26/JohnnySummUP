from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.workspace_document import (
    WorkspaceAnalysis,
    WorkspaceDocument,
    WorkspaceFinding,
)
from app.schemas.workspace_document import (
    WorkspaceAnalysisResponse,
    WorkspaceDocumentListResponse,
    WorkspaceDocumentResponse,
    WorkspaceFindingResponse,
    WorkspaceFindingUpdate,
    WorkspaceOverviewResponse,
)
from app.services.documents.classification import VALID_WORKSPACES, normalize_workspace
from app.services.documents.orchestrator import workspace_orchestrator
from app.services.documents.storage import workspace_storage_service
from app.services.domains.comparison import document_comparison_service

router = APIRouter(tags=["workspace-documents"])


def validate_workspace(workspace: str) -> str:
    norm = normalize_workspace(workspace)
    if norm not in VALID_WORKSPACES and workspace not in VALID_WORKSPACES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workspace '{workspace}'. Allowed: legal, finance, insurance, education, employment-government",
        )
    return norm


@router.post("/documents/{workspace}", response_model=WorkspaceDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_workspace_document(
    workspace: str,
    file: UploadFile = File(...),
    document_subtype: str | None = Form(default=None),
    label: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    norm_workspace = validate_workspace(workspace)
    doc = await workspace_orchestrator.ingest_document(
        db=db,
        user_id=current_user.id,
        workspace=norm_workspace,
        upload=file,
        document_subtype=document_subtype,
        label=label,
    )
    return doc


@router.get("/documents/{workspace}", response_model=WorkspaceDocumentListResponse)
def list_workspace_documents(
    workspace: str,
    search: str | None = Query(default=None),
    subtype: str | None = Query(default=None),
    status_filter: str | None = Query(default=None),
    sort: str = Query(default="newest"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    norm_workspace = validate_workspace(workspace)
    query = select(WorkspaceDocument).where(
        WorkspaceDocument.user_id == current_user.id,
        WorkspaceDocument.workspace == norm_workspace,
        WorkspaceDocument.deleted_at.is_(None),
    )

    if subtype:
        query = query.where(WorkspaceDocument.document_subtype == subtype)
    if status_filter:
        query = query.where(WorkspaceDocument.status == status_filter)
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            WorkspaceDocument.original_filename.ilike(search_pattern)
            | WorkspaceDocument.label.ilike(search_pattern)
            | WorkspaceDocument.document_subtype.ilike(search_pattern)
        )

    # Count
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    # Sort
    if sort == "oldest":
        query = query.order_by(WorkspaceDocument.created_at.asc())
    elif sort == "filename":
        query = query.order_by(WorkspaceDocument.original_filename.asc())
    else:
        query = query.order_by(WorkspaceDocument.created_at.desc())

    # Pagination
    offset = (page - 1) * limit
    items = (
        db.execute(
            query.offset(offset)
            .limit(limit)
            .options(
                joinedload(WorkspaceDocument.analyses),
                joinedload(WorkspaceDocument.findings),
            )
        )
        .unique()
        .scalars()
        .all()
    )

    total_pages = max(1, (total + limit - 1) // limit)
    return WorkspaceDocumentListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/documents/{workspace}/{document_id}", response_model=WorkspaceDocumentResponse)
def get_workspace_document(
    workspace: str,
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    norm_workspace = validate_workspace(workspace)
    doc = (
        db.execute(
            select(WorkspaceDocument)
            .where(
                WorkspaceDocument.id == document_id,
                WorkspaceDocument.user_id == current_user.id,
                WorkspaceDocument.workspace == norm_workspace,
                WorkspaceDocument.deleted_at.is_(None),
            )
            .options(
                joinedload(WorkspaceDocument.analyses).joinedload(WorkspaceAnalysis.findings),
                joinedload(WorkspaceDocument.findings),
            )
        )
        .unique()
        .scalar_one_or_none()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


@router.get("/documents/{workspace}/{document_id}/status")
def get_document_status(
    workspace: str,
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    norm_workspace = validate_workspace(workspace)
    doc = db.execute(
        select(WorkspaceDocument).where(
            WorkspaceDocument.id == document_id,
            WorkspaceDocument.user_id == current_user.id,
            WorkspaceDocument.workspace == norm_workspace,
            WorkspaceDocument.deleted_at.is_(None),
        )
    ).scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return {
        "id": str(doc.id),
        "status": doc.status,
        "failure_code": doc.failure_code,
        "failure_message": doc.failure_message,
        "extraction_method": doc.extraction_method,
        "page_count": doc.page_count,
        "character_count": doc.character_count,
        "updated_at": doc.updated_at.isoformat(),
    }


@router.get("/documents/{workspace}/{document_id}/analysis", response_model=WorkspaceAnalysisResponse)
def get_latest_analysis(
    workspace: str,
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    norm_workspace = validate_workspace(workspace)
    # Check document ownership
    doc = db.execute(
        select(WorkspaceDocument).where(
            WorkspaceDocument.id == document_id,
            WorkspaceDocument.user_id == current_user.id,
            WorkspaceDocument.workspace == norm_workspace,
            WorkspaceDocument.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    analysis = (
        db.execute(
            select(WorkspaceAnalysis)
            .where(
                WorkspaceAnalysis.document_id == document_id,
                WorkspaceAnalysis.user_id == current_user.id,
            )
            .order_by(WorkspaceAnalysis.version.desc())
            .options(joinedload(WorkspaceAnalysis.findings))
        )
        .unique()
        .scalar_one_or_none()
    )
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found for this document")
    return analysis


@router.get("/documents/{workspace}/{document_id}/findings", response_model=list[WorkspaceFindingResponse])
def get_document_findings(
    workspace: str,
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    norm_workspace = validate_workspace(workspace)
    doc = db.execute(
        select(WorkspaceDocument).where(
            WorkspaceDocument.id == document_id,
            WorkspaceDocument.user_id == current_user.id,
            WorkspaceDocument.workspace == norm_workspace,
            WorkspaceDocument.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    findings = (
        db.execute(
            select(WorkspaceFinding)
            .where(
                WorkspaceFinding.document_id == document_id,
                WorkspaceFinding.user_id == current_user.id,
            )
            .order_by(WorkspaceFinding.created_at.asc())
        )
        .scalars()
        .all()
    )
    return findings


@router.patch("/documents/{workspace}/{document_id}/findings/{finding_id}", response_model=WorkspaceFindingResponse)
def update_finding(
    workspace: str,
    document_id: UUID,
    finding_id: UUID,
    payload: WorkspaceFindingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_workspace(workspace)
    finding = db.execute(
        select(WorkspaceFinding).where(
            WorkspaceFinding.id == finding_id,
            WorkspaceFinding.document_id == document_id,
            WorkspaceFinding.user_id == current_user.id,
        )
    ).scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    if payload.is_reviewed is not None:
        finding.is_reviewed = payload.is_reviewed
    if payload.review_status is not None:
        finding.review_status = payload.review_status
        if payload.review_status in ("reviewed", "dismissed"):
            finding.is_reviewed = True

    db.commit()
    db.refresh(finding)
    return finding


@router.post("/documents/{workspace}/{document_id}/retry", response_model=WorkspaceDocumentResponse)
async def retry_document_analysis(
    workspace: str,
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_workspace(workspace)
    doc = await workspace_orchestrator.process_document(db, document_id, current_user.id)
    return doc


@router.get("/documents/{workspace}/{document_id}/download")
def download_workspace_document(
    workspace: str,
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    norm_workspace = validate_workspace(workspace)
    doc = db.execute(
        select(WorkspaceDocument).where(
            WorkspaceDocument.id == document_id,
            WorkspaceDocument.user_id == current_user.id,
            WorkspaceDocument.workspace == norm_workspace,
            WorkspaceDocument.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    file_path = workspace_storage_service.get_file_path(doc.storage_key, current_user.id)
    return FileResponse(
        path=file_path,
        media_type=doc.mime_type,
        filename=doc.original_filename,
    )


@router.delete("/documents/{workspace}/{document_id}")
def delete_workspace_document(
    workspace: str,
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    norm_workspace = validate_workspace(workspace)
    doc = db.execute(
        select(WorkspaceDocument).where(
            WorkspaceDocument.id == document_id,
            WorkspaceDocument.user_id == current_user.id,
            WorkspaceDocument.workspace == norm_workspace,
            WorkspaceDocument.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    doc.deleted_at = datetime.now(timezone.utc)
    db.commit()
    workspace_storage_service.delete_file(doc.storage_key, current_user.id)
    return {"message": "Document deleted successfully"}


@router.post("/documents/{workspace}/compare")
def compare_workspace_documents(
    workspace: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    norm_workspace = validate_workspace(workspace)
    doc_a_str = payload.get("document_id_1")
    doc_b_str = payload.get("document_id_2")
    if not doc_a_str or not doc_b_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="document_id_1 and document_id_2 are required",
        )

    try:
        doc_a_id = UUID(str(doc_a_str))
        doc_b_id = UUID(str(doc_b_str))
        result = document_comparison_service.compare_documents(
            db, doc_a_id, doc_b_id, current_user.id, norm_workspace
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/workspaces/{workspace}/overview", response_model=WorkspaceOverviewResponse)
def get_workspace_overview(
    workspace: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    norm_workspace = validate_workspace(workspace)

    base_filter = [
        WorkspaceDocument.user_id == current_user.id,
        WorkspaceDocument.workspace == norm_workspace,
        WorkspaceDocument.deleted_at.is_(None),
    ]

    total = db.scalar(select(func.count(WorkspaceDocument.id)).where(*base_filter)) or 0
    completed = db.scalar(select(func.count(WorkspaceDocument.id)).where(*base_filter, WorkspaceDocument.status == "completed")) or 0
    failed = db.scalar(select(func.count(WorkspaceDocument.id)).where(*base_filter, WorkspaceDocument.status == "failed")) or 0
    pending = total - completed - failed

    # Subtypes breakdown
    subtypes_rows = db.execute(
        select(WorkspaceDocument.document_subtype, func.count(WorkspaceDocument.id))
        .where(*base_filter)
        .group_by(WorkspaceDocument.document_subtype)
    ).all()
    subtypes_breakdown = {row[0] or "other": row[1] for row in subtypes_rows}

    # Recent documents
    recent_docs = (
        db.execute(
            select(WorkspaceDocument)
            .where(*base_filter)
            .order_by(WorkspaceDocument.created_at.desc())
            .limit(5)
            .options(
                joinedload(WorkspaceDocument.analyses),
                joinedload(WorkspaceDocument.findings),
            )
        )
        .unique()
        .scalars()
        .all()
    )

    # Urgent findings
    urgent_findings = (
        db.execute(
            select(WorkspaceFinding)
            .where(
                WorkspaceFinding.user_id == current_user.id,
                WorkspaceFinding.workspace == norm_workspace,
                WorkspaceFinding.review_priority.in_(("high", "review")),
                WorkspaceFinding.is_reviewed.is_(False),
            )
            .order_by(WorkspaceFinding.created_at.desc())
            .limit(6)
        )
        .scalars()
        .all()
    )

    # Deadlines / action items
    deadlines = (
        db.execute(
            select(WorkspaceFinding)
            .where(
                WorkspaceFinding.user_id == current_user.id,
                WorkspaceFinding.workspace == norm_workspace,
                WorkspaceFinding.finding_type == "deadline",
                WorkspaceFinding.is_reviewed.is_(False),
            )
            .order_by(WorkspaceFinding.created_at.desc())
            .limit(6)
        )
        .scalars()
        .all()
    )

    return WorkspaceOverviewResponse(
        workspace=norm_workspace,
        total_documents=total,
        completed_documents=completed,
        failed_documents=failed,
        pending_documents=max(0, pending),
        subtypes_breakdown=subtypes_breakdown,
        recent_documents=recent_docs,
        urgent_findings=urgent_findings,
        deadlines=deadlines,
    )


@router.get("/workspaces/{workspace}/findings", response_model=list[WorkspaceFindingResponse])
def get_all_workspace_findings(
    workspace: str,
    priority: str | None = None,
    is_reviewed: bool | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    norm_workspace = validate_workspace(workspace)
    stmt = select(WorkspaceFinding).where(
        WorkspaceFinding.user_id == current_user.id,
        WorkspaceFinding.workspace == norm_workspace,
    )
    if priority and priority != "all":
        stmt = stmt.where(WorkspaceFinding.review_priority == priority.lower())
    if is_reviewed is not None:
        stmt = stmt.where(WorkspaceFinding.is_reviewed.is_(is_reviewed))

    stmt = stmt.order_by(WorkspaceFinding.created_at.desc()).limit(min(limit, 200))
    return db.execute(stmt).scalars().all()


@router.patch("/workspaces/{workspace}/findings/{finding_id}", response_model=WorkspaceFindingResponse)
def update_workspace_finding(
    workspace: str,
    finding_id: UUID,
    payload: WorkspaceFindingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    norm_workspace = validate_workspace(workspace)
    finding = db.execute(
        select(WorkspaceFinding).where(
            WorkspaceFinding.id == finding_id,
            WorkspaceFinding.workspace == norm_workspace,
            WorkspaceFinding.user_id == current_user.id,
        )
    ).scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    if payload.is_reviewed is not None:
        finding.is_reviewed = payload.is_reviewed
    if payload.review_status is not None:
        finding.review_status = payload.review_status
        if payload.review_status in ("reviewed", "dismissed"):
            finding.is_reviewed = True

    db.commit()
    db.refresh(finding)
    return finding

