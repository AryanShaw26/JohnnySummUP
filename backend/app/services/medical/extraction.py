import base64
import logging
from pathlib import Path
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class DocumentExtractionService:
    @staticmethod
    def image_data_url(file_path: Path, mime_type: str) -> str:
        if mime_type not in {"image/jpeg", "image/png"}:
            raise ValueError(f"Unsupported image MIME type: {mime_type}")
        encoded_image = base64.b64encode(file_path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded_image}"

    @staticmethod
    def extract_text(file_path: Path, mime_type: str) -> tuple[str, list[dict], int]:
        """
        Extracts textual content and page metadata from supported documents.
        Returns: (full_text, pages_data, page_count)
        """
        full_text_parts = []
        pages_data = []
        page_count = 1

        if mime_type == "application/pdf" or file_path.suffix.lower() == ".pdf":
            try:
                reader = PdfReader(str(file_path))
                page_count = len(reader.pages)
                for idx, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    clean_text = page_text.strip()
                    pages_data.append({"page": idx + 1, "text": clean_text})
                    if clean_text:
                        full_text_parts.append(clean_text)
            except Exception as exc:
                logger.warning("PDF extraction encountered error: %s", exc)
                return "", [], 0
        else:
            # Images (JPG, PNG)
            pages_data.append({"page": 1, "text": ""})
            page_count = 1

        full_text = "\n\n".join(full_text_parts)
        return full_text, pages_data, page_count


extraction_service = DocumentExtractionService()
