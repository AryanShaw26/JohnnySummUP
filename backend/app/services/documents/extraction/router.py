import logging
import string
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.services.documents.extraction.docx_extractor import DOCXExtractor
from app.services.documents.extraction.image_extractor import ImageExtractor
from app.services.documents.extraction.pdf_extractor import PageData, PDFExtractor

logger = logging.getLogger("johnnysummup.extraction.router")

PRINTABLE_SET = set(string.printable)
MIN_PRINTABLE_RATIO = 0.75
MIN_SEARCHABLE_CHARS = 20


@dataclass
class WorkspaceExtractionResult:
    status: str  # "success" | "partial" | "no_readable_text" | "unsupported" | "corrupt" | "encrypted" | "failed"
    extraction_method: str  # "pdf_text" | "docx_parser" | "ocr" | "hybrid" | "none"
    text: str
    pages: list[PageData] = field(default_factory=list)
    page_count: int = 0
    total_characters: int = 0
    warnings: list[str] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "extraction_method": self.extraction_method,
            "text": self.text,
            "pages": [asdict(p) for p in self.pages],
            "page_count": self.page_count,
            "total_characters": self.total_characters,
            "warnings": self.warnings,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


class ExtractionRouter:
    @classmethod
    def validate_quality(cls, raw_text: str) -> tuple[float, bool]:
        """Evaluates printable characters ratio and determines if text is usable."""
        if not raw_text:
            return 0.0, False
        cleaned = raw_text.strip()
        if len(cleaned) < MIN_SEARCHABLE_CHARS:
            return 0.0, False

        printable_count = sum(1 for c in cleaned if c in PRINTABLE_SET)
        ratio = printable_count / len(cleaned)
        is_usable = ratio >= MIN_PRINTABLE_RATIO
        return ratio, is_usable

    @classmethod
    def extract_document(cls, file_path: Path, mime_type: str) -> WorkspaceExtractionResult:
        """Dispatches to the appropriate format extractor and evaluates quality."""
        if not file_path.exists() or file_path.stat().st_size == 0:
            return WorkspaceExtractionResult(
                status="corrupt",
                extraction_method="none",
                text="",
                error_code="EMPTY_OR_MISSING_FILE",
                error_message="The uploaded file is empty or missing from storage.",
            )

        ext = file_path.suffix.lower()
        is_pdf = mime_type == "application/pdf" or ext == ".pdf"
        is_docx = (
            mime_type in (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword",
            )
            or ext in (".docx", ".doc")
        )
        is_image = (
            mime_type in ("image/jpeg", "image/png", "image/jpg")
            or ext in (".jpg", ".jpeg", ".png")
        )

        if is_pdf:
            full_text, pages, warnings, err_code, err_msg = PDFExtractor.extract(file_path)
            method = "pdf_text"
        elif is_docx:
            full_text, pages, warnings, err_code, err_msg = DOCXExtractor.extract(file_path)
            method = "docx_parser"
        elif is_image:
            full_text, pages, warnings, err_code, err_msg = ImageExtractor.extract(file_path)
            method = "ocr"
        else:
            return WorkspaceExtractionResult(
                status="unsupported",
                extraction_method="none",
                text="",
                error_code="UNSUPPORTED_FORMAT",
                error_message=f"Unsupported format '{ext}'. Allowed: PDF, DOCX, JPG, PNG.",
            )

        if err_code:
            return WorkspaceExtractionResult(
                status="failed" if err_code in ("EMPTY_PDF", "EMPTY_DOCX", "OCR_NO_TEXT") else "corrupt",
                extraction_method="none",
                text="",
                warnings=warnings,
                error_code=err_code,
                error_message=err_msg or "Extraction failed.",
            )

        if not full_text.strip():
            return WorkspaceExtractionResult(
                status="no_readable_text",
                extraction_method="none",
                text="",
                page_count=len(pages),
                total_characters=0,
                warnings=warnings,
                error_code="NO_READABLE_TEXT",
                error_message="We could not extract readable text from this document.",
            )

        ratio, usable = cls.validate_quality(full_text)
        if not usable:
            warnings.append(f"Low extraction text quality (printable ratio: {ratio:.2f})")

        return WorkspaceExtractionResult(
            status="success",
            extraction_method=method,
            text=full_text,
            pages=pages,
            page_count=len(pages),
            total_characters=len(full_text),
            warnings=warnings,
        )


extraction_router = ExtractionRouter()
