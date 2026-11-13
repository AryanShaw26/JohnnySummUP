import re
from dataclasses import dataclass
from typing import Literal

VALID_WORKSPACES = {
    "legal",
    "finance",
    "insurance",
    "education",
    "employment_government",
    "employment-government",
}

WORKSPACE_SUBTYPES: dict[str, list[str]] = {
    "legal": [
        "agreement",
        "contract",
        "nda",
        "rental_lease",
        "employment_agreement",
        "service_agreement",
        "terms_conditions",
        "notice",
        "legal_correspondence",
        "other",
    ],
    "finance": [
        "bank_statement",
        "credit_card_statement",
        "invoice",
        "receipt",
        "bill",
        "loan_statement",
        "repayment_schedule",
        "tax_statement",
        "expense_report",
        "other",
    ],
    "insurance": [
        "policy_document",
        "schedule",
        "premium_notice",
        "renewal_notice",
        "endorsement",
        "claim_form",
        "claim_correspondence",
        "benefit_statement",
        "other",
    ],
    "education": [
        "transcript",
        "marksheet",
        "grade_report",
        "syllabus",
        "academic_calendar",
        "assignment_brief",
        "exam_notice",
        "certificate",
        "offer_letter",
        "other",
    ],
    "employment_government": [
        "offer_letter",
        "employment_contract",
        "payslip",
        "experience_letter",
        "hr_policy",
        "benefit_document",
        "government_notice",
        "scheme_guideline",
        "official_circular",
        "application_instructions",
        "other",
    ],
}

# Normalize workspace slug
def normalize_workspace(workspace: str) -> str:
    cleaned = workspace.strip().lower()
    if cleaned == "employment-government":
        return "employment_government"
    return cleaned


@dataclass
class ClassificationResult:
    workspace: str
    suggested_subtype: str
    confidence: float
    rationale: str
    is_ambiguous: bool = False


class DocumentClassifier:
    """Classifies document types and subtypes within the authoritative user workspace."""

    SUBTYPE_KEYWORDS: dict[str, dict[str, list[str]]] = {
        "legal": {
            "nda": ["non-disclosure", "confidentiality agreement", "proprietary information", "disclosing party", "receiving party"],
            "rental_lease": ["lease agreement", "landlord", "tenant", "premises", "rent", "security deposit"],
            "service_agreement": ["statement of work", "master services agreement", "client", "contractor", "services agreement"],
            "employment_agreement": ["employment agreement", "probation period", "employee", "duties and responsibilities"],
            "terms_conditions": ["terms of service", "terms and conditions", "privacy policy", "user agreement"],
            "notice": ["notice of termination", "legal notice", "formal notice", "default notice"],
            "contract": ["contract", "agreement", "parties", "hereby agree", "terms and conditions"],
        },
        "finance": {
            "invoice": ["invoice", "bill to", "due date", "amount due", "tax invoice", "subtotal", "gst", "vat"],
            "receipt": ["receipt", "payment received", "cashier", "total paid", "transaction receipt"],
            "bank_statement": ["bank statement", "account balance", "deposits", "withdrawals", "opening balance", "closing balance", "ledger balance"],
            "credit_card_statement": ["credit card statement", "minimum payment", "credit limit", "available credit", "payment due date"],
            "loan_statement": ["loan statement", "principal balance", "interest rate", "emi", "amortization", "loan account"],
            "tax_statement": ["form 16", "w-2", "1099", "tax return", "tax assessment", "income tax"],
            "expense_report": ["expense report", "reimbursement", "business expense", "travel expense"],
        },
        "insurance": {
            "claim_form": ["claim form", "claimant", "date of loss", "incident details", "claim number"],
            "endorsement": ["endorsement", "policy amendment", "rider", "schedule of changes", "amended terms"],
            "premium_notice": ["premium notice", "premium due", "renewal premium", "grace period"],
            "renewal_notice": ["policy renewal", "renewal invitation", "expiry date", "renew by"],
            "policy_document": ["policy schedule", "sum insured", "deductible", "copay", "exclusions", "coverage limits", "policyholder", "waiting period"],
        },
        "education": {
            "transcript": ["official transcript", "cumulative gpa", "cgpa", "semester credits", "grade point average", "academic record"],
            "marksheet": ["statement of marks", "marks obtained", "maximum marks", "grade card", "pass/fail", "controller of examinations"],
            "syllabus": ["course syllabus", "learning objectives", "grading policy", "weekly schedule", "required reading", "textbooks"],
            "assignment_brief": ["assignment brief", "submission deadline", "word count", "rubric", "assessment criteria"],
            "exam_notice": ["examination schedule", "hall ticket", "date sheet", "exam timetable"],
            "certificate": ["certificate of completion", "has successfully completed", "degree certificate", "diploma"],
            "offer_letter": ["offer of admission", "letter of acceptance", "admitted to", "enrollment fee"],
        },
        "employment_government": {
            "payslip": ["payslip", "salary slip", "earnings", "deductions", "basic pay", "hra", "provident fund", "pf", "net pay", "gross pay"],
            "offer_letter": ["offer letter", "offer of employment", "we are pleased to offer", "annual compensation", "ctc"],
            "experience_letter": ["experience certificate", "relieving letter", "worked with us", "service certificate"],
            "government_notice": ["gazette notification", "public notice", "circular", "ministry of", "department of", "government of", "ref no"],
            "scheme_guideline": ["guidelines for scheme", "beneficiary eligibility", "financial assistance", "subsidy"],
            "application_instructions": ["instructions to candidates", "application procedure", "eligibility criteria", "how to apply"],
        },
    }

    @classmethod
    def classify(cls, workspace: str, text: str, user_subtype_hint: str | None = None) -> ClassificationResult:
        norm_workspace = normalize_workspace(workspace)
        if norm_workspace not in WORKSPACE_SUBTYPES:
            norm_workspace = "legal"

        # If user explicitly supplied a known subtype, respect it
        valid_subtypes = WORKSPACE_SUBTYPES.get(norm_workspace, [])
        if user_subtype_hint and user_subtype_hint.lower() in valid_subtypes:
            return ClassificationResult(
                workspace=norm_workspace,
                suggested_subtype=user_subtype_hint.lower(),
                confidence=1.0,
                rationale="User-specified document type.",
                is_ambiguous=False,
            )

        lower_text = text.lower()
        subtypes_for_workspace = cls.SUBTYPE_KEYWORDS.get(norm_workspace, {})

        best_subtype = valid_subtypes[0] if valid_subtypes else "other"
        best_score = 0
        matches: list[tuple[str, int]] = []

        for subtype, keywords in subtypes_for_workspace.items():
            score = sum(lower_text.count(kw) for kw in keywords)
            if score > 0:
                matches.append((subtype, score))
            if score > best_score:
                best_score = score
                best_subtype = subtype

        if best_score == 0:
            return ClassificationResult(
                workspace=norm_workspace,
                suggested_subtype=best_subtype,
                confidence=0.5,
                rationale="Default subtype assigned based on selected workspace.",
                is_ambiguous=True,
            )

        # Check if multiple subtypes have close scores
        matches.sort(key=lambda x: x[1], reverse=True)
        is_ambiguous = len(matches) > 1 and matches[0][1] == matches[1][1]

        return ClassificationResult(
            workspace=norm_workspace,
            suggested_subtype=best_subtype,
            confidence=min(0.95, 0.6 + 0.05 * best_score),
            rationale=f"Matched keywords for '{best_subtype}'.",
            is_ambiguous=is_ambiguous,
        )


document_classifier = DocumentClassifier()
