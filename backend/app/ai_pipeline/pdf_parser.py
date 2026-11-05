"""
PDF text extraction engine using pypdf.
Extracts page-indexed text blocks, detects digital text quality,
and segments content for evidence linking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import pypdf

logger = logging.getLogger(__name__)


@dataclass
class TextBlock:
    text: str
    page_number: int
    confidence: float = 0.98
    block_type: str = "text"


@dataclass
class PageData:
    page_number: int
    text: str
    blocks: List[TextBlock] = field(default_factory=list)


@dataclass
class ExtractedDocumentText:
    pages: List[PageData]
    total_page_count: int
    is_digital_text_sufficient: bool
    full_text: str


def extract_text_from_pdf(file_path: str | Path) -> ExtractedDocumentText:
    """
    Extract embedded text from a PDF file page by page.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    pages_data: List[PageData] = []
    total_characters = 0

    try:
        reader = pypdf.PdfReader(str(path))
        num_pages = len(reader.pages)

        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            extracted = page.extract_text() or ""
            total_characters += len(extracted.strip())

            blocks: List[TextBlock] = []
            for line in extracted.split("\n"):
                line_str = line.strip()
                if line_str:
                    blocks.append(TextBlock(
                        text=line_str,
                        page_number=page_num,
                        confidence=0.98,
                        block_type="line",
                    ))

            pages_data.append(PageData(
                page_number=page_num,
                text=extracted,
                blocks=blocks,
            ))

        full_text = "\n\n".join(f"--- Page {p.page_number} ---\n{p.text}" for p in pages_data)
        avg_chars_per_page = (total_characters / num_pages) if num_pages > 0 else 0
        is_sufficient = avg_chars_per_page > 40 and total_characters > 80

        return ExtractedDocumentText(
            pages=pages_data,
            total_page_count=num_pages,
            is_digital_text_sufficient=is_sufficient,
            full_text=full_text,
        )
    except Exception as exc:
        logger.warning(f"pypdf extraction error for {file_path}: {exc}")
        return ExtractedDocumentText(
            pages=[],
            total_page_count=0,
            is_digital_text_sufficient=False,
            full_text="",
        )

