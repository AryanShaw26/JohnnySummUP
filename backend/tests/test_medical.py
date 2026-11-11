import asyncio
import io
import json
import os
import shutil
from collections.abc import Generator
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from google.genai.errors import APIError
from pydantic import SecretStr
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.core.database import get_db, get_engine, get_session_factory
from app.main import app
from app.models.base import Base
from app.models.document_analysis import DocumentAnalysis
from app.models.medical_document import MedicalDocument
from app.models.user import User
from app.services.medical.gemini_adapter import GeminiAdapter, GeminiAdapterError

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
        session.execute(delete(User))
        session.commit()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    storage_dir = get_settings().medical_storage_path
    if storage_dir.exists():
        shutil.rmtree(storage_dir, ignore_errors=True)


# =
# 1. CORE MEDICAL ROUTE & CRUD TESTS
# =

def test_medical_unauthenticated_returns_401(client: TestClient) -> None:
    assert client.get("/api/medical/overview").status_code == 401
    assert client.get("/api/medical/documents").status_code == 401
    assert client.get("/api/medical/flags").status_code == 401
    assert client.get("/api/medical/analytics/trends").status_code == 401


def test_medical_upload_list_and_details(client: TestClient) -> None:
    reg = client.post(
        "/api/auth/register",
        json={"full_name": "Test User", "email": "user@example.com", "password": "password123"},
    )
    assert reg.status_code == 201

    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_resp = client.post(
        "/api/medical/documents",
        data={"document_type": "laboratory_report", "report_date": "2026-11-01"},
        files={"file": ("lab_report.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    assert doc_data["original_filename"] == "lab_report.pdf"
    assert doc_data["document_type"] == "laboratory_report"
    assert doc_data["report_date"] == "2026-11-01"
    doc_id = doc_data["id"]

    list_resp = client.get("/api/medical/documents")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] == 1
    assert list_data["items"][0]["id"] == doc_id

    detail_resp = client.get(f"/api/medical/documents/{doc_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == doc_id

    download_resp = client.get(f"/api/medical/documents/{doc_id}/download")
    assert download_resp.status_code == 200
    assert download_resp.content == pdf_content

    overview_resp = client.get("/api/medical/overview")
    assert overview_resp.status_code == 200
    assert overview_resp.json()["total_reports"] == 1
    assert overview_resp.json()["lab_reports_count"] == 1

    del_resp = client.delete(f"/api/medical/documents/{doc_id}")
    assert del_resp.status_code == 204
    assert client.get(f"/api/medical/documents/{doc_id}").status_code == 404
    assert client.get("/api/medical/documents").json()["total"] == 0


def test_cross_user_isolation(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"full_name": "User A", "email": "usera@example.com", "password": "password123"},
    )
    pdf_content = b"%PDF-1.4\nUser A Report\n%%EOF"
    upload_a = client.post(
        "/api/medical/documents",
        data={"document_type": "prescription"},
        files={"file": ("rx_a.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    doc_a_id = upload_a.json()["id"]

    client.post("/api/auth/logout")

    client.post(
        "/api/auth/register",
        json={"full_name": "User B", "email": "userb@example.com", "password": "password123"},
    )

    list_b = client.get("/api/medical/documents").json()
    assert list_b["total"] == 0
    assert client.get(f"/api/medical/documents/{doc_a_id}").status_code == 404
    assert client.get(f"/api/medical/documents/{doc_a_id}/download").status_code == 404
    assert client.delete(f"/api/medical/documents/{doc_a_id}").status_code == 404
    assert client.post(f"/api/medical/documents/{doc_a_id}/analyze").status_code == 404


def test_invalid_upload_rejected(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"full_name": "Test User", "email": "val@example.com", "password": "password123"},
    )

    empty_resp = client.post(
        "/api/medical/documents",
        data={"document_type": "prescription"},
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert empty_resp.status_code == 400

    exe_resp = client.post(
        "/api/medical/documents",
        data={"document_type": "prescription"},
        files={"file": ("script.exe", io.BytesIO(b"binary"), "application/x-msdownload")},
    )
    assert exe_resp.status_code == 400

    fake_pdf = client.post(
        "/api/medical/documents",
        data={"document_type": "prescription"},
        files={"file": ("fake.pdf", io.BytesIO(b"Not a real PDF header"), "application/pdf")},
    )
    assert fake_pdf.status_code == 400


def test_filtering_and_pagination(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"full_name": "Filter User", "email": "filter@example.com", "password": "password123"},
    )
    pdf = b"%PDF-1.4\nSample content\n%%EOF"

    client.post(
        "/api/medical/documents",
        data={"document_type": "prescription"},
        files={"file": ("rx_alpha.pdf", io.BytesIO(pdf), "application/pdf")},
    )
    client.post(
        "/api/medical/documents",
        data={"document_type": "prescription"},
        files={"file": ("rx_beta.pdf", io.BytesIO(pdf), "application/pdf")},
    )
    client.post(
        "/api/medical/documents",
        data={"document_type": "laboratory_report"},
        files={"file": ("lab_blood.pdf", io.BytesIO(pdf), "application/pdf")},
    )

    rx_list = client.get("/api/medical/documents?document_type=prescription").json()
    assert rx_list["total"] == 2

    lab_list = client.get("/api/medical/documents?document_type=laboratory_report").json()
    assert lab_list["total"] == 1
    assert lab_list["items"][0]["original_filename"] == "lab_blood.pdf"

    search_list = client.get("/api/medical/documents?search=alpha").json()
    assert search_list["total"] == 1
    assert search_list["items"][0]["original_filename"] == "rx_alpha.pdf"

    paged = client.get("/api/medical/documents?page=1&page_size=2").json()
    assert len(paged["items"]) == 2
    assert paged["total"] == 3
    assert paged["total_pages"] == 2


def test_analytics_and_history(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"full_name": "Analytics User", "email": "analytics@example.com", "password": "password123"},
    )
    pdf = b"%PDF-1.4\nTest\n%%EOF"
    upload = client.post(
        "/api/medical/documents",
        data={"document_type": "laboratory_report", "report_date": "2026-06-15"},
        files={"file": ("cbc_june.pdf", io.BytesIO(pdf), "application/pdf")},
    )
    assert upload.status_code == 201

    uploads_hist = client.get("/api/medical/history/uploads")
    assert uploads_hist.status_code == 200
    assert len(uploads_hist.json()) == 1

    timeline = client.get("/api/medical/history/timeline")
    assert timeline.status_code == 200
    assert len(timeline.json()) == 1
    assert timeline.json()[0]["report_name"] == "cbc_june.pdf"


def test_empty_text_fails_with_ocr_no_text(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"full_name": "OCR User", "email": "ocr@example.com", "password": "password123"},
    )
    blank_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload = client.post(
        "/api/medical/documents",
        data={"document_type": "laboratory_report"},
        files={"file": ("blank_scan.pdf", io.BytesIO(blank_pdf), "application/pdf")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    detail = client.get(f"/api/medical/documents/{doc_id}").json()
    assert detail["status"] == "failed"
    assert detail["failure_code"] in ("OCR_NO_TEXT", "extraction_failed")
    assert "could not extract readable text" in detail["failure_message"].lower()


@pytest.mark.anyio
async def test_ai_analysis_with_mock_provider_and_persistence(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.medical.analysis import analysis_service

    reg = client.post(
        "/api/auth/register",
        json={"full_name": "AI Test User", "email": "ai@example.com", "password": "password123"},
    )
    user_id = reg.json()["id"]

    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload = client.post(
        "/api/medical/documents",
        data={"document_type": "laboratory_report", "report_date": "2026-11-01"},
        files={"file": ("blood_report.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    doc_id = upload.json()["id"]

    mock_ai_output = {
        "summary": "Blood test shows hemoglobin within normal reference range.",
        "key_points": ["Hemoglobin 13.5 g/dL (Normal)"],
        "report_date": "2026-11-01",
        "findings": [
            {
                "category": "laboratory",
                "finding_type": "test_result",
                "name": "Hemoglobin",
                "value_text": "13.5 g/dL",
                "numeric_value": 13.5,
                "unit": "g/dL",
                "reference_low": 12.0,
                "reference_high": 16.0,
                "reference_text": "12.0 - 16.0 g/dL",
                "source_page": 1,
                "confidence": 0.98,
            }
        ],
        "measurements": [
            {
                "parameter_name": "Hemoglobin",
                "parameter_code": "hemoglobin",
                "numeric_value": 13.5,
                "unit": "g/dL",
                "reference_low": 12.0,
                "reference_high": 16.0,
                "reference_text": "12.0 - 16.0 g/dL",
            }
        ],
        "flags": [],
    }

    with TestSession() as session:
        await analysis_service.run_analysis(
            db=session,
            document_id=UUID(doc_id),
            user_id=UUID(user_id),
            extracted_text="Hemoglobin: 13.5 g/dL Normal range: 12.0 - 16.0 g/dL",
            document_type="laboratory_report",
            mock_response=mock_ai_output,
        )

    detail = client.get(f"/api/medical/documents/{doc_id}").json()
    assert detail["status"] == "completed"
    assert len(detail["analyses"]) >= 1
    assert detail["analyses"][0]["summary"] == "Blood test shows hemoglobin within normal reference range."
    assert len(detail["findings"]) == 1
    assert detail["findings"][0]["name"] == "Hemoglobin"
    assert len(detail["measurements"]) == 1
    assert detail["measurements"][0]["numeric_value"] == 13.5

    trend = client.get("/api/medical/analytics/trends?parameter=Hemoglobin").json()
    assert trend["parameter_name"] == "Hemoglobin"
    assert len(trend["points"]) == 1
    assert trend["current_value"] == 13.5


# =
# 2. CONFIGURATION TESTS (Section 13: 1-6)
# =

def test_config_gemini_key_present_and_model_loaded() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://user:pass@localhost:5432/test_db",
        jwt_secret_key="a" * 32,
        gemini_api_key="valid-test-gemini-key",
        gemini_model="gemini-2.5-flash",
    )
    assert settings.gemini_api_key is not None
    assert settings.gemini_api_key.get_secret_value() == "valid-test-gemini-key"
    assert settings.gemini_model == "gemini-2.5-flash"


def test_config_gemini_key_empty_or_placeholder_normalized_to_none() -> None:
    settings_empty = Settings(
        database_url="postgresql+psycopg://user:pass@localhost:5432/test_db",
        jwt_secret_key="a" * 32,
        gemini_api_key="",
    )
    assert settings_empty.gemini_api_key is None

    settings_placeholder = Settings(
        database_url="postgresql+psycopg://user:pass@localhost:5432/test_db",
        jwt_secret_key="a" * 32,
        gemini_api_key="PASTE_VALID_GEMINI_KEY_HERE",
    )
    assert settings_placeholder.gemini_api_key is None


def test_config_no_openai_variable_required() -> None:
    # Ensure settings initializes and Medical AI functions without any OpenAI environment variable
    settings = Settings(
        database_url="postgresql+psycopg://user:pass@localhost:5432/test_db",
        jwt_secret_key="a" * 32,
        gemini_api_key="valid-gemini-key",
    )
    assert settings.openai_api_key is None
    assert settings.gemini_model == "gemini-2.5-flash"


def test_diagnostics_does_not_expose_api_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.medical import analysis as analysis_module

    client.post(
        "/api/auth/register",
        json={"full_name": "Diag User", "email": "diag@example.com", "password": "password123"},
    )
    settings = get_settings().model_copy(update={"gemini_api_key": SecretStr("super-secret-gemini-key")})
    monkeypatch.setattr(analysis_module, "get_settings", lambda: settings)

    resp = client.get("/api/medical/diagnostics/provider")
    assert resp.status_code == 200
    data = resp.json()

    assert data["provider"] == "gemini"
    assert data["configured"] is True
    assert data["model"] == "gemini-2.5-flash"
    assert "super-secret" not in json.dumps(data)


# =
# 3. GEMINI ADAPTER TESTS (Section 13: 7-16)
# =

@pytest.mark.anyio
async def test_gemini_adapter_success_parsed() -> None:
    mock_candidate = MagicMock()
    mock_candidate.finish_reason = "STOP"
    mock_part = MagicMock()
    mock_part.text = '{"summary": "Test Summary", "key_points": []}'
    mock_candidate.content.parts = [mock_part]

    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]
    mock_response.usage_metadata.prompt_token_count = 120
    mock_response.usage_metadata.candidates_token_count = 45

    with patch.object(GeminiAdapter, "get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        result = await GeminiAdapter.generate_content(
            prompt="Analyze this text",
            system_instruction="System prompt",
            api_key_override="mock-key",
            model_override="gemini-2.5-flash",
        )

        assert result["provider"] == "gemini"
        assert result["model"] == "gemini-2.5-flash"
        assert result["content"] == '{"summary": "Test Summary", "key_points": []}'
        assert result["usage"]["input_tokens"] == 120
        assert result["usage"]["output_tokens"] == 45
        assert "request_id" in result


@pytest.mark.anyio
async def test_gemini_adapter_safety_blocked() -> None:
    mock_candidate = MagicMock()
    mock_candidate.finish_reason = "SAFETY"
    mock_candidate.content.parts = []

    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]

    with patch.object(GeminiAdapter, "get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        with pytest.raises(GeminiAdapterError) as exc_info:
            await GeminiAdapter.generate_content(
                prompt="Sensitive content",
                system_instruction="Prompt",
                api_key_override="mock-key",
            )
        assert exc_info.value.error_code == "provider_blocked"


@pytest.mark.anyio
async def test_gemini_adapter_empty_response() -> None:
    mock_response = MagicMock()
    mock_response.candidates = []

    with patch.object(GeminiAdapter, "get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        with pytest.raises(GeminiAdapterError) as exc_info:
            await GeminiAdapter.generate_content(
                prompt="Prompt",
                system_instruction="Prompt",
                api_key_override="mock-key",
            )
        assert exc_info.value.error_code == "empty_provider_response"


@pytest.mark.anyio
async def test_gemini_adapter_missing_key() -> None:
    with patch("app.services.medical.gemini_adapter.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(gemini_api_key=None)
        with pytest.raises(GeminiAdapterError) as exc_info:
            await GeminiAdapter.generate_content(
                prompt="Prompt",
                system_instruction="Prompt",
                api_key_override=None,
            )
        assert exc_info.value.error_code == "provider_not_configured"


def test_gemini_error_classification() -> None:
    # 401 Authentication failed
    e401 = APIError(401, {"error": {"message": "API key not valid", "status": "UNAUTHENTICATED"}})
    code, msg = GeminiAdapter.classify_api_error(e401, "req-1")
    assert code == "authentication_failed"
    assert "authentication failed" in msg.lower()

    # 403 Permission denied
    e403 = APIError(403, {"error": {"message": "Permission denied for model", "status": "PERMISSION_DENIED"}})
    code, msg = GeminiAdapter.classify_api_error(e403, "req-2")
    assert code == "permission_denied"

    # 404 Model not found
    e404 = APIError(404, {"error": {"message": "models/gemini-not-found was not found", "status": "NOT_FOUND"}})
    code, msg = GeminiAdapter.classify_api_error(e404, "req-3")
    assert code == "model_unavailable"

    # 429 Quota exhaustion
    e429_quota = APIError(429, {"error": {"message": "Quota exceeded for quota metric", "status": "RESOURCE_EXHAUSTED"}})
    code, msg = GeminiAdapter.classify_api_error(e429_quota, "req-4")
    assert code == "quota_exceeded"
    assert "quota is exhausted" in msg.lower()

    # 429 Rate limited (transient)
    e429_rate = APIError(429, {"error": {"message": "Too many requests per minute", "status": "RESOURCE_EXHAUSTED"}})
    code, msg = GeminiAdapter.classify_api_error(e429_rate, "req-5")
    assert code == "rate_limited"
    assert "rate-limiting" in msg.lower()

    # 503 Provider unavailable
    e503 = APIError(503, {"error": {"message": "Service unavailable", "status": "UNAVAILABLE"}})
    code, msg = GeminiAdapter.classify_api_error(e503, "req-6")
    assert code == "provider_unavailable"


# =
# 4. OCR & PIPELINE VERIFICATION TESTS (Section 13: 17-26)
# =

@pytest.mark.anyio
async def test_searchable_pdf_extracts_text_and_invokes_gemini_once(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.medical import analysis as analysis_module
    from app.services.medical import documents as documents_module

    client.post(
        "/api/auth/register",
        json={"full_name": "Pipeline User", "email": "pipe@example.com", "password": "password123"},
    )
    settings = get_settings().model_copy(update={"gemini_api_key": SecretStr("test-gemini-key")})
    monkeypatch.setattr(analysis_module, "get_settings", lambda: settings)

    gemini_call_count = 0

    async def mock_generate_content(*args, **kwargs):
        nonlocal gemini_call_count
        gemini_call_count += 1
        return {
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "content": json.dumps({"summary": "Valid PDF analysis", "key_points": []}),
            "request_id": "test-req-id",
            "usage": {"input_tokens": 50, "output_tokens": 10},
        }

    monkeypatch.setattr(analysis_module.GeminiAdapter, "generate_content", mock_generate_content)

    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload = client.post(
        "/api/medical/documents",
        data={"document_type": "laboratory_report"},
        files={"file": ("searchable.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    # Re-run analysis explicitly
    with patch.object(
        documents_module.extraction_service,
        "extract_document",
        return_value=MagicMock(status="success", text="Hemoglobin 14.0 g/dL"),
    ):
        analyze_resp = client.post(f"/api/medical/documents/{doc_id}/analyze")
        assert analyze_resp.status_code == 200
        assert analyze_resp.json()["status"] == "completed"
        assert analyze_resp.json()["summary"] == "Valid PDF analysis"
        assert gemini_call_count == 1


@pytest.mark.anyio
async def test_gemini_failure_preserves_extraction_and_marks_failed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.medical import analysis as analysis_module
    from app.services.medical import documents as documents_module

    client.post(
        "/api/auth/register",
        json={"full_name": "Fail User", "email": "fail@example.com", "password": "password123"},
    )
    settings = get_settings().model_copy(update={"gemini_api_key": SecretStr("test-gemini-key")})
    monkeypatch.setattr(analysis_module, "get_settings", lambda: settings)

    async def mock_generate_fail(*args, **kwargs):
        raise GeminiAdapterError("quota_exceeded", "Gemini quota is exhausted for this project/model. Check project limits and billing.")

    monkeypatch.setattr(analysis_module.GeminiAdapter, "generate_content", mock_generate_fail)

    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload = client.post(
        "/api/medical/documents",
        data={"document_type": "laboratory_report"},
        files={"file": ("lab_fail.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    doc_id = upload.json()["id"]

    with patch.object(
        documents_module.extraction_service,
        "extract_document",
        return_value=MagicMock(status="success", text="Valid extracted medical text"),
    ):
        analyze_resp = client.post(f"/api/medical/documents/{doc_id}/analyze")
        assert analyze_resp.status_code == 200
        data = analyze_resp.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "quota_exceeded"
        assert "quota is exhausted" in data["error_message"].lower()

        # Check detail endpoint preserves failure status
        detail = client.get(f"/api/medical/documents/{doc_id}").json()
        assert detail["status"] == "failed"
        assert detail["failure_code"] == "quota_exceeded"


@pytest.mark.anyio
async def test_concurrent_analysis_requests_prevent_duplicate_gemini_calls(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.medical import analysis as analysis_module
    from app.services.medical import documents as documents_module
    from app.services.medical.analysis import analysis_service

    client.post(
        "/api/auth/register",
        json={"full_name": "Conc User", "email": "conc@example.com", "password": "password123"},
    )
    user_id = UUID(client.get("/api/users/me").json()["id"])
    settings = get_settings().model_copy(update={"gemini_api_key": SecretStr("test-gemini-key")})
    monkeypatch.setattr(analysis_module, "get_settings", lambda: settings)

    upload = client.post(
        "/api/medical/documents",
        data={"document_type": "laboratory_report"},
        files={"file": ("report.pdf", io.BytesIO(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"), "application/pdf")},
    )
    document_id = UUID(upload.json()["id"])

    request_started = asyncio.Event()
    release_request = asyncio.Event()
    gemini_call_count = 0

    async def mock_blocking_gemini(*args, **kwargs):
        nonlocal gemini_call_count
        gemini_call_count += 1
        request_started.set()
        await release_request.wait()
        return {
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "content": json.dumps({"summary": "Single call summary", "key_points": []}),
            "request_id": "test-req-id",
            "usage": {"input_tokens": 50, "output_tokens": 10},
        }

    monkeypatch.setattr(analysis_module.GeminiAdapter, "generate_content", mock_blocking_gemini)

    first_session = TestSession()
    second_session = TestSession()

    first_task = asyncio.create_task(
        analysis_service.run_analysis(
            db=first_session,
            document_id=document_id,
            user_id=user_id,
            extracted_text="Medical test text",
            document_type="laboratory_report",
        )
    )

    try:
        await asyncio.wait_for(request_started.wait(), timeout=5)
        # Attempt second concurrent analysis while first is active
        duplicate = await analysis_service.run_analysis(
            db=second_session,
            document_id=document_id,
            user_id=user_id,
            extracted_text="Medical test text",
            document_type="laboratory_report",
        )
        assert duplicate.status == "processing"
        assert gemini_call_count == 1
    finally:
        release_request.set()
        completed = await first_task
        first_session.close()
        second_session.close()

    assert completed.status == "completed"
    assert gemini_call_count == 1
