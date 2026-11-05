"""
Evidence-grounded medical summarizer for JohnnySummUP V1.
Generates cautious, plain-language summaries strictly constrained
to supplied evidence. Never diagnoses, prescribes, or invents values.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from app.ai_pipeline.medical_extractor import ExtractedMeasurementData, ExtractedPrescriptionItemData
from app.ai_pipeline.rule_evaluator import FindingCandidate
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class KeyPoint:
    text: str
    evidenceIds: List[str]
    category: str = "measurement_explanation"


@dataclass
class StructuredSummaryPayload:
    overview: str
    keyPoints: List[KeyPoint] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    questionsForClinician: List[str] = field(default_factory=list)
    safetyNotice: str = (
        "This is an informational explanation, not a medical diagnosis or treatment plan. "
        "Always consult a qualified healthcare professional regarding test results or medical conditions."
    )


def generate_local_grounded_summary(
    document_type: str,
    test_date_str: Optional[str],
    facility: Optional[str],
    measurements: List[ExtractedMeasurementData],
    calculated_statuses: List[str],
    findings: List[FindingCandidate],
    prescriptions: List[ExtractedPrescriptionItemData],
) -> StructuredSummaryPayload:
    """
    Deterministically generates an evidence-grounded summary adhering
    strictly to the V1 AI/ML Technical Specification schema and non-negotiables.
    """
    total_count = len(measurements)
    outside_range = [f for f in findings if f.finding_type in ("below_report_range", "above_report_range")]
    flagged = [f for f in findings if f.finding_type == "source_flagged"]
    needs_review = [f for f in findings if f.finding_type == "needs_review"]

    type_display = document_type.replace("_", " ").title()
    fac_str = f" from {facility}" if facility else ""
    date_str = f" dated {test_date_str}" if test_date_str else ""

    if document_type == "prescription":
        overview = (
            f"This is a {type_display}{fac_str}{date_str} containing "
            f"{len(prescriptions)} listed medication instruction(s)."
        )
    else:
        overview = (
            f"This is a {type_display}{fac_str}{date_str} with {total_count} extracted "
            f"measurement(s). {len(outside_range)} result(s) are outside the reference "
            f"intervals printed on this specific report."
        )

    key_points: List[KeyPoint] = []

    # 1. Add key points for findings outside range
    for idx, f in enumerate(outside_range):
        ev_id = f"ev_range_{idx+1}"
        key_points.append(KeyPoint(
            text=f.explanation,
            evidenceIds=[ev_id],
            category="out_of_range_finding",
        ))

    # 2. Add normal/within range points if any
    within_count = sum(1 for s in calculated_statuses if s == "within_range")
    if within_count > 0:
        key_points.append(KeyPoint(
            text=f"{within_count} measurement(s) fall within the reference intervals stated on this report.",
            evidenceIds=["ev_normal"],
            category="within_range_summary",
        ))

    # 3. Add prescription items if any
    for p_idx, rx in enumerate(prescriptions):
        instr = f" ({rx.instructions_text})" if rx.instructions_text else ""
        key_points.append(KeyPoint(
            text=f"Medication: {rx.medicine_name_raw} {rx.strength_text or ''}{instr}".strip(),
            evidenceIds=[f"ev_rx_{p_idx+1}"],
            category="prescription_item",
        ))

    # Limitations
    limitations: List[str] = [
        "Results must be reviewed against the original uploaded report.",
        "Reference intervals are specific to the issuing laboratory and cannot be generalized.",
    ]
    if needs_review:
        limitations.append(
            f"{len(needs_review)} field(s) had lower extraction confidence and require verification."
        )

    # Questions for clinician
    questions: List[str] = [
        "What do these results mean in the context of my current health history?",
    ]
    if outside_range:
        tested_names = ", ".join(
            set(f.title.split(" is ")[0] for f in outside_range[:3])
        )
        questions.append(
            f"Are any follow-up tests or lifestyle considerations advised for {tested_names}?"
        )
    if prescriptions:
        questions.append(
            "What is the recommended timing and expected duration for the prescribed medications?"
        )

    return StructuredSummaryPayload(
        overview=overview,
        keyPoints=key_points,
        limitations=limitations,
        questionsForClinician=questions,
    )


async def generate_summary(
    document_type: str,
    test_date_str: Optional[str],
    facility: Optional[str],
    measurements: List[ExtractedMeasurementData],
    calculated_statuses: List[str],
    findings: List[FindingCandidate],
    prescriptions: List[ExtractedPrescriptionItemData],
) -> Dict[str, Any]:
    """
    Generates summary using configured LLM provider or reliable local grounded generator.
    """
    # If external provider is configured and available (e.g. OpenAI or Gemini):
    if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            # Build strictly constrained prompt
            prompt = (
                "You are an informational medical document summarizer. "
                "DO NOT diagnose, DO NOT predict health outcomes, DO NOT prescribe. "
                "Summarize these verified facts and return pure JSON with keys: "
                "overview, keyPoints (list of text, evidenceIds, category), limitations, questionsForClinician, safetyNotice.\n"
                f"Data: {json.dumps({'type': document_type, 'measurements': [asdict(m) for m in measurements[:15]]})}"
            )
            response = await model.generate_content_async(prompt)
            data = json.loads(response.text)
            return data
        except Exception as exc:
            logger.warning(f"External LLM generation failed, falling back to local engine: {exc}")

    # Deterministic evidence-grounded generator
    summary_obj = generate_local_grounded_summary(
        document_type=document_type,
        test_date_str=test_date_str,
        facility=facility,
        measurements=measurements,
        calculated_statuses=calculated_statuses,
        findings=findings,
        prescriptions=prescriptions,
    )

    return {
        "overview": summary_obj.overview,
        "keyPoints": [asdict(kp) for kp in summary_obj.keyPoints],
        "limitations": summary_obj.limitations,
        "questionsForClinician": summary_obj.questionsForClinician,
        "safetyNotice": summary_obj.safetyNotice,
    }

