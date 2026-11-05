"""
Deterministic Rule Evaluator for JohnnySummUP V1.
Evaluates numeric measurements strictly against the reference interval
printed on that specific source report. Never applies universal ranges.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.ai_pipeline.medical_extractor import ExtractedMeasurementData


@dataclass
class FindingCandidate:
    finding_type: str  # below_report_range, above_report_range, source_flagged, needs_review
    title: str
    explanation: str
    rule_code: str
    measurement_ref_idx: int
    source_page: int
    source_snippet: str


@dataclass
class EvaluationResult:
    calculated_statuses: List[str]  # within_range, below_range, above_range, unknown
    findings: List[FindingCandidate]


def evaluate_measurement_range(
    numeric_value: Optional[float],
    ref_low: Optional[float],
    ref_high: Optional[float],
) -> str:
    """
    Deterministic range status calculation.
    """
    if numeric_value is None:
        return "unknown"

    if ref_low is not None and numeric_value < ref_low:
        return "below_range"
    if ref_high is not None and numeric_value > ref_high:
        return "above_range"

    if ref_low is not None or ref_high is not None:
        return "within_range"

    return "unknown"  # No usable reference interval on this report


def evaluate_document_rules(measurements: List[ExtractedMeasurementData]) -> EvaluationResult:
    """
    Run deterministic rules on all extracted measurements and generate evidence-linked findings.
    """
    statuses: List[str] = []
    findings: List[FindingCandidate] = []

    for idx, m in enumerate(measurements):
        ref_low = m.reference_range.low if m.reference_range else None
        ref_high = m.reference_range.high if m.reference_range else None

        status = evaluate_measurement_range(m.numeric_value, ref_low, ref_high)
        statuses.append(status)

        name = m.parameter_name_display or m.parameter_name_raw
        unit_str = f" {m.source_unit}" if m.source_unit else ""

        # Finding: below range
        if status == "below_range":
            findings.append(FindingCandidate(
                finding_type="below_report_range",
                title=f"{name} is below report reference range",
                explanation=(
                    f"The extracted value of {m.raw_value_text}{unit_str} is below the lower reference "
                    f"bound of {ref_low}{unit_str} printed on this report."
                ),
                rule_code="RR_BELOW",
                measurement_ref_idx=idx,
                source_page=m.source_page,
                source_snippet=m.source_snippet,
            ))

        # Finding: above range
        elif status == "above_range":
            findings.append(FindingCandidate(
                finding_type="above_report_range",
                title=f"{name} is above report reference range",
                explanation=(
                    f"The extracted value of {m.raw_value_text}{unit_str} is above the upper reference "
                    f"bound of {ref_high}{unit_str} printed on this report."
                ),
                rule_code="RR_ABOVE",
                measurement_ref_idx=idx,
                source_page=m.source_page,
                source_snippet=m.source_snippet,
            ))

        # Finding: lab source flag (e.g. HIGH, LOW, *)
        if m.source_flag and m.source_flag in ["HIGH", "LOW", "ABNORMAL", "POSITIVE", "CRITICAL", "H", "L", "*"]:
            if status not in ["below_range", "above_range"]:  # avoid redundant duplicate if already flagged
                findings.append(FindingCandidate(
                    finding_type="source_flagged",
                    title=f"{name} was marked as '{m.source_flag}' by the laboratory",
                    explanation=f"The source laboratory explicitly marked this result as '{m.source_flag}'.",
                    rule_code="SRC_FLAG",
                    measurement_ref_idx=idx,
                    source_page=m.source_page,
                    source_snippet=m.source_snippet,
                ))

        # Finding: needs review if confidence < 0.85 or numeric parsing failed on key measurement
        if m.confidence < 0.85:
            findings.append(FindingCandidate(
                finding_type="needs_review",
                title=f"Review recommended for {name}",
                explanation=(
                    f"Extraction confidence ({int(m.confidence * 100)}%) is below standard threshold. "
                    f"Please verify against the original document."
                ),
                rule_code="CONF_LOW",
                measurement_ref_idx=idx,
                source_page=m.source_page,
                source_snippet=m.source_snippet,
            ))

    return EvaluationResult(
        calculated_statuses=statuses,
        findings=findings,
    )

