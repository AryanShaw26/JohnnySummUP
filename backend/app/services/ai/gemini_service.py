import asyncio
import json
import logging
import time
from typing import Any
from uuid import uuid4

from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.services.domains.prompts import DOMAIN_SYSTEM_PROMPTS
from app.services.domains.schemas import (
    EducationAnalysisSchema,
    EmploymentGovernmentAnalysisSchema,
    FinanceAnalysisSchema,
    InsuranceAnalysisSchema,
    LegalAnalysisSchema,
)

logger = logging.getLogger("johnnysummup.ai.gemini")

DOMAIN_SCHEMA_MAP: dict[str, type[BaseModel]] = {
    "legal": LegalAnalysisSchema,
    "finance": FinanceAnalysisSchema,
    "insurance": InsuranceAnalysisSchema,
    "education": EducationAnalysisSchema,
    "employment_government": EmploymentGovernmentAnalysisSchema,
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


class GeminiServiceError(Exception):
    def __init__(self, error_code: str, user_message: str | None = None, details: Any = None):
        super().__init__(user_message or f"AI analysis failed ({error_code})")
        self.error_code = error_code
        self.user_message = user_message or f"AI analysis failed ({error_code})"
        self.details = details


class GeminiWorkspaceService:
    """Unified Gemini integration for all 5 workspaces with chunking and Pydantic validation."""

    @classmethod
    def get_client(cls, api_key: str | None = None) -> genai.Client:
        settings = get_settings()
        key = api_key or (settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None)
        if not key:
            raise GeminiServiceError(
                "provider_not_configured",
                "Gemini AI is not configured. Add a valid server-side API key."
            )
        return genai.Client(api_key=key)

    @classmethod
    def classify_error(cls, exc: Exception, request_id: str) -> tuple[str, str]:
        if isinstance(exc, GeminiServiceError):
            return exc.error_code, exc.user_message

        if isinstance(exc, APIError):
            status_code = getattr(exc, "code", None)
            message = str(getattr(exc, "message", exc) or "").lower()
            resp_json = str(getattr(exc, "response_json", "") or "").lower()
            combined = f"{message} {resp_json}"

            if status_code == 401 or "unauthenticated" in combined:
                return "authentication_failed", "Gemini authentication failed. Check the configured API key."
            elif status_code == 403 or "permission_denied" in combined:
                return "permission_denied", "This Gemini project does not have permission for the requested service."
            elif status_code == 404 or "not_found" in combined:
                return "model_unavailable", "The configured Gemini model is unavailable for this API project."
            elif status_code == 429 or "resource_exhausted" in combined:
                if any(k in combined for k in QUOTA_KEYWORDS):
                    return "quota_exceeded", "Gemini quota is exhausted for this project/model. Check project billing."
                return "rate_limited", "Gemini is temporarily rate-limiting requests. Please retry in a few moments."
            elif status_code in (500, 502, 503, 504) or "unavailable" in combined:
                return "provider_unavailable", "Could not connect to Gemini service. Please retry."

        if isinstance(exc, asyncio.TimeoutError):
            return "provider_timeout", "Gemini analysis timed out. Please retry."

        return "provider_error", f"AI analysis failed. Reference: {request_id}"

    @classmethod
    def chunk_document_text(cls, text: str, max_chunk_chars: int = 14000) -> list[str]:
        """Splits document text along page or paragraph boundaries preserving page references."""
        if len(text) <= max_chunk_chars:
            return [text]

        # Split by page boundary first
        pages = text.split("--- Page ")
        if len(pages) > 1:
            chunks: list[str] = []
            current_chunk = ""
            for p in pages:
                if not p.strip():
                    continue
                page_text = f"--- Page {p}"
                if len(current_chunk) + len(page_text) > max_chunk_chars and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = page_text
                else:
                    current_chunk += "\n\n" + page_text if current_chunk else page_text
            if current_chunk:
                chunks.append(current_chunk.strip())
            return chunks

        # Fallback to paragraph splitting
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) > max_chunk_chars and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    @classmethod
    async def analyze_workspace_document(
        cls,
        workspace: str,
        document_text: str,
        document_subtype: str | None = None,
        timeout_seconds: float = 60.0,
        api_key_override: str | None = None,
        model_override: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyzes document text using Gemini for the specified workspace domain.
        Returns validated structured data dict.
        """
        settings = get_settings()
        model_name = model_override or settings.gemini_model
        request_id = str(uuid4())
        start_time = time.time()

        system_prompt = DOMAIN_SYSTEM_PROMPTS.get(workspace, DOMAIN_SYSTEM_PROMPTS["legal"])
        schema_cls = DOMAIN_SCHEMA_MAP.get(workspace, LegalAnalysisSchema)

        chunks = cls.chunk_document_text(document_text)
        client = cls.get_client(api_key=api_key_override)

        # For single chunk or first chunk
        user_prompt = f"""DOCUMENT METADATA:
Workspace: {workspace}
Suggested Subtype: {document_subtype or 'Unspecified'}

UNTRUSTED DOCUMENT CONTENT:
<untrusted_document_content>
{chunks[0]}
</untrusted_document_content>

Analyze this document strictly according to the rules and return JSON."""

        logger.info(
            "gemini_workspace_request_start request_id=%s workspace=%s model=%s text_len=%d chunks=%d",
            request_id,
            workspace,
            model_name,
            len(document_text),
            len(chunks),
        )

        try:
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.1,
                response_mime_type="application/json",
            )

            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=config,
                ),
                timeout=timeout_seconds,
            )

        except Exception as exc:
            code, msg = cls.classify_error(exc, request_id)
            logger.error("gemini_request_failed request_id=%s code=%s exc=%s", request_id, code, exc)
            raise GeminiServiceError(code, msg) from exc

        if not response.candidates:
            raise GeminiServiceError("empty_provider_response", "Gemini returned no candidates.")

        candidate = response.candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        finish_str = str(finish_reason).upper() if finish_reason else ""
        if any(r in finish_str for r in ("SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT")):
            raise GeminiServiceError("provider_blocked", "Gemini flagged this document as prohibited or blocked.")

        raw_text = ""
        if candidate.content and candidate.content.parts:
            parts = [p.text for p in candidate.content.parts if getattr(p, "text", None)]
            raw_text = "".join(parts).strip()

        if not raw_text:
            raise GeminiServiceError("empty_provider_response", "Gemini returned an empty response.")

        clean_text = raw_text
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        try:
            parsed = json.loads(clean_text)
            validated = schema_cls.model_validate(parsed)
            validated_dict = validated.model_dump()
        except (json.JSONDecodeError, ValidationError) as parse_err:
            logger.error("gemini_response_parse_failed request_id=%s err=%s", request_id, parse_err)
            raise GeminiServiceError(
                "invalid_provider_response",
                "Gemini returned an invalid response structure.",
                details=str(parse_err),
            ) from parse_err

        # Extract normalized findings list
        findings_list = cls._extract_and_normalize_findings(workspace, validated_dict)
        validated_dict["findings"] = findings_list

        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "gemini_workspace_request_success request_id=%s workspace=%s duration_ms=%d findings=%d",
            request_id,
            workspace,
            duration_ms,
            len(findings_list),
        )

        return {
            "provider": "gemini",
            "model_name": model_name,
            "structured_data": validated_dict,
            "summary": validated_dict.get("overview", "Document analysis completed."),
            "key_points": cls._extract_key_points(workspace, validated_dict),
            "findings": findings_list,
        }

    @classmethod
    def _extract_key_points(cls, workspace: str, data: dict[str, Any]) -> list[str]:
        points = []
        if workspace == "legal":
            parties = [p.get("name") for p in data.get("parties", []) if p.get("name")]
            if parties:
                points.append(f"Parties involved: {', '.join(parties)}")
            gov_law = data.get("governing_law")
            if gov_law:
                points.append(f"Governing Law: {gov_law}")
            renewal = data.get("renewal", {})
            if renewal.get("automatic_renewal"):
                points.append(f"Automatic Renewal: Yes ({renewal.get('notice_window', 'Check policy')})")
            if data.get("unusual_clauses"):
                points.append(f"{len(data['unusual_clauses'])} unusual/important clause(s) identified")
        elif workspace == "finance":
            cur = data.get("currency", "$")
            if data.get("closing_balance") is not None:
                points.append(f"Closing Balance: {cur} {data.get('closing_balance'):,.2f}")
            if data.get("total_debits") is not None:
                points.append(f"Total Debits: {cur} {data.get('total_debits'):,.2f}")
            if data.get("total_credits") is not None:
                points.append(f"Total Credits: {cur} {data.get('total_credits'):,.2f}")
            if data.get("payment_due_date"):
                points.append(f"Payment Due Date: {data.get('payment_due_date')}")
        elif workspace == "insurance":
            if data.get("sum_insured"):
                points.append(f"Sum Insured: {data.get('sum_insured')}")
            if data.get("premium_amount"):
                points.append(f"Premium: {data.get('premium_amount')} ({data.get('premium_frequency', 'period')})")
            if data.get("exclusions"):
                points.append(f"{len(data['exclusions'])} policy exclusion(s) flagged")
            if data.get("waiting_periods"):
                points.append(f"{len(data['waiting_periods'])} waiting period(s) applicable")
        elif workspace == "education":
            if data.get("reported_gpa"):
                points.append(f"GPA / Academic Standing: {data.get('reported_gpa')}")
            if data.get("total_credits_earned"):
                points.append(f"Total Credits Earned: {data.get('total_credits_earned')}")
            if data.get("courses_and_subjects"):
                points.append(f"Courses Listed: {len(data['courses_and_subjects'])}")
            if data.get("deadlines_and_milestones"):
                points.append(f"Upcoming Deadlines: {len(data['deadlines_and_milestones'])}")
        elif workspace == "employment_government":
            comp = data.get("compensation", {})
            if comp.get("gross_salary"):
                points.append(f"Gross Salary: {comp.get('gross_salary')} ({comp.get('payment_frequency', 'annual')})")
            if data.get("joining_date"):
                points.append(f"Joining Date: {data.get('joining_date')}")
            if data.get("notice_period"):
                points.append(f"Notice Period: {data.get('notice_period')}")
            if data.get("restrictive_covenants"):
                points.append(f"{len(data['restrictive_covenants'])} restrictive covenant(s) noted")

        if not points:
            points.append(data.get("overview", "Analysis completed successfully.")[:150])
        return points

    @classmethod
    def _extract_and_normalize_findings(cls, workspace: str, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Collects domain-specific flags into normalized WorkspaceFinding records with evidence."""
        findings: list[dict[str, Any]] = []

        # 1. Existing explicit findings
        for f in data.get("findings", []):
            findings.append(f)

        # 2. Legal: unusual_clauses
        if workspace == "legal":
            for c in data.get("unusual_clauses", []):
                findings.append({
                    "finding_type": "unusual_clause",
                    "title": c.get("title", "Unusual Clause"),
                    "explanation": c.get("explanation", ""),
                    "why_it_matters": c.get("why_it_matters"),
                    "review_priority": c.get("review_priority", "review"),
                    "source_page": c.get("source_page"),
                    "source_excerpt": c.get("source_excerpt"),
                })
            for d in data.get("deadlines_checklist", []):
                findings.append({
                    "finding_type": "deadline",
                    "title": f"Deadline: {d.get('action', 'Action Required')}",
                    "explanation": f"Due by {d.get('deadline', 'specified date')} for {d.get('party', 'contracting party')}",
                    "why_it_matters": "Contractual compliance and notice window requirement.",
                    "review_priority": "review",
                    "source_page": d.get("source_page"),
                    "source_excerpt": None,
                })

        # 3. Finance: candidate_anomalies
        elif workspace == "finance":
            for a in data.get("candidate_anomalies", []):
                findings.append({
                    "finding_type": a.get("flag_type", "anomaly"),
                    "title": a.get("title", "Review Item"),
                    "explanation": a.get("explanation", ""),
                    "why_it_matters": "Candidate item for human review; not confirmed fraud.",
                    "review_priority": a.get("review_priority", "review"),
                    "source_page": a.get("source_page"),
                    "source_excerpt": a.get("source_excerpt"),
                    "metadata_json": {"amount": a.get("amount")},
                })

        # 4. Insurance: exclusions and waiting periods
        elif workspace == "insurance":
            for ex in data.get("exclusions", []):
                findings.append({
                    "finding_type": "exclusion",
                    "title": f"Exclusion: {ex.get('title', 'Policy Exclusion')}",
                    "explanation": ex.get("explanation", ""),
                    "why_it_matters": f"Conditions: {ex.get('conditions', 'Applies as per terms')}",
                    "review_priority": "high",
                    "source_page": ex.get("source_page"),
                    "source_excerpt": ex.get("source_excerpt"),
                })
            for wp in data.get("waiting_periods", []):
                findings.append({
                    "finding_type": "waiting_period",
                    "title": f"Waiting Period: {wp.get('condition_or_treatment')}",
                    "explanation": f"No claims payable during initial {wp.get('period')}.",
                    "why_it_matters": "Claims arising during waiting period are non-payable.",
                    "review_priority": "review",
                    "source_page": wp.get("source_page"),
                    "source_excerpt": wp.get("source_excerpt"),
                })

        # 5. Education: deadlines and review flags
        elif workspace == "education":
            for dl in data.get("deadlines_and_milestones", []):
                findings.append({
                    "finding_type": "deadline",
                    "title": f"Milestone: {dl.get('title')}",
                    "explanation": f"Due on {dl.get('date_or_deadline', 'TBD')}. Weight: {dl.get('weight_percentage', 0)}%",
                    "why_it_matters": dl.get("description", "Academic milestone assessment."),
                    "review_priority": "info" if (dl.get("weight_percentage") or 0) < 20 else "high",
                    "source_page": dl.get("source_page"),
                    "source_excerpt": None,
                })
            for rf in data.get("review_flags", []):
                findings.append(rf)

        # 6. Employment & Government: restrictive covenants
        elif workspace == "employment_government":
            for rc in data.get("restrictive_covenants", []):
                findings.append({
                    "finding_type": "restriction",
                    "title": rc.get("clause_title", "Restrictive Clause"),
                    "explanation": rc.get("description", ""),
                    "why_it_matters": rc.get("why_it_matters", f"Duration: {rc.get('duration', 'N/A')}; Scope: {rc.get('scope', 'N/A')}"),
                    "review_priority": rc.get("review_priority", "high"),
                    "source_page": rc.get("source_page"),
                    "source_excerpt": rc.get("source_excerpt"),
                })
            for chk in data.get("obligations_and_checklist", []):
                findings.append({
                    "finding_type": "deadline",
                    "title": f"Requirement: {chk.get('task')}",
                    "explanation": f"Deadline: {chk.get('deadline', 'Specified date')}",
                    "why_it_matters": f"Responsible entity: {chk.get('responsible_entity', 'Applicant/Employee')}",
                    "review_priority": "review",
                    "source_page": chk.get("source_page"),
                    "source_excerpt": None,
                })

        return findings


gemini_workspace_service = GeminiWorkspaceService()
