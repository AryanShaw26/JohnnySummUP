"""
Health analytics, dashboard aggregation, and longitudinal trend comparison.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai_pipeline.parameter_catalog import PARAMETER_CATALOG
from app.core.errors import ForbiddenError, NotFoundError
from app.models.finding import MedicalFinding
from app.models.measurement import ExtractedMeasurement
from app.models.medical_document import MedicalDocument
from app.schemas.analytics import (
    AlignedMeasurementRow,
    DashboardOverviewData,
    TrackedParameterPreview,
    TrendPointData,
    TrendResponseData,
)


async def get_dashboard_overview(db: AsyncSession, user_id: UUID) -> Dict[str, Any]:
    """
    Computes dashboard summary counts, recent activity, and tracked parameter previews.
    NO health score is computed (PRD non-negotiable).
    """
    # 1. Total document count
    docs_stmt = select(MedicalDocument).where(
        MedicalDocument.user_id == user_id,
        MedicalDocument.deleted_at.is_(None),
    )
    docs_res = await db.execute(docs_stmt.order_by(desc(MedicalDocument.created_at)))
    docs = docs_res.scalars().all()

    report_count = len(docs)
    analysed_count = sum(1 for d in docs if d.status == "completed")
    needs_review_count = sum(1 for d in docs if d.status == "needs_review")

    # 2. Recent documents with counts
    recent_docs: List[Dict[str, Any]] = []
    for d in docs[:5]:
        recent_docs.append({
            "id": d.id,
            "original_filename": d.original_filename,
            "document_title": d.document_title or d.original_filename,
            "document_type": d.document_type,
            "document_date": d.document_date,
            "created_at": d.created_at,
            "status": d.status,
            "page_count": d.page_count,
            "measurementCount": 0,
            "findingCount": 0,
        })

    # 3. Recent findings
    findings_stmt = (
        select(MedicalFinding)
        .join(MedicalDocument, MedicalFinding.document_id == MedicalDocument.id)
        .where(MedicalDocument.user_id == user_id)
        .order_by(desc(MedicalFinding.created_at))
        .limit(5)
    )
    findings_res = await db.execute(findings_stmt)
    findings = findings_res.scalars().all()

    recent_findings: List[Dict[str, Any]] = []
    for f in findings:
        recent_findings.append({
            "id": str(f.id),
            "documentId": str(f.document_id),
            "findingType": f.finding_type,
            "title": f.title,
            "explanation": f.explanation,
            "evidence": f.evidence_reference or [],
            "reviewStatus": f.review_status,
            "createdAt": f.created_at.isoformat() if f.created_at else None,
        })

    # 4. Parameter previews
    meas_stmt = (
        select(ExtractedMeasurement)
        .join(MedicalDocument, ExtractedMeasurement.document_id == MedicalDocument.id)
        .where(
            MedicalDocument.user_id == user_id,
            ExtractedMeasurement.parameter_code.isnot(None),
        )
        .order_by(desc(ExtractedMeasurement.created_at))
    )
    meas_res = await db.execute(meas_stmt)
    measurements = meas_res.scalars().all()

    # Group by parameter_code
    grouped: Dict[str, List[ExtractedMeasurement]] = {}
    for m in measurements:
        if m.parameter_code:
            grouped.setdefault(m.parameter_code, []).append(m)

    parameter_previews: List[Dict[str, Any]] = []
    for code, items in grouped.items():
        cat_info = PARAMETER_CATALOG.get(code)
        latest = items[0]
        parameter_previews.append({
            "parameterCode": code,
            "displayName": cat_info.canonical_name if cat_info else (latest.parameter_name_display or latest.parameter_name_raw),
            "category": cat_info.category if cat_info else "General",
            "unit": latest.source_unit or "",
            "readingCount": len(items),
            "latestValue": latest.raw_value_text,
            "latestStatus": latest.calculated_range_status,
            "latestDate": latest.test_date or latest.created_at,
        })

    return {
        "reportCount": report_count,
        "analysedCount": analysed_count,
        "needsReviewCount": needs_review_count,
        "trackedParameterCount": len(grouped),
        "recentDocuments": recent_docs,
        "recentFindings": recent_findings,
        "trackedParameterPreviews": parameter_previews,
    }


async def get_parameter_trends(
    db: AsyncSession,
    user_id: UUID,
    parameter_code: str,
) -> Dict[str, Any]:
    """
    Retrieves longitudinal points for a parameter with comparability check.
    Preserves per-reading reference range bounds.
    """
    stmt = (
        select(ExtractedMeasurement, MedicalDocument.document_title, MedicalDocument.original_filename)
        .join(MedicalDocument, ExtractedMeasurement.document_id == MedicalDocument.id)
        .where(
            MedicalDocument.user_id == user_id,
            MedicalDocument.deleted_at.is_(None),
            ExtractedMeasurement.parameter_code == parameter_code,
            ExtractedMeasurement.numeric_value.isnot(None),
        )
        .order_by(ExtractedMeasurement.test_date.asc().nulls_last(), ExtractedMeasurement.created_at.asc())
    )
    res = await db.execute(stmt)
    rows = res.all()

    cat_def = PARAMETER_CATALOG.get(parameter_code)
    display_name = cat_def.canonical_name if cat_def else parameter_code.replace("_", " ").title()

    if not rows:
        return {
            "parameterCode": parameter_code,
            "displayName": display_name,
            "unit": "",
            "comparabilityStatus": "insufficient_data",
            "explanation": "No numeric historical readings recorded yet for this parameter.",
            "points": [],
        }

    # Verify unit compatibility
    units_used = set((m.source_unit or "").lower() for m, _, _ in rows)
    is_compatible = len(units_used) <= 1
    comp_status = "comparable" if len(rows) >= 2 and is_compatible else ("incompatible_units" if not is_compatible else "insufficient_data")

    explanation = (
        "Historical readings are comparable."
        if comp_status == "comparable"
        else ("Measurements use different units across reports; direct visual trend is withheld." if not is_compatible else "At least two readings needed to establish a trend.")
    )

    primary_unit = rows[0][0].source_unit or ""
    points: List[Dict[str, Any]] = []

    for m, doc_title, orig_name in rows:
        date_val = m.test_date or m.created_at
        date_str = date_val.strftime("%Y-%m-%d") if date_val else "Unknown"

        points.append({
            "measurementId": str(m.id),
            "documentId": str(m.document_id),
            "documentTitle": doc_title or orig_name,
            "testDate": date_str,
            "value": m.numeric_value,
            "rawValue": m.raw_value_text,
            "unit": m.source_unit or primary_unit,
            "referenceLow": m.reference_low,
            "referenceHigh": m.reference_high,
            "calculatedRangeStatus": m.calculated_range_status,
            "reviewStatus": m.review_status,
        })

    return {
        "parameterCode": parameter_code,
        "displayName": display_name,
        "unit": primary_unit,
        "comparabilityStatus": comp_status,
        "explanation": explanation,
        "points": points,
    }


async def compare_documents(
    db: AsyncSession,
    user_id: UUID,
    document_ids: List[UUID],
) -> Dict[str, Any]:
    """
    Compares two or more user-owned documents, aligning extracted measurements side-by-side.
    """
    stmt = (
        select(MedicalDocument)
        .where(
            MedicalDocument.id.in_(document_ids),
            MedicalDocument.user_id == user_id,
        )
        .options(selectinload(MedicalDocument.extracted_measurements))
    )
    res = await db.execute(stmt)
    docs = res.scalars().all()

    if len(docs) < 2:
        raise NotFoundError(message="Select at least 2 valid documents belonging to your account.")

    # Align measurements by parameter_code or parameter_name_raw
    aligned_map: Dict[str, Dict[str, Any]] = {}

    for d in docs:
        doc_id_str = str(d.id)
        for m in d.extracted_measurements:
            key = m.parameter_code or m.parameter_name_raw.lower()
            if key not in aligned_map:
                aligned_map[key] = {
                    "parameterCode": m.parameter_code,
                    "parameterName": m.parameter_name_display or m.parameter_name_raw,
                    "unit": m.source_unit,
                    "valuesByDocument": {},
                }
            aligned_map[key]["valuesByDocument"][doc_id_str] = {
                "rawValue": m.raw_value_text,
                "numericValue": m.numeric_value,
                "status": m.calculated_range_status,
                "referenceText": m.reference_text_raw or (
                    f"{m.reference_low} - {m.reference_high}" if m.reference_low and m.reference_high else None
                ),
                "sourceFlag": m.source_flag,
            }

    docs_meta = [
        {
            "id": str(d.id),
            "title": d.document_title or d.original_filename,
            "testDate": d.document_date.strftime("%Y-%m-%d") if d.document_date else None,
            "documentType": d.document_type,
        }
        for d in docs
    ]

    return {
        "documents": docs_meta,
        "alignedMeasurements": list(aligned_map.values()),
    }

