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

