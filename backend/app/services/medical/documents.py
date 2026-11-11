import math
from datetime import date
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.medical_document import MedicalDocument
from app.services.medical.analysis import analysis_service
from app.services.medical.extraction import extraction_service
from app.services.medical.storage import storage_service


class MedicalDocumentService:
    @staticmethod
    async def create_document(
        db: Session,
        upload: UploadFile,
        document_type: str,
        user_id: UUID,
        report_date: date | None = None,
        provider: str | None = None,
    ) -> MedicalDocument:
        # Validate document_type
        allowed_types = {"prescription", "laboratory_report", "other"}
        if document_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document type '{document_type}'. Allowed: {', '.join(sorted(allowed_types))}",
            )

        stored_filename, storage_key, file_size, mime_type, ext = (
            await storage_service.save_upload(upload, user_id)
        )

        doc = MedicalDocument(
            user_id=user_id,
            original_filename=upload.filename or "uploaded_document",
            stored_filename=stored_filename,
            storage_key=storage_key,
            mime_type=mime_type,
            file_extension=ext,
            file_size_bytes=file_size,
            document_type=document_type,
            report_date=report_date,
            status="uploaded",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Extract text using structured extraction pipeline
        file_path = storage_service.get_file_path(storage_key, user_id)

        extraction_result = extraction_service.extract_document(file_path, mime_type)

        if extraction_result.status in ("corrupt", "encrypted", "unsupported") or not extraction_result.text.strip():
            doc.status = "failed"
            doc.failure_code = "extraction_failed" if extraction_result.error_code in ("EMPTY_PDF", None) else extraction_result.error_code
            doc.failure_message = "We could not extract readable text from this document."
            db.commit()
            db.refresh(doc)
            return doc

        image_data_url = (
            extraction_service.image_data_url(file_path, mime_type)
            if mime_type.startswith("image/")
            else None
        )

        # Trigger initial analysis
        try:
            await analysis_service.run_analysis(
                db=db,
                document_id=doc.id,
                user_id=user_id,
                extracted_text=extraction_result.text,
                document_type=document_type,
                image_data_url=image_data_url,
            )
        except Exception:
            # Document is still saved safely even if analysis fails
            pass

        db.refresh(doc)
        return doc

    @staticmethod
    def get_document(db: Session, document_id: UUID, user_id: UUID) -> MedicalDocument:
        doc = (
            db.execute(
                select(MedicalDocument)
                .where(
                    MedicalDocument.id == document_id,
                    MedicalDocument.user_id == user_id,
                    MedicalDocument.deleted_at.is_(None),
                )
                .options(
                    joinedload(MedicalDocument.analyses),
                    joinedload(MedicalDocument.findings),
                    joinedload(MedicalDocument.flags),
                    joinedload(MedicalDocument.measurements),
                )
            )
            .unique()
            .scalar_one_or_none()
        )
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medical document not found",
            )
        return doc

    @staticmethod
    def list_documents(
        db: Session,
        user_id: UUID,
        document_type: str | None = None,
        status_filter: str | None = None,
        search: str | None = None,
        sort: str = "newest",
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[MedicalDocument], int, int]:
        query = select(MedicalDocument).where(
            MedicalDocument.user_id == user_id,
            MedicalDocument.deleted_at.is_(None),
        )

        if document_type and document_type != "all":
            query = query.where(MedicalDocument.document_type == document_type)

        if status_filter and status_filter != "all":
            query = query.where(MedicalDocument.status == status_filter)

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(MedicalDocument.original_filename.ilike(term))

        total_stmt = select(func.count()).select_from(query.subquery())
        total = db.scalar(total_stmt) or 0

        # Sort order
        if sort == "oldest":
            query = query.order_by(MedicalDocument.created_at.asc())
        elif sort == "name_asc":
            query = query.order_by(MedicalDocument.original_filename.asc())
        elif sort == "name_desc":
            query = query.order_by(MedicalDocument.original_filename.desc())
        else:
            query = query.order_by(MedicalDocument.created_at.desc())

        # Pagination
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).options(joinedload(MedicalDocument.analyses))

        items = db.execute(query).unique().scalars().all()
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return list(items), total, total_pages

    @staticmethod
    def delete_document(db: Session, document_id: UUID, user_id: UUID) -> None:
        doc = db.get(MedicalDocument, document_id)
        if not doc or doc.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medical document not found",
            )

        storage_key = doc.storage_key
        # Delete dependent database rows cleanly via CASCADE in DB, or session delete
        db.delete(doc)
        db.commit()

        # Delete physical file
        storage_service.delete_file(storage_key, user_id)


document_service = MedicalDocumentService()
