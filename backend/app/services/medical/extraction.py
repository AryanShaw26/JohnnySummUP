import logging
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageOps

from app.core.config import get_settings

logger = logging.getLogger("johnnysummup.medical.extraction")

# Optional imports with safe fallbacks
try:
    import pymupdf as fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    try:
        import fitz
        HAS_PYMUPDF = True
    except ImportError:
        HAS_PYMUPDF = False

try:
    import pytesseract
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False

try:
    from pypdf import PdfReader
    from pypdf.errors import FileNotDecryptedError
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


@dataclass
class PageExtraction:
    page_number: int
    text: str
    method: str  # "pdf_text", "ocr", "empty"
    character_count: int
    is_blank: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    status: str  # "success", "partial", "no_readable_text", "corrupt", "encrypted", "ocr_unavailable", "failed"
    error_code: str | None = None
    error_message: str | None = None
    extraction_method: str = "pdf_text"  # "pdf_text", "ocr", "hybrid"
    full_text: str = ""
    pages: list[PageExtraction] = field(default_factory=list)
    page_count: int = 0
    ocr_page_count: int = 0
    total_characters: int = 0
    warnings: list[str] = field(default_factory=list)


class OCREngineAdapter:
    """
    Adapter for Optical Character Recognition using Tesseract OCR.
    Handles executable location resolution on Windows, Linux, and macOS.
    """

    def __init__(self):
        self._tesseract_available: bool | None = None
        self._resolved_cmd: str | None = None

    def resolve_tesseract_cmd(self) -> str | None:
        if self._resolved_cmd is not None:
            return self._resolved_cmd

        settings = get_settings()

        # 1. Configured explicitly in settings
        if settings.tesseract_cmd and Path(settings.tesseract_cmd).is_file():
            self._resolved_cmd = settings.tesseract_cmd
            if HAS_PYTESSERACT:
                pytesseract.pytesseract.tesseract_cmd = self._resolved_cmd
            return self._resolved_cmd

        # 2. In PATH
        path_cmd = shutil.which("tesseract")
        if path_cmd:
            self._resolved_cmd = path_cmd
            if HAS_PYTESSERACT:
                pytesseract.pytesseract.tesseract_cmd = self._resolved_cmd
            return self._resolved_cmd

        # 3. Standard Windows installation directories
        windows_candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for candidate in windows_candidates:
            if candidate and Path(candidate).is_file():
                self._resolved_cmd = candidate
                if HAS_PYTESSERACT:
                    pytesseract.pytesseract.tesseract_cmd = self._resolved_cmd
                return self._resolved_cmd

        return None

    def is_available(self) -> bool:
        if not HAS_PYTESSERACT:
            return False
        if self._tesseract_available is not None:
            return self._tesseract_available
        cmd = self.resolve_tesseract_cmd()
        self._tesseract_available = cmd is not None
        return self._tesseract_available

    def ocr_image(self, image: Image.Image) -> str:
        if not self.is_available():
            raise RuntimeError("Tesseract OCR is not configured or installed on this system.")

        # Non-destructive preprocessing
        processed = ImageOps.exif_transpose(image)
        if processed.mode not in ("L", "RGB"):
            processed = processed.convert("RGB")

        # Convert to grayscale
        gray = processed.convert("L")

        # Mild contrast enhancement (preserving decimal points and minus signs)
        try:
            enhancer = ImageEnhance.Contrast(gray)
            enhanced = enhancer.enhance(1.25)
        except Exception:
            enhanced = gray

        try:
            text = pytesseract.image_to_string(enhanced, lang="eng")
            return text or ""
        except Exception as exc:
            logger.warning("OCR processing error: %s", exc)
            return ""


ocr_engine = OCREngineAdapter()


class DocumentExtractionService:
    @staticmethod
    def _validate_page_text(text: str) -> tuple[bool, float, list[str]]:
        """
        Validates page text quality.
        Returns: (is_valid_content, printable_ratio, warnings)
        """
        warnings = []
        if not text or not text.strip():
            return False, 0.0, ["Page contains no text."]

        stripped = text.strip()
        printable_count = sum(1 for c in stripped if c.isprintable() or c in "\n\r\t")
        total_len = len(stripped)
        printable_ratio = printable_count / total_len if total_len > 0 else 0.0

        if printable_ratio < 0.70:
            warnings.append(f"Low printable character ratio ({printable_ratio:.2f}).")
            return False, printable_ratio, warnings

        # Check for genuine alphanumeric characters (at least one letter or digit)
        has_alphanumeric = bool(re.search(r"[a-zA-Z0-9]", stripped))
        if not has_alphanumeric:
            warnings.append("Page contains symbols but no recognizable alphanumeric content.")
            return False, printable_ratio, warnings

        return True, printable_ratio, warnings

    def extract_document(self, file_path: Path, mime_type: str) -> ExtractionResult:
        """
        Executes multi-tier document extraction:
        1. Searchable PDFs: extract embedded text page-by-page.
        2. Scanned/image-only PDFs: render pages to images and run OCR.
        3. Mixed PDFs: embedded parser on searchable pages, OCR on image pages.
        4. JPG/PNG images: run OCR directly with preprocessing.
        5. Quality validation with page-aware aggregation.
        """
        path = Path(file_path).resolve()
        if not path.is_file():
            return ExtractionResult(
                status="failed",
                error_code="CORRUPT_DOCUMENT",
                error_message="Document file not found on server storage.",
            )

        is_pdf = mime_type == "application/pdf" or path.suffix.lower() == ".pdf"
        is_image = (
            mime_type in ("image/jpeg", "image/png", "image/jpg")
            or path.suffix.lower() in (".jpg", ".jpeg", ".png")
        )

        if is_pdf:
            return self._extract_pdf(path)
        elif is_image:
            return self._extract_image(path)
        else:
            return ExtractionResult(
                status="failed",
                error_code="UNSUPPORTED_DOCUMENT",
                error_message=f"Unsupported document type or format '{path.suffix}'. Supported types are PDF, JPEG, and PNG.",
            )

    def _extract_pdf(self, file_path: Path) -> ExtractionResult:
        settings = get_settings()

        # Try opening with PyMuPDF first, falling back to pypdf
        if HAS_PYMUPDF:
            try:
                doc = fitz.open(str(file_path))
            except Exception as exc:
                exc_str = str(exc).lower()
                if "password" in exc_str or "encrypted" in exc_str:
                    return ExtractionResult(
                        status="encrypted",
                        error_code="ENCRYPTED_DOCUMENT",
                        error_message="Document is password-protected or encrypted.",
                    )
                logger.warning("PyMuPDF failed to open PDF: %s", exc)
                return ExtractionResult(
                    status="failed",
                    error_code="CORRUPT_DOCUMENT",
                    error_message="The PDF file is damaged, corrupted, or unsupported.",
                )

            if doc.is_encrypted:
                doc.close()
                return ExtractionResult(
                    status="encrypted",
                    error_code="ENCRYPTED_DOCUMENT",
                    error_message="Document is password-protected or encrypted.",
                )

            total_pages = min(len(doc), settings.ocr_max_pages)
            pages_result: list[PageExtraction] = []
            ocr_count = 0
            text_count = 0
            ocr_available = ocr_engine.is_available()

            try:
                for page_idx in range(total_pages):
                    page = doc[page_idx]
                    page_num = page_idx + 1

                    # 1. Attempt embedded text extraction
                    embedded_text = page.get_text("text") or ""
                    cleaned_text = embedded_text.strip()
                    is_valid_embedded, _, _ = self._validate_page_text(cleaned_text)

                    # Determine if embedded text is sufficient (has alphanumeric & not overly trivial)
                    # We accept even short genuine text (e.g. >= 20 chars with alphanumeric)
                    if is_valid_embedded and len(cleaned_text) >= 20:
                        pages_result.append(
                            PageExtraction(
                                page_number=page_num,
                                text=cleaned_text,
                                method="pdf_text",
                                character_count=len(cleaned_text),
                                is_blank=False,
                            )
                        )
                        text_count += 1
                        continue

                    # 2. Insufficient embedded text -> Attempt OCR fallback on this page
                    if ocr_available:
                        try:
                            pix = page.get_pixmap(dpi=settings.ocr_dpi)
                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            ocr_text = ocr_engine.ocr_image(img).strip()
                            is_valid_ocr, _, ocr_warns = self._validate_page_text(ocr_text)

                            if is_valid_ocr:
                                pages_result.append(
                                    PageExtraction(
                                        page_number=page_num,
                                        text=ocr_text,
                                        method="ocr",
                                        character_count=len(ocr_text),
                                        is_blank=False,
                                        warnings=ocr_warns,
                                    )
                                )
                                ocr_count += 1
                            elif is_valid_embedded:
                                # Fall back to embedded text if OCR was blank but embedded had short text
                                pages_result.append(
                                    PageExtraction(
                                        page_number=page_num,
                                        text=cleaned_text,
                                        method="pdf_text",
                                        character_count=len(cleaned_text),
                                        is_blank=False,
                                    )
                                )
                                text_count += 1
                            else:
                                pages_result.append(
                                    PageExtraction(
                                        page_number=page_num,
                                        text="",
                                        method="ocr",
                                        character_count=0,
                                        is_blank=True,
                                        warnings=["Page could not be read via OCR or embedded text."],
                                    )
                                )
                        except Exception as ocr_err:
                            logger.warning("Error during page %d OCR: %s", page_num, ocr_err)
                            pages_result.append(
                                PageExtraction(
                                    page_number=page_num,
                                    text=cleaned_text if is_valid_embedded else "",
                                    method="pdf_text" if is_valid_embedded else "ocr",
                                    character_count=len(cleaned_text) if is_valid_embedded else 0,
                                    is_blank=not is_valid_embedded,
                                    warnings=[f"OCR failed: {ocr_err}"],
                                )
                            )
                    else:
                        # OCR not available
                        if is_valid_embedded:
                            pages_result.append(
                                PageExtraction(
                                    page_number=page_num,
                                    text=cleaned_text,
                                    method="pdf_text",
                                    character_count=len(cleaned_text),
                                    is_blank=False,
                                )
                            )
                            text_count += 1
                        else:
                            pages_result.append(
                                PageExtraction(
                                    page_number=page_num,
                                    text="",
                                    method="empty",
                                    character_count=0,
                                    is_blank=True,
                                    warnings=["Scanned page could not be read because OCR engine is not configured."],
                                )
                            )
            finally:
                doc.close()

        elif HAS_PYPDF:
            # Fallback when PyMuPDF is not installed
            try:
                reader = PdfReader(str(file_path))
                if reader.is_encrypted:
                    return ExtractionResult(
                        status="encrypted",
                        error_code="ENCRYPTED_DOCUMENT",
                        error_message="Document is password-protected or encrypted.",
                    )
                total_pages = min(len(reader.pages), settings.ocr_max_pages)
                pages_result = []
                ocr_count = 0
                text_count = 0
                for idx, page in enumerate(reader.pages[:total_pages]):
                    clean_text = (page.extract_text() or "").strip()
                    is_valid, _, warns = self._validate_page_text(clean_text)
                    pages_result.append(
                        PageExtraction(
                            page_number=idx + 1,
                            text=clean_text if is_valid else "",
                            method="pdf_text",
                            character_count=len(clean_text) if is_valid else 0,
                            is_blank=not is_valid,
                            warnings=warns,
                        )
                    )
                    if is_valid:
                        text_count += 1
            except Exception as exc:
                exc_str = str(exc).lower()
                if "decrypt" in exc_str or "encrypt" in exc_str:
                    return ExtractionResult(
                        status="encrypted",
                        error_code="ENCRYPTED_DOCUMENT",
                        error_message="Document is password-protected or encrypted.",
                    )
                return ExtractionResult(
                    status="failed",
                    error_code="CORRUPT_DOCUMENT",
                    error_message="The PDF file could not be parsed.",
                )
        else:
            return ExtractionResult(
                status="failed",
                error_code="CORRUPT_DOCUMENT",
                error_message="No PDF extraction library available on backend.",
            )

        # Aggregate extraction result
        return self._assemble_result(pages_result, ocr_count, text_count)

    def _extract_image(self, file_path: Path) -> ExtractionResult:
        if not ocr_engine.is_available():
            return ExtractionResult(
                status="ocr_unavailable",
                error_code="OCR_NOT_CONFIGURED",
                error_message=(
                    "OCR engine is not installed or configured on the server. "
                    "Please upload a searchable PDF or configure Tesseract."
                ),
            )

        try:
            with Image.open(file_path) as img:
                ocr_text = ocr_engine.ocr_image(img).strip()
        except Exception as exc:
            logger.warning("Failed to open image for OCR: %s", exc)
            return ExtractionResult(
                status="failed",
                error_code="CORRUPT_DOCUMENT",
                error_message="The uploaded image file is corrupt or invalid.",
            )

        is_valid, _, warns = self._validate_page_text(ocr_text)
        page = PageExtraction(
            page_number=1,
            text=ocr_text if is_valid else "",
            method="ocr",
            character_count=len(ocr_text) if is_valid else 0,
            is_blank=not is_valid,
            warnings=warns,
        )

        return self._assemble_result([page], ocr_count=1 if is_valid else 0, text_count=0)

    def _assemble_result(
        self,
        pages: list[PageExtraction],
        ocr_count: int,
        text_count: int,
    ) -> ExtractionResult:
        valid_pages = [p for p in pages if not p.is_blank and p.text.strip()]
        total_chars = sum(len(p.text) for p in valid_pages)

        # Determine overall extraction method
        if ocr_count > 0 and text_count > 0:
            method = "hybrid"
        elif ocr_count > 0:
            method = "ocr"
        else:
            method = "pdf_text"

        if not valid_pages:
            # Check if failure was due to OCR being unconfigured on scanned document
            any_ocr_missing = any(
                "OCR engine is not configured" in w for p in pages for w in p.warnings
            )
            if any_ocr_missing:
                return ExtractionResult(
                    status="ocr_unavailable",
                    error_code="OCR_NOT_CONFIGURED",
                    error_message=(
                        "This document appears to be scanned or image-based, but OCR is not configured "
                        "on the server. Please upload a PDF with selectable text or install Tesseract OCR."
                    ),
                    extraction_method=method,
                    pages=pages,
                    page_count=len(pages),
                    ocr_page_count=ocr_count,
                    total_characters=0,
                )
            return ExtractionResult(
                status="no_readable_text",
                error_code="OCR_NO_TEXT",
                error_message=(
                    "We could not extract readable text from this document. "
                    "Please ensure the document contains clear, readable medical text."
                ),
                extraction_method=method,
                pages=pages,
                page_count=len(pages),
                ocr_page_count=ocr_count,
                total_characters=0,
            )

        # Build page-delimited structured text
        page_chunks = [f"=== PAGE {p.page_number} ===\n{p.text}" for p in valid_pages]
        full_text = "\n\n".join(page_chunks)

        status = "partial" if len(valid_pages) < len(pages) else "success"

        return ExtractionResult(
            status=status,
            extraction_method=method,
            full_text=full_text,
            pages=pages,
            page_count=len(pages),
            ocr_page_count=ocr_count,
            total_characters=total_chars,
        )

    # Legacy compatibility wrapper
    def extract_text(self, file_path: Path, mime_type: str) -> tuple[str, list[dict[str, Any]], int]:
        result = self.extract_document(file_path, mime_type)
        pages_data = [
            {"page": p.page_number, "text": p.text, "method": p.method}
            for p in result.pages
        ]
        return result.full_text, pages_data, result.page_count


extraction_service = DocumentExtractionService()
