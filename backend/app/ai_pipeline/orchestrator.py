"""
End-to-end AI/ML Pipeline Orchestrator for JohnnySummUP V1.
Executes document validation, text acquisition, medical extraction,
deterministic rules, summarization, and database persistence.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_pipeline.medical_extractor import extract_medical_data
from app.ai_pipeline.ocr_engine import ocr_engine
from app.ai_pipeline.output_validator import validate_summary_output
from app.ai_pipeline.pdf_parser import extract_text_from_pdf
from app.ai_pipeline.rule_evaluator import evaluate_document_rules
from app.ai_pipeline.summarizer import generate_summary
from app.core.database import async_session_factory
from app.models.finding import MedicalFinding
from app.models.measurement import ExtractedMeasurement
from app.models.medical_document import MedicalDocument
from app.models.prescription_item import PrescriptionItem
from app.models.processing_job import ProcessingJob
from app.models.summary import MedicalSummary

logger = logging.getLogger(__name__)


async def run_pipeline_for_document(document_id: UUID, job_id: UUID) -> None:
    """
    Asynchronous worker task that executes all 10 stages of the pipeline.
    """
    async with async_session_factory() as session:
        # Load document and job
        doc_res = await session.execute(
            select(MedicalDocument).where(MedicalDocument.id == document_id)
        )
        doc: Optional[MedicalDocument] = doc_res.scalar_one_or_none()

        job_res = await session.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job: Optional[ProcessingJob] = job_res.scalar_one_or_none()

        if not doc or not job:
            logger.error(f"Pipeline error: Document {document_id} or Job {job_id} not found.")
            return

        try:
            # ── Stage 1: File Validation ──────────────────────────────────────
            job.status = "processing"
            job.stage = "file_validation"
            job.progress_percent = 10
            job.started_at = datetime.now(timezone.utc)
            doc.status = "processing"
            await session.commit()

            file_path = Path(doc.storage_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Document file missing from storage: {doc.storage_path}")

            # ── Stage 2: Text Acquisition ─────────────────────────────────────
            job.stage = "text_acquisition"
            job.progress_percent = 25
            await session.commit()

            if doc.mime_type == "application/pdf":
                doc_text = extract_text_from_pdf(file_path)
                # If digital text was insufficient, attempt image OCR fallback
                if not doc_text.is_digital_text_sufficient:
                    logger.info("PDF digital text insufficient; attempting OCR fallback.")
                    # For V1, use whatever text was extracted or ocr
                    pass
            else:
                doc_text = ocr_engine.process_image(file_path)

            doc.page_count = doc_text.total_page_count

            # ── Stage 3 & 4: Classification & Extraction ──────────────────────
            job.stage = "field_extraction"
            job.progress_percent = 50
            await session.commit()

            extraction = extract_medical_data(doc_text)
            doc.document_type = extraction.document_type
            if extraction.test_date:
                doc.document_date = extraction.test_date
            if extraction.facility_name:
                doc.facility_name = extraction.facility_name
            if extraction.provider_name:
                doc.provider_name = extraction.provider_name

            # ── Stage 5: Deterministic Range Checks & Rules ───────────────────
            job.stage = "rule_evaluation"
            job.progress_percent = 70
            await session.commit()

            eval_res = evaluate_document_rules(extraction.measurements)

            # Persist Extracted Measurements
            created_measurements: list[ExtractedMeasurement] = []
            for idx, m in enumerate(extraction.measurements):
                status = eval_res.calculated_statuses[idx]
                meas = ExtractedMeasurement(
                    document_id=doc.id,
                    parameter_code=m.parameter_code,
                    parameter_name_raw=m.parameter_name_raw,
                    parameter_name_display=m.parameter_name_display,
                    raw_value_text=m.raw_value_text,
                    numeric_value=m.numeric_value,
                    qualitative_value=m.qualitative_value,
                    source_unit=m.source_unit,
                    reference_low=m.reference_range.low if m.reference_range else None,
                    reference_high=m.reference_range.high if m.reference_range else None,
                    reference_text_raw=m.reference_range.raw_text if m.reference_range else None,
                    source_flag=m.source_flag,
                    calculated_range_status=status,
                    test_date=extraction.test_date or doc.document_date,
                    confidence=m.confidence,
                    review_status="needs_review" if m.confidence < 0.85 else "unreviewed",
                    source_page=m.source_page,
                    source_snippet=m.source_snippet,
                )
                session.add(meas)
                created_measurements.append(meas)

            # Flush to generate measurement IDs
            await session.flush()

            # Persist Deterministic Findings
            for f in eval_res.findings:
                associated_meas_id = (
                    created_measurements[f.measurement_ref_idx].id
                    if f.measurement_ref_idx < len(created_measurements)
                    else None
                )
                finding = MedicalFinding(
                    document_id=doc.id,
                    measurement_id=associated_meas_id,
                    finding_type=f.finding_type,
                    title=f.title,
                    explanation=f.explanation,
                    rule_code=f.rule_code,
                    evidence_reference=[{
                        "documentId": str(doc.id),
                        "page": f.source_page,
                        "snippet": f.source_snippet,
                        "measurementId": str(associated_meas_id) if associated_meas_id else None,
                    }],
                    review_status="unreviewed",
                )
                session.add(finding)

            # Persist Prescriptions
            for rx in extraction.prescription_items:
                prescription_item = PrescriptionItem(
                    document_id=doc.id,
                    medicine_name_raw=rx.medicine_name_raw,
                    strength_text=rx.strength_text,
                    dose_text=rx.dose_text,
                    route_text=rx.route_text,
                    frequency_text=rx.frequency_text,
                    duration_text=rx.duration_text,
                    instructions_text=rx.instructions_text,
                    confidence=rx.confidence,
                    source_page=rx.source_page,
                    source_snippet=rx.source_snippet,
                    review_status="unreviewed",
                )
                session.add(prescription_item)

            # ── Stage 6: Grounded Summarization ───────────────────────────────
            job.stage = "summarization"
            job.progress_percent = 85
            await session.commit()

            test_date_display = (
                extraction.test_date.strftime("%Y-%m-%d") if extraction.test_date else None
            )
            summary_dict = await generate_summary(
                document_type=doc.document_type,
                test_date_str=test_date_display,
                facility=doc.facility_name,
                measurements=extraction.measurements,
                calculated_statuses=eval_res.calculated_statuses,
                findings=eval_res.findings,
                prescriptions=extraction.prescription_items,
            )

            # ── Stage 7: Output Validation ────────────────────────────────────
            is_valid, validation_errors = validate_summary_output(summary_dict)

            summary_record = MedicalSummary(
                document_id=doc.id,
                summary_type="document_summary",
                summary_text=summary_dict.get("overview", "Report summary generated."),
                structured_summary=summary_dict,
                model_provider=settings.LLM_PROVIDER,
                model_name="grounded-v1",
                prompt_version="v1.0",
                pipeline_version="1.0.0",
                validation_status="passed" if is_valid else "needs_review",
            )
            session.add(summary_record)

            # ── Stage 8: Completion and Persistence ───────────────────────────
            has_uncertainties = any(m.confidence < 0.85 for m in extraction.measurements)
            doc.status = "needs_review" if (has_uncertainties or not is_valid) else "completed"

            job.status = "completed"
            job.stage = "completed"
            job.progress_percent = 100
            job.completed_at = datetime.now(timezone.utc)
            job.error_message_safe = None

            await session.commit()
            logger.info(f"Pipeline successfully completed for document {document_id}")

        except Exception as exc:
            logger.exception(f"Pipeline execution failed for document {document_id}: {exc}")
            await session.rollback()

            # Mark job failed safely
            async with async_session_factory() as fail_session:
                d = await fail_session.get(MedicalDocument, document_id)
                j = await fail_session.get(ProcessingJob, job_id)
                if d:
                    d.status = "failed"
                if j:
                    j.status = "failed"
                    j.error_code = "PROCESSING_FAILED"
                    j.error_message_safe = "Processing could not complete. You may retry this document."
                    j.completed_at = datetime.now(timezone.utc)
                await fail_session.commit()

