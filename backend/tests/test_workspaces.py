import io
import json
import os
import shutil
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.database import get_db, get_engine, get_session_factory
from app.main import app
from app.models.base import Base
from app.models.user import User
from app.models.workspace_document import (
    WorkspaceAnalysis,
    WorkspaceDocument,
    WorkspaceFinding,
)
from app.services.ai.gemini_service import GeminiServiceError, gemini_workspace_service

db_url = os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")
if "sqlite" in db_url:
    test_engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    test_engine = create_engine(db_url, pool_pre_ping=True)
TestSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    Base.metadata.create_all(test_engine)

    def override_get_db():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    with TestSession() as session:
        session.execute(delete(WorkspaceFinding))
        session.execute(delete(WorkspaceAnalysis))
        session.execute(delete(WorkspaceDocument))
        session.execute(delete(User))
        session.commit()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    storage_dir = get_settings().workspace_storage_path
    if storage_dir.exists():
        shutil.rmtree(storage_dir, ignore_errors=True)


def register_user(client: TestClient, email: str = "test@example.com") -> dict[str, Any]:
    resp = client.post(
        "/api/auth/register",
        json={"full_name": "Test User", "email": email, "password": "password123"},
    )
    assert resp.status_code == 201
    return resp.json()


def make_test_pdf(text: str = "This is a valid test document with sufficient text content.") -> bytes:
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def make_test_docx(paragraphs: list[str]) -> bytes:
    import docx
    doc = docx.Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def make_test_image(format: str = "PNG") -> bytes:
    from PIL import Image
    img = Image.new("RGB", (120, 80), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


# ==============================================================================
# 1. AUTHENTICATION & ACCESS CONTROL TESTS
# ==============================================================================

def test_workspace_routes_unauthenticated_returns_401(client: TestClient) -> None:
    for ws in ["legal", "finance", "insurance", "education", "employment-government"]:
        assert client.get(f"/api/documents/{ws}").status_code == 401
        assert client.get(f"/api/workspaces/{ws}/overview").status_code == 401


def test_invalid_workspace_returns_400(client: TestClient) -> None:
    register_user(client)
    res = client.get("/api/documents/invalid_workspace")
    assert res.status_code == 400


# ==============================================================================
# 2. LEGAL WORKSPACE TESTS
# ==============================================================================

def test_legal_upload_analysis_and_findings(client: TestClient) -> None:
    register_user(client)

    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_resp = client.post(
        "/api/documents/legal",
        data={"document_subtype": "nda", "label": "Mutual NDA Agreement"},
        files={"file": ("mutual_nda.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    assert doc_data["workspace"] == "legal"
    assert doc_data["document_subtype"] == "nda"
    doc_id = doc_data["id"]

    # Verify list
    list_resp = client.get("/api/documents/legal")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1

    # Verify overview
    overview_resp = client.get("/api/workspaces/legal/overview")
    assert overview_resp.status_code == 200
    assert overview_resp.json()["total_documents"] == 1


# ==============================================================================
# 3. FINANCE WORKSPACE TESTS
# ==============================================================================

def test_finance_upload_and_status(client: TestClient) -> None:
    register_user(client)

    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_resp = client.post(
        "/api/documents/finance",
        data={"document_subtype": "bank_statement"},
        files={"file": ("statement_nov_2026.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # Check status endpoint
    status_resp = client.get(f"/api/documents/finance/{doc_id}/status")
    assert status_resp.status_code == 200
    assert "status" in status_resp.json()


# ==============================================================================
# 4. INSURANCE WORKSPACE TESTS
# ==============================================================================

def test_insurance_upload_and_findings(client: TestClient) -> None:
    register_user(client)

    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_resp = client.post(
        "/api/documents/insurance",
        data={"document_subtype": "policy_document"},
        files={"file": ("health_policy.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    findings_resp = client.get(f"/api/documents/insurance/{doc_id}/findings")
    assert findings_resp.status_code == 200
    assert isinstance(findings_resp.json(), list)


# ==============================================================================
# 5. EDUCATION WORKSPACE TESTS
# ==============================================================================

def test_education_upload_and_overview(client: TestClient) -> None:
    register_user(client)

    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_resp = client.post(
        "/api/documents/education",
        data={"document_subtype": "transcript"},
        files={"file": ("fall_2026_transcript.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    assert upload_resp.json()["workspace"] == "education"

    overview_resp = client.get("/api/workspaces/education/overview")
    assert overview_resp.status_code == 200
    assert overview_resp.json()["total_documents"] == 1


# ==============================================================================
# 6. EMPLOYMENT & GOVERNMENT WORKSPACE TESTS
# ==============================================================================

def test_employment_government_slug_formats(client: TestClient) -> None:
    register_user(client)

    # Test kebab-case route
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    resp_kebab = client.post(
        "/api/documents/employment-government",
        data={"document_subtype": "offer_letter"},
        files={"file": ("offer.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp_kebab.status_code == 201
    assert resp_kebab.json()["workspace"] == "employment_government"

    # Test snake_case route
    resp_snake = client.get("/api/documents/employment_government")
    assert resp_snake.status_code == 200
    assert resp_snake.json()["total"] == 1


# ==============================================================================
# 7. CROSS-USER ISOLATION TESTS
# ==============================================================================

def test_cross_user_isolation(client: TestClient) -> None:
    # User 1 registers and uploads
    register_user(client, "user1@example.com")
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    up1 = client.post(
        "/api/documents/legal",
        data={"document_subtype": "contract"},
        files={"file": ("private_contract.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert up1.status_code == 201
    doc1_id = up1.json()["id"]

    # User 2 registers
    client.post("/api/auth/logout")
    register_user(client, "user2@example.com")

    # User 2 cannot list User 1's documents
    list2 = client.get("/api/documents/legal").json()
    assert list2["total"] == 0

    # User 2 cannot read User 1's document
    assert client.get(f"/api/documents/legal/{doc1_id}").status_code == 404

    # User 2 cannot download User 1's file
    assert client.get(f"/api/documents/legal/{doc1_id}/download").status_code == 404

    # User 2 cannot delete User 1's document
    assert client.delete(f"/api/documents/legal/{doc1_id}").status_code == 404


# ==============================================================================
# 8. MOCKED GEMINI ANALYSIS & EVIDENCE PRESERVATION
# ==============================================================================

@pytest.mark.anyio
async def test_legal_gemini_analysis_with_mock_and_evidence(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    register_user(client)

    mock_legal_output = {
        "provider": "gemini",
        "model_name": "gemini-2.5-flash",
        "summary": "Standard Mutual Non-Disclosure Agreement between Acme Inc and Beta Corp.",
        "key_points": ["2-year confidentiality duration", "California governing law"],
        "structured_data": {
            "overview": "Standard Mutual Non-Disclosure Agreement between Acme Inc and Beta Corp.",
            "document_type": "nda",
            "parties": [{"name": "Acme Inc", "role": "Disclosing Party"}, {"name": "Beta Corp", "role": "Receiving Party"}],
            "dates": {"effective_date": "2026-11-01"},
            "governing_law": "State of California",
            "jurisdiction": "San Francisco Courts",
            "unusual_clauses": [
                {
                    "title": "Indefinite Trade Secret Protection",
                    "explanation": "Trade secrets protected indefinitely beyond standard 2-year term.",
                    "why_it_matters": "Requires permanent retention protocol.",
                    "review_priority": "review",
                    "source_page": 2,
                    "source_excerpt": "Trade secrets shall remain confidential in perpetuity.",
                }
            ],
            "deadlines_checklist": [
                {
                    "action": "Return or destroy materials",
                    "deadline": "30 days post-termination",
                    "party": "Beta Corp",
                    "source_page": 3,
                }
            ],
            "findings": [],
            "disclaimer": "This is document information, not legal advice.",
        },
        "findings": [
            {
                "finding_type": "unusual_clause",
                "title": "Indefinite Trade Secret Protection",
                "explanation": "Trade secrets protected indefinitely beyond standard 2-year term.",
                "why_it_matters": "Requires permanent retention protocol.",
                "review_priority": "review",
                "source_page": 2,
                "source_excerpt": "Trade secrets shall remain confidential in perpetuity.",
            },
            {
                "finding_type": "deadline",
                "title": "Deadline: Return or destroy materials",
                "explanation": "Due within 30 days post-termination for Beta Corp",
                "why_it_matters": "Compliance requirement.",
                "review_priority": "review",
                "source_page": 3,
            }
        ],
    }

    async def mock_analyze(*args, **kwargs):
        return mock_legal_output

    monkeypatch.setattr(gemini_workspace_service, "analyze_workspace_document", mock_analyze)

    pdf_bytes = make_test_pdf("Mutual Non-Disclosure Agreement between Acme and Beta with confidential terms.")
    upload = client.post(
        "/api/documents/legal",
        data={"document_subtype": "nda"},
        files={"file": ("nda_contract.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    # Reopen saved analysis
    analysis_resp = client.get(f"/api/documents/legal/{doc_id}/analysis")
    assert analysis_resp.status_code == 200
    analysis_data = analysis_resp.json()
    assert analysis_data["summary"] == "Standard Mutual Non-Disclosure Agreement between Acme Inc and Beta Corp."
    assert analysis_data["provider"] == "gemini"

    # Verify source-linked findings
    findings_resp = client.get(f"/api/documents/legal/{doc_id}/findings")
    assert findings_resp.status_code == 200
    findings = findings_resp.json()
    assert len(findings) == 2

    trade_secret_finding = next(f for f in findings if "Trade Secret" in f["title"])
    assert trade_secret_finding["source_page"] == 2
    assert "in perpetuity" in trade_secret_finding["source_excerpt"]
    finding_id = trade_secret_finding["id"]

    # Mark finding as reviewed
    patch_resp = client.patch(
        f"/api/documents/legal/{doc_id}/findings/{finding_id}",
        json={"review_status": "reviewed"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_reviewed"] is True
    assert patch_resp.json()["review_status"] == "reviewed"


# ==============================================================================
# 9. COMPARISON ENDPOINT TESTS
# ==============================================================================

def test_document_comparison(client: TestClient) -> None:
    register_user(client)

    pdf_bytes_1 = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    up1 = client.post(
        "/api/documents/legal",
        data={"document_subtype": "contract"},
        files={"file": ("v1.pdf", io.BytesIO(pdf_bytes_1), "application/pdf")},
    ).json()

    pdf_bytes_2 = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    up2 = client.post(
        "/api/documents/legal",
        data={"document_subtype": "contract"},
        files={"file": ("v2.pdf", io.BytesIO(pdf_bytes_2), "application/pdf")},
    ).json()

    comp_resp = client.post(
        "/api/documents/legal/compare",
        json={"document_id_1": up1["id"], "document_id_2": up2["id"]},
    )
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert "summary_comparison" in comp_data
    assert comp_data["document_a"]["id"] == up1["id"]
    assert comp_data["document_b"]["id"] == up2["id"]


# ==============================================================================
# 10. ERROR HANDLING AND RESILIENCE TESTS
# ==============================================================================

def test_unsupported_format_rejected(client: TestClient) -> None:
    register_user(client)
    res = client.post(
        "/api/documents/legal",
        files={"file": ("script.exe", io.BytesIO(b"MZ12345"), "application/x-msdownload")},
    )
    assert res.status_code == 400
    assert "unsupported file format" in res.json()["detail"].lower()


@pytest.mark.anyio
async def test_gemini_quota_error_handled_gracefully(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    register_user(client)

    async def mock_quota_fail(*args, **kwargs):
        raise GeminiServiceError(
            "quota_exceeded",
            "Gemini quota is exhausted for this project/model. Check project billing."
        )

    monkeypatch.setattr(gemini_workspace_service, "analyze_workspace_document", mock_quota_fail)

    pdf_bytes = make_test_pdf("Contract terms and conditions for testing quota failure handling.")
    upload = client.post(
        "/api/documents/legal",
        files={"file": ("contract.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    detail = client.get(f"/api/documents/legal/{doc_id}").json()
    assert detail["status"] == "failed"
    assert detail["failure_code"] == "quota_exceeded"
    assert "quota is exhausted" in detail["failure_message"].lower()


# ==============================================================================
# 11. WORKSPACE-WIDE FINDINGS ENDPOINTS
# ==============================================================================

@pytest.mark.anyio
async def test_workspace_findings_list_and_update(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    register_user(client)

    async def mock_analyze(*args, **kwargs):
        return {
            "summary": "Legal agreement analysis with findings",
            "key_points": ["Point A"],
            "structured_data": {"governing_law": "California"},
            "findings": [
                {
                    "finding_type": "discrepancy",
                    "title": "Strict non-compete clause",
                    "explanation": "Clause restricts worldwide employment for 5 years.",
                    "why_it_matters": "Likely unenforceable under California law.",
                    "review_priority": "high",
                    "source_page": 1,
                    "source_section": "Section 9",
                    "source_excerpt": "Employee shall not compete anywhere in the world for 5 years.",
                }
            ],
            "confidence_score": 0.95,
        }

    monkeypatch.setattr(gemini_workspace_service, "analyze_workspace_document", mock_analyze)

    pdf_bytes = make_test_pdf("Sample employment contract clause 9 non-compete worldwide.")
    up = client.post(
        "/api/documents/legal",
        files={"file": ("contract.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert up.status_code == 201
    doc_id = up.json()["id"]

    # 1. Fetch all findings in the workspace
    findings_resp = client.get("/api/workspaces/legal/findings")
    assert findings_resp.status_code == 200
    findings = findings_resp.json()
    assert len(findings) == 1
    finding_id = findings[0]["id"]
    assert findings[0]["review_priority"] == "high"
    assert findings[0]["is_reviewed"] is False

    # 2. Update finding review status via workspace endpoint
    patch_resp = client.patch(
        f"/api/workspaces/legal/findings/{finding_id}",
        json={"is_reviewed": True, "review_status": "reviewed"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_reviewed"] is True
    assert patch_resp.json()["review_status"] == "reviewed"

    # 3. Filter by is_reviewed=false should now return 0
    unreviewed = client.get("/api/workspaces/legal/findings?is_reviewed=false").json()
    assert len(unreviewed) == 0

    # 4. Filter by is_reviewed=true should return 1
    reviewed = client.get("/api/workspaces/legal/findings?is_reviewed=true").json()
    assert len(reviewed) == 1


# ==============================================================================
# 12. CLASSIFICATION OVERRIDE TEST
# ==============================================================================

def test_update_workspace_document_classification_override(client: TestClient) -> None:
    register_user(client)

    pdf_bytes = make_test_pdf("Agreement between Alpha and Beta regarding commercial licensing.")
    upload = client.post(
        "/api/documents/legal",
        data={"document_subtype": "agreement", "label": "Initial Agreement Label"},
        files={"file": ("licensing.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]
    assert upload.json()["document_subtype"] == "agreement"

    # User corrects classification to "nda" and updates label
    patch_resp = client.patch(
        f"/api/documents/legal/{doc_id}",
        json={"document_subtype": "nda", "label": "Updated Mutual NDA"},
    )
    assert patch_resp.status_code == 200
    updated_doc = patch_resp.json()
    assert updated_doc["document_subtype"] == "nda"
    assert updated_doc["label"] == "Updated Mutual NDA"

    # Re-fetch document to verify persistence
    get_resp = client.get(f"/api/documents/legal/{doc_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["document_subtype"] == "nda"
    assert get_resp.json()["label"] == "Updated Mutual NDA"


# ==============================================================================
# 13. FINANCE WORKSPACE EXTENSIVE TESTS
# ==============================================================================

@pytest.mark.anyio
async def test_finance_gemini_analysis_with_transactions_and_anomalies(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    register_user(client)

    mock_finance_output = {
        "provider": "gemini",
        "model_name": "gemini-2.5-flash",
        "summary": "Bank statement for November 2026 showing opening balance $5,000.00 and closing balance $4,250.00.",
        "key_points": ["Opening balance: $5,000.00", "Closing balance: $4,250.00", "Total debits: $750.00"],
        "structured_data": {
            "overview": "Bank statement for checking account ending in 4321.",
            "document_type": "bank_statement",
            "issuer_name": "First National Bank",
            "masked_account_number": "**** 4321",
            "account_type": "Checking",
            "statement_period_start": "2026-11-01",
            "statement_period_end": "2026-11-30",
            "currency": "USD",
            "opening_balance": 5000.00,
            "closing_balance": 4250.00,
            "total_debits": 750.00,
            "total_credits": 0.00,
            "total_fees": 35.00,
            "transactions": [
                {
                    "date": "2026-11-05",
                    "description": "Office Supplies Inc",
                    "amount": 250.00,
                    "transaction_type": "debit",
                    "balance_after": 4750.00,
                    "currency": "USD",
                    "source_page": 1,
                },
                {
                    "date": "2026-11-10",
                    "description": "Wire Transfer Fee",
                    "amount": 35.00,
                    "transaction_type": "fee",
                    "balance_after": 4715.00,
                    "currency": "USD",
                    "source_page": 1,
                },
                {
                    "date": "2026-11-15",
                    "description": "SaaS Subscription",
                    "amount": 465.00,
                    "transaction_type": "debit",
                    "balance_after": 4250.00,
                    "currency": "USD",
                    "source_page": 1,
                },
            ],
            "candidate_anomalies": [
                {
                    "title": "Wire Transfer Fee",
                    "explanation": "International wire fee of $35.00 charged on November 10.",
                    "flag_type": "unusual_fee",
                    "review_priority": "review",
                    "amount": 35.00,
                    "source_page": 1,
                    "source_excerpt": "11/10 WIRE TRANSFER FEE $35.00",
                }
            ],
            "disclaimer": "This summary is for informational purposes only.",
        },
        "findings": [
            {
                "finding_type": "unusual_fee",
                "title": "Unusual Fee: Wire Transfer",
                "explanation": "Fee of $35.00 charged on November 10.",
                "why_it_matters": "Verify if wire service was authorized.",
                "review_priority": "review",
                "source_page": 1,
                "source_excerpt": "11/10 WIRE TRANSFER FEE $35.00",
            }
        ],
    }

    async def mock_analyze(*args, **kwargs):
        return mock_finance_output

    monkeypatch.setattr(gemini_workspace_service, "analyze_workspace_document", mock_analyze)

    pdf_bytes = make_test_pdf("First National Bank Statement. Checking ending 4321. Nov 2026.")
    upload = client.post(
        "/api/documents/finance",
        data={"document_subtype": "bank_statement"},
        files={"file": ("statement.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    # Verify analysis
    analysis_resp = client.get(f"/api/documents/finance/{doc_id}/analysis")
    assert analysis_resp.status_code == 200
    data = analysis_resp.json()
    assert data["structured_data"]["opening_balance"] == 5000.00
    assert data["structured_data"]["closing_balance"] == 4250.00
    assert data["structured_data"]["currency"] == "USD"
    assert len(data["structured_data"]["transactions"]) == 3

    # Verify findings
    findings = client.get(f"/api/documents/finance/{doc_id}/findings").json()
    assert len(findings) == 1
    assert "Wire Transfer" in findings[0]["title"]
    assert findings[0]["source_page"] == 1


# ==============================================================================
# 14. INSURANCE WORKSPACE EXTENSIVE TESTS
# ==============================================================================

@pytest.mark.anyio
async def test_insurance_gemini_analysis_with_exclusions_and_limits(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    register_user(client)

    mock_insurance_output = {
        "provider": "gemini",
        "model_name": "gemini-2.5-flash",
        "summary": "Health insurance policy schedule for Policy POL-****-8899 with $500,000 maximum sum insured.",
        "key_points": ["Sum insured: $500,000", "Deductible: $1,000", "24-month pre-existing condition waiting period"],
        "structured_data": {
            "overview": "Comprehensive Health Plan covering inpatient and outpatient medical expenses.",
            "document_type": "policy_document",
            "insurer_name": "Global Shield Health",
            "policyholder_name": "Jane Doe",
            "masked_policy_number": "POL-****-8899",
            "sum_insured": "$500,000",
            "deductibles_and_copay": "$1,000 annual deductible, 10% copay thereafter",
            "coverages": [
                {"name": "Hospital Inpatient", "limit": "$500,000", "source_page": 2},
                {"name": "Emergency Outpatient", "limit": "$10,000", "source_page": 3},
            ],
            "exclusions": [
                {
                    "title": "Cosmetic Surgery Exclusion",
                    "explanation": "Elective cosmetic and aesthetic treatments are excluded from coverage.",
                    "source_page": 4,
                    "source_excerpt": "Section 8.1: Treatments for aesthetic purposes are not payable.",
                }
            ],
            "waiting_periods": [
                {
                    "condition_or_treatment": "Pre-existing conditions",
                    "period": "24 months",
                    "source_page": 5,
                    "source_excerpt": "Pre-existing medical conditions require a 24-month continuous coverage waiting period.",
                }
            ],
            "claim_instructions": [
                {
                    "step_number": 1,
                    "instruction": "Notify insurer within 48 hours of emergency admission.",
                    "deadline_or_timeline": "48 hours",
                    "required_documents": ["Admission form", "Doctor prescription"],
                    "source_page": 6,
                }
            ],
            "disclaimer": "This document summary is not a guarantee of coverage.",
        },
        "findings": [
            {
                "finding_type": "waiting_period",
                "title": "24-Month Pre-existing Condition Waiting Period",
                "explanation": "Pre-existing conditions not covered until 24 months of continuous policy coverage.",
                "why_it_matters": "Claims related to prior medical history will be declined during this period.",
                "review_priority": "high",
                "source_page": 5,
                "source_excerpt": "Pre-existing medical conditions require a 24-month continuous coverage waiting period.",
            }
        ],
    }

    async def mock_analyze(*args, **kwargs):
        return mock_insurance_output

    monkeypatch.setattr(gemini_workspace_service, "analyze_workspace_document", mock_analyze)

    pdf_bytes = make_test_pdf("Global Shield Health Policy POL-8899. Sum insured $500,000.")
    upload = client.post(
        "/api/documents/insurance",
        data={"document_subtype": "policy_document"},
        files={"file": ("policy.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    analysis = client.get(f"/api/documents/insurance/{doc_id}/analysis").json()
    assert analysis["structured_data"]["sum_insured"] == "$500,000"
    assert len(analysis["structured_data"]["exclusions"]) == 1
    assert len(analysis["structured_data"]["waiting_periods"]) == 1
    assert len(analysis["structured_data"]["claim_instructions"]) == 1

    findings = client.get(f"/api/documents/insurance/{doc_id}/findings").json()
    assert len(findings) == 1
    assert findings[0]["finding_type"] == "waiting_period"
    assert findings[0]["review_priority"] == "high"


# ==============================================================================
# 15. EDUCATION WORKSPACE EXTENSIVE TESTS
# ==============================================================================

@pytest.mark.anyio
async def test_education_gemini_analysis_with_grades_and_deadlines(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    register_user(client)

    mock_edu_output = {
        "provider": "gemini",
        "model_name": "gemini-2.5-flash",
        "summary": "Official academic transcript for B.S. Computer Science, Cumulative GPA 3.85.",
        "key_points": ["Cumulative GPA: 3.85", "Total Credits: 16.0", "Dean's List Honors"],
        "structured_data": {
            "overview": "Official transcript for Fall 2026 semester at Apex University.",
            "document_type": "transcript",
            "institution_name": "Apex University",
            "student_name": "Student A",
            "program_or_major": "B.S. Computer Science",
            "academic_term": "Fall 2026",
            "reported_gpa": "3.85 / 4.0",
            "total_credits_earned": 16.0,
            "courses_and_subjects": [
                {"code": "CS301", "name": "Algorithms & Data Structures", "credits": 4.0, "grade": "A", "source_page": 1},
                {"code": "CS320", "name": "Operating Systems", "credits": 4.0, "grade": "A-", "source_page": 1},
                {"code": "MATH210", "name": "Discrete Mathematics", "credits": 4.0, "grade": "A", "source_page": 1},
                {"code": "PHYS101", "name": "Physics for Engineers", "credits": 4.0, "grade": "B+", "source_page": 1},
            ],
            "deadlines_and_milestones": [
                {"title": "Spring 2027 Registration Deadline", "date_or_deadline": "2027-01-15", "source_page": 2}
            ],
            "assignment_requirements": [],
            "disclaimer": "Academic records extracted from document.",
        },
        "findings": [
            {
                "finding_type": "deadline",
                "title": "Spring 2027 Course Registration Deadline",
                "explanation": "Registration for upcoming semester closes on January 15, 2027.",
                "why_it_matters": "Late registration incurs fee.",
                "review_priority": "review",
                "source_page": 2,
            }
        ],
    }

    async def mock_analyze(*args, **kwargs):
        return mock_edu_output

    monkeypatch.setattr(gemini_workspace_service, "analyze_workspace_document", mock_analyze)

    pdf_bytes = make_test_pdf("Apex University Transcript. B.S. Computer Science. GPA 3.85.")
    upload = client.post(
        "/api/documents/education",
        data={"document_subtype": "transcript"},
        files={"file": ("transcript.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    analysis = client.get(f"/api/documents/education/{doc_id}/analysis").json()
    assert analysis["structured_data"]["reported_gpa"] == "3.85 / 4.0"
    assert len(analysis["structured_data"]["courses_and_subjects"]) == 4
    assert analysis["structured_data"]["total_credits_earned"] == 16.0


# ==============================================================================
# 16. EMPLOYMENT & GOVERNMENT EXTENSIVE TESTS
# ==============================================================================

@pytest.mark.anyio
async def test_employment_government_analysis_with_compensation_and_notice(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    register_user(client)

    mock_emp_gov_output = {
        "provider": "gemini",
        "model_name": "gemini-2.5-flash",
        "summary": "Employment offer letter for Senior Software Engineer with $150,000 gross annual compensation.",
        "key_points": ["Base salary: $135,000", "Annual bonus target: $15,000", "Probation period: 3 months", "Notice period: 60 days"],
        "structured_data": {
            "overview": "Offer letter from Acme Technologies Ltd for Senior Software Engineer.",
            "document_type": "offer_letter",
            "issuing_organization": "Acme Technologies Ltd",
            "role_or_scheme_title": "Senior Software Engineer",
            "work_location": "San Francisco, CA",
            "joining_date": "2027-01-04",
            "probation_period": "3 months",
            "notice_period": "60 days",
            "bond_or_service_obligation": "None",
            "compensation": {
                "gross_salary": "$150,000",
                "basic_salary": "$135,000",
                "currency": "USD",
                "payment_frequency": "annual",
                "variable_pay": "$15,000 performance bonus",
                "benefits": ["Health Insurance", "401(k) 4% match", "20 days PTO"],
            },
            "restrictive_covenants": [
                {
                    "clause_title": "Non-Solicitation of Customers & Employees",
                    "description": "Employee cannot solicit company customers or employees for 12 months post-employment.",
                    "duration": "12 months",
                    "why_it_matters": "Post-employment restriction.",
                    "review_priority": "review",
                    "source_page": 3,
                    "source_excerpt": "Section 9.2: For twelve (12) months following termination...",
                }
            ],
            "government_notice": {
                "reference_number": "REF-2026-GOV-987",
                "issuing_authority": "Department of Labor",
                "effective_date": "2026-11-01",
                "eligibility_criteria": ["US Citizen or Permanent Resident", "Valid SSN"],
            },
            "disclaimer": "Information extracted from uploaded copy.",
        },
        "findings": [
            {
                "finding_type": "restrictive_covenant",
                "title": "12-Month Non-Solicitation Covenant",
                "explanation": "Restriction against soliciting customers and employees for 12 months after leaving.",
                "why_it_matters": "Review prior to accepting future roles.",
                "review_priority": "review",
                "source_page": 3,
                "source_excerpt": "Section 9.2: For twelve (12) months following termination...",
            }
        ],
    }

    async def mock_analyze(*args, **kwargs):
        return mock_emp_gov_output

    monkeypatch.setattr(gemini_workspace_service, "analyze_workspace_document", mock_analyze)

    pdf_bytes = make_test_pdf("Acme Technologies Offer Letter. Senior Engineer. $150,000 annual.")
    upload = client.post(
        "/api/documents/employment-government",
        data={"document_subtype": "offer_letter"},
        files={"file": ("offer_letter.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    analysis = client.get(f"/api/documents/employment-government/{doc_id}/analysis").json()
    assert analysis["structured_data"]["compensation"]["gross_salary"] == "$150,000"
    assert analysis["structured_data"]["notice_period"] == "60 days"
    assert len(analysis["structured_data"]["restrictive_covenants"]) == 1
    assert analysis["structured_data"]["government_notice"]["reference_number"] == "REF-2026-GOV-987"


# ==============================================================================
# 17. DOCX AND IMAGE FILE EXTRACTION TESTS
# ==============================================================================

def test_docx_file_upload_and_extraction(client: TestClient) -> None:
    register_user(client)

    docx_bytes = make_test_docx([
        "Master Services Agreement between Alpha Corp and Gamma LLC.",
        "## Section 1 - Scope of Work",
        "The vendor shall deliver cloud architecture consulting.",
        "## Section 2 - Payment Terms",
        "- Payment terms are Net 30 days from invoice.",
        "- Late payments subject to 1.5% interest per month.",
    ])

    upload = client.post(
        "/api/documents/legal",
        data={"document_subtype": "service_agreement", "label": "Cloud Consulting MSA"},
        files={"file": ("consulting_msa.docx", io.BytesIO(docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert upload.status_code == 201
    doc_data = upload.json()
    assert doc_data["file_extension"] == ".docx"
    assert doc_data["extraction_method"] == "docx_parser"
    assert doc_data["page_count"] >= 1
    assert doc_data["character_count"] > 50


def test_image_file_upload_and_validation(client: TestClient) -> None:
    register_user(client)

    png_bytes = make_test_image("PNG")
    upload = client.post(
        "/api/documents/finance",
        data={"document_subtype": "receipt", "label": "Lunch Receipt Scan"},
        files={"file": ("receipt.png", io.BytesIO(png_bytes), "image/png")},
    )
    assert upload.status_code == 201
    doc_data = upload.json()
    assert doc_data["file_extension"] == ".png"
    assert doc_data["mime_type"] == "image/png"


def test_corrupt_docx_and_empty_file_handling(client: TestClient) -> None:
    register_user(client)

    # 1. Zero-byte file rejected
    empty_res = client.post(
        "/api/documents/legal",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert empty_res.status_code == 400
    assert "empty" in empty_res.json()["detail"].lower()

    # 2. Corrupt DOCX rejected by file signature validator
    corrupt_docx_res = client.post(
        "/api/documents/legal",
        files={"file": ("corrupt.docx", io.BytesIO(b"PK\x03\x04corruptedbytesthatarenotazip"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert corrupt_docx_res.status_code == 400


# ==============================================================================
# 18. GEMINI TIMEOUT AND PROVIDER ERROR MAPPING TESTS
# ==============================================================================

@pytest.mark.anyio
async def test_gemini_timeout_and_provider_error_handling(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio
    register_user(client)

    async def mock_timeout(*args, **kwargs):
        raise asyncio.TimeoutError("Gemini call timed out after 45 seconds")

    monkeypatch.setattr(gemini_workspace_service, "analyze_workspace_document", mock_timeout)

    pdf_bytes = make_test_pdf("Document text to test timeout error handling.")
    upload = client.post(
        "/api/documents/legal",
        files={"file": ("timeout_doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    detail = client.get(f"/api/documents/legal/{doc_id}").json()
    assert detail["status"] == "failed"
    assert detail["failure_code"] in ("provider_timeout", "analysis_failed")


