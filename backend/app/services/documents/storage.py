import os
import secrets
import zipfile
from io import BytesIO
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings


class WorkspaceStorageService:
    def __init__(self):
        self.settings = get_settings()
        self.base_dir = self.settings.workspace_storage_path.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_user_dir(self, user_id: UUID) -> Path:
        user_dir = (self.base_dir / str(user_id)).resolve()
        # Security: verify path traversal cannot escape base_dir
        if not str(user_dir).startswith(str(self.base_dir)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid storage path",
            )
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def validate_file_bytes(self, contents: bytes, filename: str, content_type: str | None) -> tuple[str, str]:
        """
        Validates extension, MIME type, size, and file signature/magic bytes.
        Returns: (mime_type, file_extension)
        """
        ext = Path(filename).suffix.lower()
        if ext not in self.settings.workspace_allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(self.settings.workspace_allowed_extensions)}",
            )

        file_size = len(contents)
        if file_size <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )

        if file_size > self.settings.workspace_max_upload_bytes:
            max_mb = self.settings.workspace_max_upload_bytes // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {max_mb} MB.",
            )

        # Signature / magic bytes validation
        mime_type = content_type or "application/octet-stream"

        if ext == ".pdf":
            if not contents.startswith(b"%PDF-"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File content does not match PDF format.",
                )
            mime_type = "application/pdf"
        elif ext == ".docx":
            if not contents.startswith(b"PK\x03\x04"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File content does not match DOCX format.",
                )
            try:
                with zipfile.ZipFile(BytesIO(contents)) as zf:
                    namelist = zf.namelist()
                    if "word/document.xml" not in namelist and "[Content_Types].xml" not in namelist:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid DOCX archive structure.",
                        )
            except zipfile.BadZipFile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Corrupt DOCX archive.",
                )
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext in [".jpg", ".jpeg"]:
            if not contents.startswith(b"\xff\xd8\xff"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File content does not match JPEG format.",
                )
            mime_type = "image/jpeg"
        elif ext == ".png":
            if not contents.startswith(b"\x89PNG\r\n\x1a\n"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File content does not match PNG format.",
                )
            mime_type = "image/png"

        return mime_type, ext

    async def save_upload(
        self, upload: UploadFile, user_id: UUID
    ) -> tuple[str, str, int, str, str]:
        """
        Saves uploaded file securely under user's directory.
        Returns: (stored_filename, storage_key, file_size_bytes, mime_type, file_extension)
        """
        filename = upload.filename or "uploaded_document"
        contents = await upload.read()
        mime_type, ext = self.validate_file_bytes(contents, filename, upload.content_type)

        random_prefix = secrets.token_hex(16)
        stored_filename = f"{random_prefix}{ext}"
        user_dir = self._get_user_dir(user_id)
        target_path = (user_dir / stored_filename).resolve()

        if not str(target_path).startswith(str(user_dir)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid target path",
            )

        with open(target_path, "wb") as f:
            f.write(contents)

        storage_key = f"{user_id}/{stored_filename}"
        return stored_filename, storage_key, len(contents), mime_type, ext

    def get_file_path(self, storage_key: str, user_id: UUID) -> Path:
        """Resolves file path and verifies ownership."""
        parts = storage_key.split("/")
        if len(parts) != 2 or parts[0] != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to storage item",
            )

        path = (self.base_dir / parts[0] / parts[1]).resolve()
        if not str(path).startswith(str(self.base_dir)) or not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stored document file not found",
            )
        return path

    def delete_file(self, storage_key: str, user_id: UUID) -> None:
        """Deletes file safely if exists."""
        try:
            path = self.get_file_path(storage_key, user_id)
            if path.exists():
                path.unlink()
        except HTTPException:
            pass


workspace_storage_service = WorkspaceStorageService()
