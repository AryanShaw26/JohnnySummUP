import json
import logging
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.abnormality_flag import AbnormalityFlag
from app.models.document_analysis import DocumentAnalysis
from app.models.extracted_finding import ExtractedFinding
from app.models.medical_document import MedicalDocument
from app.models.medical_measurement import MedicalMeasurement

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
        Returns: (provider_name, model_name, api_key_or_none)
        """
        settings = get_settings()
        openai_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
        gemini_key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None

        req = (requested_provider or "").strip().lower()

        if req == "gemini":
            return "gemini", settings.gemini_model, gemini_key
        elif req == "openai":
            return "openai", settings.openai_model, openai_key
        else:
            # Default fallback based on configured keys
            if settings.default_ai_provider == "gemini" and gemini_key:
                return "gemini", settings.gemini_model, gemini_key
            if openai_key:
                return "openai", settings.openai_model, openai_key
            if gemini_key:
                return "gemini", settings.gemini_model, gemini_key
            # Neither configured, default to settings preference
            chosen = settings.default_ai_provider
            chosen_model = settings.gemini_model if chosen == "gemini" else settings.openai_model
            return chosen, chosen_model, None

    @staticmethod
    def get_provider_diagnostics() -> dict[str, Any]:
        """Returns provider availability and configuration metadata without exposing secret keys."""
        settings = get_settings()
        return {
            "openai": {
                "configured": bool(settings.openai_api_key and settings.openai_api_key.get_secret_value()),
                "model": settings.openai_model,
            },
            "gemini": {
                "configured": bool(settings.gemini_api_key and settings.gemini_api_key.get_secret_value()),
                "model": settings.gemini_model,
            },
            "default_provider": settings.default_ai_provider,
        }

    @classmethod
    async def test_provider_connectivity(cls, provider: str) -> dict[str, Any]:
        """Runs a minimal non-medical connectivity check against the requested provider."""
        settings = get_settings()
        request_id = str(uuid4())
        start_time = time.time()

        prov, model_name, api_key = cls.resolve_provider(provider)
        if not api_key:
            return {
                "success": False,
                "provider": prov,
                "model": model_name,
                "request_id": request_id,
                "error_code": "authentication_failed",
                "error_message": f"AI provider '{prov}' is not configured with an API key.",
                "duration_ms": int((time.time() - start_time) * 1000),
            }

        try:
            if prov == "gemini":
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}",
                        headers={"Content-Type": "application/json"},
                        json={
                            "contents": [{"parts": [{"text": "Return JSON: {\"status\": \"ok\"}"}]}],
                            "generationConfig": {"responseMimeType": "application/json"},
                        },
                    )
            else:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model_name,
                            "messages": [{"role": "user", "content": "Return JSON: {\"status\": \"ok\"}"}],
                            "response_format": {"type": "json_object"},
                            "temperature": 0.0,
                        },
                    )

            duration_ms = int((time.time() - start_time) * 1000)

            if resp.status_code == 200:
                return {
                    "success": True,
                    "provider": prov,
                    "model": model_name,
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                }

            error_code, error_msg = cls._classify_http_error(prov, resp.status_code, resp.text, request_id)
            return {
                "success": False,
                "provider": prov,
                "model": model_name,
                "request_id": request_id,
                "error_code": error_code,
                "error_message": error_msg,
                "duration_ms": duration_ms,
            }
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            error_code, error_msg = cls._classify_exception(exc, request_id)
            return {
                "success": False,
                "provider": prov,
                "model": model_name,
                "request_id": request_id,
                "error_code": error_code,
                "error_message": error_msg,
                "duration_ms": duration_ms,
            }

    @staticmethod
    def _classify_http_error(provider: str, status_code: int, response_text: str, request_id: str) -> tuple[str, str]:
        """Classifies HTTP errors into standardized error codes and safe messages (Section 5.3)."""
        body_str = response_text.lower()

        if status_code == 429:
            # Distinguish actual exhausted billing quota from transient rate limits
            if any(term in body_str for term in ["insufficient_quota", "quota_exceeded", "resource_exhausted", "quota", "credit"]):
                return (
                    "quota_exceeded",
                    "The selected AI provider has exhausted its available quota. Check the provider project, billing and limits.",
                )
            return (
                "rate_limited",
                "The AI provider is temporarily rate-limiting requests. Please retry shortly.",
            )
        elif status_code in (401, 403):
            if "api_key_invalid" in body_str or "unauthorized" in body_str or "invalid" in body_str:
                return (
                    "authentication_failed",
                    "AI provider authentication failed. Check the configured API key.",
                )
            if "quota" in body_str or "resource_exhausted" in body_str:
                return (
                    "quota_exceeded",
                    "The selected AI provider has exhausted its available quota. Check the provider project, billing and limits.",
                )
            return (
                "authentication_failed",
                "AI provider authentication failed. Check the configured API key.",
            )
        elif status_code == 404:
            return (
                "model_unavailable",
                "The configured AI model is unavailable for this provider account.",
            )
        elif status_code >= 500:
            return (
                "provider_unavailable",
                "Could not connect to the AI provider. Please retry.",
            )
        else:
            return (
                "provider_error",
                f"AI analysis failed. Reference: {request_id}",
            )

    @staticmethod
    def _classify_exception(exc: Exception, request_id: str) -> tuple[str, str]:
        """Classifies runtime and network exceptions."""
        if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
            return "provider_timeout", "AI analysis timed out. Please retry."
        elif isinstance(exc, httpx.RequestError):
            return "provider_unavailable", "Could not connect to the AI provider. Please retry."
        elif isinstance(exc, (json.JSONDecodeError, ValidationError)):
            return "invalid_provider_response", "The AI provider returned an unusable response."
        else:
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
    ) -> DocumentAnalysis:
        request_id = str(uuid4())

        # Find document
        doc = db.get(MedicalDocument, document_id)
        if not doc or doc.user_id != user_id:
            raise ValueError("Document not found or ownership mismatch")

        # Determine next version
        existing_versions = [a.version for a in doc.analyses] if doc.analyses else []
        next_version = (max(existing_versions) + 1) if existing_versions else 1

        provider_name, model_name, api_key = cls.resolve_provider(requested_provider)

        analysis = DocumentAnalysis(
            document_id=doc.id,
            user_id=user_id,
            version=next_version,
            status="processing",
            extracted_text=extracted_text[:12000] if extracted_text else None,
            provider="mock" if mock_response is not None else provider_name,
            model_name="mock" if mock_response is not None else model_name,
            prompt_version="v1.1",
            started_at=datetime.now(timezone.utc),
        )
        db.add(analysis)
        doc.status = "processing"
        db.commit()
        db.refresh(analysis)

        logger.info(
            "analysis_queued request_id=%s document_id=%s analysis_id=%s version=%d provider=%s model=%s",
            request_id,
            doc.id,
            analysis.id,
            analysis.version,
            provider_name,
            model_name,
        )

        # Check if text is present
        if not extracted_text or not extracted_text.strip():
            logger.warning("extraction_failed_no_text request_id=%s document_id=%s", request_id, doc.id)
            analysis.status = "failed"
            analysis.error_code = "extraction_empty"
            analysis.error_message = "No readable text was extracted. Try a clearer scan or another file."
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "failed"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis

        # If mock_response is provided for testing, use it directly
        if mock_response is not None:
            return cls._persist_analysis_output(
                db=db,
                doc=doc,
                analysis=analysis,
                user_id=user_id,
                parsed_data=mock_response,
            )

        # Check if API key is configured for selected provider
        if not api_key:
            logger.info("provider_not_configured request_id=%s provider=%s", request_id, provider_name)
            analysis.status = "unavailable"
            analysis.error_code = "AI_NOT_CONFIGURED"
            analysis.error_message = (
                f"AI analysis with {provider_name.upper()} is not configured on this server. Document is safely stored."
            )
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "analysis_unavailable"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis

        # Bound extracted text to avoid prompt exhaustion and wrap in untrusted data delimiters
        safe_text = extracted_text[:10000]
        user_prompt = (
            f"Document Type: {document_type}\n"
            f"Filename: {doc.original_filename}\n\n"
            f"<DOCUMENT_CONTENT>\n{safe_text}\n</DOCUMENT_CONTENT>"
        )

        logger.info(
            "provider_request_started request_id=%s document_id=%s provider=%s model=%s",
            request_id,
            doc.id,
            provider_name,
            model_name,
        )

        try:
            raw_content = ""
            if provider_name == "gemini":
                # Google Gemini API Call
                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                async with httpx.AsyncClient(timeout=45.0) as client:
                    response = await client.post(
                        gemini_url,
                        headers={"Content-Type": "application/json"},
                        json={
                            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                            "contents": [{"parts": [{"text": user_prompt}]}],
                            "generationConfig": {
                                "temperature": 0.1,
                                "responseMimeType": "application/json",
                            },
                        },
                    )
                if response.status_code != 200:
                    err_code, err_msg = cls._classify_http_error("gemini", response.status_code, response.text, request_id)
                    logger.error("gemini_request_failed request_id=%s status=%d code=%s", request_id, response.status_code, err_code)
                    return cls._mark_analysis_failed(db, doc, analysis, err_code, err_msg)

                gemini_resp = response.json()
                try:
                    raw_content = gemini_resp["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    return cls._mark_analysis_failed(
                        db, doc, analysis, "invalid_provider_response", "The AI provider returned an unusable response."
                    )
            else:
                # OpenAI Chat Completion Call
                async with httpx.AsyncClient(timeout=45.0) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model_name,
                            "response_format": {"type": "json_object"},
                            "messages": [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": user_prompt},
                            ],
                            "temperature": 0.1,
                        },
                    )
                if response.status_code != 200:
                    err_code, err_msg = cls._classify_http_error("openai", response.status_code, response.text, request_id)
                    logger.error("openai_request_failed request_id=%s status=%d code=%s", request_id, response.status_code, err_code)
                    return cls._mark_analysis_failed(db, doc, analysis, err_code, err_msg)

                openai_resp = response.json()
                try:
                    raw_content = openai_resp["choices"][0]["message"]["content"] or ""
                except (KeyError, IndexError):
                    return cls._mark_analysis_failed(
                        db, doc, analysis, "invalid_provider_response", "The AI provider returned an unusable response."
                    )

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

            logger.info("provider_request_succeeded request_id=%s document_id=%s", request_id, doc.id)

            return cls._persist_analysis_output(
                db=db,
                doc=doc,
                analysis=analysis,
                user_id=user_id,
                parsed_data=validated.model_dump(),
            )

        except Exception as exc:
            err_code, err_msg = cls._classify_exception(exc, request_id)
            logger.error("analysis_exception request_id=%s error=%s code=%s", request_id, exc, err_code)
            return cls._mark_analysis_failed(db, doc, analysis, err_code, err_msg)

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

        # Clean any stale child findings/measurements/flags for this analysis to prevent duplication
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
