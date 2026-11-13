import base64
import logging
from pathlib import Path

from PIL import Image

from app.services.documents.extraction.pdf_extractor import PageData
from app.services.medical.extraction import OCREngine, DocumentExtractionService

logger = logging.getLogger("johnnysummup.extraction.image")


class ImageExtractor:
    @classmethod
    def extract(cls, file_path: Path) -> tuple[str, list[PageData], list[str], str | None, str | None]:
        """
        Extracts content from JPEG/PNG via preprocessing and OCR.
        Returns: (full_text, pages, warnings, error_code, error_message)
        """
        try:
            with Image.open(file_path) as img:
                # Preprocess image safely
                processed = DocumentExtractionService.preprocess_image(img)
                if OCREngine.is_available():
                    ocr_text, ok = OCREngine.run_ocr(processed)
                    if ok and ocr_text.strip():
                        text = ocr_text.strip()
                        page = PageData(
                            page_number=1,
                            text=text,
                            method="ocr",
                            character_count=len(text),
                        )
                        return text, [page], [], None, None

                # If OCR is not installed or returned no text, return status indicating OCR unavailable or no text
                if not OCREngine.is_available():
                    return "", [], ["Tesseract OCR is not installed on the system."], "OCR_UNAVAILABLE", "Tesseract OCR engine is not installed on this server."

                return "", [], [], "OCR_NO_TEXT", "No readable text was detected in the uploaded image."

        except Exception as exc:
            logger.error("image_extraction_error: %s", exc)
            return "", [], [], "CORRUPT_IMAGE", f"Failed to process image file: {exc}"
