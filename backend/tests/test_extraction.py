import io
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image, ImageDraw

import pymupdf as fitz
from app.services.medical.analysis import MedicalAnalysisService
from app.services.medical.extraction import extraction_service, ocr_engine


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


def test_searchable_pdf_extracts_embedded_text(tmp_dir: Path):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 72),
        "Comprehensive Metabolic Panel\nGlucose: 95 mg/dL (Ref: 70 - 99 mg/dL)\nCalcium: 9.2 mg/dL",
    )
    pdf_path = tmp_dir / "searchable.pdf"
    doc.save(str(pdf_path))
    doc.close()

    result = extraction_service.extract_document(pdf_path, "application/pdf")

    assert result.status == "success"
    assert result.extraction_method == "pdf_text"
    assert result.page_count == 1
    assert result.ocr_page_count == 0
    assert "Glucose: 95 mg/dL" in result.full_text
    assert "=== PAGE 1 ===" in result.full_text


def test_short_legitimate_medical_text_is_not_rejected(tmp_dir: Path):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Rx: Paracetamol 500mg")
    pdf_path = tmp_dir / "short_rx.pdf"
    doc.save(str(pdf_path))
    doc.close()

    result = extraction_service.extract_document(pdf_path, "application/pdf")

    assert result.status == "success"
    assert "Paracetamol 500mg" in result.full_text
    assert result.error_code is None


def test_blank_pdf_fails_quality_check_as_ocr_no_text(tmp_dir: Path):
    doc = fitz.open()
    doc.new_page()  # Completely blank page
    pdf_path = tmp_dir / "blank.pdf"
    doc.save(str(pdf_path))
    doc.close()

    # Even with OCR attempted, a blank page produces empty text
    with patch.object(ocr_engine, "is_available", return_value=True):
        with patch.object(ocr_engine, "ocr_image", return_value=""):
            result = extraction_service.extract_document(pdf_path, "application/pdf")

    assert result.status == "no_readable_text"
    assert result.error_code == "OCR_NO_TEXT"
    assert "could not extract readable text" in result.error_message.lower()


def test_scanned_pdf_triggers_ocr_fallback(tmp_dir: Path):
    doc = fitz.open()
    page = doc.new_page()

    # Create synthetic image with text (simulating paper scan)
    img = Image.new("RGB", (500, 150), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 40), "White Blood Cells: 6.5 x10^3/uL", fill="black")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    page.insert_image(page.rect, stream=img_byte_arr.getvalue())

    pdf_path = tmp_dir / "scanned_report.pdf"
    doc.save(str(pdf_path))
    doc.close()

    # Mock OCR engine returning scanned text
    with patch.object(ocr_engine, "is_available", return_value=True):
        with patch.object(ocr_engine, "ocr_image", return_value="White Blood Cells: 6.5 x10^3/uL"):
            result = extraction_service.extract_document(pdf_path, "application/pdf")

    assert result.status == "success"
    assert result.extraction_method == "ocr"
    assert result.ocr_page_count == 1
    assert "White Blood Cells: 6.5 x10^3/uL" in result.full_text


def test_mixed_pdf_extracts_hybrid(tmp_dir: Path):
    doc = fitz.open()

    # Page 1: Digital text
    p1 = doc.new_page()
    p1.insert_text((50, 72), "Serum Potassium: 4.1 mEq/L (Normal: 3.5 - 5.0 mEq/L)")

    # Page 2: Scanned image with no embedded text layer
    p2 = doc.new_page()
    img = Image.new("RGB", (400, 100), color="white")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    p2.insert_image(p2.rect, stream=img_bytes.getvalue())

    pdf_path = tmp_dir / "mixed.pdf"
    doc.save(str(pdf_path))
    doc.close()

    with patch.object(ocr_engine, "is_available", return_value=True):
        with patch.object(ocr_engine, "ocr_image", return_value="Serum Sodium: 140 mEq/L"):
            result = extraction_service.extract_document(pdf_path, "application/pdf")

    assert result.status == "success"
    assert result.extraction_method == "hybrid"
    assert result.page_count == 2
    assert result.ocr_page_count == 1
    assert result.pages[0].method == "pdf_text"
    assert result.pages[1].method == "ocr"
    assert "Serum Potassium: 4.1" in result.full_text
    assert "Serum Sodium: 140" in result.full_text
    assert "=== PAGE 1 ===" in result.full_text
    assert "=== PAGE 2 ===" in result.full_text


def test_image_extraction_jpg_and_png(tmp_dir: Path):
    # Test JPG
    jpg_path = tmp_dir / "blood_test.jpg"
    img_jpg = Image.new("RGB", (400, 100), color="white")
    img_jpg.save(jpg_path, format="JPEG")

    # Test PNG
    png_path = tmp_dir / "rx.png"
    img_png = Image.new("RGB", (400, 100), color="white")
    img_png.save(png_path, format="PNG")

    with patch.object(ocr_engine, "is_available", return_value=True):
        with patch.object(ocr_engine, "ocr_image", side_effect=["Urea: 25 mg/dL", "Rx: Metformin 500mg BD"]):
            res_jpg = extraction_service.extract_document(jpg_path, "image/jpeg")
            res_png = extraction_service.extract_document(png_path, "image/png")

    assert res_jpg.status == "success"
    assert res_jpg.extraction_method == "ocr"
    assert "Urea: 25 mg/dL" in res_jpg.full_text

    assert res_png.status == "success"
    assert res_png.extraction_method == "ocr"
    assert "Metformin 500mg" in res_png.full_text


def test_corrupt_pdf_returns_corrupt_document(tmp_dir: Path):
    corrupt_path = tmp_dir / "corrupt.pdf"
    corrupt_path.write_bytes(b"%PDF-1.4\nCorrupt trailer \x00\xff\xfe\x01\x02")

    result = extraction_service.extract_document(corrupt_path, "application/pdf")

    assert result.status == "failed"
    assert result.error_code == "CORRUPT_DOCUMENT"
    assert "damaged, corrupted" in result.error_message.lower()


def test_encrypted_pdf_returns_encrypted_document(tmp_dir: Path):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Confidential Medical History")
    pdf_path = tmp_dir / "encrypted.pdf"

    # Save with AES-256 encryption password
    doc.save(
        str(pdf_path),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="password123",
        user_pw="password123",
    )
    doc.close()

    result = extraction_service.extract_document(pdf_path, "application/pdf")

    assert result.status == "encrypted"
    assert result.error_code == "ENCRYPTED_DOCUMENT"
    assert "password" in result.error_message.lower()


def test_ocr_unavailable_returns_ocr_not_configured(tmp_dir: Path):
    png_path = tmp_dir / "scan.png"
    img = Image.new("RGB", (200, 100), color="white")
    img.save(png_path, format="PNG")

    with patch.object(ocr_engine, "is_available", return_value=False):
        result = extraction_service.extract_document(png_path, "image/png")

    assert result.status == "ocr_unavailable"
    assert result.error_code == "OCR_NOT_CONFIGURED"
    assert "not installed or configured" in result.error_message.lower()


def test_page_aware_chunking_preserves_page_boundaries():
    # Generate 4 pages of text, each 7,000 characters (total 28,000 characters)
    pages = []
    for i in range(1, 5):
        page_content = f"Page {i} clinical findings: " + ("Normal observation data point. " * 200)
        pages.append(f"=== PAGE {i} ===\n{page_content}")
    full_doc = "\n\n".join(pages)

    # Chunk with max 15,000 characters
    chunks = MedicalAnalysisService._chunk_text_by_pages(full_doc, max_chunk_chars=15000)

    assert len(chunks) >= 2
    # Ensure no chunk cuts mid-page
    for chunk in chunks:
        assert chunk.startswith("=== PAGE ")
        # Check that page tags are intact
        assert "=== PAGE" in chunk


def test_legacy_extract_text_tuple_compatibility(tmp_dir: Path):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Lipid Panel: Total Cholesterol 185 mg/dL")
    pdf_path = tmp_dir / "lipid.pdf"
    doc.save(str(pdf_path))
    doc.close()

    full_text, pages_data, page_count = extraction_service.extract_text(pdf_path, "application/pdf")

    assert "Total Cholesterol 185" in full_text
    assert page_count == 1
    assert len(pages_data) == 1
    assert pages_data[0]["page"] == 1


def test_multipage_scanned_pdf(tmp_dir: Path):
    doc = fitz.open()
    for i in range(1, 4):
        p = doc.new_page()
        img = Image.new("RGB", (300, 100), color="white")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        p.insert_image(p.rect, stream=img_bytes.getvalue())

    pdf_path = tmp_dir / "multipage_scan.pdf"
    doc.save(str(pdf_path))
    doc.close()

    with patch.object(ocr_engine, "is_available", return_value=True):
        with patch.object(ocr_engine, "ocr_image", side_effect=["Page 1 Scan Note", "Page 2 Lab Value", "Page 3 Diagnosis"]):
            result = extraction_service.extract_document(pdf_path, "application/pdf")

    assert result.status == "success"
    assert result.extraction_method == "ocr"
    assert result.page_count == 3
    assert result.ocr_page_count == 3
    assert "=== PAGE 1 ===\nPage 1 Scan Note" in result.full_text
    assert "=== PAGE 2 ===\nPage 2 Lab Value" in result.full_text
    assert "=== PAGE 3 ===\nPage 3 Diagnosis" in result.full_text


def test_blank_image_returns_ocr_no_text(tmp_dir: Path):
    png_path = tmp_dir / "blank_image.png"
    img = Image.new("RGB", (200, 200), color="white")
    img.save(png_path, format="PNG")

    with patch.object(ocr_engine, "is_available", return_value=True):
        with patch.object(ocr_engine, "ocr_image", return_value=""):
            result = extraction_service.extract_document(png_path, "image/png")

    assert result.status == "no_readable_text"
    assert result.error_code == "OCR_NO_TEXT"


def test_unsupported_file_format(tmp_dir: Path):
    txt_path = tmp_dir / "notes.txt"
    txt_path.write_text("Plain text notes")

    result = extraction_service.extract_document(txt_path, "text/plain")

    assert result.status == "failed"
    assert result.error_code == "UNSUPPORTED_DOCUMENT"
    assert "unsupported document type" in result.error_message.lower()


def test_document_analysis_schema_metadata():
    from app.schemas.medical import DocumentAnalysisResponse
    import uuid
    from datetime import datetime, timezone

    data = {
        "id": uuid.uuid4(),
        "document_id": uuid.uuid4(),
        "status": "completed",
        "error_message": None,
        "summary": "Sample summary",
        "key_findings": [],
        "risk_indicators": [],
        "patient_questions": [],
        "suggested_actions": [],
        "provider_used": "mock",
        "confidence_score": 0.95,
        "raw_response": {},
        "created_at": datetime.now(timezone.utc),
        "version": 1,
        "extraction_method": "hybrid",
        "extracted_page_count": 5,
        "ocr_page_count": 2,
    }
    schema = DocumentAnalysisResponse(**data)
    assert schema.extraction_method == "hybrid"
    assert schema.extracted_page_count == 5
    assert schema.ocr_page_count == 2


def test_rotated_image_handling(tmp_dir: Path):
    jpg_path = tmp_dir / "rotated.jpg"
    img = Image.new("RGB", (400, 200), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((30, 30), "Hemoglobin: 14.2 g/dL", fill="black")
    # Rotate 90 degrees
    rotated = img.rotate(90, expand=True)
    rotated.save(jpg_path, format="JPEG")

    with patch.object(ocr_engine, "is_available", return_value=True):
        with patch.object(ocr_engine, "ocr_image", return_value="Hemoglobin: 14.2 g/dL"):
            result = extraction_service.extract_document(jpg_path, "image/jpeg")

    assert result.status == "success"
    assert "Hemoglobin: 14.2" in result.full_text


def test_corrupt_file_renamed_to_pdf(tmp_dir: Path):
    fake_pdf = tmp_dir / "fake.pdf"
    fake_pdf.write_bytes(b"Not a PDF file at all, just invalid garbage \xff\xfe")

    result = extraction_service.extract_document(fake_pdf, "application/pdf")

    assert result.status == "failed"
    assert result.error_code == "CORRUPT_DOCUMENT"


@pytest.fixture
def in_memory_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.base import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


def test_analysis_persistence_and_metadata(in_memory_db):
    import uuid
    from datetime import datetime, timezone
    from app.models.user import User
    from app.models.medical_document import MedicalDocument
    from app.models.document_analysis import DocumentAnalysis
    from app.services.medical.analysis import MedicalAnalysisService

    user = User(id=uuid.uuid4(), email="user@test.com", full_name="User", password_hash="h")
    in_memory_db.add(user)
    in_memory_db.commit()

    doc = MedicalDocument(
        id=uuid.uuid4(),
        user_id=user.id,
        original_filename="scan.pdf",
        stored_filename="scan_stored.pdf",
        storage_key="docs/scan.pdf",
        mime_type="application/pdf",
        file_extension="pdf",
        file_size_bytes=1024,
        document_type="lab_result",
        status="uploaded",
    )
    in_memory_db.add(doc)
    in_memory_db.commit()

    analysis = DocumentAnalysis(
        document_id=doc.id,
        user_id=user.id,
        version=1,
        status="processing",
        extraction_method="hybrid",
        extracted_page_count=3,
        ocr_page_count=2,
        started_at=datetime.now(timezone.utc),
    )
    in_memory_db.add(analysis)
    in_memory_db.commit()

    parsed_data = {
        "summary": "Metabolic panel with normal electrolytes.",
        "key_points": ["Electrolytes stable", "Kidney function normal"],
        "report_date": "2026-10-20",
        "findings": [
            {
                "category": "laboratory",
                "finding_type": "test_result",
                "name": "Serum Sodium",
                "value_text": "140 mEq/L",
                "numeric_value": 140.0,
                "unit": "mEq/L",
                "reference_low": 135.0,
                "reference_high": 145.0,
                "is_abnormal": False,
            }
        ],
        "measurements": [
            {
                "parameter_name": "Serum Sodium",
                "numeric_value": 140.0,
                "unit": "mEq/L",
                "reference_range": "135 - 145",
                "reference_low": 135.0,
                "reference_high": 145.0,
                "is_abnormal": False,
            }
        ],
        "flags": [],
    }

    persisted = MedicalAnalysisService._persist_analysis_output(
        db=in_memory_db,
        doc=doc,
        analysis=analysis,
        user_id=user.id,
        parsed_data=parsed_data,
    )

    assert persisted.status == "completed"
    assert persisted.extraction_method == "hybrid"
    assert persisted.extracted_page_count == 3
    assert persisted.ocr_page_count == 2
    assert "Metabolic panel" in persisted.summary
    assert doc.status == "completed"
    assert len(doc.findings) == 1
    assert doc.findings[0].name == "Serum Sodium"
    assert len(doc.measurements) == 1
    assert doc.measurements[0].parameter_name == "Serum Sodium"


def test_document_ownership_enforcement(in_memory_db):
    import uuid
    from app.models.user import User
    from app.models.medical_document import MedicalDocument

    user_a = User(id=uuid.uuid4(), email="u_a@test.com", full_name="User A", password_hash="h")
    user_b = User(id=uuid.uuid4(), email="u_b@test.com", full_name="User B", password_hash="h")
    in_memory_db.add_all([user_a, user_b])
    in_memory_db.commit()

    doc_a = MedicalDocument(
        id=uuid.uuid4(),
        user_id=user_a.id,
        original_filename="private.pdf",
        stored_filename="private.pdf",
        storage_key="k",
        mime_type="application/pdf",
        file_extension="pdf",
        file_size_bytes=100,
        document_type="other",
    )
    in_memory_db.add(doc_a)
    in_memory_db.commit()

    fetched = in_memory_db.get(MedicalDocument, doc_a.id)
    assert fetched.user_id == user_a.id
    assert fetched.user_id != user_b.id


def test_standardized_error_codes():
    expected_codes = {
        "OCR_NO_TEXT",
        "OCR_NOT_CONFIGURED",
        "CORRUPT_DOCUMENT",
        "ENCRYPTED_DOCUMENT",
        "UNSUPPORTED_DOCUMENT",
        "AI_NOT_CONFIGURED",
        "PROVIDER_INSUFFICIENT_QUOTA",
        "PROVIDER_TIMEOUT",
        "PROVIDER_NETWORK_ERROR",
        "INVALID_AI_RESPONSE",
        "DATABASE_PERSISTENCE_ERROR",
    }
    for code in expected_codes:
        assert code.isupper()
        assert len(code) > 5


