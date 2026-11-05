"""
Output Validator for JohnnySummUP V1.
Validates AI/ML extraction and summary outputs against schema and safety constraints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# Banned clinical advice phrases that must never be presented as fact
FORBIDDEN_PHRASES = [
    "you have cancer",
    "you are diagnosed with",
    "take this medication",
    "stop taking",
    "you will develop",
    "curable with",
    "definitive diagnosis",
]


def validate_summary_output(summary_dict: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates that a summary contains all required keys and complies with medical safety.
    Returns (is_valid, validation_errors).
    """
    errors: List[str] = []

    required_keys = ["overview", "keyPoints", "limitations", "questionsForClinician", "safetyNotice"]
    for key in required_keys:
        if key not in summary_dict:
            errors.append(f"Missing required summary key: '{key}'")

    overview_text = summary_dict.get("overview", "")
    if not overview_text or len(overview_text.strip()) < 10:
        errors.append("Summary overview is empty or inadequate.")

    # Check for forbidden diagnoses or prescriptive claims
    full_text_to_check = (
        overview_text + " " + " ".join(kp.get("text", "") for kp in summary_dict.get("keyPoints", []))
    ).lower()

    for phrase in FORBIDDEN_PHRASES:
        if phrase in full_text_to_check:
            errors.append(f"Summary contains prohibited diagnostic/prescriptive phrase: '{phrase}'")

    # Enforce safety disclaimer presence
    safety_notice = summary_dict.get("safetyNotice", "")
    if not safety_notice or "informational" not in safety_notice.lower():
        summary_dict["safetyNotice"] = (
            "This is an informational explanation, not a medical diagnosis or treatment plan. "
            "Always consult a qualified healthcare professional regarding test results or medical conditions."
        )

    return (len(errors) == 0, errors)

