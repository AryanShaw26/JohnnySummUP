from typing import Any, Literal
from pydantic import BaseModel, Field


class FindingItem(BaseModel):
    finding_type: str = "general"
    title: str
    explanation: str
    why_it_matters: str | None = None
    review_priority: Literal["info", "review", "high"] = "info"
    source_page: int | None = None
    source_section: str | None = None
    source_excerpt: str | None = None
    metadata_json: dict[str, Any] | None = None


# --- 1. LEGAL SCHEMA ---
class LegalParty(BaseModel):
    name: str
    role: str | None = None  # e.g., "Disclosing Party", "Landlord", "Employer"


class LegalDates(BaseModel):
    effective_date: str | None = None
    execution_date: str | None = None
    expiration_date: str | None = None


class LegalObligation(BaseModel):
    party: str
    description: str
    deadline: str | None = None
    source_page: int | None = None


class LegalRenewal(BaseModel):
    automatic_renewal: bool | None = None
    notice_window: str | None = None
    renewal_term: str | None = None


class LegalTermination(BaseModel):
    notice_period: str | None = None
    conditions: str | None = None
    early_termination_fee: str | None = None


class LegalLiability(BaseModel):
    liability_cap: str | None = None
    indemnity_scope: str | None = None
    exclusions: str | None = None


class LegalUnusualClause(BaseModel):
    title: str
    explanation: str
    why_it_matters: str | None = None
    review_priority: Literal["info", "review", "high"] = "review"
    source_page: int | None = None
    source_excerpt: str | None = None


class LegalDeadlineItem(BaseModel):
    action: str
    deadline: str | None = None
    party: str | None = None
    source_page: int | None = None


class LegalAnalysisSchema(BaseModel):
    overview: str
    document_type: str = "agreement"
    parties: list[LegalParty] = Field(default_factory=list)
    dates: LegalDates = Field(default_factory=LegalDates)
    governing_law: str | None = None
    jurisdiction: str | None = None
    financial_terms: dict[str, Any] | None = None
    obligations: list[LegalObligation] = Field(default_factory=list)
    deliverables: list[dict[str, Any]] = Field(default_factory=list)
    termination: LegalTermination = Field(default_factory=LegalTermination)
    renewal: LegalRenewal = Field(default_factory=LegalRenewal)
    confidentiality_duration: str | None = None
    liability_and_indemnity: LegalLiability = Field(default_factory=LegalLiability)
    dispute_resolution: str | None = None
    unusual_clauses: list[LegalUnusualClause] = Field(default_factory=list)
    missing_terms: list[str] = Field(default_factory=list)
    deadlines_checklist: list[LegalDeadlineItem] = Field(default_factory=list)
    findings: list[FindingItem] = Field(default_factory=list)
    disclaimer: str = (
        "This analysis provides document information only and does not constitute legal advice. "
        "Consult qualified legal counsel for consequential decisions."
    )


# --- 2. FINANCE SCHEMA ---
class FinanceTransaction(BaseModel):
    date: str | None = None
    description: str
    amount: float | None = None
    transaction_type: Literal["debit", "credit", "fee", "transfer", "other"] = "other"
    balance_after: float | None = None
    currency: str | None = None
    source_page: int | None = None
    source_row: int | None = None


class FinanceRecurring(BaseModel):
    description: str
    expected_amount: float | None = None
    frequency: str | None = None


class FinanceAnomaly(BaseModel):
    title: str
    explanation: str
    flag_type: Literal["unusual_fee", "near_due_date", "inconsistent_total", "candidate_duplicate", "large_transaction"]
    review_priority: Literal["info", "review", "high"] = "review"
    amount: float | None = None
    source_page: int | None = None
    source_excerpt: str | None = None


class FinanceAnalysisSchema(BaseModel):
    overview: str
    document_type: str = "statement"
    issuer_name: str | None = None
    masked_account_number: str | None = None
    account_type: str | None = None
    statement_period_start: str | None = None
    statement_period_end: str | None = None
    currency: str = "USD"
    opening_balance: float | None = None
    closing_balance: float | None = None
    payment_due_date: str | None = None
    minimum_payment_due: float | None = None
    total_debits: float | None = None
    total_credits: float | None = None
    total_fees: float | None = None
    total_taxes: float | None = None
    total_interest: float | None = None
    income_total: float | None = None
    expense_total: float | None = None
    recurring_charges: list[FinanceRecurring] = Field(default_factory=list)
    transactions: list[FinanceTransaction] = Field(default_factory=list)
    candidate_anomalies: list[FinanceAnomaly] = Field(default_factory=list)
    findings: list[FindingItem] = Field(default_factory=list)
    disclaimer: str = (
        "This summary is for informational purposes only and does not constitute financial, investment, or tax advice. "
        "Amounts are extracted directly from the uploaded record."
    )


# --- 3. INSURANCE SCHEMA ---
class InsuranceCoverageItem(BaseModel):
    name: str
    limit: str | None = None
    deductible: str | None = None
    copay: str | None = None
    conditions: str | None = None
    source_page: int | None = None


class InsuranceExclusion(BaseModel):
    title: str
    explanation: str
    conditions: str | None = None
    source_page: int | None = None
    source_excerpt: str | None = None


class InsuranceWaitingPeriod(BaseModel):
    condition_or_treatment: str
    period: str
    source_page: int | None = None
    source_excerpt: str | None = None


class InsuranceClaimStep(BaseModel):
    step_number: int
    instruction: str
    deadline_or_timeline: str | None = None
    required_documents: list[str] = Field(default_factory=list)
    source_page: int | None = None


class InsuranceAnalysisSchema(BaseModel):
    overview: str
    document_type: str = "policy"
    insurer_name: str | None = None
    policyholder_name: str | None = None
    masked_policy_number: str | None = None
    policy_type: str | None = None
    policy_start_date: str | None = None
    policy_end_date: str | None = None
    premium_amount: str | None = None
    premium_frequency: str | None = None
    premium_due_date: str | None = None
    sum_insured: str | None = None
    deductibles_and_copay: str | None = None
    coverages: list[InsuranceCoverageItem] = Field(default_factory=list)
    exclusions: list[InsuranceExclusion] = Field(default_factory=list)
    limitations_and_sublimits: list[dict[str, Any]] = Field(default_factory=list)
    waiting_periods: list[InsuranceWaitingPeriod] = Field(default_factory=list)
    claim_instructions: list[InsuranceClaimStep] = Field(default_factory=list)
    renewal_and_cancellation: str | None = None
    review_flags: list[FindingItem] = Field(default_factory=list)
    findings: list[FindingItem] = Field(default_factory=list)
    disclaimer: str = (
        "This document summary is not a guarantee of coverage or claim approval. "
        "Official insurer policy terms and conditions govern all benefits and exclusions."
    )


# --- 4. EDUCATION SCHEMA ---
class EducationCourse(BaseModel):
    code: str | None = None
    name: str
    credits: float | None = None
    grade: str | None = None
    marks_obtained: float | None = None
    max_marks: float | None = None
    semester: str | None = None
    source_page: int | None = None


class EducationDeadline(BaseModel):
    title: str
    date_or_deadline: str | None = None
    weight_percentage: float | None = None
    description: str | None = None
    source_page: int | None = None


class EducationAssignmentReq(BaseModel):
    title: str
    requirement_details: str
    submission_format: str | None = None
    evaluation_criteria: str | None = None
    deadline: str | None = None
    source_page: int | None = None


class EducationAnalysisSchema(BaseModel):
    overview: str
    document_type: str = "transcript"
    institution_name: str | None = None
    student_name: str | None = None
    masked_student_id: str | None = None
    program_or_major: str | None = None
    academic_term: str | None = None
    reported_gpa: str | None = None
    grading_scale_description: str | None = None
    total_credits_earned: float | None = None
    courses_and_subjects: list[EducationCourse] = Field(default_factory=list)
    performance_summary: str | None = None
    calculated_metrics: dict[str, Any] | None = None
    deadlines_and_milestones: list[EducationDeadline] = Field(default_factory=list)
    assignment_requirements: list[EducationAssignmentReq] = Field(default_factory=list)
    review_flags: list[FindingItem] = Field(default_factory=list)
    findings: list[FindingItem] = Field(default_factory=list)
    disclaimer: str = (
        "Academic records and deadlines are extracted from the supplied document. "
        "Official institutional transcripts govern academic status."
    )


# --- 5. EMPLOYMENT & GOVERNMENT SCHEMA ---
class EmploymentCompensation(BaseModel):
    gross_salary: str | None = None
    net_salary: str | None = None
    basic_salary: str | None = None
    currency: str | None = None
    payment_frequency: str | None = None  # "annual", "monthly"
    allowances: list[dict[str, Any]] = Field(default_factory=list)
    deductions: list[dict[str, Any]] = Field(default_factory=list)
    variable_pay: str | None = None
    benefits: list[str] = Field(default_factory=list)


class EmploymentRestrictiveClause(BaseModel):
    clause_title: str
    description: str
    duration: str | None = None
    scope: str | None = None
    why_it_matters: str | None = None
    review_priority: Literal["info", "review", "high"] = "review"
    source_page: int | None = None
    source_excerpt: str | None = None


class GovernmentNoticeInfo(BaseModel):
    reference_number: str | None = None
    issuing_authority: str | None = None
    publication_date: str | None = None
    effective_date: str | None = None
    scheme_or_exam_name: str | None = None
    application_window_start: str | None = None
    application_window_end: str | None = None
    eligibility_criteria: list[str] = Field(default_factory=list)
    fees: str | None = None
    required_documents: list[str] = Field(default_factory=list)
    application_steps: list[str] = Field(default_factory=list)


class EmploymentGovernmentAnalysisSchema(BaseModel):
    overview: str
    document_type: str = "offer_letter"
    issuing_organization: str | None = None
    employee_or_applicant_name: str | None = None
    masked_identifier: str | None = None
    role_or_scheme_title: str | None = None
    department_or_ministry: str | None = None
    work_location: str | None = None
    employment_type: str | None = None
    joining_date: str | None = None
    probation_period: str | None = None
    notice_period: str | None = None
    bond_or_service_obligation: str | None = None
    compensation: EmploymentCompensation = Field(default_factory=EmploymentCompensation)
    restrictive_covenants: list[EmploymentRestrictiveClause] = Field(default_factory=list)
    government_notice: GovernmentNoticeInfo = Field(default_factory=GovernmentNoticeInfo)
    obligations_and_checklist: list[dict[str, Any]] = Field(default_factory=list)
    review_flags: list[FindingItem] = Field(default_factory=list)
    findings: list[FindingItem] = Field(default_factory=list)
    disclaimer: str = (
        "Information is extracted from the uploaded document copy. This does not determine legal enforceability "
        "or guarantee government eligibility or application outcome."
    )
