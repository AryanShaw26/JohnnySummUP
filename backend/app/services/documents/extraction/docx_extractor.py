import logging
from pathlib import Path
from typing import Any

from app.services.documents.extraction.pdf_extractor import PageData

logger = logging.getLogger("johnnysummup.extraction.docx")


class DOCXExtractor:
    @classmethod
    def extract(cls, file_path: Path) -> tuple[str, list[PageData], list[str], str | None, str | None]:
        """
        Extracts structured content from a DOCX file: headings, paragraphs, lists, and tables.
        Returns: (full_text, pages, warnings, error_code, error_message)
        """
        try:
            import docx
        except ImportError:
            return "", [], [], "PARSER_UNAVAILABLE", "python-docx is not installed."

        try:
            doc = docx.Document(str(file_path))
        except Exception as exc:
            logger.error("docx_open_error: %s", exc)
            return "", [], [], "CORRUPT_DOCX", f"Failed to open DOCX file: {exc}"

        lines: list[str] = []
        headings: list[str] = []

        # Process document elements in sequence
        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            style_name = p.style.name.lower() if p.style and p.style.name else ""
            if "heading" in style_name:
                headings.append(text)
                lines.append(f"\n## {text}\n")
            elif "list" in style_name or p.text.startswith("•") or p.text.startswith("-"):
                lines.append(f"- {text}")
            else:
                lines.append(text)

        # Process tables
        for table in doc.tables:
            table_lines: list[str] = []
            for row in table.rows:
                cells = [c.text.strip().replace("\n", " ") for c in row.cells]
                # Filter duplicate consecutive cells resulting from merges
                cleaned_cells = []
                for cell in cells:
                    if not cleaned_cells or cell != cleaned_cells[-1]:
                        cleaned_cells.append(cell)
                if any(cleaned_cells):
                    table_lines.append(" | ".join(cleaned_cells))

            if table_lines:
                lines.append("\n[Table]")
                lines.extend(table_lines)
                lines.append("[End Table]\n")

        full_text = "\n\n".join(lines).strip()
        if not full_text:
            return "", [], [], "EMPTY_DOCX", "The DOCX file contains no readable text."

        # Approximate pages for DOCX (roughly 500 words or 3000 chars per page)
        chars_per_page = 3000
        page_chunks = [full_text[i:i + chars_per_page] for i in range(0, len(full_text), chars_per_page)] or [full_text]
        pages = [
            PageData(
                page_number=idx + 1,
                text=chunk,
                method="docx_parser",
                character_count=len(chunk),
                headings=headings if idx == 0 else [],
            )
            for idx, chunk in enumerate(page_chunks)
        ]

        return full_text, pages, [], None, None
