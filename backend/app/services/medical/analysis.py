"""Medical document analysis service for JohnnySummUP.

Supports Gemini and OpenAI-compatible chat-completions APIs, validates the
provider's structured response, and persists findings, measurements and flags.
"""

import json
import logging
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.abnormality_flag import AbnormalityFlag
from app.models.document_analysis import DocumentAnalysis
from app.models.extracted_finding import ExtractedFinding
from app.models.medical_document import MedicalDocument
from app.models.medical_measurement import MedicalMeasurement
from app.services.medical.gemini_adapter import GeminiAdapter, GeminiAdapterError

logger = logging.getLogger("johnnysummup.medical.analysis")

QUOTA_ERROR_MARKERS = (
    "insufficient_quota",
    "billing_hard_limit",
    "billing_not_active",
    "quota",
    "credit",
)

SYSTEM_PROMPT = """You are a medical document analyzer for JohnnySummUP.

Analyze the provided medical report text and extract structured information
strictly according to what is present in the document.

SAFETY AND INTEGRITY RULES:
1. NEVER diagnose diseases, conditions, or suggest medical treatments.
2. Only extract values and reference ranges explicitly present in the report.
   NEVER invent or hallucinate reference ranges.
3. If a reference range is absent, set reference_low, reference_high, and
   reference_text to null.
4. For prescriptions, extract medicine name, dosage, frequency, and
   instructions if stated; do NOT infer missing values.
5. Only flag an item as below_range or above_range if the report explicitly
   provides a reference range and the observed numeric value falls outside it.
   Use neutral phrasing such as "Outside the reference range in this report".
6. Return valid JSON only, with no Markdown code fences or wrapper.

Return an object with this schema:
{
  "summary": "Plain-language summary of what the document contains, avoiding diagnosis.",
  "key_points": ["Highlight 1", "Highlight 2"],
  "report_date": "YYYY-MM-DD or null if not detected",
  "findings": [
    {
      "category": "laboratory | prescription | general",
      "finding_type": "test_result | medicine | observation",
      "name": "Parameter or Medicine Name",
      "value_text": "Original text representation of value",
      "numeric_value": 12.5,
      "unit": "g/dL or null",
      "reference_low": 12.0,
      "reference_high": 16.0,
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
      "reference_low": 12.0,
      "reference_high": 16.0,
      "reference_text": "12.0 - 16.0 g/dL or null"
    }
  ],
  "flags": [
    {
      "parameter_name": "Parameter Name",
      "observed_value": 22.0,
      "unit": "mm/hr",
      "reference_text": "0 - 20 mm/hr",
      "flag_type": "above_range | below_range | needs_review",
      "severity": "review | high | info",
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
    """Runs AI analysis and persists the normalized medical-document output."""

    @staticmethod
    def _secret_value(secret: Any) -> str | None:
        if secret is None:
            return None
        return secret.get_secret_value() if hasattr(secret, "get_secret_value") else str(secret)

    @classmethod
    def resolve_provider(
        cls, requested_provider: str | None = None
    ) -> tuple[str, str, str | None]:
        """Resolve provider, model and API key using explicit/default preferences."""
        settings = get_settings()
        gemini_key = cls._secret_value(settings.gemini_api_key)
        openai_key = cls._secret_value(settings.openai_api_key)
        requested = (requested_provider or "").strip().lower()

        if requested:
            if requested == "gemini":
                return "gemini", settings.gemini_model, gemini_key
            if requested == "openai":
                return "openai", settings.openai_model, openai_key
            raise ValueError(f"Unsupported AI provider: {requested_provider}")

        preferred = (settings.default_ai_provider or "gemini").strip().lower()
        if preferred == "openai" and openai_key:
            return "openai", settings.openai_model, openai_key
        if preferred == "gemini" and gemini_key:
            return "gemini", settings.gemini_model, gemini_key
        if openai_key:
            return "openai", settings.openai_model, openai_key
        if gemini_key:
            return "gemini", settings.gemini_model, gemini_key

        # Preserve the configured preference in diagnostics when neither key exists.
        if preferred == "openai":
            return "openai", settings.openai_model, None
        return "gemini", settings.gemini_model, None

    @classmethod
    def get_provider_diagnostics(cls) -> dict[str, Any]:
        """Return provider configuration metadata without exposing secret keys."""
        settings = get_settings()
        gemini_key = cls._secret_value(settings.gemini_api_key)
        openai_key = cls._secret_value(settings.openai_api_key)
        return {
            "provider": "gemini",
            "configured": bool(gemini_key),
            "model": settings.gemini_model,
            "openai": {
                "configured": bool(openai_key),
                "model": settings.openai_model,
            },
            "gemini": {
                "configured": bool(gemini_key),
                "model": settings.gemini_model,
            },
            "default_provider": settings.default_ai_provider,
        }

    @classmethod
    async def test_provider_connectivity(
        cls, provider: str | None = None
    ) -> dict[str, Any]:
        """Send a minimal non-medical ping to the selected provider."""
        request_id = str(uuid4())
        start_time = time.time()

        try:
            provider_name, model_name, api_key = cls.resolve_provider(provider)
        except ValueError as exc:
            return {
                "success": False,
                "provider": provider,
                "model": None,
                "request_id": request_id,
                "error_code": "unsupported_provider",
                "error_message": str(exc),
                "duration_ms": int((time.time() - start_time) * 1000),
            }

        if not api_key:
            return {
                "success": False,
                "provider": provider_name,
                "model": model_name,
                "request_id": request_id,
                "error_code": "authentication_failed",
                "error_message": f"AI provider '{provider_name}' is not configured with an API key.",
                "duration_ms": int((time.time() - start_time) * 1000),
            }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                if provider_name == "gemini":
                    response = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
                        params={"key": api_key},
                        headers={"Content-Type": "application/json"},
                        json={
                            "contents": [
                                {"parts": [{"text": 'Return JSON: {"status":"ok"}'}]}
                            ],
                            "generationConfig": {"responseMimeType": "application/json"},
                        },
                    )
                else:
                    settings = get_settings()
                    base_url = str(settings.openai_base_url).rstrip("/")
                    response = await client.post(
                        f"{base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model_name,
                            "messages": [
                                {"role": "user", "content": 'Return JSON: {"status":"ok"}'}
                            ],
                            "response_format": {"type": "json_object"},
                            "temperature": 0.0,
                        },
                    )

            duration_ms = int((time.time() - start_time) * 1000)
            if response.status_code == 200:
                return {
                    "success": True,
                    "provider": provider_name,
                    "model": model_name,
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                }

            error_code, error_message = cls._classify_http_error(
                provider_name, response.status_code, response.text, request_id
            )
            return {
                "success": False,
                "provider": provider_name,
                "model": model_name,
                "request_id": request_id,
                "error_code": error_code,
                "error_message": error_message,
                "duration_ms": duration_ms,
            }
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            error_code, error_message = cls._classify_exception(exc, request_id)
            return {
                "success": False,
                "provider": provider_name,
                "model": model_name,
                "request_id": request_id,
                "error_code": error_code,
                "error_message": error_message,
                "duration_ms": duration_ms,
            }

    @staticmethod
    def _classify_http_error(
        provider: str, status_code: int, response_text: str, request_id: str
    ) -> tuple[str, str]:
        """Map provider HTTP errors to stable application error codes."""
        body = response_text.lower()

        if status_code == 429:
            if any(marker in body for marker in QUOTA_ERROR_MARKERS):
                return (
                    "quota_exceeded",
                    "The selected AI provider has exhausted its available quota. Check the provider project, billing and limits.",
                )
            return (
                "rate_limited",
                "The AI provider is temporarily rate-limiting requests. Please retry shortly.",
            )

        if status_code in (401, 403):
            if any(marker in body for marker in ("quota", "resource_exhausted", "credit")):
                return (
                    "quota_exceeded",
                    "The selected AI provider has exhausted its available quota. Check the provider project, billing and limits.",
                )
            return (
                "authentication_failed",
                "AI provider authentication failed. Check the configured API key.",
            )

        if status_code == 404:
            return (
                "model_unavailable",
                "The configured AI model is unavailable for this provider account.",
            )

        if status_code >= 500:
            return (
                "provider_unavailable",
                "Could not connect to the AI provider. Please retry.",
            )

        return "provider_error", f"AI analysis failed. Reference: {request_id}"

    @staticmethod
    def _classify_exception(
        exc: Exception, request_id: str
    ) -> tuple[str, str]:
        """Map network, timeout and response errors to stable application codes."""
        if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
            return "provider_timeout", "AI analysis timed out. Please retry."
        if isinstance(exc, httpx.RequestError):
            return "provider_unavailable", "Could not connect to the AI provider. Please retry."
        if isinstance(exc, (json.JSONDecodeError, ValidationError)):
            return "invalid_provider_response", "The AI provider returned an unusable response."
        return "provider_error", f"AI analysis failed. Reference: {request_id}"

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
        """Claim a document, call the AI provider, validate and persist its output."""
        request_id = str(uuid4())
        settings = get_settings()

        # Verify ownership before changing document state.
        doc = db.get(MedicalDocument, document_id)
        if not doc or doc.user_id != user_id:
            raise ValueError("Document not found or ownership mismatch")

        # Atomically claim the document so concurrent requests cannot analyze it twice.
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
            raise ValueError(
                "Document is already marked as processing without an active analysis"
            )

        latest_version = db.scalar(
            select(func.max(DocumentAnalysis.version)).where(
                DocumentAnalysis.document_id == document_id,
                DocumentAnalysis.user_id == user_id,
            )
        )
        next_version = (latest_version or 0) + 1

        try:
            provider_name, model_name, api_key = cls.resolve_provider(
                requested_provider
            )
        except ValueError as exc:
            db.rollback()
            raise

        analysis = DocumentAnalysis(
            document_id=doc.id,
            user_id=user_id,
            version=next_version,
            status="processing",
            extracted_text=(extracted_text or "")[:12000] or None,
            provider="mock" if mock_response is not None else provider_name,
            model_name="mock" if mock_response is not None else model_name,
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
            "analysis_started request_id=%s document_id=%s analysis_id=%s version=%d provider=%s model=%s",
            request_id,
            doc.id,
            analysis.id,
            analysis.version,
            analysis.provider,
            analysis.model_name,
        )

        # Image-only documents are allowed when an image data URL is available.
        if not (extracted_text or "").strip() and image_data_url is None:
            logger.warning(
                "extraction_failed_no_text request_id=%s document_id=%s",
                request_id,
                doc.id,
            )
            return cls._mark_analysis_failed(
                db,
                doc,
                analysis,
                "extraction_failed",
                "No readable text was extracted. Try a clearer scan or another file.",
            )

        # Mock path keeps tests independent of external API keys.
        if mock_response is not None:
            return cls._persist_analysis_output(
                db=db,
                doc=doc,
                analysis=analysis,
                user_id=user_id,
                parsed_data=mock_response,
            )

        if not api_key:
            logger.info(
                "provider_not_configured request_id=%s provider=%s",
                request_id,
                provider_name,
            )
            analysis.status = "unavailable"
            analysis.error_code = "provider_not_configured"
            analysis.error_message = (
                f"AI analysis with {provider_name.upper()} is not configured "
                "on this server. Document is safely stored."
            )
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "analysis_unavailable"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            db.refresh(analysis)
            return analysis

        safe_text = (extracted_text or "")[:10000]
        user_prompt = (
            f"Document Type: {document_type}\n"
            f"Filename: {doc.original_filename}\n\n"
            "<DOCUMENT_CONTENT>\n"
            f"{safe_text}\n"
            "</DOCUMENT_CONTENT>"
        )

        logger.info(
            "provider_request_started request_id=%s document_id=%s provider=%s model=%s",
            request_id,
            doc.id,
            provider_name,
            model_name,
        )

        try:
            if provider_name == "gemini":
                try:
                    gemini_res = await GeminiAdapter.generate_content(
                        prompt=user_prompt,
                        system_instruction=SYSTEM_PROMPT,
                        timeout_seconds=45.0,
                        api_key_override=api_key,
                        model_override=model_name,
                    )
                    raw_content = gemini_res["content"]
                except GeminiAdapterError as exc:
                    return cls._mark_analysis_failed(
                        db, doc, analysis, exc.error_code, exc.user_message
                    )
                except Exception as exc:
                    return cls._mark_analysis_failed(
                        db, doc, analysis, "provider_error", str(exc)
                    )
            else:
                try:
                    async with httpx.AsyncClient(timeout=45.0) as client:
                        if provider_name == "openai":
                            user_content: str | list[dict[str, Any]] = user_prompt
                            if image_data_url is not None:
                                user_content = [
                                    {"type": "text", "text": user_prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": image_data_url,
                                            "detail": "high",
                                        },
                                    },
                                ]

                            base_url = str(settings.openai_base_url).rstrip("/")
                            response = await client.post(
                                f"{base_url}/chat/completions",
                                headers={
                                    "Authorization": f"Bearer {api_key}",
                                    "Content-Type": "application/json",
                                },
                                json={
                                    "model": model_name,
                                    "response_format": {"type": "json_object"},
                                    "messages": [
                                        {"role": "system", "content": SYSTEM_PROMPT},
                                        {"role": "user", "content": user_content},
                                    ],
                                    "temperature": 0.1,
                                },
                            )
                        else:
                            return cls._mark_analysis_failed(
                                db,
                                doc,
                                analysis,
                                "unsupported_provider",
                                f"Unsupported AI provider: {provider_name}",
                            )

                    if response.status_code != 200:
                        error_code, error_message = cls._classify_http_error(
                            provider_name,
                            response.status_code,
                            response.text,
                            request_id,
                        )
                        logger.error(
                            "provider_request_failed request_id=%s provider=%s status=%d code=%s",
                            request_id,
                            provider_name,
                            response.status_code,
                            error_code,
                        )
                        return cls._mark_analysis_failed(
                            db, doc, analysis, error_code, error_message
                        )

                    provider_response = response.json()
                    raw_content = (
                        provider_response["choices"][0]["message"]["content"] or ""
                    )
                except Exception as exc:
                    return cls._mark_analysis_failed(
                        db,
                        doc,
                        analysis,
                        "invalid_provider_response",
                        "The AI provider returned an unusable response.",
                    )

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
                logger.error(
                    "invalid_provider_response request_id=%s parse_exc=%s",
                    request_id,
                    parse_exc,
                )
                return cls._mark_analysis_failed(
                    db,
                    doc,
                    analysis,
                    "invalid_provider_response",
                    "The AI provider returned an unusable response.",
                )

            logger.info(
                "provider_request_succeeded request_id=%s document_id=%s",
                request_id,
                doc.id,
            )
            return cls._persist_analysis_output(
                db=db,
                doc=doc,
                analysis=analysis,
                user_id=user_id,
                parsed_data=validated.model_dump(),
            )

        except Exception as exc:
            error_code, error_message = cls._classify_exception(exc, request_id)
            logger.exception(
                "analysis_exception request_id=%s document_id=%s code=%s",
                request_id,
                doc.id,
                error_code,
            )
            return cls._mark_analysis_failed(
                db, doc, analysis, error_code, error_message
            )

    @staticmethod
    def _mark_analysis_failed(
        db: Session,
        doc: MedicalDocument,
        analysis: DocumentAnalysis,
        error_code: str,
        error_message: str,
    ) -> DocumentAnalysis:
        """Persist a consistent failed state for both analysis and document."""
        analysis.status = "failed"
        analysis.error_code = error_code
        analysis.error_message = error_message
        analysis.completed_at = datetime.now(timezone.utc)

        doc.status = "failed"
        doc.failure_code = error_code
        doc.failure_message = error_message

        db.commit()
        db.refresh(analysis)
        return analysis

    @staticmethod
    def _persist_analysis_output(
        db: Session,
        doc: MedicalDocument,
        analysis: DocumentAnalysis,
        user_id: UUID,
        parsed_data: dict[str, Any],
    ) -> DocumentAnalysis:
        """Replace derived child records and persist validated analysis output."""
        try:
            # Remove stale document-level measurements/flags before inserting the
            # current analysis results. Findings are scoped to this analysis version.
            db.execute(
                delete(AbnormalityFlag).where(
                    AbnormalityFlag.document_id == doc.id
                )
            )
            db.execute(
                delete(MedicalMeasurement).where(
                    MedicalMeasurement.document_id == doc.id
                )
            )
            db.execute(
                delete(ExtractedFinding).where(
                    ExtractedFinding.analysis_id == analysis.id
                )
            )

            analysis.summary = parsed_data.get("summary")
            analysis.key_points = parsed_data.get("key_points", [])
            analysis.status = "completed"
            analysis.error_code = None
            analysis.error_message = None
            analysis.completed_at = datetime.now(timezone.utc)

            report_date_str = parsed_data.get("report_date")
            if report_date_str and not doc.report_date:
                try:
                    doc.report_date = datetime.strptime(
                        str(report_date_str), "%Y-%m-%d"
                    ).date()
                except ValueError:
                    logger.warning(
                        "invalid_report_date document_id=%s value=%r",
                        doc.id,
                        report_date_str,
                    )

            doc_date = doc.report_date or date.today()

            # Persist extracted findings.
            finding_objects: list[ExtractedFinding] = []
            for item in parsed_data.get("findings", []):
                name = str(item.get("name", "")).strip()
                if not name:
                    continue

                numeric_value = item.get("numeric_value")
                reference_low = item.get("reference_low")
                reference_high = item.get("reference_high")
                confidence = item.get("confidence")

                finding = ExtractedFinding(
                    analysis_id=analysis.id,
                    document_id=doc.id,
                    user_id=user_id,
                    category=str(item.get("category", "general"))[:40],
                    finding_type=str(item.get("finding_type", "test_result"))[:80],
                    name=name[:255],
                    value_text=(
                        str(item.get("value_text", ""))[:500]
                        if item.get("value_text")
                        else None
                    ),
                    numeric_value=(
                        Decimal(str(numeric_value))
                        if numeric_value is not None
                        else None
                    ),
                    unit=str(item.get("unit", ""))[:60] if item.get("unit") else None,
                    reference_low=(
                        Decimal(str(reference_low))
                        if reference_low is not None
                        else None
                    ),
                    reference_high=(
                        Decimal(str(reference_high))
                        if reference_high is not None
                        else None
                    ),
                    reference_text=(
                        str(item.get("reference_text", ""))[:255]
                        if item.get("reference_text")
                        else None
                    ),
                    source_page=item.get("source_page", 1),
                    confidence=(
                        Decimal(str(confidence)) if confidence is not None else None
                    ),
                    is_extracted=True,
                )
                db.add(finding)
                finding_objects.append(finding)

            db.flush()
            finding_by_name = {
                finding.name.lower(): finding.id for finding in finding_objects
            }

            # Persist numeric measurements.
            measurement_objects: list[MedicalMeasurement] = []
            for item in parsed_data.get("measurements", []):
                parameter_name = str(item.get("parameter_name", "")).strip()
                numeric_value = item.get("numeric_value")
                unit = str(item.get("unit", "")).strip()
                if not parameter_name or numeric_value is None or not unit:
                    continue

                reference_low = item.get("reference_low")
                reference_high = item.get("reference_high")
                parameter_code = item.get("parameter_code") or parameter_name.lower().replace(" ", "_")

                measurement = MedicalMeasurement(
                    user_id=user_id,
                    document_id=doc.id,
                    source_finding_id=finding_by_name.get(parameter_name.lower()),
                    parameter_name=parameter_name[:160],
                    parameter_code=str(parameter_code)[:100],
                    numeric_value=Decimal(str(numeric_value)),
                    unit=unit[:60],
                    report_date=doc_date,
                    reference_low=(
                        Decimal(str(reference_low))
                        if reference_low is not None
                        else None
                    ),
                    reference_high=(
                        Decimal(str(reference_high))
                        if reference_high is not None
                        else None
                    ),
                    reference_text=(
                        str(item.get("reference_text", ""))[:255]
                        if item.get("reference_text")
                        else None
                    ),
                )
                db.add(measurement)
                measurement_objects.append(measurement)

            db.flush()
            measurement_by_name = {
                measurement.parameter_name.lower(): measurement.id
                for measurement in measurement_objects
            }

            # Persist neutral abnormality/review flags.
            flags_data = parsed_data.get("flags", [])
            for item in flags_data:
                parameter_name = str(item.get("parameter_name", "")).strip()
                if not parameter_name:
                    continue

                observed_value = item.get("observed_value")
                severity = str(item.get("severity", "review"))[:20]
                if severity not in {"info", "review", "high"}:
                    severity = "review"

                flag = AbnormalityFlag(
                    user_id=user_id,
                    document_id=doc.id,
                    source_finding_id=finding_by_name.get(parameter_name.lower()),
                    measurement_id=measurement_by_name.get(parameter_name.lower()),
                    parameter_name=parameter_name[:160],
                    observed_value=(
                        Decimal(str(observed_value))
                        if observed_value is not None
                        else None
                    ),
                    unit=str(item.get("unit", ""))[:60] if item.get("unit") else None,
                    reference_text=(
                        str(item.get("reference_text"))[:255]
                        if item.get("reference_text")
                        else None
                    ),
                    flag_type=str(item.get("flag_type", "needs_review"))[:30],
                    severity=severity,
                    explanation=(
                        str(item.get("explanation", ""))[:1000]
                        if item.get("explanation")
                        else None
                    ),
                )
                db.add(flag)

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
            logger.exception(
                "persistence_failed document_id=%s analysis_id=%s: %s",
                doc.id,
                analysis.id,
                exc,
            )
            # Reload ORM instances after rollback before updating their state.
            refreshed_doc = db.get(MedicalDocument, doc.id)
            refreshed_analysis = db.get(DocumentAnalysis, analysis.id)
            if refreshed_doc is None or refreshed_analysis is None:
                raise
            return MedicalAnalysisService._mark_analysis_failed(
                db,
                refreshed_doc,
                refreshed_analysis,
                "persistence_failed",
                "Could not save the extracted medical analysis. Please retry.",
            )


analysis_service = MedicalAnalysisService()
