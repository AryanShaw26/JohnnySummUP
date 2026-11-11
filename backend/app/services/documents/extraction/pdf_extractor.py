import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pymupdf  # PyMuPDF
from PIL import Image

from app.services.medical.extraction import OCREngine, MIN_SEARCHABLE_CHARS_PER_PAGE

logger = logging.getLogger("johnnysummup.extraction.pdf")


@dataclass
class PageData:
    page_number: int
    text: str
    method: str  # "pdf_text" | "ocr" | "none"
    character_count: int
    headings: list[str] = field(default_factory=list)


class PDFExtractor:
    MAX_PAGES_TO_PROCESS = 50

    @classmethod
    def extract(cls, file_path: Path) -> tuple[str, list[PageData], list[str], str | None, str | None]:
        """
        Extracts text from PDF page by page with OCR fallback for image pages.
        Returns: (full_text, pages, warnings, error_code, error_message)
        """
        try:
            doc = pymupdf.open(str(file_path))
        except Exception as exc:
            logger.error("pdf_open_error: %s", exc)
            return "", [], [], "CORRUPT_PDF", f"Failed to open PDF document: {exc}"

        if doc.is_encrypted:
            doc.close()
            return "", [], [], "ENCRYPTED_PDF", "This PDF is password-protected or encrypted."

        page_count = len(doc)
        if page_count == 0:
            doc.close()
            return "", [], [], "EMPTY_PDF", "The PDF contains no pages."

        pages: list[PageData] = []
        full_text_parts: list[str] = []
        warnings: list[str] = []

        total_pages = min(page_count, cls.MAX_PAGES_TO_PROCESS)
        if page_count > cls.MAX_PAGES_TO_PROCESS:
            warnings.append(
                f"Document exceeds maximum processed pages limit ({cls.MAX_PAGES_TO_PROCESS}). "
                f"Only the first {cls.MAX_PAGES_TO_PROCESS} of {page_count} pages were processed."
            )

        for page_idx in range(total_pages):
            page_num = page_idx + 1
            page = doc[page_idx]

            # 1. Try native text extraction
            text = page.get_text("text").strip()
            method = "pdf_text"

            # Extract headings if text blocks exist
            headings = []
            try:
                blocks = page.get_text("blocks")
                for b in blocks:
                    block_text = b[4].strip()
                    # Simple heuristic: short single line with bold or capital letters
                    if 3 < len(block_text) < 100 and "\n" not in block_text and (block_text.isupper() or block_text.istitle()):
                        headings.append(block_text)
            except Exception:
                pass

            # 2. If text is sparse or absent, attempt OCR if available
            if len(text) < MIN_SEARCHABLE_CHARS_PER_PAGE and OCREngine.is_available():
                try:
                    pix = page.get_pixmap(dpi=150)
                    mode = "RGBA" if pix.alpha else "RGB"
                    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
                    ocr_text, ok = OCREngine.run_ocr(img)
                    if ok and len(ocr_text.strip()) > len(text):
                        text = ocr_text.strip()
                        method = "ocr"
                except Exception as ocr_err:
                    logger.warning("ocr_page_fallback_failed page=%d error=%s", page_num, ocr_err)

            page_data = PageData(
                page_number=page_num,
                text=text,
                method=method if text else "none",
                character_count=len(text),
                headings=headings,
            )
            pages.append(page_data)

            if text:
                full_text_parts.append(f"--- Page {page_num} ---\n{text}")

        doc.close()
        full_text = "\n\n".join(full_text_parts)
        return full_text, pages, warnings, None, None
