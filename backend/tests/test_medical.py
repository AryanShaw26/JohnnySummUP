import io
import json
import os
import shutil
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import get_db, get_engine, get_session_factory
from app.main import app
from app.models.base import Base
from app.models.user import User


@pytest.mark.parametrize(
    ("error_type", "error_code", "error_message", "expected"),
    [
        ("insufficient_quota", "", "", True),
        ("", "billing_hard_limit_reached", "", True),
        ("rate_limit_exceeded", "", "Too many requests", False),
        ("", "", "Request rate limit reached", False),
    ],
)
def test_provider_429_classification(
    error_type: str,
    error_code: str,
    error_message: str,
    expected: bool,
) -> None:
    from app.services.medical.analysis import _is_quota_error

    assert _is_quota_error(error_type, error_code, error_message) is expected


test_engine = create_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
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

    # Clean up test uploads directory if created
    storage_dir = get_settings().medical_storage_path
    if storage_dir.exists():
        shutil.rmtree(storage_dir, ignore_errors=True)


def test_medical_unauthenticated_returns_401(client: TestClient) -> None:
    assert client.get("/api/medical/overview").status_code == 401
    assert client.get("/api/medical/documents").status_code == 401
    assert client.get("/api/medical/flags").status_code == 401
    assert client.get("/api/medical/analytics/trends").status_code == 401


def test_medical_upload_list_and_details(client: TestClient) -> None:
    # Register and login user
    reg = client.post(
        "/api/auth/register",
        json={"full_name": "Test User", "email": "user@example.com", "password": "password123"},
    )
    assert reg.status_code == 201

    # Upload valid PDF
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

    # List documents
    list_resp = client.get("/api/medical/documents")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] == 1
    assert list_data["items"][0]["id"] == doc_id

    # Get details
    detail_resp = client.get(f"/api/medical/documents/{doc_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == doc_id

    # Download document
    download_resp = client.get(f"/api/medical/documents/{doc_id}/download")
    assert download_resp.status_code == 200
    assert download_resp.content == pdf_content

    # Overview returns count
    overview_resp = client.get("/api/medical/overview")
    assert overview_resp.status_code == 200
    assert overview_resp.json()["total_reports"] == 1
    assert overview_resp.json()["lab_reports_count"] == 1

    # Delete document
    del_resp = client.delete(f"/api/medical/documents/{doc_id}")
    assert del_resp.status_code == 204

    # Verify deleted
    assert client.get(f"/api/medical/documents/{doc_id}").status_code == 404
    assert client.get("/api/medical/documents").json()["total"] == 0


def test_cross_user_isolation(client: TestClient) -> None:
    # Register User A
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

    # Logout User A
    client.post("/api/auth/logout")

    # Register User B
    client.post(
        "/api/auth/register",
        json={"full_name": "User B", "email": "userb@example.com", "password": "password123"},
    )

    # User B should NOT see User A's document in list
    list_b = client.get("/api/medical/documents").json()
    assert list_b["total"] == 0

    # User B should be blocked from details, download, delete, analyze User A's document
    assert client.get(f"/api/medical/documents/{doc_a_id}").status_code == 404
    assert client.get(f"/api/medical/documents/{doc_a_id}/download").status_code == 404
    assert client.delete(f"/api/medical/documents/{doc_a_id}").status_code == 404
    assert client.post(f"/api/medical/documents/{doc_a_id}/analyze").status_code == 404


def test_invalid_upload_rejected(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"full_name": "Test User", "email": "val@example.com", "password": "password123"},
    )

    # Empty file
    empty_resp = client.post(
        "/api/medical/documents",
        data={"document_type": "prescription"},
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert empty_resp.status_code == 400

    # Invalid extension
    exe_resp = client.post(
        "/api/medical/documents",
        data={"document_type": "prescription"},
        files={"file": ("script.exe", io.BytesIO(b"binary"), "application/x-msdownload")},
    )
    assert exe_resp.status_code == 400

    # Invalid PDF magic number
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

    # Upload 2 prescriptions and 1 lab report
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

    # Filter prescription
    rx_list = client.get("/api/medical/documents?document_type=prescription").json()
    assert rx_list["total"] == 2

    # Filter lab
    lab_list = client.get("/api/medical/documents?document_type=laboratory_report").json()
    assert lab_list["total"] == 1
    assert lab_list["items"][0]["original_filename"] == "lab_blood.pdf"

    # Search by keyword
    search_list = client.get("/api/medical/documents?search=alpha").json()
    assert search_list["total"] == 1
    assert search_list["items"][0]["original_filename"] == "rx_alpha.pdf"

    # Pagination
    paged = client.get("/api/medical/documents?page=1&page_size=2").json()
    assert len(paged["items"]) == 2
    assert paged["total"] == 3
    assert paged["total_pages"] == 2


def test_analytics_and_history(client: TestClient) -> None:
    reg = client.post(
        "/api/auth/register",
        json={"full_name": "Analytics User", "email": "analytics@example.com", "password": "password123"},
    )
    user_id = reg.json()["id"]

    pdf = b"%PDF-1.4\nTest\n%%EOF"
    upload = client.post(
        "/api/medical/documents",
        data={"document_type": "laboratory_report", "report_date": "2026-06-15"},
        files={"file": ("cbc_june.pdf", io.BytesIO(pdf), "application/pdf")},
    )
    doc_id = upload.json()["id"]

    # History uploads
    uploads_hist = client.get("/api/medical/history/uploads")
    assert uploads_hist.status_code == 200
    assert len(uploads_hist.json()) == 1

    # Timeline
    timeline = client.get("/api/medical/history/timeline")
    assert timeline.status_code == 200
    assert len(timeline.json()) == 1
    assert timeline.json()[0]["report_name"] == "cbc_june.pdf"


def test_empty_text_fails_with_ocr_no_text(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"full_name": "OCR User", "email": "ocr@example.com", "password": "password123"},
    )
    # A PDF without any text layer
    blank_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload = client.post(
        "/api/medical/documents",
        data={"document_type": "laboratory_report"},
        files={"file": ("blank_scan.pdf", io.BytesIO(blank_pdf), "application/pdf")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    # Verify document is marked failed with OCR_NO_TEXT (never marked completed)
    detail = client.get(f"/api/medical/documents/{doc_id}").json()
    assert detail["status"] == "failed"
    assert detail["failure_code"] == "OCR_NO_TEXT"
    assert "could not extract readable text" in detail["failure_message"].lower()


@pytest.mark.anyio
async def test_ai_analysis_with_mock_provider_and_persistence(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.config import get_settings
    from app.services.medical.analysis import analysis_service
    from app.services.medical import analysis as analysis_module

    reg = client.post(
        "/api/auth/register",
        json={"full_name": "AI Test User", "email": "ai@example.com", "password": "password123"},
    )
    user_id = reg.json()["id"]
    settings = get_settings().model_copy(update={"openai_api_key": None})
    monkeypatch.setattr(analysis_module, "get_settings", lambda: settings)

    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n5 0 obj\n<< /Length 73 >>\nstream\nBT\n/F1 12 Tf\n72 712 Td\n(Hemoglobin: 13.5 g/dL Normal range: 12.0 - 16.0 g/dL) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000227 00000 n \n0000000305 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n428\n%%EOF"

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

    from uuid import UUID
    with TestSession() as session:
        await analysis_service.run_analysis(
            db=session,
            document_id=UUID(doc_id),
            user_id=UUID(user_id),
            extracted_text="Hemoglobin: 13.5 g/dL Normal range: 12.0 - 16.0 g/dL",
            document_type="laboratory_report",
            mock_response=mock_ai_output,
        )

    # Verify status is now completed and findings/measurements are persisted
    detail = client.get(f"/api/medical/documents/{doc_id}").json()
    assert detail["status"] == "completed"
    assert len(detail["analyses"]) >= 1
    assert detail["analyses"][0]["summary"] == "Blood test shows hemoglobin within normal reference range."
    assert len(detail["findings"]) == 1
    assert detail["findings"][0]["name"] == "Hemoglobin"
    assert len(detail["measurements"]) == 1
    assert detail["measurements"][0]["numeric_value"] == 13.5

    # Verify trends API returns this measurement
    trend = client.get("/api/medical/analytics/trends?parameter=Hemoglobin").json()
    assert trend["parameter_name"] == "Hemoglobin"
    assert len(trend["points"]) == 1
    assert trend["current_value"] == 13.5


@pytest.mark.anyio
async def test_ai_analysis_uses_configured_provider_url_and_model(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import httpx
    from pydantic import SecretStr

    from app.core.config import get_settings
    from app.services.medical import analysis as analysis_module
    from app.services.medical import documents as documents_module

    settings = get_settings().model_copy(
        update={
            "openai_api_key": SecretStr("test-provider-key"),
            "openai_base_url": "https://provider.example/v1",
            "openai_model": "configured-model",
        }
    )
    monkeypatch.setattr(analysis_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        documents_module.extraction_service,
        "extract_text",
        lambda *_: ("Example report text", [], 1),
    )

    captured_request: dict[str, Any] = {}
    response_content = json.dumps({"summary": "Configured provider summary", "key_points": []})

    class MockAsyncClient:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, url: str, **kwargs):
            captured_request["url"] = url
            captured_request["headers"] = kwargs["headers"]
            captured_request["body"] = kwargs["json"]
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": response_content}}]},
            )

    monkeypatch.setattr(analysis_module.httpx, "AsyncClient", MockAsyncClient)

    client.post(
        "/api/auth/register",
        json={
            "full_name": "Provider Test User",
            "email": "provider@example.com",
            "password": "password123",
        },
    )
    upload = client.post(
        "/api/medical/documents",
        data={"document_type": "laboratory_report"},
        files={"file": ("report.pdf", io.BytesIO(b"%PDF-1.4\nreport\n%%EOF"), "application/pdf")},
    )

    assert upload.status_code == 201
    assert upload.json()["status"] == "completed"
    assert upload.json()["latest_analysis"]["summary"] == "Configured provider summary"
    assert captured_request["url"] == "https://provider.example/v1/chat/completions"
    assert captured_request["headers"]["Authorization"] == "Bearer test-provider-key"
    assert captured_request["body"]["model"] == "configured-model"


@pytest.mark.anyio
async def test_ai_analysis_reports_provider_key_rejection(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import httpx
    from pydantic import SecretStr

    from app.core.config import get_settings
    from app.services.medical import analysis as analysis_module
    from app.services.medical import documents as documents_module

    settings = get_settings().model_copy(update={"openai_api_key": SecretStr("invalid-test-key")})
    monkeypatch.setattr(analysis_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        documents_module.extraction_service,
        "extract_text",
        lambda *_: ("Example report text", [], 1),
    )

    class UnauthorizedAsyncClient:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, *_args, **_kwargs):
            return httpx.Response(
                401,
                json={"error": {"type": "invalid_api_key", "message": "Invalid API key"}},
            )

    monkeypatch.setattr(analysis_module.httpx, "AsyncClient", UnauthorizedAsyncClient)

    client.post(
        "/api/auth/register",
        json={
            "full_name": "Invalid Key User",
            "email": "invalid-key@example.com",
            "password": "password123",
        },
    )
    upload = client.post(
        "/api/medical/documents",
        data={"document_type": "laboratory_report"},
        files={"file": ("report.pdf", io.BytesIO(b"%PDF-1.4\nreport\n%%EOF"), "application/pdf")},
    )

    assert upload.status_code == 201
    assert upload.json()["status"] == "failed"
    assert upload.json()["failure_code"] == "PROVIDER_AUTH_ERROR"
    assert "provider at OPENAI_BASE_URL" in upload.json()["failure_message"]
    assert "ChatGPT subscriptions are not API keys" in upload.json()["failure_message"]


@pytest.mark.anyio
async def test_retry_analysis_persists_provider_quota_failure(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import httpx
    from pydantic import SecretStr

    from app.core.config import get_settings
    from app.services.medical import analysis as analysis_module
    from app.services.medical import documents as documents_module

    settings = get_settings().model_copy(update={"openai_api_key": SecretStr("quota-test-key")})
    monkeypatch.setattr(analysis_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        documents_module.extraction_service,
        "extract_text",
        lambda *_: ("Example report text", [], 1),
    )
    request_count = 0

    class QuotaAsyncClient:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, *_args, **_kwargs):
            nonlocal request_count
            request_count += 1
            return httpx.Response(
                429,
                json={
                    "error": {
                        "type": "insufficient_quota",
                        "code": "insufficient_quota",
                        "message": "API quota is unavailable",
                    }
                },
            )

    monkeypatch.setattr(analysis_module.httpx, "AsyncClient", QuotaAsyncClient)

    client.post(
        "/api/auth/register",
        json={
            "full_name": "Quota Test User",
            "email": "quota@example.com",
            "password": "password123",
        },
    )
    upload = client.post(
        "/api/medical/documents",
        data={"document_type": "laboratory_report"},
        files={"file": ("report.pdf", io.BytesIO(b"%PDF-1.4\nreport\n%%EOF"), "application/pdf")},
    )
    document_id = upload.json()["id"]

    assert upload.status_code == 201
    assert upload.json()["status"] == "failed"
    assert upload.json()["failure_code"] == "PROVIDER_INSUFFICIENT_QUOTA"
    assert request_count == 1

    retry = client.post(f"/api/medical/documents/{document_id}/analyze")
    details = client.get(f"/api/medical/documents/{document_id}").json()

    assert retry.status_code == 200
    assert retry.json()["version"] == 2
    assert retry.json()["status"] == "failed"
    assert retry.json()["error_code"] == "PROVIDER_INSUFFICIENT_QUOTA"
    assert details["status"] == "failed"
    assert details["failure_code"] == "PROVIDER_INSUFFICIENT_QUOTA"
    assert details["analyses"][0]["id"] == retry.json()["id"]
    assert request_count == 2


@pytest.mark.anyio
async def test_image_upload_is_sent_as_vision_input(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import httpx
    from pydantic import SecretStr

    from app.core.config import get_settings
    from app.services.medical import analysis as analysis_module
    from app.services.medical import documents as documents_module

    settings = get_settings().model_copy(update={"openai_api_key": SecretStr("image-test-key")})
    monkeypatch.setattr(analysis_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        documents_module.extraction_service,
        "extract_text",
        lambda *_: ("", [], 1),
    )
    captured_content: list[dict[str, Any]] = []

    class VisionAsyncClient:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, *_args, **kwargs):
            captured_content.extend(kwargs["json"]["messages"][1]["content"])
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {"summary": "Image report analyzed", "key_points": []}
                                )
                            }
                        }
                    ]
                },
            )

    monkeypatch.setattr(analysis_module.httpx, "AsyncClient", VisionAsyncClient)
    client.post(
        "/api/auth/register",
        json={
            "full_name": "Image Test User",
            "email": "image@example.com",
            "password": "password123",
        },
    )
    upload = client.post(
        "/api/medical/documents",
        data={"document_type": "laboratory_report"},
        files={"file": ("report.png", io.BytesIO(b"\x89PNG\r\n\x1a\nimage"), "image/png")},
    )

    assert upload.status_code == 201
    assert upload.json()["status"] == "completed"
    assert upload.json()["latest_analysis"]["summary"] == "Image report analyzed"
    assert captured_content[0]["type"] == "text"
    assert captured_content[1]["type"] == "image_url"
    assert captured_content[1]["image_url"]["url"].startswith("data:image/png;base64,")


@pytest.mark.anyio
async def test_concurrent_analysis_requests_share_in_flight_analysis(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio
    import httpx
    from pydantic import SecretStr
    from uuid import UUID

    from app.core.config import get_settings
    from app.services.medical import analysis as analysis_module
    from app.services.medical import documents as documents_module

    settings = get_settings().model_copy(update={"openai_api_key": None})
    monkeypatch.setattr(analysis_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        documents_module.extraction_service,
        "extract_text",
        lambda *_: ("Example report text", [], 1),
    )
    client.post(
        "/api/auth/register",
        json={
            "full_name": "Duplicate Test User",
            "email": "duplicate@example.com",
            "password": "password123",
        },
    )
    upload = client.post(
        "/api/medical/documents",
        data={"document_type": "laboratory_report"},
        files={"file": ("report.pdf", io.BytesIO(b"%PDF-1.4\nreport\n%%EOF"), "application/pdf")},
    )
    assert upload.status_code == 201
    document_id = UUID(upload.json()["id"])
    user_id = UUID(client.get("/api/users/me").json()["id"])

    settings = settings.model_copy(update={"openai_api_key": SecretStr("duplicate-test-key")})
    request_started = asyncio.Event()
    release_request = asyncio.Event()
    request_count = 0
    response_content = json.dumps({"summary": "Single provider call", "key_points": []})

    class BlockingAsyncClient:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, *_args, **_kwargs):
            nonlocal request_count
            request_count += 1
            request_started.set()
            await release_request.wait()
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": response_content}}]},
            )

    monkeypatch.setattr(analysis_module.httpx, "AsyncClient", BlockingAsyncClient)
    from app.services.medical.analysis import analysis_service

    first_session = TestSession()
    second_session = TestSession()
    first_task = asyncio.create_task(
        analysis_service.run_analysis(
            db=first_session,
            document_id=document_id,
            user_id=user_id,
            extracted_text="Example report text",
            document_type="laboratory_report",
        )
    )
    try:
        await asyncio.wait_for(request_started.wait(), timeout=5)
        duplicate = await analysis_service.run_analysis(
            db=second_session,
            document_id=document_id,
            user_id=user_id,
            extracted_text="Example report text",
            document_type="laboratory_report",
        )
        assert duplicate.status == "processing"
        assert request_count == 1
    finally:
        release_request.set()
        completed = await first_task
        first_session.close()
        second_session.close()

    assert completed.status == "completed"
    assert request_count == 1
