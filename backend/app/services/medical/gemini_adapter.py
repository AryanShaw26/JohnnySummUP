import asyncio
import logging
import time
from typing import Any
from uuid import uuid4

from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.core.config import get_settings

logger = logging.getLogger("johnnysummup.medical.gemini")

# Error message mappings according to JohnnySummUP specification (Section 6)
ERROR_MESSAGES: dict[str, str] = {
    "provider_not_configured": "Gemini AI is not configured. Add a valid server-side API key.",
    "authentication_failed": "Gemini authentication failed. Check the configured API key.",
    "quota_exceeded": "Gemini quota is exhausted for this project/model. Check project limits and billing.",
    "rate_limited": "Gemini is temporarily rate-limiting requests. Retry later.",
    "model_unavailable": "The configured Gemini model is unavailable for this API project.",
    "permission_denied": "This Gemini API project does not have permission to use the requested service/model.",
    "provider_unavailable": "Could not connect to Gemini. Please retry.",
    "provider_timeout": "Gemini analysis timed out. Please retry.",
    "provider_blocked": "Gemini could not process this request. Review the document or try another supported input.",
    "empty_provider_response": "Gemini returned no usable analysis. Please retry.",
    "invalid_provider_response": "Gemini returned an unusable response.",
    "extraction_failed": "We could not extract readable text from this document.",
    "persistence_failed": "The analysis could not be saved. Please retry.",
    "provider_error": "AI analysis failed. Reference: {request_id}",
}

QUOTA_KEYWORDS = (
    "quota",
    "exhausted",
    "resource_exhausted",
    "credit",
    "billing",
    "free tier",
    "insufficient_quota",
)


class GeminiAdapterError(Exception):
    def __init__(self, error_code: str, user_message: str | None = None, details: Any = None):
        msg = user_message or ERROR_MESSAGES.get(error_code, f"AI analysis failed ({error_code})")
        super().__init__(msg)
        self.error_code = error_code
        self.user_message = msg
        self.details = details


class GeminiAdapter:
    """Official Gemini SDK provider adapter for JohnnySummUP Medical AI."""

    @classmethod
    def get_client(cls, api_key: str | None = None) -> genai.Client:
        settings = get_settings()
        key = api_key or (settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None)
        if not key:
            raise GeminiAdapterError("provider_not_configured")
        return genai.Client(api_key=key)

    @classmethod
    def classify_api_error(cls, exc: APIError, request_id: str) -> tuple[str, str]:
        status_code = getattr(exc, "code", None)
        message = str(getattr(exc, "message", exc) or "").lower()
        resp_json = str(getattr(exc, "response_json", "") or "").lower()
        combined = f"{message} {resp_json}"

        if status_code == 401 or "unauthenticated" in combined:
            code = "authentication_failed"
        elif status_code == 403 or "permission_denied" in combined:
            code = "permission_denied"
        elif status_code == 404 or "not_found" in combined or ("model" in combined and "not found" in combined):
            code = "model_unavailable"
        elif status_code == 429 or "resource_exhausted" in combined:
            if any(k in combined for k in QUOTA_KEYWORDS):
                code = "quota_exceeded"
            else:
                code = "rate_limited"
        elif status_code in (500, 502, 503, 504) or "server error" in combined or "unavailable" in combined:
            code = "provider_unavailable"
        else:
            code = "provider_error"

        user_msg = ERROR_MESSAGES[code].format(request_id=request_id)
        return code, user_msg

    @classmethod
    async def generate_content(
        cls,
        prompt: str,
        system_instruction: str,
        timeout_seconds: float = 45.0,
        api_key_override: str | None = None,
        model_override: str | None = None,
    ) -> dict[str, Any]:
        """Submits content generation request to Gemini via official google-genai SDK."""
        settings = get_settings()
        model_name = model_override or settings.gemini_model
        request_id = str(uuid4())
        start_time = time.time()

        # 1. Check configuration
        key = api_key_override or (settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None)
        if not key:
            raise GeminiAdapterError("provider_not_configured")

        client = cls.get_client(api_key=key)

        logger.info(
            "gemini_request_started request_id=%s model=%s prompt_len=%d",
            request_id,
            model_name,
            len(prompt),
        )

        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1,
                response_mime_type="application/json",
            )

            # Enforce explicit bounded timeout
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                ),
                timeout=timeout_seconds,
            )

        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error("gemini_request_timeout request_id=%s duration_ms=%d", request_id, duration_ms)
            raise GeminiAdapterError("provider_timeout")
        except APIError as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            code, user_msg = cls.classify_api_error(exc, request_id)
            logger.error("gemini_api_error request_id=%s code=%s duration_ms=%d", request_id, code, duration_ms)
            raise GeminiAdapterError(code, user_msg, details=str(exc))
        except GeminiAdapterError:
            raise
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error("gemini_unexpected_error request_id=%s duration_ms=%d: %s", request_id, duration_ms, exc)
            code = "provider_unavailable" if "connection" in str(exc).lower() else "provider_error"
            user_msg = ERROR_MESSAGES[code].format(request_id=request_id)
            raise GeminiAdapterError(code, user_msg, details=str(exc))

        duration_ms = int((time.time() - start_time) * 1000)

        # 2. Check candidates and safety block
        if not response.candidates:
            logger.warning("gemini_empty_candidates request_id=%s duration_ms=%d", request_id, duration_ms)
            raise GeminiAdapterError("empty_provider_response")

        candidate = response.candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        finish_reason_str = str(finish_reason).upper() if finish_reason else ""

        blocked_reasons = ("SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT", "RECITATION")
        if any(r in finish_reason_str for r in blocked_reasons):
            logger.warning(
                "gemini_candidate_blocked request_id=%s reason=%s",
                request_id,
                finish_reason_str,
            )
            raise GeminiAdapterError("provider_blocked")

        # 3. Extract text content
        raw_text = ""
        if candidate.content and candidate.content.parts:
            parts_text = [p.text for p in candidate.content.parts if getattr(p, "text", None)]
            raw_text = "".join(parts_text).strip()

        if not raw_text:
            logger.warning("gemini_empty_text request_id=%s duration_ms=%d", request_id, duration_ms)
            raise GeminiAdapterError("empty_provider_response")

        # 4. Extract usage metadata safely
        usage_meta = getattr(response, "usage_metadata", None)
        input_tokens = getattr(usage_meta, "prompt_token_count", None) if usage_meta else None
        output_tokens = getattr(usage_meta, "candidates_token_count", None) if usage_meta else None

        logger.info(
            "gemini_request_succeeded request_id=%s model=%s duration_ms=%d in_tokens=%s out_tokens=%s",
            request_id,
            model_name,
            duration_ms,
            input_tokens,
            output_tokens,
        )

        return {
            "provider": "gemini",
            "model": model_name,
            "content": raw_text,
            "request_id": request_id,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
        }

    @classmethod
    async def test_connectivity(cls) -> dict[str, Any]:
        """Runs a minimal non-medical ping check against Gemini."""
        settings = get_settings()
        request_id = str(uuid4())
        start_time = time.time()
        model_name = settings.gemini_model

        key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None
        if not key:
            return {
                "success": False,
                "provider": "gemini",
                "model": model_name,
                "request_id": request_id,
                "error_code": "provider_not_configured",
                "error_message": ERROR_MESSAGES["provider_not_configured"],
                "duration_ms": int((time.time() - start_time) * 1000),
            }

        try:
            client = cls.get_client(api_key=key)
            config = types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
            )
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model_name,
                    contents='Return exactly: {"status": "ok"}',
                    config=config,
                ),
                timeout=15.0,
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if response.candidates and response.candidates[0].content:
                return {
                    "success": True,
                    "provider": "gemini",
                    "model": model_name,
                    "request_id": request_id,
                    "duration_ms": duration_ms,
                }
            return {
                "success": False,
                "provider": "gemini",
                "model": model_name,
                "request_id": request_id,
                "error_code": "empty_provider_response",
                "error_message": ERROR_MESSAGES["empty_provider_response"],
                "duration_ms": duration_ms,
            }
        except APIError as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            code, msg = cls.classify_api_error(exc, request_id)
            return {
                "success": False,
                "provider": "gemini",
                "model": model_name,
                "request_id": request_id,
                "error_code": code,
                "error_message": msg,
                "duration_ms": duration_ms,
            }
        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "provider": "gemini",
                "model": model_name,
                "request_id": request_id,
                "error_code": "provider_timeout",
                "error_message": ERROR_MESSAGES["provider_timeout"],
                "duration_ms": duration_ms,
            }
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            code = "provider_unavailable" if "connect" in str(exc).lower() else "provider_error"
            return {
                "success": False,
                "provider": "gemini",
                "model": model_name,
                "request_id": request_id,
                "error_code": code,
                "error_message": ERROR_MESSAGES[code].format(request_id=request_id),
                "duration_ms": duration_ms,
            }
