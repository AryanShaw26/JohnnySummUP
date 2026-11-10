import json
import logging
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.abnormality_flag import AbnormalityFlag
from app.models.document_analysis import DocumentAnalysis
from app.models.extracted_finding import ExtractedFinding
from app.models.medical_document import MedicalDocument
from app.models.medical_measurement import MedicalMeasurement
from app.services.medical.gemini_adapter import ERROR_MESSAGES, GeminiAdapter, GeminiAdapterError

logger = logging.getLogger("johnnysummup.medical.analysis")

SYSTEM_PROMPT = """You are a medical document analyzer for JohnnySummUP.
Analyze the provided medical report text and extract structured information strictly according to what is present in the document.

SAFETY AND INTEGRITY RULES:
1. NEVER diagnose diseases, conditions, or suggest medical treatments.
2. Only extract values and reference ranges that explicitly exist in the report. NEVER invent or hallucinate reference ranges.
3. If a reference range is absent, leave reference_low, reference_high, and reference_text as null.
4. For prescriptions, extract medicine name, dosage, frequency, and instructions if stated; do NOT infer missing values.
5. Only flag an item as out-of-range ('below_range' or 'above_range') if the report explicitly provides a reference range and the observed numeric value falls outside it. Use neutral phrasing like 'Outside the reference range in this report'.
6. Return valid JSON only, with no markdown code blocks or wrapper.

Return the following JSON schema:
{
  "summary": "Plain-language summary of what the document contains, avoiding diagnosis.",
  "key_points": ["Highlight 1", "Highlight 2"],
  "report_date": "YYYY-MM-DD or null if not detected",
  "findings": [
    {
      "category": "laboratory" | "prescription" | "general",
      "finding_type": "test_result" | "medicine" | "observation",
      "name": "Parameter or Medicine Name",
      "value_text": "Original text representation of value",
      "numeric_value": 12.5 or null,
      "unit": "g/dL or null",
      "reference_low": 12.0 or null,
      "reference_high": 16.0 or null,
      "reference_text": "12.0 - 16.0 g/dL or null",
      "source_page": 1,
      "confidence": 0.95
    }
  ],
  "measurements": [
    {
      "parameter_name": "Hemoglobin",
      "parameter_code": "hemoglobin",
      "numeric_value": 12.5,
      "unit": "g/dL",
      "reference_low": 12.0 or null,
      "reference_high": 16.0 or null,
      "reference_text": "12.0 - 16.0 g/dL or null"
    }
  ],
  "flags": [
    {
      "parameter_name": "Parameter Name",
      "observed_value": 22.0,
      "unit": "mm/hr",
      "reference_text": "0 - 20 mm/hr",
      "flag_type": "above_range" | "below_range" | "needs_review",
      "severity": "review" | "high" | "info",
      "explanation": "Neutral explanation noting value is outside stated reference range"
    }
  ]
}
"""


class RawFindingItem(BaseModel):
    category: str = "general"
    finding_type: str = "test_result"
    name: str
    value_text: str | None = None
    numeric_value: float | None = None
    unit: str | None = None
    reference_low: float | None = None
    reference_high: float | None = None
    reference_text: str | None = None
    source_page: int | None = 1
    confidence: float | None = None


class RawMeasurementItem(BaseModel):
    parameter_name: str
    parameter_code: str | None = None
    numeric_value: float
    unit: str
    reference_low: float | None = None
    reference_high: float | None = None
    reference_text: str | None = None


class RawFlagItem(BaseModel):
    parameter_name: str
    observed_value: float | None = None
    unit: str | None = None
    reference_text: str | None = None
    flag_type: str = "needs_review"
    severity: str = "review"
    explanation: str | None = None


class RawAnalysisOutput(BaseModel):
    summary: str
    key_points: list[str] = Field(default_factory=list)
    report_date: str | None = None
    findings: list[RawFindingItem] = Field(default_factory=list)
    measurements: list[RawMeasurementItem] = Field(default_factory=list)
    flags: list[RawFlagItem] = Field(default_factory=list)


class MedicalAnalysisService:
    @staticmethod
    def resolve_provider(requested_provider: str | None = None) -> tuple[str, str, str | None]:
        """
        Resolves the provider to use, model name, and API key.
        Always resolves to Gemini in JohnnySummUP.
        Returns: (provider_name, model_name, api_key_or_none)
        """
        settings = get_settings()
        gemini_key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None
        return "gemini", settings.gemini_model, gemini_key

    @staticmethod
    def get_provider_diagnostics() -> dict[str, Any]:
        """Returns provider availability and configuration metadata without exposing secret keys."""
        settings = get_settings()
        try:
            import importlib.metadata
            sdk_version = importlib.metadata.version("google-genai")
        except Exception:
            sdk_version = "3.0.0"

        has_key = bool(settings.gemini_api_key and settings.gemini_api_key.get_secret_value())
        return {
            "provider": "gemini",
            "configured": has_key,
            "model": settings.gemini_model,
            "sdk_version": sdk_version,
            "configuration_source": "GEMINI_API_KEY",
        }

    @classmethod
    async def test_provider_connectivity(cls, provider: str | None = None) -> dict[str, Any]:
        """Runs a minimal non-medical ping check against Gemini."""
        return await GeminiAdapter.test_connectivity()

    @classmethod
    async def run_analysis(
        cls,
        db: Session,
        document_id: UUID,
        user_id: UUID,
        extracted_text: str,
        document_type: str,
        requested_provider: str | None = None,
        mock_response: dict[str, Any] | None = None,
        image_data_url: str | None = None,
    ) -> DocumentAnalysis:
        request_id = str(uuid4())
        settings = get_settings()

        # Find document
        doc = db.get(MedicalDocument, document_id)
        if not doc or doc.user_id != user_id:
            raise ValueError("Document not found or ownership mismatch")

        # Atomic claim to prevent duplicate analysis runs on the same document
        claim = db.execute(
            update(MedicalDocument)
            .where(
                MedicalDocument.id == document_id,
                MedicalDocument.user_id == user_id,
                MedicalDocument.deleted_at.is_(None),
                MedicalDocument.status.notin_(("processing", "queued")),
            )
            .values(status="processing", failure_code=None, failure_message=None)
            .execution_options(synchronize_session=False)
        )
        if claim.rowcount != 1:
            active_analysis = db.scalar(
                select(DocumentAnalysis)
                .where(
                    DocumentAnalysis.document_id == document_id,
                    DocumentAnalysis.user_id == user_id,
                    DocumentAnalysis.status.in_(("queued", "processing")),
                )
                .order_by(DocumentAnalysis.version.desc())
                .limit(1)
            )
            if active_analysis is not None:
                return active_analysis
            raise ValueError("Document is already marked as processing without an active analysis")

        latest_version = db.scalar(
            select(func.max(DocumentAnalysis.version)).where(
                DocumentAnalysis.document_id == document_id,
                DocumentAnalysis.user_id == user_id,
            )
        )
        next_version = (latest_version or 0) + 1

        analysis = DocumentAnalysis(
            document_id=doc.id,
            user_id=user_id,
            version=next_version,
            status="processing",
            extracted_text=extracted_text[:12000] if extracted_text else None,
            provider="mock" if mock_response is not None else "gemini",
            model_name="mock" if mock_response is not None else settings.gemini_model,
            prompt_version="v2.0",
            started_at=datetime.now(timezone.utc),
        )
        db.add(analysis)
        doc.status = "processing"
        doc.failure_code = None
        doc.failure_message = None
        db.commit()
        db.refresh(analysis)

        logger.info(
            "analysis_queued request_id=%s document_id=%s analysis_id=%s version=%d provider=%s model=%s",
            request_id,
            doc.id,
            analysis.id,
            analysis.version,
            analysis.provider,
            analysis.model_name,
        )

        # 1. Check if usable text is present (Extraction check)
        if not extracted_text or not extracted_text.strip():
            logger.warning("extraction_failed_no_text request_id=%s document_id=%s", request_id, doc.id)
            return cls._mark_analysis_failed(
                db, doc, analysis, "extraction_failed", ERROR_MESSAGES["extraction_failed"]
            )

        # If mock_response is provided for testing, use it directly
        if mock_response is not None:
            return cls._persist_analysis_output(
                db=db,
                doc=doc,
                analysis=analysis,
                user_id=user_id,
                parsed_data=mock_response,
            )

        # 2. Check if Gemini key is configured
        if not settings.gemini_api_key or not settings.gemini_api_key.get_secret_value():
            logger.info("provider_not_configured request_id=%s", request_id)
            analysis.status = "unavailable"
            analysis.error_code = "provider_not_configured"
            analysis.error_message = ERROR_MESSAGES["provider_not_configured"]
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "analysis_unavailable"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis

        # 3. Bound extracted text and delimit as untrusted data
        safe_text = extracted_text[:10000]
        user_prompt = (
            f"Document Type: {document_type}\n"
            f"Filename: {doc.original_filename}\n\n"
            f"<DOCUMENT_CONTENT>\n{safe_text}\n</DOCUMENT_CONTENT>"
        )

        try:
            # 4. Invoke Gemini via GeminiAdapter
            gemini_result = await GeminiAdapter.generate_content(
                prompt=user_prompt,
                system_instruction=SYSTEM_PROMPT,
                timeout_seconds=45.0,
            )
            raw_content = gemini_result["content"]

            # Strip markdown fences if present
            clean_content = raw_content.strip()
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            elif clean_content.startswith("```"):
                clean_content = clean_content[3:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            clean_content = clean_content.strip()

            try:
                parsed_raw = json.loads(clean_content)
                validated = RawAnalysisOutput.model_validate(parsed_raw)
            except (json.JSONDecodeError, ValidationError) as parse_exc:
                logger.error("invalid_provider_response request_id=%s parse_exc=%s", request_id, parse_exc)
                return cls._mark_analysis_failed(
                    db,
                    doc,
                    analysis,
                    "invalid_provider_response",
                    ERROR_MESSAGES["invalid_provider_response"],
                )

            logger.info("provider_request_succeeded request_id=%s document_id=%s", request_id, doc.id)

            return cls._persist_analysis_output(
                db=db,
                doc=doc,
                analysis=analysis,
                user_id=user_id,
                parsed_data=validated.model_dump(),
            )

        except GeminiAdapterError as g_err:
            logger.error("gemini_adapter_error request_id=%s code=%s msg=%s", request_id, g_err.error_code, g_err.user_message)
            return cls._mark_analysis_failed(db, doc, analysis, g_err.error_code, g_err.user_message)
        except Exception as exc:
            logger.error("unexpected_analysis_error request_id=%s: %s", request_id, exc)
            return cls._mark_analysis_failed(
                db, doc, analysis, "provider_error", ERROR_MESSAGES["provider_error"].format(request_id=request_id)
            )

    @staticmethod
    def _mark_analysis_failed(
        db: Session,
        doc: MedicalDocument,
        analysis: DocumentAnalysis,
        error_code: str,
        error_message: str,
    ) -> DocumentAnalysis:
        analysis.status = "failed"
        analysis.error_code = error_code
        analysis.error_message = error_message
        analysis.completed_at = datetime.now(timezone.utc)

        doc.status = "failed"
        doc.failure_code = error_code
        doc.failure_message = error_message

        db.commit()
        return analysis

    @classmethod
    def _persist_analysis_output(
        cls,
        db: Session,
        doc: MedicalDocument,
        analysis: DocumentAnalysis,
        user_id: UUID,
        parsed_data: dict[str, Any],
    ) -> DocumentAnalysis:
        try:
            # Clean any existing child records for this document to prevent duplicate items upon re-analysis
            db.execute(delete(AbnormalityFlag).where(AbnormalityFlag.document_id == doc.id))
            db.execute(delete(MedicalMeasurement).where(MedicalMeasurement.document_id == doc.id))
            db.execute(delete(ExtractedFinding).where(ExtractedFinding.analysis_id == analysis.id))

            # Persist summary
            analysis.summary = parsed_data.get("summary")
            analysis.key_points = parsed_data.get("key_points", [])
            analysis.status = "completed"
            analysis.error_code = None
            analysis.error_message = None
            analysis.completed_at = datetime.now(timezone.utc)

            # Update document report date if parsed and not previously set
            report_date_str = parsed_data.get("report_date")
            if report_date_str:
                try:
                    parsed_report_date = datetime.strptime(str(report_date_str), "%Y-%m-%d").date()
                    if not doc.report_date:
                        doc.report_date = parsed_report_date
                except ValueError:
                    pass

            doc_date = doc.report_date or date.today()

            # Persist findings
            findings_data = parsed_data.get("findings", [])
            finding_objects: list[ExtractedFinding] = []
            for item in findings_data:
                name = str(item.get("name", "")).strip()
                if not name:
                    continue
                num_val = item.get("numeric_value")
                ref_low = item.get("reference_low")
                ref_high = item.get("reference_high")
                conf = item.get("confidence")

                finding = ExtractedFinding(
                    analysis_id=analysis.id,
                    document_id=doc.id,
                    user_id=user_id,
                    category=str(item.get("category", "general"))[:40],
                    finding_type=str(item.get("finding_type", "test_result"))[:80],
                    name=name[:255],
                    value_text=str(item.get("value_text", ""))[:500] if item.get("value_text") else None,
                    numeric_value=Decimal(str(num_val)) if num_val is not None else None,
                    unit=str(item.get("unit", ""))[:60] if item.get("unit") else None,
                    reference_low=Decimal(str(ref_low)) if ref_low is not None else None,
                    reference_high=Decimal(str(ref_high)) if ref_high is not None else None,
                    reference_text=str(item.get("reference_text", ""))[:255] if item.get("reference_text") else None,
                    source_page=item.get("source_page", 1),
                    confidence=Decimal(str(conf)) if conf is not None else None,
                    is_extracted=True,
                )
                db.add(finding)
                finding_objects.append(finding)

            db.flush()

            finding_by_name = {f.name.lower(): f.id for f in finding_objects}

            # Persist measurements
            measurements_data = parsed_data.get("measurements", [])
            measurement_objects: list[MedicalMeasurement] = []
            for m in measurements_data:
                param_name = str(m.get("parameter_name", "")).strip()
                num_val = m.get("numeric_value")
                unit = str(m.get("unit", "")).strip()
                if not param_name or num_val is None or not unit:
                    continue

                ref_low = m.get("reference_low")
                ref_high = m.get("reference_high")

                meas = MedicalMeasurement(
                    user_id=user_id,
                    document_id=doc.id,
                    source_finding_id=finding_by_name.get(param_name.lower()),
                    parameter_name=param_name[:160],
                    parameter_code=str(m.get("parameter_code", param_name.lower().replace(" ", "_")))[:100],
                    numeric_value=Decimal(str(num_val)),
                    unit=unit[:60],
                    report_date=doc_date,
                    reference_low=Decimal(str(ref_low)) if ref_low is not None else None,
                    reference_high=Decimal(str(ref_high)) if ref_high is not None else None,
                    reference_text=str(m.get("reference_text", ""))[:255] if m.get("reference_text") else None,
                )
                db.add(meas)
                measurement_objects.append(meas)

            db.flush()

            meas_by_name = {m.parameter_name.lower(): m.id for m in measurement_objects}

            # Persist abnormality flags
            flags_data = parsed_data.get("flags", [])
            for flag in flags_data:
                param_name = str(flag.get("parameter_name", "")).strip()
                if not param_name:
                    continue
                obs_val = flag.get("observed_value")
                ref_text = flag.get("reference_text")
                flag_type = str(flag.get("flag_type", "needs_review"))[:30]
                severity = str(flag.get("severity", "review"))[:20]

                if severity not in ["info", "review", "high"]:
                    severity = "review"

                flag_obj = AbnormalityFlag(
                    user_id=user_id,
                    document_id=doc.id,
                    source_finding_id=finding_by_name.get(param_name.lower()),
                    measurement_id=meas_by_name.get(param_name.lower()),
                    parameter_name=param_name[:160],
                    observed_value=Decimal(str(obs_val)) if obs_val is not None else None,
                    unit=str(flag.get("unit", ""))[:60] if flag.get("unit") else None,
                    reference_text=str(ref_text)[:255] if ref_text else None,
                    flag_type=flag_type,
                    severity=severity,
                    explanation=str(flag.get("explanation", ""))[:1000] if flag.get("explanation") else None,
                )
                db.add(flag_obj)

            doc.status = "completed"
            doc.failure_code = None
            doc.failure_message = None
            db.commit()
            db.refresh(analysis)

            logger.info(
                "analysis_persisted document_id=%s findings_count=%d measurements_count=%d flags_count=%d",
                doc.id,
                len(finding_objects),
                len(measurement_objects),
                len(flags_data),
            )

            return analysis

        except Exception as exc:
            db.rollback()
            logger.error("persistence_failed document_id=%s analysis_id=%s: %s", doc.id, analysis.id, exc)
            return cls._mark_analysis_failed(
                db,
                doc,
                analysis,
                "persistence_failed",
                ERROR_MESSAGES["persistence_failed"],
            )


analysis_service = MedicalAnalysisService()
