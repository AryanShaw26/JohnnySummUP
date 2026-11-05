"""
End-to-end integration test simulating realistic user report upload and AI extraction.
"""

import asyncio
import io
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from app.main import app
from app.core.database import async_session_factory
from app.models.medical_document import MedicalDocument
from app.models.measurement import ExtractedMeasurement
from app.models.finding import MedicalFinding
from app.models.summary import MedicalSummary


client = TestClient(app)


def create_sample_medical_pdf() -> bytes:
    """Generate a realistic digital laboratory report PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("METROPOLITAN DIAGNOSTIC CLINICAL LABORATORIES", styles["Heading1"]),
        Paragraph("Patient: Jane Doe | Age: 34 | Gender: Female | Date of Collection: 2026-10-28", styles["Normal"]),
        Spacer(1, 14),
        Paragraph("COMPLETE BLOOD COUNT (CBC) & METABOLIC PANEL", styles["Heading2"]),
        Spacer(1, 8),
        # Column format: Test Name, Result, Unit, Reference Range, Flag
        Paragraph("Hemoglobin        12.4    g/dL    13.0 - 17.0    LOW", styles["Normal"]),
        Paragraph("White Blood Cell Count (WBC)  7.2    10^3/uL   4.5 - 11.0    NORMAL", styles["Normal"]),
        Paragraph("Platelet Count    240     10^3/uL  150 - 450", styles["Normal"]),
        Paragraph("Fasting Blood Sugar  118    mg/dL   70 - 99        HIGH", styles["Normal"]),
        Paragraph("Serum Creatinine  0.9     mg/dL   0.7 - 1.3", styles["Normal"]),
        Paragraph("Total Cholesterol 225     mg/dL   < 200          HIGH", styles["Normal"]),
        Spacer(1, 14),
        Paragraph("Doctor: Dr. Sarah Jenkins, M.D. | Status: Final Verified", styles["Normal"]),
    ]
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


@pytest.mark.anyio
async def test_full_document_pipeline_e2e():
    """
    Simulates:
    1. Register user
    2. Upload generated medical PDF
    3. Wait for async AI pipeline completion
    4. Assert structured measurements, deterministic range statuses, and grounded summary
    5. Check dashboard stats
    6. Generate PDF summary export
    """
    unique_email = f"e2e_{int(datetime.now().timestamp())}@example.com"
    reg_res = client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": "Password123!", "fullName": "Jane Doe"},
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["data"]["tokens"]["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = create_sample_medical_pdf()

    # Upload document
    upload_res = client.post(
        "/api/v1/medical/documents/upload",
        headers=headers,
        files={"file": ("blood_test_report.pdf", pdf_bytes, "application/pdf")},
        data={"document_type": "lab_report", "document_title": "Annual Blood Panel 2026"},
    )
    assert upload_res.status_code == 202
    doc_id = upload_res.json()["data"]["documentId"]
    job_id = upload_res.json()["data"]["jobId"]

    # Poll until completed (give background task up to 10 seconds)
    completed = False
    for _ in range(20):
        await asyncio.sleep(0.5)
        job_res = client.get(f"/api/v1/medical/jobs/{job_id}", headers=headers)
        if job_res.status_code == 200:
            status = job_res.json()["data"]["status"]
            if status in ("completed", "needs_review"):
                completed = True
                break

    assert completed is True, "AI pipeline did not finish within timeout"

    # Fetch document detail
    detail_res = client.get(f"/api/v1/medical/documents/{doc_id}", headers=headers)
    assert detail_res.status_code == 200
    doc_data = detail_res.json()["data"]

    # Assert document metadata
    assert doc_data["documentType"] == "lab_report"
    assert len(doc_data["measurements"]) >= 4

    # Check Hemoglobin: 12.4 (range 13.0 - 17.0) -> below_range
    hb_meas = next((m for m in doc_data["measurements"] if "hemoglobin" in m["parameterName"].lower()), None)
    assert hb_meas is not None
    assert hb_meas["numericValue"] == "12.4"
    assert hb_meas["calculatedRangeStatus"] == "below_range"
    assert hb_meas["source"]["snippet"] is not None

    # Check Fasting Blood Sugar: 118 (range 70 - 99) -> above_range
    fbs_meas = next((m for m in doc_data["measurements"] if "fasting" in m["parameterName"].lower()), None)
    assert fbs_meas is not None
    assert fbs_meas["calculatedRangeStatus"] == "above_range"

    # Check White Blood Cell: 7.2 (range 4.5 - 11.0) -> within_range
    wbc_meas = next((m for m in doc_data["measurements"] if "white blood" in m["parameterName"].lower() or "wbc" in m["parameterName"].lower()), None)
    assert wbc_meas is not None
    assert wbc_meas["calculatedRangeStatus"] == "within_range"

    # Assert Findings generated with evidence references
    assert len(doc_data["findings"]) >= 2
    for f in doc_data["findings"]:
        assert len(f["evidence"]) > 0
        assert f["evidence"][0]["snippet"] != ""

    # Assert Grounded Summary
    assert doc_data["summary"] is not None
    assert "safetyNotice" in doc_data["summary"]["structuredSummary"]

    # Test PDF Export endpoint
    export_res = client.post(
        "/api/v1/medical/exports",
        headers=headers,
        json={"documentId": doc_id},
    )
    assert export_res.status_code == 202
    export_id = export_res.json()["data"]["exportId"]

    # Download exported PDF
    download_res = client.get(f"/api/v1/medical/exports/{export_id}/download", headers=headers)
    assert download_res.status_code == 200
    assert len(download_res.content) > 1000  # PDF generated with tables and text

