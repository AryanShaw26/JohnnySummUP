import os
import secrets
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings


class StorageService:
    def __init__(self):
        self.settings = get_settings()
        self.base_dir = self.settings.medical_storage_path.resolve()
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

    async def save_upload(
        self, upload: UploadFile, user_id: UUID
    ) -> tuple[str, str, int, str, str]:
        """
        Validates and saves the uploaded file securely.
        Returns: (stored_filename, storage_key, file_size_bytes, mime_type, file_extension)
        """
        filename = upload.filename or "uploaded_document"
        ext = Path(filename).suffix.lower()
        if ext not in self.settings.medical_allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(self.settings.medical_allowed_extensions)}",
            )

        mime_type = upload.content_type or "application/octet-stream"
        if (
            mime_type not in self.settings.medical_allowed_mime_types
            and mime_type != "application/octet-stream"
        ):
            # Allow octet-stream only if extension is valid, else reject
            if ext not in [".pdf", ".jpg", ".jpeg", ".png"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid MIME type '{mime_type}' for document.",
                )

        # Normalize mime type if needed
        if mime_type == "application/octet-stream":
            if ext == ".pdf":
                mime_type = "application/pdf"
            elif ext in [".jpg", ".jpeg"]:
                mime_type = "image/jpeg"
            elif ext == ".png":
                mime_type = "image/png"

        # Read content and enforce size limits
        contents = await upload.read()
        file_size = len(contents)

        if file_size <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )

        if file_size > self.settings.medical_max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {self.settings.medical_max_upload_bytes // (1024 * 1024)} MB.",
            )

        # Validate magic numbers (PDF / JPEG / PNG)
        if ext == ".pdf" and not contents.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match PDF format.",
            )
        elif ext in [".jpg", ".jpeg"] and not (contents.startswith(b"\xff\xd8\xff")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match JPEG format.",
            )
        elif ext == ".png" and not (contents.startswith(b"\x89PNG\r\n\x1a\n")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match PNG format.",
            )

        random_prefix = secrets.token_hex(16)
        stored_filename = f"{random_prefix}{ext}"
        user_dir = self._get_user_dir(user_id)
        target_path = (user_dir / stored_filename).resolve()

        try:
            with open(target_path, "wb") as f:
                f.write(contents)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store document file.",
            ) from exc

        # Relative storage key for isolation
        storage_key = f"{user_id}/{stored_filename}"
        return stored_filename, storage_key, file_size, mime_type, ext

    def get_file_path(self, storage_key: str, user_id: UUID) -> Path:
        """
        Retrieves verified path to stored file, ensuring user ownership.
        """
        parts = storage_key.replace("\\", "/").split("/")
        if len(parts) != 2 or parts[0] != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to requested document file.",
            )
        stored_file = (self.base_dir / parts[0] / parts[1]).resolve()
        if not str(stored_file).startswith(str(self.base_dir)) or not stored_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found on server.",
            )
        return stored_file

    def delete_file(self, storage_key: str, user_id: UUID) -> bool:
        try:
            path = self.get_file_path(storage_key, user_id)
            if path.exists():
                os.remove(path)
                return True
        except Exception:
            pass
        return False


storage_service = StorageService()
