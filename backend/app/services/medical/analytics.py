from collections import defaultdict
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.abnormality_flag import AbnormalityFlag
from app.models.medical_document import MedicalDocument
from app.models.medical_measurement import MedicalMeasurement
from app.schemas.medical import (
    AbnormalityFlagResponse,
    MedicalDocumentResponse,
    MedicalOverviewResponse,
    ParameterComparisonResponse,
    ParameterComparisonRow,
    TimelineItem,
    TrendPoint,
    TrendResponse,
)


class MedicalAnalyticsService:
    @staticmethod
    def get_overview(db: Session, user_id: UUID) -> MedicalOverviewResponse:
        total_reports = (
            db.scalar(
                select(func.count(MedicalDocument.id)).where(
                    MedicalDocument.user_id == user_id, MedicalDocument.deleted_at.is_(None)
                )
            )
            or 0
        )

        prescriptions_count = (
            db.scalar(
                select(func.count(MedicalDocument.id)).where(
                    MedicalDocument.user_id == user_id,
                    MedicalDocument.document_type == "prescription",
                    MedicalDocument.deleted_at.is_(None),
                )
            )
            or 0
        )

        lab_reports_count = (
            db.scalar(
                select(func.count(MedicalDocument.id)).where(
                    MedicalDocument.user_id == user_id,
                    MedicalDocument.document_type == "laboratory_report",
                    MedicalDocument.deleted_at.is_(None),
                )
            )
            or 0
        )

        important_findings_count = (
            db.scalar(
                select(func.count(AbnormalityFlag.id)).where(AbnormalityFlag.user_id == user_id)
            )
            or 0
        )

        # Recent 5 reports
        recent_docs = (
            db.execute(
                select(MedicalDocument)
                .where(MedicalDocument.user_id == user_id, MedicalDocument.deleted_at.is_(None))
                .order_by(MedicalDocument.created_at.desc())
                .limit(5)
                .options(joinedload(MedicalDocument.analyses))
            )
            .unique()
            .scalars()
            .all()
        )

        recent_doc_responses = []
        for d in recent_docs:
            latest_analysis = d.analyses[0] if d.analyses else None
            recent_doc_responses.append(
                MedicalDocumentResponse(
                    id=d.id,
                    original_filename=d.original_filename,
                    mime_type=d.mime_type,
                    file_extension=d.file_extension,
                    file_size_bytes=d.file_size_bytes,
                    document_type=d.document_type,
                    report_date=d.report_date,
                    status=d.status,
                    failure_code=d.failure_code,
                    failure_message=d.failure_message,
                    created_at=d.created_at,
                    updated_at=d.updated_at,
                    latest_analysis=latest_analysis,  # type: ignore
                )
            )

        # Recent important findings
        flags = (
            db.execute(
                select(AbnormalityFlag)
                .where(AbnormalityFlag.user_id == user_id)
                .order_by(AbnormalityFlag.created_at.desc())
                .limit(5)
                .options(joinedload(AbnormalityFlag.document))
            )
            .unique()
            .scalars()
            .all()
        )

        flag_responses = []
        for f in flags:
            flag_responses.append(
                AbnormalityFlagResponse(
                    id=f.id,
                    document_id=f.document_id,
                    source_finding_id=f.source_finding_id,
                    measurement_id=f.measurement_id,
                    parameter_name=f.parameter_name,
                    observed_value=float(f.observed_value) if f.observed_value is not None else None,
                    unit=f.unit,
                    reference_text=f.reference_text,
                    flag_type=f.flag_type,
                    severity=f.severity,
                    explanation=f.explanation,
                    created_at=f.created_at,
                    document_name=f.document.original_filename if f.document else None,
                    report_date=f.document.report_date if f.document else None,
                )
            )

        return MedicalOverviewResponse(
            total_reports=total_reports,
            prescriptions_count=prescriptions_count,
            lab_reports_count=lab_reports_count,
            important_findings_count=important_findings_count,
            recent_reports=recent_doc_responses,
            important_findings=flag_responses,
        )

    @staticmethod
    def get_health_trends(
        db: Session, user_id: UUID, parameter_name: str | None = None
    ) -> TrendResponse:
        # Get all distinct parameter names for the user
        available_params = (
            db.execute(
                select(MedicalMeasurement.parameter_name)
                .where(MedicalMeasurement.user_id == user_id)
                .group_by(MedicalMeasurement.parameter_name)
                .order_by(MedicalMeasurement.parameter_name.asc())
            )
            .scalars()
            .all()
        )

        if not available_params:
            return TrendResponse(
                parameter_name=parameter_name or "No parameters recorded",
                unit="",
                reference_range=None,
                current_value=None,
                previous_value=None,
                change=None,
                status="normal",
                points=[],
                available_parameters=[],
            )

        target_param = parameter_name if parameter_name in available_params else available_params[0]

        # Fetch measurements for target parameter sorted chronologically
        measurements = (
            db.execute(
                select(MedicalMeasurement)
                .where(
                    MedicalMeasurement.user_id == user_id,
                    MedicalMeasurement.parameter_name == target_param,
                )
                .order_by(MedicalMeasurement.report_date.asc(), MedicalMeasurement.created_at.asc())
                .options(joinedload(MedicalMeasurement.document))
            )
            .unique()
            .scalars()
            .all()
        )

        if not measurements:
            return TrendResponse(
                parameter_name=target_param,
                unit="",
                reference_range=None,
                current_value=None,
                previous_value=None,
                change=None,
                status="normal",
                points=[],
                available_parameters=list(available_params),
            )

        # Verify unit compatibility
        primary_unit = measurements[-1].unit
        ref_text = measurements[-1].reference_text

        points: list[TrendPoint] = []
        compatible_measurements = []
        for m in measurements:
            if m.unit.lower() == primary_unit.lower():
                compatible_measurements.append(m)
                val = float(m.numeric_value)
                is_abnormal = False
                if m.reference_low is not None and val < float(m.reference_low):
                    is_abnormal = True
                elif m.reference_high is not None and val > float(m.reference_high):
                    is_abnormal = True

                points.append(
                    TrendPoint(
                        date=m.report_date,
                        value=val,
                        unit=m.unit,
                        document_id=m.document_id,
                        document_name=m.document.original_filename if m.document else "Report",
                        is_abnormal=is_abnormal,
                    )
                )

        current_val = points[-1].value if points else None
        prev_val = points[-2].value if len(points) >= 2 else None
        change = round(current_val - prev_val, 2) if (current_val is not None and prev_val is not None) else None

        latest_meas = compatible_measurements[-1] if compatible_measurements else None
        status_label = "normal"
        if latest_meas and current_val is not None:
            if latest_meas.reference_high and current_val > float(latest_meas.reference_high):
                status_label = "high"
            elif latest_meas.reference_low and current_val < float(latest_meas.reference_low):
                status_label = "low"

        return TrendResponse(
            parameter_name=target_param,
            unit=primary_unit,
            reference_range=ref_text,
            current_value=current_val,
            previous_value=prev_val,
            change=change,
            status=status_label,
            points=points,
            available_parameters=list(available_params),
        )

    @staticmethod
    def get_parameter_comparison(db: Session, user_id: UUID) -> ParameterComparisonResponse:
        measurements = (
            db.execute(
                select(MedicalMeasurement)
                .where(MedicalMeasurement.user_id == user_id)
                .order_by(MedicalMeasurement.report_date.asc())
            )
            .scalars()
            .all()
        )

        if not measurements:
            return ParameterComparisonResponse(report_dates=[], rows=[])

        # Get all distinct report dates formatted as YYYY-MM-DD
        dates_set = {m.report_date.strftime("%Y-%m-%d") for m in measurements}
        sorted_dates = sorted(dates_set)

        # Group by parameter_name
        param_groups: dict[str, list[MedicalMeasurement]] = defaultdict(list)
        for m in measurements:
            param_groups[m.parameter_name].append(m)

        rows: list[ParameterComparisonRow] = []
        for param_name, items in param_groups.items():
            unit = items[-1].unit
            ref_range = items[-1].reference_text

            values_by_date: dict[str, float | None] = {d: None for d in sorted_dates}
            for it in items:
                d_str = it.report_date.strftime("%Y-%m-%d")
                values_by_date[d_str] = float(it.numeric_value)

            # Trend direction
            known_vals = [values_by_date[d] for d in sorted_dates if values_by_date[d] is not None]
            if len(known_vals) >= 2:
                if known_vals[-1] > known_vals[0]:
                    trend_dir = "up"
                elif known_vals[-1] < known_vals[0]:
                    trend_dir = "down"
                else:
                    trend_dir = "stable"
            else:
                trend_dir = "stable"

            rows.append(
                ParameterComparisonRow(
                    parameter_name=param_name,
                    unit=unit,
                    reference_range=ref_range,
                    values_by_date=values_by_date,
                    trend_direction=trend_dir,
                )
            )

        return ParameterComparisonResponse(report_dates=sorted_dates, rows=rows)

    @staticmethod
    def get_timeline(db: Session, user_id: UUID) -> list[TimelineItem]:
        docs = (
            db.execute(
                select(MedicalDocument)
                .where(MedicalDocument.user_id == user_id, MedicalDocument.deleted_at.is_(None))
                .order_by(MedicalDocument.report_date.desc().nullslast(), MedicalDocument.created_at.desc())
                .options(
                    joinedload(MedicalDocument.measurements),
                    joinedload(MedicalDocument.flags),
                )
            )
            .unique()
            .scalars()
            .all()
        )

        items: list[TimelineItem] = []
        for d in docs:
            rep_date = d.report_date or d.created_at.date()
            key_meas = [
                {
                    "name": m.parameter_name,
                    "value": float(m.numeric_value),
                    "unit": m.unit,
                }
                for m in d.measurements[:4]
            ]
            items.append(
                TimelineItem(
                    document_id=d.id,
                    report_name=d.original_filename,
                    report_date=rep_date,
                    document_type=d.document_type,
                    status=d.status,
                    key_measurements=key_meas,
                    flag_count=len(d.flags),
                )
            )

        return items


analytics_service = MedicalAnalyticsService()
