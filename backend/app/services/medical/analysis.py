import json
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.abnormality_flag import AbnormalityFlag
from app.models.document_analysis import DocumentAnalysis
from app.models.extracted_finding import ExtractedFinding
from app.models.medical_document import MedicalDocument
from app.models.medical_measurement import MedicalMeasurement

logger = logging.getLogger("johnnysummup.medical.analysis")

QUOTA_ERROR_MARKERS = (
    "insufficient_quota",
    "billing_hard_limit",
    "billing_not_active",
    "quota",
    "credit",
)


def _is_quota_error(error_type: str, error_code: str, error_message: str) -> bool:
    return any(
        marker in value
        for value in (error_type, error_code, error_message)
        for marker in QUOTA_ERROR_MARKERS
    )


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
    async def run_analysis(
        db: Session,
        document_id: UUID,
        user_id: UUID,
        extracted_text: str,
        document_type: str,
        mock_response: dict[str, Any] | None = None,
        image_data_url: str | None = None,
    ) -> DocumentAnalysis:
        settings = get_settings()

        # Find document
        doc = db.get(MedicalDocument, document_id)
        if not doc or doc.user_id != user_id:
            raise ValueError("Document not found or ownership mismatch")

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
                DocumentAnalysis.document_id == document_id
            )
        )
        next_version = (latest_version or 0) + 1

        analysis = DocumentAnalysis(
            document_id=doc.id,
            user_id=user_id,
            version=next_version,
            status="processing",
            extracted_text=extracted_text[:10000] if extracted_text else None,
            provider="mock" if mock_response is not None else ("openai" if settings.openai_api_key else None),
            model_name=(
                "mock"
                if mock_response is not None
                else (settings.openai_model if settings.openai_api_key else None)
            ),
            prompt_version="v1.0",
            started_at=datetime.now(timezone.utc),
        )
        db.add(analysis)
        doc.status = "processing"
        doc.failure_code = None
        doc.failure_message = None
        db.commit()
        db.refresh(analysis)

        logger.info(
            "analysis_queued document_id=%s analysis_id=%s version=%d",
            doc.id,
            analysis.id,
            analysis.version,
        )

        # Check if text is present
        if not extracted_text.strip() and image_data_url is None:
            logger.warning("extraction_failed_no_text document_id=%s", doc.id)
            analysis.status = "failed"
            analysis.error_code = "OCR_NO_TEXT"
            analysis.error_message = (
                "We could not extract readable text from this document. "
                "Please upload a document with a selectable digital text layer."
            )
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "failed"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis

        # If mock_response is provided for testing, use it directly
        if mock_response is not None:
            return MedicalAnalysisService._persist_analysis_output(
                db=db,
                doc=doc,
                analysis=analysis,
                user_id=user_id,
                parsed_data=mock_response,
            )

        # Check if OpenAI key is configured
        api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
        if not api_key:
            logger.info("provider_not_configured document_id=%s", doc.id)
            analysis.status = "unavailable"
            analysis.error_code = "AI_NOT_CONFIGURED"
            analysis.error_message = (
                "AI analysis is not configured on this server. Document is safely stored."
            )
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "analysis_unavailable"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis

        # Call OpenAI Chat Completion
        document_content = (
            extracted_text[:8000]
            if extracted_text.strip()
            else "No text layer was extracted; analyze the attached image."
        )
        user_prompt = (
            f"Document Type: {document_type}\nFilename: {doc.original_filename}\n\n"
            f"Document Text:\n{document_content}"
        )
        user_content: str | list[dict[str, Any]] = user_prompt
        if image_data_url is not None:
            user_content = [
                {"type": "text", "text": user_prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": image_data_url, "detail": "high"},
                },
            ]

        logger.info(
            "provider_request_started document_id=%s provider=openai model=%s",
            doc.id,
            settings.openai_model,
        )

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{settings.openai_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.openai_model,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_content},
                        ],
                        "temperature": 0.1,
                    },
                )

            if response.status_code != 200:
                error_body: dict[str, Any] = {}
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and isinstance(response_data.get("error"), dict):
                        error_body = response_data["error"]
                except (ValueError, TypeError):
                    pass

                error_type = str(error_body.get("type", "")).lower()
                error_msg = str(error_body.get("message", "")).lower()
                provider_error_code = str(error_body.get("code", "")).lower()
                status_code = response.status_code

                logger.error(
                    "provider_request_failed document_id=%s status_code=%d error_type=%s provider_error_code=%s",
                    doc.id,
                    status_code,
                    error_type,
                    provider_error_code,
                )

                if status_code == 429:
                    if _is_quota_error(error_type, provider_error_code, error_msg):
                        analysis.error_code = "PROVIDER_INSUFFICIENT_QUOTA"
                        analysis.error_message = (
                            "The AI provider rejected this request because its API quota or billing "
                            "limit is unavailable. Rejected requests may not appear in usage history. "
                            "Check billing, project spending limits, and that this API key belongs "
                            "to the intended project."
                        )
                    else:
                        analysis.error_code = "PROVIDER_RATE_LIMIT"
                        analysis.error_message = (
                            "Analysis rate limit exceeded. Please wait a moment and retry."
                        )
                elif status_code == 401:
                    analysis.error_code = "PROVIDER_AUTH_ERROR"
                    analysis.error_message = (
                        "The AI provider rejected OPENAI_API_KEY. Set it to an active API key issued "
                        "by the provider at OPENAI_BASE_URL, then restart the backend. The default "
                        "URL uses OpenAI API keys; ChatGPT subscriptions are not API keys."
                    )
                elif status_code == 404:
                    analysis.error_code = "MODEL_NOT_FOUND"
                    analysis.error_message = (
                        f"AI model '{settings.openai_model}' was not found. "
                        "Check OPENAI_MODEL and OPENAI_BASE_URL."
                    )
                elif status_code == 403:
                    analysis.error_code = "PROVIDER_PERMISSION_ERROR"
                    analysis.error_message = (
                        "The AI provider rejected this API key. Check that the key has permission "
                        "to use the configured model."
                    )
                elif status_code == 400:
                    analysis.error_code = "PROVIDER_INVALID_REQUEST"
                    analysis.error_message = (
                        "The AI provider rejected the request. Check the configured model and "
                        "provider compatibility."
                    )
                elif status_code >= 500:
                    analysis.error_code = "PROVIDER_SERVER_ERROR"
                    analysis.error_message = (
                        "AI analysis provider encountered a temporary server error. Please try again later."
                    )
                else:
                    analysis.error_code = f"PROVIDER_ERROR_{status_code}"
                    analysis.error_message = (
                        "Analysis provider returned an error while processing this document."
                    )

                analysis.status = "failed"
                analysis.completed_at = datetime.now(timezone.utc)
                doc.status = "failed"
                doc.failure_code = analysis.error_code
                doc.failure_message = analysis.error_message
                db.commit()
                return analysis

            # Parse and validate response
            resp_data = response.json()
            raw_content = resp_data["choices"][0]["message"]["content"] or ""

            # Strip markdown fences if present
            clean_content = raw_content.strip()
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            elif clean_content.startswith("```"):
                clean_content = clean_content[3:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            clean_content = clean_content.strip()

            parsed_raw = json.loads(clean_content)
            validated = RawAnalysisOutput.model_validate(parsed_raw)

            logger.info("provider_request_succeeded document_id=%s", doc.id)

            return MedicalAnalysisService._persist_analysis_output(
                db=db,
                doc=doc,
                analysis=analysis,
                user_id=user_id,
                parsed_data=validated.model_dump(),
            )

        except (httpx.TimeoutException, TimeoutError):
            logger.error("provider_timeout document_id=%s", doc.id)
            analysis.status = "failed"
            analysis.error_code = "PROVIDER_TIMEOUT"
            analysis.error_message = "AI analysis request timed out. You can retry."
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "failed"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis

        except httpx.RequestError as req_err:
            logger.error("provider_network_error document_id=%s error=%s", doc.id, req_err)
            analysis.status = "failed"
            analysis.error_code = "PROVIDER_NETWORK_ERROR"
            analysis.error_message = (
                "Unable to reach the AI analysis provider. Please check network connectivity."
            )
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "failed"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis

        except (json.JSONDecodeError, ValidationError) as schema_err:
            logger.error("response_validation_failed document_id=%s error=%s", doc.id, schema_err)
            analysis.status = "failed"
            analysis.error_code = "INVALID_AI_RESPONSE"
            analysis.error_message = (
                "The analysis result could not be validated against the required schema. Please retry."
            )
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "failed"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis

        except Exception as exc:
            logger.exception("analysis_unexpected_exception document_id=%s error=%s", doc.id, exc)
            db.rollback()
            analysis.status = "failed"
            analysis.error_code = "ANALYSIS_EXECUTION_ERROR"
            analysis.error_message = "An error occurred while generating AI analysis for this report."
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "failed"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis

    @staticmethod
    def _persist_analysis_output(
        db: Session,
        doc: MedicalDocument,
        analysis: DocumentAnalysis,
        user_id: UUID,
        parsed_data: dict[str, Any],
    ) -> DocumentAnalysis:
        # Persist summary
        analysis.summary = parsed_data.get("summary")
        analysis.key_points = parsed_data.get("key_points", [])
        analysis.status = "completed"
        analysis.completed_at = datetime.now(timezone.utc)

        # Update document report date if parsed
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


analysis_service = MedicalAnalysisService()
