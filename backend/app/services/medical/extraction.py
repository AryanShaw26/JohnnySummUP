import logging
import os
import re
import shutil
import string
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageOps

from app.core.config import get_settings

logger = logging.getLogger("johnnysummup.medical.extraction")

# Characters considered printable/usable in medical texts (letters, numbers, punctuation, whitespace)
PRINTABLE_SET = set(string.printable)
MIN_SEARCHABLE_CHARS_PER_PAGE = 40
MIN_PRINTABLE_RATIO = 0.75
MAX_PAGES_TO_PROCESS = 25
MAX_EXTRACTED_CHARACTERS = 50000


@dataclass
class PageExtraction:
    page_number: int
    text: str
    method: str  # "pdf_text" | "ocr" | "none"
    character_count: int
    status: str  # "success" | "empty" | "failed"
    warnings: list[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    status: str  # "success" | "partial" | "no_readable_text" | "unsupported" | "corrupt" | "encrypted" | "failed"
    extraction_method: str  # "pdf_text" | "ocr" | "hybrid" | "none"
    text: str
    pages: list[PageExtraction] = field(default_factory=list)
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


class OCREngine:
    """Manages OCR execution via Tesseract with automatic binary discovery and safe fallbacks."""

    _tesseract_resolved_path: str | None = None
    _tesseract_checked: bool = False

    @classmethod
    def get_tesseract_cmd(cls) -> str | None:
        if cls._tesseract_checked:
            return cls._tesseract_resolved_path

        settings = get_settings()
        # 1. Configured explicitly in settings
        if settings.tesseract_cmd and os.path.isfile(settings.tesseract_cmd):
            cls._tesseract_resolved_path = settings.tesseract_cmd
            cls._tesseract_checked = True
            return cls._tesseract_resolved_path

        # 2. On PATH
        path_binary = shutil.which("tesseract")
        if path_binary:
            cls._tesseract_resolved_path = path_binary
            cls._tesseract_checked = True
            return cls._tesseract_resolved_path

        # 3. Common Windows paths
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Tesseract-OCR\tesseract.exe"),
        ]
        for p in common_paths:
            if os.path.isfile(p):
                cls._tesseract_resolved_path = p
                cls._tesseract_checked = True
                return cls._tesseract_resolved_path

        cls._tesseract_resolved_path = None
        cls._tesseract_checked = True
        return None

    @classmethod
    def is_available(cls) -> bool:
        return cls.get_tesseract_cmd() is not None

    @classmethod
    def run_ocr(cls, pil_image: Image.Image) -> tuple[str, bool]:
        """
        Runs OCR on a PIL Image.
        Returns: (extracted_text, is_success)
        """
        tess_cmd = cls.get_tesseract_cmd()
        if not tess_cmd:
            logger.warning("tesseract_not_installed")
            return "", False

        try:
            import pytesseract

            pytesseract.pytesseract.tesseract_cmd = tess_cmd
            text = pytesseract.image_to_string(pil_image, lang="eng")
            return text or "", True
        except Exception as exc:
            logger.error("tesseract_execution_error: %s", exc)
            return "", False


class DocumentExtractionService:
    """Production extraction pipeline for PDFs, Scanned PDFs, and Images."""

    @staticmethod
    def preprocess_image(image: Image.Image) -> Image.Image:
        """
        Applies safe image enhancements for OCR without distorting decimal points or minus signs.
        """
        # 1. Correct EXIF orientation
        try:
            image = ImageOps.exif_transpose(image)
        except Exception:
            pass

        # 2. Convert to Grayscale
        gray = image.convert("L")

        # 3. Enhance contrast slightly to make faint text/decimal points clearer
        try:
            enhancer = ImageEnhance.Contrast(gray)
            enhanced = enhancer.enhance(1.5)
            return enhanced
        except Exception:
            return gray

    @staticmethod
    def clean_and_validate_text(raw_text: str) -> tuple[str, float, bool]:
        """
        Cleans text, preserves line breaks for tabular structures, and evaluates quality.
        Returns: (cleaned_text, printable_ratio, is_usable)
        """
        if not raw_text:
            return "", 0.0, False

        # Replace non-printable control characters except \n, \r, \t
        cleaned_chars = []
        for ch in raw_text:
            if ch in ('\n', '\r', '\t') or (ch.isprintable() and ord(ch) >= 32):
                cleaned_chars.append(ch)
            else:
                cleaned_chars.append(" ")
        cleaned = "".join(cleaned_chars)

        # Normalize multiple horizontal spaces but preserve line breaks
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip()

        if not cleaned:
            return "", 0.0, False

        # Calculate printable ratio
        printable_count = sum(1 for c in cleaned if c in PRINTABLE_SET)
        printable_ratio = printable_count / len(cleaned)

        # Check for excessive replacement glyphs
        replacement_count = cleaned.count("\ufffd")
        if replacement_count > 10 and (replacement_count / len(cleaned)) > 0.05:
            return cleaned, printable_ratio, False

        is_usable = (len(cleaned) >= MIN_SEARCHABLE_CHARS_PER_PAGE) and (printable_ratio >= MIN_PRINTABLE_RATIO)
        return cleaned, printable_ratio, is_usable

    @classmethod
    def extract_document(cls, file_path: Path, mime_type: str) -> ExtractionResult:
        """
        Extracts content from PDF or Image with per-page tracking and OCR fallback.
        """
        if not file_path.exists() or file_path.stat().st_size == 0:
            return ExtractionResult(
                status="corrupt",
                extraction_method="none",
                text="",
                error_code="EMPTY_OR_MISSING_FILE",
                error_message="The uploaded file is empty or missing from storage.",
            )

        ext = file_path.suffix.lower()
        is_pdf = mime_type == "application/pdf" or ext == ".pdf"
        is_image = mime_type in ["image/jpeg", "image/png", "image/jpg"] or ext in [".jpg", ".jpeg", ".png"]

        if is_pdf:
            return cls._extract_pdf(file_path)
        elif is_image:
            return cls._extract_image(file_path)
        else:
            return ExtractionResult(
                status="unsupported",
                extraction_method="none",
                text="",
                error_code="UNSUPPORTED_MIME_TYPE",
                error_message=f"Unsupported file format '{ext}'. Allowed formats: PDF, JPG, PNG.",
            )

    @classmethod
    def _extract_pdf(cls, file_path: Path) -> ExtractionResult:
        """Extracts text page-by-page from PDF, running OCR fallback on image-only/scanned pages."""
        try:
            doc = fitz.open(file_path)
        except Exception as exc:
            logger.warning("pdf_open_failed: %s", exc)
            return ExtractionResult(
                status="corrupt",
                extraction_method="none",
                text="",
                error_code="CORRUPT_PDF",
                error_message="We could not read this PDF document. The file may be corrupt.",
            )

        if doc.is_encrypted:
            doc.close()
            return ExtractionResult(
                status="encrypted",
                extraction_method="none",
                text="",
                error_code="ENCRYPTED_PDF",
                error_message="This PDF is password-protected or encrypted. Please upload an unprotected copy.",
            )

        page_count = len(doc)
        if page_count == 0:
            doc.close()
            return ExtractionResult(
                status="corrupt",
                extraction_method="none",
                text="",
                error_code="EMPTY_PDF",
                error_message="The PDF contains no pages.",
            )

        pages_extracted: list[PageExtraction] = []
        full_text_parts: list[str] = []
        methods_used: set[str] = set()
        warnings: list[str] = []

        total_pages_to_read = min(page_count, MAX_PAGES_TO_PROCESS)
        if page_count > MAX_PAGES_TO_PROCESS:
            warnings.append(
                f"Document exceeds maximum processed pages limit ({MAX_PAGES_TO_PROCESS}). "
                f"Only the first {MAX_PAGES_TO_PROCESS} of {page_count} pages were processed."
            )

        for page_idx in range(total_pages_to_read):
            page_num = page_idx + 1
            page = doc[page_idx]

            # 1. Attempt embedded text extraction first
            raw_page_text = page.get_text("text") or ""
            clean_text, ratio, is_usable = cls.clean_and_validate_text(raw_page_text)

            if is_usable:
                # Searchable text layer found and usable
                methods_used.add("pdf_text")
                pages_extracted.append(
                    PageExtraction(
                        page_number=page_num,
                        text=clean_text,
                        method="pdf_text",
                        character_count=len(clean_text),
                        status="success",
                    )
                )
                full_text_parts.append(f"--- Page {page_num} ---\n{clean_text}")
                continue

            # 2. Embedded text insufficient -> Scanned page detected. Run OCR fallback.
            logger.info("scanned_page_detected page=%d, attempting OCR fallback", page_num)
            page_pixmap = None
            try:
                # Render page at 150 DPI for fast and clear OCR
                page_pixmap = page.get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [page_pixmap.width, page_pixmap.height], page_pixmap.samples)
                processed_img = cls.preprocess_image(img)

                ocr_text, ocr_success = OCREngine.run_ocr(processed_img)
                clean_ocr_text, _, ocr_usable = cls.clean_and_validate_text(ocr_text)

                if ocr_success and clean_ocr_text:
                    methods_used.add("ocr")
                    pages_extracted.append(
                        PageExtraction(
                            page_number=page_num,
                            text=clean_ocr_text,
                            method="ocr",
                            character_count=len(clean_ocr_text),
                            status="success" if ocr_usable else "empty",
                        )
                    )
                    full_text_parts.append(f"--- Page {page_num} (OCR) ---\n{clean_ocr_text}")
                else:
                    if not OCREngine.is_available():
                        page_status = "failed"
                        page_warn = "OCR engine is not installed on this server."
                    else:
                        page_status = "empty"
                        page_warn = "No readable text could be recognized from scan."
                    warnings.append(f"Page {page_num}: {page_warn}")
                    pages_extracted.append(
                        PageExtraction(
                            page_number=page_num,
                            text=clean_text,  # keep whatever sparse embedded text existed
                            method="ocr_failed" if not OCREngine.is_available() else "ocr_empty",
                            character_count=len(clean_text),
                            status=page_status,
                            warnings=[page_warn],
                        )
                    )
                    if clean_text:
                        full_text_parts.append(f"--- Page {page_num} ---\n{clean_text}")
            except Exception as ocr_err:
                logger.error("page_render_or_ocr_failed page=%d error=%s", page_num, ocr_err)
                pages_extracted.append(
                    PageExtraction(
                        page_number=page_num,
                        text=clean_text,
                        method="none",
                        character_count=len(clean_text),
                        status="failed",
                        warnings=[f"OCR failed: {ocr_err}"],
                    )
                )
            finally:
                page_pixmap = None

        doc.close()

        full_text = "\n\n".join(full_text_parts)
        if len(full_text) > MAX_EXTRACTED_CHARACTERS:
            full_text = full_text[:MAX_EXTRACTED_CHARACTERS]
            warnings.append(f"Extracted content bounded to {MAX_EXTRACTED_CHARACTERS} characters.")

        total_chars = sum(p.character_count for p in pages_extracted)
        successful_pages = [p for p in pages_extracted if p.character_count > 0 and p.status == "success"]

        # Determine overall extraction method
        if "pdf_text" in methods_used and "ocr" in methods_used:
            overall_method = "hybrid"
        elif "ocr" in methods_used:
            overall_method = "ocr"
        elif "pdf_text" in methods_used:
            overall_method = "pdf_text"
        else:
            overall_method = "none"

        # Determine overall status
        if len(successful_pages) == total_pages_to_read and total_chars >= MIN_SEARCHABLE_CHARS_PER_PAGE:
            status = "success"
        elif len(successful_pages) > 0 and total_chars > 0:
            status = "partial"
        else:
            status = "no_readable_text"

        error_code = None
        error_message = None
        if status == "no_readable_text":
            if not OCREngine.is_available() and "pdf_text" not in methods_used:
                error_code = "OCR_DEPENDENCY_MISSING"
                error_message = (
                    "This document contains scanned images, but the OCR engine is not installed on this server. "
                    "Please upload a searchable PDF or contact support."
                )
            else:
                error_code = "extraction_empty"
                error_message = "No readable text was extracted. Try a clearer scan or another file."

        return ExtractionResult(
            status=status,
            extraction_method=overall_method,
            text=full_text,
            pages=pages_extracted,
            page_count=page_count,
            total_characters=total_chars,
            warnings=warnings,
            error_code=error_code,
            error_message=error_message,
        )

    @classmethod
    def _extract_image(cls, file_path: Path) -> ExtractionResult:
        """Extracts text directly from an image (JPG, PNG) using OCR."""
        try:
            with Image.open(file_path) as img:
                img.verify()
        except Exception as exc:
            logger.warning("image_verify_failed: %s", exc)
            return ExtractionResult(
                status="corrupt",
                extraction_method="ocr",
                text="",
                error_code="CORRUPT_IMAGE",
                error_message="We could not read this image file. The image may be corrupt or invalid.",
            )

        if not OCREngine.is_available():
            return ExtractionResult(
                status="failed",
                extraction_method="ocr",
                text="",
                page_count=1,
                error_code="OCR_DEPENDENCY_MISSING",
                error_message=(
                    "Image analysis requires OCR, which is not currently installed on this server. "
                    "Please upload a searchable PDF or contact support."
                ),
            )

        try:
            with Image.open(file_path) as raw_img:
                processed_img = cls.preprocess_image(raw_img)
                ocr_text, ocr_success = OCREngine.run_ocr(processed_img)

            clean_text, _, is_usable = cls.clean_and_validate_text(ocr_text)

            if ocr_success and clean_text:
                status = "success" if is_usable else "partial"
                page_item = PageExtraction(
                    page_number=1,
                    text=clean_text,
                    method="ocr",
                    character_count=len(clean_text),
                    status="success" if is_usable else "empty",
                )
                return ExtractionResult(
                    status=status,
                    extraction_method="ocr",
                    text=clean_text,
                    pages=[page_item],
                    page_count=1,
                    total_characters=len(clean_text),
                )
            else:
                page_item = PageExtraction(
                    page_number=1,
                    text="",
                    method="ocr",
                    character_count=0,
                    status="empty",
                    warnings=["No readable text extracted from image scan."],
                )
                return ExtractionResult(
                    status="no_readable_text",
                    extraction_method="ocr",
                    text="",
                    pages=[page_item],
                    page_count=1,
                    total_characters=0,
                    error_code="extraction_empty",
                    error_message="No readable text was extracted. Try a clearer scan or another file.",
                )
        except Exception as exc:
            logger.error("image_ocr_failed: %s", exc)
            return ExtractionResult(
                status="failed",
                extraction_method="ocr",
                text="",
                page_count=1,
                error_code="OCR_EXECUTION_FAILED",
                error_message=f"An error occurred during image OCR processing: {exc}",
            )

    @classmethod
    def extract_text(cls, file_path: Path, mime_type: str) -> tuple[str, list[dict], int]:
        """
        Backward-compatible method returning (full_text, pages_data, page_count).
        """
        result = cls.extract_document(file_path, mime_type)
        pages_data = [
            {
                "page": p.page_number,
                "text": p.text,
                "method": p.method,
                "character_count": p.character_count,
                "status": p.status,
            }
            for p in result.pages
        ]
        return result.text, pages_data, result.page_count


extraction_service = DocumentExtractionService()
