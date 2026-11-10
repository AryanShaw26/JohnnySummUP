import json
import logging
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.abnormality_flag import AbnormalityFlag
from app.models.document_analysis import DocumentAnalysis
from app.models.extracted_finding import ExtractedFinding
from app.models.medical_document import MedicalDocument
from app.models.medical_measurement import MedicalMeasurement
from app.services.medical.extraction import ExtractionResult

logger = logging.getLogger("johnnysummup.medical.analysis")


class ConcurrentAnalysisError(Exception):
    """Raised when an analysis is already actively in-flight on a document."""
    pass


STANDARD_ERROR_MESSAGES = {
    "quota_exceeded": "The selected AI provider has exhausted its available quota. Check the provider project, billing and limits.",
    "rate_limited": "The AI provider is temporarily rate-limiting requests. Please retry shortly.",
    "authentication_failed": "AI provider authentication failed. Check the configured API key.",
    "model_unavailable": "The configured AI model is unavailable for this provider account.",
    "provider_unavailable": "Could not connect to the AI provider. Please retry.",
    "provider_timeout": "AI analysis timed out. Please retry.",
    "invalid_provider_response": "The AI provider returned an unusable response.",
    "extraction_empty": "No readable text was extracted. Try a clearer scan or another file.",
    "provider_error": "AI analysis failed.",
}

SYSTEM_PROMPT = """You are a medical document analyzer for JohnnySummUP.
Analyze the provided medical report text and extract structured information strictly according to what is present in the document.

SAFETY AND INTEGRITY RULES:
1. NEVER diagnose diseases, conditions, or suggest medical treatments.
2. Only extract values and reference ranges that explicitly exist in the report. NEVER invent or hallucinate reference ranges.
3. If a reference range is absent, leave reference_low, reference_high, and reference_text as null.
4. For prescriptions, extract medicine name, dosage, frequency, and instructions if stated; do NOT infer missing values.
5. Only flag an item as out-of-range ('below_range' or 'above_range') if the report explicitly provides a reference range and the observed numeric value falls outside it. Use neutral phrasing like 'Outside the reference range in this report'.
6. Keep source_page matching the page number indicated in the text (e.g. === PAGE 2 === means source_page 2).
7. Return valid JSON only, with no markdown code blocks or wrapper.

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
    def _chunk_text_by_pages(text: str, max_chunk_chars: int = 25000) -> list[str]:
        """
        Splits long document text strictly along '=== PAGE ' boundaries.
        Never splits a single page across chunks to preserve table rows.
        """
        if len(text) <= max_chunk_chars:
            return [text]

        pages = text.split("=== PAGE ")
        chunks: list[str] = []
        current_chunk = ""

        for idx, page in enumerate(pages):
            if not page.strip():
                continue
            reconstructed_page = f"=== PAGE {page}" if idx > 0 else page
            if len(current_chunk) + len(reconstructed_page) > max_chunk_chars and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = reconstructed_page
            else:
                current_chunk = f"{current_chunk}\n\n{reconstructed_page}" if current_chunk else reconstructed_page

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks or [text]

    @staticmethod
    def _classify_openai_error(status_code: int, error_body: dict[str, Any], request_id: str) -> tuple[str, str]:
        code = str(error_body.get("code", "")).lower()
        err_type = str(error_body.get("type", "")).lower()
        msg = str(error_body.get("message", "")).lower()

        if status_code == 429:
            if code == "insufficient_quota" or err_type == "insufficient_quota" or "insufficient_quota" in msg:
                return "quota_exceeded", STANDARD_ERROR_MESSAGES["quota_exceeded"]
            return "rate_limited", STANDARD_ERROR_MESSAGES["rate_limited"]
        elif status_code == 401:
            return "authentication_failed", STANDARD_ERROR_MESSAGES["authentication_failed"]
        elif status_code == 404:
            return "model_unavailable", STANDARD_ERROR_MESSAGES["model_unavailable"]
        elif status_code in (500, 502, 503, 504):
            return "provider_unavailable", STANDARD_ERROR_MESSAGES["provider_unavailable"]
        return "provider_error", f"AI analysis failed. Reference: {request_id}."

    @staticmethod
    def _classify_gemini_error(status_code: int, error_body: dict[str, Any], request_id: str) -> tuple[str, str]:
        status = str(error_body.get("status", "")).upper()
        msg = str(error_body.get("message", "")).lower()
        details = error_body.get("details", [])
        detail_reasons = [str(d.get("reason", "")).upper() for d in details if isinstance(d, dict)]

        if status_code == 429 or status == "RESOURCE_EXHAUSTED":
            if "QUOTA_EXCEEDED" in detail_reasons or "quota" in msg or "billing" in msg:
                return "quota_exceeded", STANDARD_ERROR_MESSAGES["quota_exceeded"]
            return "rate_limited", STANDARD_ERROR_MESSAGES["rate_limited"]
        elif status_code in (400, 403) or status in ("INVALID_ARGUMENT", "PERMISSION_DENIED"):
            if "api key" in msg or "key" in msg or status == "PERMISSION_DENIED" or "API_KEY_INVALID" in detail_reasons:
                return "authentication_failed", STANDARD_ERROR_MESSAGES["authentication_failed"]
            return "provider_error", f"AI analysis failed. Reference: {request_id}."
        elif status_code == 404 or status == "NOT_FOUND":
            return "model_unavailable", STANDARD_ERROR_MESSAGES["model_unavailable"]
        elif status_code in (500, 503) or status == "UNAVAILABLE":
            return "provider_unavailable", STANDARD_ERROR_MESSAGES["provider_unavailable"]
        return "provider_error", f"AI analysis failed. Reference: {request_id}."

    @staticmethod
    async def run_analysis(
        db: Session,
        document_id: UUID,
        user_id: UUID,
        extracted_text: str = "",
        document_type: str = "other",
        mock_response: dict[str, Any] | None = None,
        extraction_result: ExtractionResult | None = None,
        requested_provider: str | None = None,
    ) -> DocumentAnalysis:
        request_id = f"req_{uuid4().hex[:12]}"
        settings = get_settings()

        # 1. Atomic reservation of processing status to eliminate duplicate analysis runs
        stmt = (
            update(MedicalDocument)
            .where(
                MedicalDocument.id == document_id,
                MedicalDocument.user_id == user_id,
                MedicalDocument.status != "processing",
            )
            .values(status="processing")
        )
        lock_res = db.execute(stmt)
        db.commit()

        if lock_res.rowcount == 0:
            doc = db.get(MedicalDocument, document_id)
            if not doc or doc.user_id != user_id:
                raise ValueError("Document not found or ownership mismatch")
            if doc.status == "processing":
                raise ConcurrentAnalysisError("Analysis is already actively running on this document.")
        else:
            doc = db.get(MedicalDocument, document_id)

        # Determine next version
        existing_versions = [a.version for a in doc.analyses] if doc.analyses else []
        next_version = (max(existing_versions) + 1) if existing_versions else 1

        effective_text = (
            extraction_result.full_text if (extraction_result and extraction_result.full_text) else extracted_text
        )
        extraction_method = (
            extraction_result.extraction_method if extraction_result else "pdf_text"
        )
        page_count = (
            extraction_result.page_count
            if extraction_result
            else (1 if effective_text else 0)
        )
        ocr_pages = extraction_result.ocr_page_count if extraction_result else 0

        # Provider determination (strictly no silent fallback between providers)
        selected_provider = (requested_provider or settings.ai_provider or "openai").lower().strip()
        if selected_provider not in ("openai", "gemini"):
            selected_provider = "openai"

        if selected_provider == "openai":
            model_name = settings.openai_model or "gpt-4o-mini"
            api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
        else:
            model_name = settings.gemini_model or "gemini-1.5-flash"
            api_key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None

        active_provider = "mock" if mock_response is not None else selected_provider
        active_model = "mock" if mock_response is not None else model_name

        analysis = DocumentAnalysis(
            document_id=doc.id,
            user_id=user_id,
            version=next_version,
            status="processing",
            extraction_method=extraction_method,
            extracted_page_count=page_count,
            ocr_page_count=ocr_pages,
            extracted_text=effective_text[:20000] if effective_text else None,
            provider=active_provider,
            model_name=active_model,
            prompt_version="v1.0",
            started_at=datetime.now(timezone.utc),
        )
        db.add(analysis)
        doc.status = "processing"
        db.commit()
        db.refresh(analysis)

        # Safe diagnostic logging (no medical text or secrets)
        total_chars = len(effective_text)
        est_tokens = total_chars // 4
        logger.info(
            "analysis_started request_id=%s doc_id=%s version=%d provider=%s model=%s pages=%d ocr_pages=%d total_chars=%d est_tokens=%d",
            request_id,
            doc.id,
            analysis.version,
            active_provider,
            active_model,
            page_count,
            ocr_pages,
            total_chars,
            est_tokens,
        )

        # 2. Handle extraction failure or OCR unavailability
        if extraction_result and extraction_result.status in (
            "no_readable_text",
            "corrupt",
            "encrypted",
            "ocr_unavailable",
            "failed",
        ):
            logger.warning(
                "extraction_error request_id=%s doc_id=%s status=%s code=%s",
                request_id,
                doc.id,
                extraction_result.status,
                extraction_result.error_code,
            )
            analysis.status = "failed"
            analysis.error_code = extraction_result.error_code or "extraction_empty"
            analysis.error_message = (
                extraction_result.error_message
                or STANDARD_ERROR_MESSAGES.get(analysis.error_code, "We could not extract readable text from this document.")
            )
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "failed"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis

        # 3. Check if extracted text is empty
        if not effective_text.strip():
            logger.warning("extraction_empty request_id=%s doc_id=%s", request_id, doc.id)
            analysis.status = "failed"
            analysis.error_code = "extraction_empty"
            analysis.error_message = STANDARD_ERROR_MESSAGES["extraction_empty"]
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "failed"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis

        # 4. If mock_response is provided for testing, use it directly
        if mock_response is not None:
            return MedicalAnalysisService._persist_analysis_output(
                db=db,
                doc=doc,
                analysis=analysis,
                user_id=user_id,
                parsed_data=mock_response,
            )

        # 5. Check if provider key is configured (never silently fallback)
        if not api_key:
            logger.info("provider_auth_missing request_id=%s doc_id=%s provider=%s", request_id, doc.id, selected_provider)
            analysis.status = "failed"
            analysis.error_code = "authentication_failed"
            analysis.error_message = f"AI provider '{selected_provider}' authentication failed. Check the configured API key."
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "failed"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis

        # 6. Call Selected Provider with bounded chunking
        chunks = MedicalAnalysisService._chunk_text_by_pages(effective_text, max_chunk_chars=25000)
        logger.info("provider_request_started request_id=%s doc_id=%s provider=%s chunks=%d", request_id, doc.id, selected_provider, len(chunks))

        aggregated_output: dict[str, Any] = {
            "summary": "",
            "key_points": [],
            "report_date": None,
            "findings": [],
            "measurements": [],
            "flags": [],
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                for chunk_idx, chunk_text in enumerate(chunks):
                    user_prompt = (
                        f"Document Type: {document_type}\n"
                        f"Filename: {doc.original_filename}\n"
                        f"Part: {chunk_idx + 1} of {len(chunks)}\n\n"
                        f"Document Text:\n{chunk_text}"
                    )

                    if selected_provider == "openai":
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
                    else:  # gemini
                        response = await client.post(
                            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
                            headers={
                                "x-goog-api-key": api_key,
                                "Content-Type": "application/json",
                            },
                            json={
                                "systemInstruction": {
                                    "parts": [{"text": SYSTEM_PROMPT}]
                                },
                                "contents": [
                                    {
                                        "role": "user",
                                        "parts": [{"text": user_prompt}]
                                    }
                                ],
                                "generationConfig": {
                                    "responseMimeType": "application/json",
                                    "temperature": 0.1,
                                },
                            },
                        )

                    if response.status_code != 200:
                        error_body: dict[str, Any] = {}
                        try:
                            resp_json = response.json()
                            error_body = resp_json.get("error", {}) if isinstance(resp_json, dict) else {}
                        except Exception:
                            pass

                        if selected_provider == "openai":
                            err_code, err_msg = MedicalAnalysisService._classify_openai_error(
                                response.status_code, error_body, request_id
                            )
                        else:
                            err_code, err_msg = MedicalAnalysisService._classify_gemini_error(
                                response.status_code, error_body, request_id
                            )

                        logger.error(
                            "provider_request_failed request_id=%s doc_id=%s provider=%s status=%d code=%s",
                            request_id,
                            doc.id,
                            selected_provider,
                            response.status_code,
                            err_code,
                        )

                        analysis.status = "failed"
                        analysis.error_code = err_code
                        analysis.error_message = err_msg
                        analysis.completed_at = datetime.now(timezone.utc)
                        doc.status = "failed"
                        doc.failure_code = analysis.error_code
                        doc.failure_message = analysis.error_message
                        db.commit()
                        return analysis

                    # Parse response depending on provider
                    resp_data = response.json()
                    if selected_provider == "openai":
                        raw_content = resp_data["choices"][0]["message"]["content"] or ""
                    else:
                        candidates = resp_data.get("candidates", [])
                        if not candidates:
                            raise ValidationError.from_exception_data(
                                title="GeminiEmptyCandidates",
                                line_errors=[],
                            )
                        raw_content = candidates[0]["content"]["parts"][0]["text"] or ""

                    clean_content = raw_content.strip()
                    if clean_content.startswith("```json"):
                        clean_content = clean_content[7:]
                    elif clean_content.startswith("```"):
                        clean_content = clean_content[3:]
                    if clean_content.endswith("```"):
                        clean_content = clean_content[:-3]
                    clean_content = clean_content.strip()

                    parsed_chunk = json.loads(clean_content)
                    validated_chunk = RawAnalysisOutput.model_validate(parsed_chunk)

                    # Accumulate chunk results
                    if not aggregated_output["summary"]:
                        aggregated_output["summary"] = validated_chunk.summary
                    else:
                        aggregated_output["summary"] += f"\n\n{validated_chunk.summary}"

                    aggregated_output["key_points"].extend(validated_chunk.key_points)
                    if validated_chunk.report_date and not aggregated_output["report_date"]:
                        aggregated_output["report_date"] = validated_chunk.report_date

                    aggregated_output["findings"].extend([f.model_dump() for f in validated_chunk.findings])
                    aggregated_output["measurements"].extend([m.model_dump() for m in validated_chunk.measurements])
                    aggregated_output["flags"].extend([fl.model_dump() for fl in validated_chunk.flags])

            logger.info("provider_request_succeeded request_id=%s doc_id=%s provider=%s", request_id, doc.id, selected_provider)
            return MedicalAnalysisService._persist_analysis_output(
                db=db,
                doc=doc,
                analysis=analysis,
                user_id=user_id,
                parsed_data=aggregated_output,
            )

        except (httpx.TimeoutException, TimeoutError):
            logger.error("provider_timeout request_id=%s doc_id=%s provider=%s", request_id, doc.id, selected_provider)
            analysis.status = "failed"
            analysis.error_code = "provider_timeout"
            analysis.error_message = STANDARD_ERROR_MESSAGES["provider_timeout"]
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "failed"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis

        except httpx.RequestError as req_err:
            logger.error("provider_network_error request_id=%s doc_id=%s error=%s", request_id, doc.id, req_err)
            analysis.status = "failed"
            analysis.error_code = "provider_unavailable"
            analysis.error_message = STANDARD_ERROR_MESSAGES["provider_unavailable"]
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "failed"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis

        except (json.JSONDecodeError, ValidationError, KeyError, IndexError) as schema_err:
            logger.error("response_validation_failed request_id=%s doc_id=%s error=%s", request_id, doc.id, schema_err)
            analysis.status = "failed"
            analysis.error_code = "invalid_provider_response"
            analysis.error_message = STANDARD_ERROR_MESSAGES["invalid_provider_response"]
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "failed"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis

        except Exception as exc:
            logger.exception("analysis_unexpected_exception request_id=%s doc_id=%s error=%s", request_id, doc.id, exc)
            db.rollback()
            analysis.status = "failed"
            analysis.error_code = "provider_error"
            analysis.error_message = f"AI analysis failed. Reference: {request_id}."
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "failed"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis

    @staticmethod
    async def test_provider_connectivity(provider: str | None = None) -> dict[str, Any]:
        settings = get_settings()
        selected_provider = (provider or settings.ai_provider or "openai").lower().strip()
        request_id = f"diag_{uuid4().hex[:12]}"
        start_time = time.time()

        if selected_provider not in ("openai", "gemini"):
            return {
                "success": False,
                "provider": selected_provider,
                "model": "unknown",
                "key_present": False,
                "latency_ms": 0,
                "error_code": "model_unavailable",
                "error_message": f"Unsupported provider '{selected_provider}'.",
                "request_id": request_id,
            }

        if selected_provider == "openai":
            model = settings.openai_model or "gpt-4o-mini"
            key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
        else:
            model = settings.gemini_model or "gemini-1.5-flash"
            key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None

        key_present = bool(key)
        if not key_present:
            return {
                "success": False,
                "provider": selected_provider,
                "model": model,
                "key_present": False,
                "latency_ms": 0,
                "error_code": "authentication_failed",
                "error_message": f"No API key configured for {selected_provider}.",
                "request_id": request_id,
            }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                if selected_provider == "openai":
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": "ping"}],
                            "max_tokens": 5,
                        },
                    )
                    latency_ms = int((time.time() - start_time) * 1000)
                    if resp.status_code == 200:
                        return {
                            "success": True,
                            "provider": selected_provider,
                            "model": model,
                            "key_present": True,
                            "latency_ms": latency_ms,
                            "error_code": None,
                            "error_message": None,
                            "request_id": request_id,
                        }
                    err_body = resp.json().get("error", {}) if resp.content else {}
                    code, msg = MedicalAnalysisService._classify_openai_error(resp.status_code, err_body, request_id)
                    return {
                        "success": False,
                        "provider": selected_provider,
                        "model": model,
                        "key_present": True,
                        "latency_ms": latency_ms,
                        "error_code": code,
                        "error_message": msg,
                        "request_id": request_id,
                    }
                else:
                    resp = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                        json={"contents": [{"parts": [{"text": "ping"}]}]},
                    )
                    latency_ms = int((time.time() - start_time) * 1000)
                    if resp.status_code == 200:
                        return {
                            "success": True,
                            "provider": selected_provider,
                            "model": model,
                            "key_present": True,
                            "latency_ms": latency_ms,
                            "error_code": None,
                            "error_message": None,
                            "request_id": request_id,
                        }
                    err_body = resp.json().get("error", {}) if resp.content else {}
                    code, msg = MedicalAnalysisService._classify_gemini_error(resp.status_code, err_body, request_id)
                    return {
                        "success": False,
                        "provider": selected_provider,
                        "model": model,
                        "key_present": True,
                        "latency_ms": latency_ms,
                        "error_code": code,
                        "error_message": msg,
                        "request_id": request_id,
                    }
        except (httpx.TimeoutException, TimeoutError):
            return {
                "success": False,
                "provider": selected_provider,
                "model": model,
                "key_present": True,
                "latency_ms": int((time.time() - start_time) * 1000),
                "error_code": "provider_timeout",
                "error_message": STANDARD_ERROR_MESSAGES["provider_timeout"],
                "request_id": request_id,
            }
        except httpx.RequestError:
            return {
                "success": False,
                "provider": selected_provider,
                "model": model,
                "key_present": True,
                "latency_ms": int((time.time() - start_time) * 1000),
                "error_code": "provider_unavailable",
                "error_message": STANDARD_ERROR_MESSAGES["provider_unavailable"],
                "request_id": request_id,
            }
        except Exception:
            return {
                "success": False,
                "provider": selected_provider,
                "model": model,
                "key_present": True,
                "latency_ms": int((time.time() - start_time) * 1000),
                "error_code": "provider_error",
                "error_message": f"AI analysis failed. Reference: {request_id}.",
                "request_id": request_id,
            }

    @staticmethod
    def _persist_analysis_output(
        db: Session,
        doc: MedicalDocument,
        analysis: DocumentAnalysis,
        user_id: UUID,
        parsed_data: dict[str, Any],
    ) -> DocumentAnalysis:
        try:
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
                "analysis_persisted document_id=%s findings=%d measurements=%d flags=%d",
                doc.id,
                len(finding_objects),
                len(measurement_objects),
                len(flags_data),
            )
            return analysis

        except Exception as exc:
            logger.exception("persistence_failure document_id=%s error=%s", doc.id, exc)
            db.rollback()
            analysis.status = "failed"
            analysis.error_code = "DATABASE_PERSISTENCE_ERROR"
            analysis.error_message = "Failed to safely persist extracted analysis results to database."
            analysis.completed_at = datetime.now(timezone.utc)
            doc.status = "failed"
            doc.failure_code = analysis.error_code
            doc.failure_message = analysis.error_message
            db.commit()
            return analysis


analysis_service = MedicalAnalysisService()
