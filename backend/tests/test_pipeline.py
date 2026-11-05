"""
Unit and integration tests for the JohnnySummUP AI/ML Pipeline and API.
"""

import io
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.ai_pipeline.parameter_catalog import map_parameter_name
from app.ai_pipeline.medical_extractor import parse_numeric, parse_reference_range, ExtractedRange, ExtractedMeasurementData
from app.ai_pipeline.rule_evaluator import evaluate_measurement_range, evaluate_document_rules
from app.ai_pipeline.output_validator import validate_summary_output


client = TestClient(app)


def test_parameter_catalog_mapping():
    """Verify raw lab labels map accurately to canonical parameters."""
    hb = map_parameter_name("Hemoglobin")
    assert hb is not None
    assert hb.parameter_code == "hemoglobin"
    assert hb.canonical_name == "Hemoglobin"

    wbc = map_parameter_name("Total Leukocyte Count (TLC)")
    assert wbc is not None
    assert wbc.parameter_code == "wbc"

    fbs = map_parameter_name("Fasting Blood Sugar")
    assert fbs is not None
    assert fbs.parameter_code == "fasting_glucose"

    unmapped = map_parameter_name("XYZ Unknown Test 123")
    assert unmapped is None


def test_reference_range_parsing():
    """Verify range parsing handles two-sided and one-sided bounds."""
    r1 = parse_reference_range("13.0 - 17.0 g/dL")
    assert r1 is not None
    assert r1.low == 13.0
    assert r1.high == 17.0

    r2 = parse_reference_range("< 200 mg/dL")
    assert r2 is not None
    assert r2.high == 200.0
    assert r2.low is None

    r3 = parse_reference_range("> 50")
    assert r3 is not None
    assert r3.low == 50.0


def test_deterministic_range_evaluation():
    """
    Test non-negotiable rule:
    Range status must be calculated deterministically against the source report interval.
    """
    # Normal / within range
    assert evaluate_measurement_range(14.5, 13.0, 17.0) == "within_range"

    # Below range
    assert evaluate_measurement_range(12.4, 13.0, 17.0) == "below_range"

    # Above range
    assert evaluate_measurement_range(18.2, 13.0, 17.0) == "above_range"

    # Missing interval -> unknown (never invent universal ranges)
    assert evaluate_measurement_range(14.5, None, None) == "unknown"


def test_output_validator_safety():
    """Verify safety validator catches prohibited diagnostic phrases."""
    valid_summary = {
        "overview": "This is a laboratory report with 5 extracted measurements.",
        "keyPoints": [{"text": "Hemoglobin is below reference range.", "evidenceIds": ["ev_1"]}],
        "limitations": ["Review with physician."],
        "questionsForClinician": ["What does this mean?"],
        "safetyNotice": "This is an informational explanation, not a medical diagnosis."
    }
    is_valid, errs = validate_summary_output(valid_summary)
    assert is_valid is True

    unsafe_summary = {
        "overview": "You are diagnosed with severe anemia.",
        "keyPoints": [],
        "limitations": [],
        "questionsForClinician": [],
        "safetyNotice": "None"
    }
    is_valid_unsafe, errs_unsafe = validate_summary_output(unsafe_summary)
    assert is_valid_unsafe is False
    assert any("prohibited diagnostic" in e for e in errs_unsafe)


def test_auth_and_user_lifecycle():
    """Verify user registration, login, profile fetch, and dashboard flow."""
    unique_email = f"test_{int(datetime.now().timestamp())}@example.com"
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "StrongPassword123!",
            "fullName": "Jane Doe",
        },
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["success"] is True
    token = reg_data["data"]["tokens"]["accessToken"]

    # Fetch /me
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["data"]["email"] == unique_email
    assert me_res.json()["data"]["fullName"] == "Jane Doe"

    # Fetch dashboard stats
    dash_res = client.get(
        "/api/v1/medical/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dash_res.status_code == 200
    assert dash_res.json()["data"]["reportCount"] == 0
