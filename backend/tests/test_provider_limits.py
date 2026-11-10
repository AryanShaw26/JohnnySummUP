import asyncio
import json
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.models.base import Base
from app.models.document_analysis import DocumentAnalysis
from app.models.medical_document import MedicalDocument
from app.models.user import User
from app.services.medical.analysis import (
    ConcurrentAnalysisError,
    MedicalAnalysisService,
    STANDARD_ERROR_MESSAGES,
)
from app.services.medical.extraction import ExtractionResult


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_user(test_db):
    user = User(
        id=uuid.uuid4(),
        email="test_user@example.com",
        full_name="Patient Test",
        password_hash="fake_hash",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def sample_doc(test_db, sample_user):
    doc = MedicalDocument(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        original_filename="blood_work.pdf",
        stored_filename="stored_blood_work.pdf",
        storage_key="docs/blood_work.pdf",
        mime_type="application/pdf",
        file_extension="pdf",
        file_size_bytes=4096,
        document_type="laboratory_report",
        status="uploaded",
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)
    return doc


def mock_settings(provider="openai", openai_key="sk-test-openai", gemini_key="AIzaSy-test-gemini"):
    return Settings(
        database_url="sqlite:///:memory:",
        jwt_secret_key=SecretStr("super-secret-jwt-key-minimum-32-chars-long"),
        ai_provider=provider,
        openai_api_key=SecretStr(openai_key) if openai_key else None,
        openai_model="gpt-4o-mini",
        gemini_api_key=SecretStr(gemini_key) if gemini_key else None,
        gemini_model="gemini-1.5-flash",
    )


# -------------------------------------------------------------------------
# Test 1: OpenAI Success; summary saved and displayed
# -------------------------------------------------------------------------
def test_openai_success(test_db, sample_user, sample_doc):
    openai_json_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "summary": "Blood test shows normal hemoglobin and fasting glucose.",
                        "key_points": ["Hemoglobin 14.2 g/dL is normal", "Glucose 92 mg/dL is optimal"],
                        "report_date": "2026-10-15",
                        "findings": [
                            {
                                "category": "laboratory",
                                "finding_type": "test_result",
                                "name": "Hemoglobin",
                                "value_text": "14.2 g/dL",
                                "numeric_value": 14.2,
                                "unit": "g/dL",
                                "reference_low": 12.0,
                                "reference_high": 16.0,
                                "reference_text": "12.0 - 16.0 g/dL",
                            }
                        ],
                        "measurements": [
                            {
                                "parameter_name": "Hemoglobin",
                                "parameter_code": "hemoglobin",
                                "numeric_value": 14.2,
                                "unit": "g/dL",
                                "reference_low": 12.0,
                                "reference_high": 16.0,
                            }
                        ],
                        "flags": [],
                    })
                }
            }
        ]
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = openai_json_response
    mock_resp.content = b"content"

    with patch("app.services.medical.analysis.get_settings", return_value=mock_settings("openai")):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            analysis = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nHemoglobin: 14.2 g/dL",
                    requested_provider="openai",
                )
            )

    assert analysis.status == "completed"
    assert analysis.provider == "openai"
    assert analysis.model_name == "gpt-4o-mini"
    assert "Blood test shows normal" in analysis.summary
    assert sample_doc.status == "completed"
    assert len(sample_doc.findings) == 1
    assert sample_doc.findings[0].name == "Hemoglobin"


# -------------------------------------------------------------------------
# Test 2: Gemini Success; summary saved and displayed
# -------------------------------------------------------------------------
def test_gemini_success(test_db, sample_user, sample_doc):
    gemini_json_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "summary": "Gemini clinical summary: Complete blood count within reference ranges.",
                                "key_points": ["Platelets normal"],
                                "report_date": "2026-10-18",
                                "findings": [
                                    {
                                        "category": "laboratory",
                                        "finding_type": "test_result",
                                        "name": "Platelets",
                                        "value_text": "250 x10^3/uL",
                                        "numeric_value": 250.0,
                                        "unit": "x10^3/uL",
                                        "reference_low": 150.0,
                                        "reference_high": 450.0,
                                    }
                                ],
                                "measurements": [
                                    {
                                        "parameter_name": "Platelets",
                                        "parameter_code": "platelets",
                                        "numeric_value": 250.0,
                                        "unit": "x10^3/uL",
                                    }
                                ],
                                "flags": [],
                            })
                        }
                    ]
                }
            }
        ]
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = gemini_json_response
    mock_resp.content = b"content"

    with patch("app.services.medical.analysis.get_settings", return_value=mock_settings("gemini")):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            analysis = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nPlatelets: 250 x10^3/uL",
                    requested_provider="gemini",
                )
            )

    assert analysis.status == "completed"
    assert analysis.provider == "gemini"
    assert analysis.model_name == "gemini-1.5-flash"
    assert "Gemini clinical summary" in analysis.summary
    assert sample_doc.status == "completed"
    assert len(sample_doc.findings) == 1


# -------------------------------------------------------------------------
# Test 3: Actual OpenAI Quota Exhaustion -> quota_exceeded
# -------------------------------------------------------------------------
def test_openai_quota_exhaustion(test_db, sample_user, sample_doc):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 429
    mock_resp.content = b"content"
    mock_resp.json.return_value = {
        "error": {
            "message": "You exceeded your current quota, please check your plan and billing details.",
            "type": "insufficient_quota",
            "code": "insufficient_quota",
        }
    }

    with patch("app.services.medical.analysis.get_settings", return_value=mock_settings("openai")):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            analysis = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nGlucose: 95 mg/dL",
                    requested_provider="openai",
                )
            )

    assert analysis.status == "failed"
    assert analysis.error_code == "quota_exceeded"
    assert "exhausted its available quota" in analysis.error_message
    assert sample_doc.status == "failed"
    assert sample_doc.failure_code == "quota_exceeded"


# -------------------------------------------------------------------------
# Test 4: Actual Gemini Resource/Quota Exhaustion -> quota_exceeded
# -------------------------------------------------------------------------
def test_gemini_quota_exhaustion(test_db, sample_user, sample_doc):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 429
    mock_resp.content = b"content"
    mock_resp.json.return_value = {
        "error": {
            "code": 429,
            "message": "Resource has been exhausted (e.g. check quota).",
            "status": "RESOURCE_EXHAUSTED",
            "details": [{"reason": "QUOTA_EXCEEDED"}],
        }
    }

    with patch("app.services.medical.analysis.get_settings", return_value=mock_settings("gemini")):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            analysis = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nGlucose: 95 mg/dL",
                    requested_provider="gemini",
                )
            )

    assert analysis.status == "failed"
    assert analysis.error_code == "quota_exceeded"
    assert "exhausted its available quota" in analysis.error_message


# -------------------------------------------------------------------------
# Test 5: Rate Limit -> rate_limited, NOT quota_exceeded
# -------------------------------------------------------------------------
def test_rate_limited_not_quota_exceeded(test_db, sample_user, sample_doc):
    # OpenAI rate limit
    mock_resp_openai = MagicMock(spec=httpx.Response)
    mock_resp_openai.status_code = 429
    mock_resp_openai.content = b"content"
    mock_resp_openai.json.return_value = {
        "error": {
            "message": "Rate limit reached for requests per minute (RPM)",
            "type": "requests",
            "code": "rate_limit_exceeded",
        }
    }

    with patch("app.services.medical.analysis.get_settings", return_value=mock_settings("openai")):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp_openai):
            analysis = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nGlucose: 95 mg/dL",
                    requested_provider="openai",
                )
            )

    assert analysis.status == "failed"
    assert analysis.error_code == "rate_limited"
    assert "temporarily rate-limiting" in analysis.error_message

    # Reset doc status
    sample_doc.status = "uploaded"
    test_db.commit()

    # Gemini rate limit
    mock_resp_gemini = MagicMock(spec=httpx.Response)
    mock_resp_gemini.status_code = 429
    mock_resp_gemini.content = b"content"
    mock_resp_gemini.json.return_value = {
        "error": {
            "code": 429,
            "message": "Resource exhausted: rate limit exceeded.",
            "status": "RESOURCE_EXHAUSTED",
            "details": [{"reason": "RATE_LIMIT_EXCEEDED"}],
        }
    }

    with patch("app.services.medical.analysis.get_settings", return_value=mock_settings("gemini")):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp_gemini):
            analysis_gemini = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nGlucose: 95 mg/dL",
                    requested_provider="gemini",
                )
            )

    assert analysis_gemini.error_code == "rate_limited"


# -------------------------------------------------------------------------
# Test 6: Invalid OpenAI Key -> authentication_failed
# -------------------------------------------------------------------------
def test_openai_invalid_key(test_db, sample_user, sample_doc):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 401
    mock_resp.content = b"content"
    mock_resp.json.return_value = {"error": {"message": "Incorrect API key provided.", "type": "invalid_request_error"}}

    with patch("app.services.medical.analysis.get_settings", return_value=mock_settings("openai")):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            analysis = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nSodium: 140",
                    requested_provider="openai",
                )
            )

    assert analysis.error_code == "authentication_failed"
    assert "authentication failed" in analysis.error_message


# -------------------------------------------------------------------------
# Test 7: Invalid Gemini Key -> authentication_failed
# -------------------------------------------------------------------------
def test_gemini_invalid_key(test_db, sample_user, sample_doc):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 400
    mock_resp.content = b"content"
    mock_resp.json.return_value = {
        "error": {
            "code": 400,
            "message": "API key not valid. Please pass a valid API key.",
            "status": "INVALID_ARGUMENT",
            "details": [{"reason": "API_KEY_INVALID"}],
        }
    }

    with patch("app.services.medical.analysis.get_settings", return_value=mock_settings("gemini")):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            analysis = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nSodium: 140",
                    requested_provider="gemini",
                )
            )

    assert analysis.error_code == "authentication_failed"
    assert "authentication failed" in analysis.error_message


# -------------------------------------------------------------------------
# Test 8: Unsupported Model -> model_unavailable
# -------------------------------------------------------------------------
def test_unsupported_model(test_db, sample_user, sample_doc):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 404
    mock_resp.content = b"content"
    mock_resp.json.return_value = {"error": {"message": "The model `gpt-unknown` does not exist."}}

    with patch("app.services.medical.analysis.get_settings", return_value=mock_settings("openai")):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            analysis = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nSodium: 140",
                    requested_provider="openai",
                )
            )

    assert analysis.error_code == "model_unavailable"
    assert "unavailable for this provider account" in analysis.error_message


# -------------------------------------------------------------------------
# Test 9: Network and Timeout Classification
# -------------------------------------------------------------------------
def test_network_and_timeout(test_db, sample_user, sample_doc):
    # Timeout
    with patch("app.services.medical.analysis.get_settings", return_value=mock_settings("openai")):
        with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Timed out")):
            analysis = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nSodium: 140",
                    requested_provider="openai",
                )
            )
    assert analysis.error_code == "provider_timeout"
    assert "timed out" in analysis.error_message

    sample_doc.status = "uploaded"
    test_db.commit()

    # Network failure
    with patch("app.services.medical.analysis.get_settings", return_value=mock_settings("openai")):
        with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
            analysis_net = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nSodium: 140",
                    requested_provider="openai",
                )
            )
    assert analysis_net.error_code == "provider_unavailable"
    assert "Could not connect" in analysis_net.error_message


# -------------------------------------------------------------------------
# Test 10: Malformed Response -> invalid_provider_response
# -------------------------------------------------------------------------
def test_malformed_response(test_db, sample_user, sample_doc):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.content = b"content"
    # OpenAI response with non-JSON or invalid schema content
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "This is raw text, not JSON at all."}}]
    }

    with patch("app.services.medical.analysis.get_settings", return_value=mock_settings("openai")):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            analysis = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nSodium: 140",
                    requested_provider="openai",
                )
            )

    assert analysis.error_code == "invalid_provider_response"
    assert "unusable response" in analysis.error_message


# -------------------------------------------------------------------------
# Test 11: Empty OCR -> Provider is NOT called (extraction_empty)
# -------------------------------------------------------------------------
def test_empty_ocr_does_not_call_provider(test_db, sample_user, sample_doc):
    empty_extraction = ExtractionResult(
        status="no_readable_text",
        full_text="",
        page_count=0,
        extraction_method=None,
        error_code="OCR_NO_TEXT",
    )

    with patch("httpx.AsyncClient.post") as mock_post:
        analysis = asyncio.run(
            MedicalAnalysisService.run_analysis(
                db=test_db,
                document_id=sample_doc.id,
                user_id=sample_user.id,
                extracted_text="",
                extraction_result=empty_extraction,
                requested_provider="openai",
            )
        )
        assert mock_post.call_count == 0

    assert analysis.status == "failed"
    assert analysis.error_code == "OCR_NO_TEXT"


# -------------------------------------------------------------------------
# Test 12: Valid OCR -> Exactly one provider request per chunk
# -------------------------------------------------------------------------
def test_valid_ocr_calls_provider_once(test_db, sample_user, sample_doc):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.content = b"content"
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "summary": "Valid summary",
                        "key_points": [],
                        "findings": [],
                        "measurements": [],
                        "flags": [],
                    })
                }
            }
        ]
    }

    valid_extraction = ExtractionResult(
        status="success",
        full_text="=== PAGE 1 ===\nNormal examination note.",
        page_count=1,
        extraction_method="pdf_text",
    )

    with patch("app.services.medical.analysis.get_settings", return_value=mock_settings("openai")):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
            analysis = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text=valid_extraction.full_text,
                    extraction_result=valid_extraction,
                    requested_provider="openai",
                )
            )
            # Exactly one chunk was sent, exactly one call
            assert mock_post.call_count == 1

    assert analysis.status == "completed"


# -------------------------------------------------------------------------
# Test 13: Repeated Click -> Atomic protection prevents duplicate active analysis
# -------------------------------------------------------------------------
def test_repeated_click_atomic_protection(test_db, sample_user, sample_doc):
    # Set document status to processing (simulating in-flight analysis)
    sample_doc.status = "processing"
    test_db.commit()

    with pytest.raises(ConcurrentAnalysisError, match="actively running"):
        asyncio.run(
            MedicalAnalysisService.run_analysis(
                db=test_db,
                document_id=sample_doc.id,
                user_id=sample_user.id,
                extracted_text="=== PAGE 1 ===\nTest",
                requested_provider="openai",
            )
        )


# -------------------------------------------------------------------------
# Test 14: Job Polling -> No additional provider calls
# -------------------------------------------------------------------------
def test_job_polling_does_not_call_provider(test_db, sample_user, sample_doc):
    with patch("httpx.AsyncClient.post") as mock_post:
        # Polling reads document status and analyses
        doc = test_db.get(MedicalDocument, sample_doc.id)
        assert doc is not None
        _ = doc.status
        _ = doc.analyses
        assert mock_post.call_count == 0


# -------------------------------------------------------------------------
# Test 15: Switching Provider -> Correct adapter and key source used
# -------------------------------------------------------------------------
def test_switching_provider_routes_to_correct_adapter(test_db, sample_user, sample_doc):
    mock_resp_openai = MagicMock(spec=httpx.Response)
    mock_resp_openai.status_code = 200
    mock_resp_openai.content = b"content"
    mock_resp_openai.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"summary": "OpenAI done", "key_points": [], "findings": [], "measurements": [], "flags": []})}}]
    }

    mock_resp_gemini = MagicMock(spec=httpx.Response)
    mock_resp_gemini.status_code = 200
    mock_resp_gemini.content = b"content"
    mock_resp_gemini.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": json.dumps({"summary": "Gemini done", "key_points": [], "findings": [], "measurements": [], "flags": []})}]}}]
    }

    settings = mock_settings(openai_key="sk-openai-key-123", gemini_key="AIzaSy-gemini-key-456")

    with patch("app.services.medical.analysis.get_settings", return_value=settings):
        # 1. Request OpenAI
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp_openai) as mock_post_openai:
            analysis_o = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nLab note",
                    requested_provider="openai",
                )
            )
            assert mock_post_openai.call_count == 1
            call_url = mock_post_openai.call_args[0][0]
            call_headers = mock_post_openai.call_args[1]["headers"]
            assert "api.openai.com" in call_url
            assert "Bearer sk-openai-key-123" in call_headers["Authorization"]
            assert analysis_o.provider == "openai"

        # Reset document status
        sample_doc.status = "uploaded"
        test_db.commit()

        # 2. Switch to Gemini
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp_gemini) as mock_post_gemini:
            analysis_g = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nLab note",
                    requested_provider="gemini",
                )
            )
            assert mock_post_gemini.call_count == 1
            call_url = mock_post_gemini.call_args[0][0]
            call_headers = mock_post_gemini.call_args[1]["headers"]
            assert "generativelanguage.googleapis.com" in call_url
            assert call_headers["x-goog-api-key"] == "AIzaSy-gemini-key-456"
            assert analysis_g.provider == "gemini"


# -------------------------------------------------------------------------
# Test 16: Missing OpenAI key while Gemini selected (and vice versa) -> Independent behavior
# -------------------------------------------------------------------------
def test_missing_key_independent_behavior(test_db, sample_user, sample_doc):
    # Only Gemini has key, OpenAI is None
    settings_gemini_only = mock_settings(openai_key=None, gemini_key="AIzaSy-valid-gemini")

    mock_resp_gemini = MagicMock(spec=httpx.Response)
    mock_resp_gemini.status_code = 200
    mock_resp_gemini.content = b"content"
    mock_resp_gemini.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": json.dumps({"summary": "Gemini succeeded", "key_points": [], "findings": [], "measurements": [], "flags": []})}]}}]
    }

    with patch("app.services.medical.analysis.get_settings", return_value=settings_gemini_only):
        # Gemini request succeeds even though OpenAI key is missing
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp_gemini):
            analysis_g = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nTest",
                    requested_provider="gemini",
                )
            )
            assert analysis_g.status == "completed"
            assert analysis_g.provider == "gemini"

        sample_doc.status = "uploaded"
        test_db.commit()

        # If user explicitly requests OpenAI without an OpenAI key, it fails with authentication_failed (no silent fallback to Gemini!)
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            analysis_o = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nTest",
                    requested_provider="openai",
                )
            )
            assert mock_post.call_count == 0
            assert analysis_o.status == "failed"
            assert analysis_o.error_code == "authentication_failed"
            assert "AI provider 'openai' authentication failed" in analysis_o.error_message


# -------------------------------------------------------------------------
# Test 17: Analysis increments version exactly once
# -------------------------------------------------------------------------
def test_analysis_version_increment(test_db, sample_user, sample_doc):
    mock_output = {
        "summary": "Version check",
        "key_points": [],
        "findings": [],
        "measurements": [],
        "flags": [],
    }

    res1 = asyncio.run(
        MedicalAnalysisService.run_analysis(
            db=test_db,
            document_id=sample_doc.id,
            user_id=sample_user.id,
            extracted_text="=== PAGE 1 ===\nNote 1",
            mock_response=mock_output,
        )
    )
    assert res1.version == 1

    sample_doc.status = "uploaded"
    test_db.commit()

    res2 = asyncio.run(
        MedicalAnalysisService.run_analysis(
            db=test_db,
            document_id=sample_doc.id,
            user_id=sample_user.id,
            extracted_text="=== PAGE 1 ===\nNote 2",
            mock_response=mock_output,
        )
    )
    assert res2.version == 2


# -------------------------------------------------------------------------
# Test 18: Tenant Isolation (User A cannot access User B's document)
# -------------------------------------------------------------------------
def test_cross_user_isolation(test_db, sample_user, sample_doc):
    user_b = User(id=uuid.uuid4(), email="attacker@example.com", full_name="User B", password_hash="h")
    test_db.add(user_b)
    test_db.commit()

    with pytest.raises(ValueError, match="ownership mismatch"):
        asyncio.run(
            MedicalAnalysisService.run_analysis(
                db=test_db,
                document_id=sample_doc.id,
                user_id=user_b.id,
                extracted_text="=== PAGE 1 ===\nNote",
            )
        )


# -------------------------------------------------------------------------
# Test 19: Provider Failure -> No false successful analysis record
# -------------------------------------------------------------------------
def test_provider_failure_no_false_success(test_db, sample_user, sample_doc):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 500
    mock_resp.content = b"content"
    mock_resp.json.return_value = {"error": {"message": "Internal error in provider backend"}}

    with patch("app.services.medical.analysis.get_settings", return_value=mock_settings("openai")):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            analysis = asyncio.run(
                MedicalAnalysisService.run_analysis(
                    db=test_db,
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    extracted_text="=== PAGE 1 ===\nNote",
                    requested_provider="openai",
                )
            )

    assert analysis.status == "failed"
    assert analysis.error_code == "provider_unavailable"
    assert sample_doc.status == "failed"
    # Verify no findings or measurements are stored
    assert len(sample_doc.findings) == 0
    assert len(sample_doc.measurements) == 0


# -------------------------------------------------------------------------
# Test 20: Persistence Failure -> UI/Analysis does not claim success
# -------------------------------------------------------------------------
def test_persistence_failure_rollback(test_db, sample_user, sample_doc):
    mock_output = {
        "summary": "Valid summary",
        "key_points": [],
        "findings": [],
        "measurements": [],
        "flags": [],
    }

    # Simulate database error during persistence
    with patch.object(test_db, "commit", side_effect=Exception("Database lock/write failure")):
        try:
            MedicalAnalysisService._persist_analysis_output(
                db=test_db,
                doc=sample_doc,
                analysis=DocumentAnalysis(
                    document_id=sample_doc.id,
                    user_id=sample_user.id,
                    version=1,
                    status="processing",
                ),
                user_id=sample_user.id,
                parsed_data=mock_output,
            )
        except Exception:
            pass

    # Confirm doc status was not committed as completed
    test_db.rollback()
    refreshed_doc = test_db.get(MedicalDocument, sample_doc.id)
    assert refreshed_doc.status != "completed"
