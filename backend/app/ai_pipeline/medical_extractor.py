"""
Medical information extraction engine for JohnnySummUP V1.
Extracts structured measurements, reference intervals, source flags,
dates, and prescriptions with exact source provenance snippets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

from app.ai_pipeline.parameter_catalog import map_parameter_name
from app.ai_pipeline.pdf_parser import ExtractedDocumentText


@dataclass
class ExtractedRange:
    raw_text: str
    low: Optional[float] = None
    high: Optional[float] = None


@dataclass
class ExtractedMeasurementData:
    parameter_name_raw: str
    parameter_code: Optional[str]
    parameter_name_display: Optional[str]
    raw_value_text: str
    numeric_value: Optional[float]
    qualitative_value: Optional[str]
    source_unit: Optional[str]
    reference_range: Optional[ExtractedRange]
    source_flag: Optional[str]
    confidence: float
    source_page: int
    source_snippet: str


@dataclass
class ExtractedPrescriptionItemData:
    medicine_name_raw: str
    strength_text: Optional[str] = None
    dose_text: Optional[str] = None
    route_text: Optional[str] = None
    frequency_text: Optional[str] = None
    duration_text: Optional[str] = None
    instructions_text: Optional[str] = None
    confidence: float = 0.90
    source_page: int = 1
    source_snippet: str = ""


@dataclass
class ExtractionResult:
    document_type: str  # lab_report, prescription, imaging_report, discharge_summary, other
    test_date: Optional[datetime]
    facility_name: Optional[str]
    provider_name: Optional[str]
    measurements: List[ExtractedMeasurementData] = field(default_factory=list)
    prescription_items: List[ExtractedPrescriptionItemData] = field(default_factory=list)
    classification_confidence: float = 0.95


# ── Regular expressions for clinical extraction ─────────────────────────────

# Reference interval pattern: "13.0 - 17.0", "13.0 to 17.0", "< 200", "> 50", "0.7-1.3"
RANGE_BOUNDS_REGEX = re.compile(
    r"(?:(?:ref(?:erence)?\s*(?:range|interval)?|normal)?[:\s]*)?"
    r"(?:([0-9]+(?:\.[0-9]+)?)\s*(?:-|–|to)\s*([0-9]+(?:\.[0-9]+)?)"
    r"|([<>≤≥])\s*([0-9]+(?:\.[0-9]+)?))",
    re.IGNORECASE,
)

# Date regex (e.g. 2026-10-28, 28/10/2026, 28-Oct-2026, October 28, 2026)
DATE_REGEX = re.compile(
    r"(?:(?:collected|reported|test date|date of service|date)[:\s]*)?"
    r"(\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})\b)",
    re.IGNORECASE,
)

# Common lab line formats:
# "Hemoglobin 12.4 g/dL 13.0 - 17.0 LOW"
# "Glucose, Fasting : 110 mg/dL (70 - 99) HIGH"
# "TSH 3.45 uIU/mL 0.4 - 4.5"
MEASUREMENT_LINE_REGEX = re.compile(
    r"^([A-Za-z0-9\(\)\-,\.\s\+/]+?)\s*[:\s|]\s*"  # test label
    r"([<>]?\s*[0-9]+(?:\.[0-9]+)?|[A-Za-z]+)\s+"  # value
    r"([%A-Za-z0-9/\^µ\*\-]+)?\s*"                 # unit
    r"(?:[\[\(]?([0-9\.\s\-–to<>≤≥]+)[\]\)]?)?\s*"  # ref range
    r"([*]|\b(?:HIGH|LOW|ABNORMAL|NORMAL|CRITICAL|POSITIVE|NEGATIVE|H|L)\b)?\s*$",
    re.IGNORECASE,
)


def parse_reference_range(text: str) -> Optional[ExtractedRange]:
    """Extract numeric bounds from a reference range string."""
    if not text:
        return None
    match = RANGE_BOUNDS_REGEX.search(text)
    if not match:
        return ExtractedRange(raw_text=text.strip())

    low_val, high_val, operator, one_sided_val = match.groups()
    if low_val is not None and high_val is not None:
        try:
            return ExtractedRange(
                raw_text=text.strip(),
                low=float(low_val),
                high=float(high_val),
            )
        except ValueError:
            return ExtractedRange(raw_text=text.strip())
    elif operator and one_sided_val:
        try:
            val = float(one_sided_val)
            if operator in ("<", "≤"):
                return ExtractedRange(raw_text=text.strip(), high=val)
            else:
                return ExtractedRange(raw_text=text.strip(), low=val)
        except ValueError:
            return ExtractedRange(raw_text=text.strip())
    return ExtractedRange(raw_text=text.strip())


def parse_numeric(val_str: str) -> Tuple[Optional[float], Optional[str]]:
    """Cleanly parse numeric value or qualitative string."""
    cleaned = val_str.strip()
    try:
        # Strip leading comparison symbols if any
        num_str = re.sub(r"^[<>=≤≥]\s*", "", cleaned)
        return float(num_str), None
    except ValueError:
        return None, cleaned


def parse_date(date_str: str) -> Optional[datetime]:
    """Try parsing date using dateutil or common ISO formats."""
    from dateutil import parser
    try:
        return parser.parse(date_str, fuzzy=True)
    except Exception:
        return None


def classify_document(full_text: str) -> Tuple[str, float]:
    """Heuristic classifier among supported medical document types."""
    lower = full_text.lower()

    rx_indicators = ["rx", "prescription", "sig:", "take 1 tablet", "capsule", "dosage", "refills", "dispense"]
    rx_score = sum(1 for ind in rx_indicators if ind in lower)

    imaging_indicators = ["mri", "x-ray", "ct scan", "ultrasound", "radiology", "impression:", "findings:", "technique:"]
    img_score = sum(1 for ind in imaging_indicators if ind in lower)

    discharge_indicators = ["discharge summary", "hospital admission", "discharge date", "hospital course", "chief complaint"]
    ds_score = sum(1 for ind in discharge_indicators if ind in lower)

    lab_indicators = ["specimen", "reference range", "reference interval", "result", "units", "haemoglobin", "hemoglobin", "wbc", "platelet", "lipid profile", "fasting"]
    lab_score = sum(1 for ind in lab_indicators if ind in lower)

    scores = [
        ("lab_report", lab_score * 1.5),
        ("prescription", rx_score * 1.8),
        ("imaging_report", img_score * 1.5),
        ("discharge_summary", ds_score * 1.6),
    ]
    scores.sort(key=lambda s: s[1], reverse=True)
    best_type, best_score = scores[0]

    if best_score > 2.0:
        return best_type, min(0.98, 0.75 + (best_score * 0.05))
    return "lab_report", 0.70  # Default to lab_report in V1


def extract_medical_data(doc_text: ExtractedDocumentText) -> ExtractionResult:
    """
    Main extraction function.
    Parses pages and lines into typed measurements, source references,
    and prescriptions.
    """
    full_text = doc_text.full_text
    doc_type, doc_conf = classify_document(full_text)

    # 1. Detect test date
    detected_date: Optional[datetime] = None
    date_match = DATE_REGEX.search(full_text)
    if date_match:
        detected_date = parse_date(date_match.group(1))

    # 2. Detect lab/facility/provider name
    facility_name: Optional[str] = None
    provider_name: Optional[str] = None
    for line in full_text.split("\n")[:15]:
        line_clean = line.strip()
        if any(kw in line_clean.lower() for kw in ["hospital", "diagnostic", "laboratory", "labs", "clinic", "pathology"]):
            facility_name = line_clean[:120]
            break
        if any(kw in line_clean.lower() for kw in ["dr.", "doctor", "physician", "m.d."]):
            provider_name = line_clean[:120]

    measurements: List[ExtractedMeasurementData] = []
    prescriptions: List[ExtractedPrescriptionItemData] = []

    # 3. Line by line parsing across pages
    for page in doc_text.pages:
        lines = page.text.split("\n")
        for line in lines:
            line_str = line.strip()
            if not line_str or len(line_str) < 4:
                continue

            # Check for prescription instructions
            if doc_type == "prescription" or any(kw in line_str.lower() for kw in ["mg", "tablet", "cap", "od", "bd", "tid", "qid", "daily"]):
                # Simple medication pattern: "Amoxicillin 500mg 1 tab PO TID for 7 days"
                rx_match = re.match(r"^([A-Za-z0-9\s\-]+?)\s+(\d+\s*(?:mg|mcg|g|ml))\s*(.*?)$", line_str, re.IGNORECASE)
                if rx_match:
                    med_name, strength, instr = rx_match.groups()
                    if len(med_name.strip()) > 2 and not any(kw in med_name.lower() for kw in ["page", "date", "dr", "patient", "name"]):
                        prescriptions.append(ExtractedPrescriptionItemData(
                            medicine_name_raw=med_name.strip(),
                            strength_text=strength.strip(),
                            instructions_text=instr.strip() if instr else None,
                            source_page=page.page_number,
                            source_snippet=line_str,
                            confidence=0.92,
                        ))

            # Check for laboratory measurement pattern
            # Strategy: look for line containing numbers and units or tab/space separated columns
            # Example: "Hemoglobin 12.4 g/dL 13.0 - 17.0"
            tokens = re.split(r"\s{2,}|\t|\|", line_str)
            if len(tokens) >= 2:
                # Columnar format
                label = tokens[0].strip()
                val_candidate = tokens[1].strip()
                unit_candidate = tokens[2].strip() if len(tokens) > 2 else ""
                ref_candidate = tokens[3].strip() if len(tokens) > 3 else ""
                flag_candidate = tokens[4].strip() if len(tokens) > 4 else None
            else:
                # Fallback to regex
                m = MEASUREMENT_LINE_REGEX.match(line_str)
                if m:
                    label, val_candidate, unit_candidate, ref_candidate, flag_candidate = m.groups()
                else:
                    label, val_candidate, unit_candidate, ref_candidate, flag_candidate = None, None, None, None, None

            if label and val_candidate:
                num_val, qual_val = parse_numeric(val_candidate)
                # Filter out obvious false positives like headers or page numbers
                if label.lower() in ["page", "date", "age", "sex", "gender", "id", "ref by", "referred by", "patient"]:
                    continue

                param_def = map_parameter_name(label)
                ref_range = parse_reference_range(ref_candidate) if ref_candidate else None

                # Clean unit candidate if ref range was mixed into it
                if unit_candidate and ("-" in unit_candidate or any(c in unit_candidate for c in "0123456789")):
                    # Likely reference range accidentally caught in unit
                    if not ref_range:
                        ref_range = parse_reference_range(unit_candidate)
                    unit_candidate = None

                measurements.append(ExtractedMeasurementData(
                    parameter_name_raw=label.strip(),
                    parameter_code=param_def.parameter_code if param_def else None,
                    parameter_name_display=param_def.canonical_name if param_def else label.strip(),
                    raw_value_text=val_candidate.strip(),
                    numeric_value=num_val,
                    qualitative_value=qual_val,
                    source_unit=unit_candidate.strip() if unit_candidate else None,
                    reference_range=ref_range,
                    source_flag=flag_candidate.strip().upper() if flag_candidate else None,
                    confidence=0.96 if param_def else 0.88,
                    source_page=page.page_number,
                    source_snippet=line_str,
                ))

    return ExtractionResult(
        document_type=doc_type,
        test_date=detected_date,
        facility_name=facility_name,
        provider_name=provider_name,
        measurements=measurements,
        prescription_items=prescriptions,
        classification_confidence=doc_conf,
    )

