import {
  BookOpenText,
  BriefcaseBusiness,
  GraduationCap,
  Landmark,
  LucideIcon,
  Shield,
} from "lucide-react";

export interface WorkspaceMeta {
  slug: string;
  backendSlug: string;
  name: string;
  tagline: string;
  accentColor: string;
  icon: LucideIcon;
  subtypes: Array<{ value: string; label: string; hint: string }>;
  sampleTips: string[];
}

export const WORKSPACE_CONFIGS: Record<string, WorkspaceMeta> = {
  legal: {
    slug: "legal",
    backendSlug: "legal",
    name: "Legal",
    tagline: "Contracts, NDAs, Leases, Obligations & Clause Analysis",
    accentColor: "#7136d8",
    icon: BookOpenText,
    subtypes: [
      { value: "nda", label: "NDA / Confidentiality", hint: "Mutual and unilateral non-disclosure agreements" },
      { value: "agreement", label: "General Agreement", hint: "Commercial contracts and service agreements" },
      { value: "rental_lease", label: "Rental / Lease", hint: "Commercial or residential property leases" },
      { value: "service_agreement", label: "Service Agreement / SOW", hint: "Statements of work and contractor terms" },
      { value: "employment_agreement", label: "Employment Agreement", hint: "Executive and employee contracts" },
      { value: "terms_conditions", label: "Terms & Conditions", hint: "Online terms, SaaS and platform policies" },
      { value: "notice", label: "Notice / Legal Letter", hint: "Formal notifications, demand letters, summons" },
      { value: "other", label: "Other Legal Document", hint: "Any other formal legal paperwork" },
    ],
    sampleTips: [
      "Highlights automatic renewal & short notice windows",
      "Identifies unilateral change and broad indemnity clauses",
      "Tracks obligations, deadlines & governing jurisdiction",
    ],
  },
  finance: {
    slug: "finance",
    backendSlug: "finance",
    name: "Finance",
    tagline: "Statements, Invoices, Fees, Cash Flow & Balance Extraction",
    accentColor: "#059669",
    icon: Landmark,
    subtypes: [
      { value: "bank_statement", label: "Bank Statement", hint: "Checking, savings or business account statements" },
      { value: "credit_card_statement", label: "Credit Card Statement", hint: "Monthly statements with minimum payment" },
      { value: "invoice", label: "Invoice / Bill", hint: "Vendor invoices, utility bills, receipts" },
      { value: "loan_statement", label: "Loan / Mortgage Statement", hint: "Repayment schedules, interest, EMI notices" },
      { value: "tax_statement", label: "Tax Statement", hint: "W-2, 1099, Form 16, tax return forms" },
      { value: "expense_report", label: "Expense Report", hint: "Business expense reimbursements" },
      { value: "other", label: "Other Financial Record", hint: "Any other financial statement" },
    ],
    sampleTips: [
      "Extracts opening and closing balances with exact currencies",
      "Flags unusual fees, approaching due dates & candidate duplicate charges",
      "Itemizes debits, credits, and recurring charges",
    ],
  },
  insurance: {
    slug: "insurance",
    backendSlug: "insurance",
    name: "Insurance",
    tagline: "Policies, Schedules, Exclusions, Deductibles & Claim Procedures",
    accentColor: "#0284c7",
    icon: Shield,
    subtypes: [
      { value: "policy_document", label: "Policy Document", hint: "Full policy wording and schedule of benefits" },
      { value: "schedule", label: "Policy Schedule", hint: "Coverage limits, deductibles, and premiums" },
      { value: "premium_notice", label: "Premium / Renewal Notice", hint: "Payment notices and renewal terms" },
      { value: "endorsement", label: "Endorsement / Rider", hint: "Policy amendments and coverage additions" },
      { value: "claim_form", label: "Claim Form & Documents", hint: "Claim correspondence and settlement reports" },
      { value: "other", label: "Other Insurance Document", hint: "Any insurance-related paperwork" },
    ],
    sampleTips: [
      "Extracts sum insured, deductibles, co-pays & sub-limits",
      "Surfaces pre-existing condition exclusions and waiting periods",
      "Source-linked checklist of claim instructions and notice requirements",
    ],
  },
  education: {
    slug: "education",
    backendSlug: "education",
    name: "Education",
    tagline: "Transcripts, Grades, Syllabi, Assignments & Academic Deadlines",
    accentColor: "#d97706",
    icon: GraduationCap,
    subtypes: [
      { value: "transcript", label: "Academic Transcript", hint: "Official grade cards and course records" },
      { value: "marksheet", label: "Marksheet / Report Card", hint: "Term and semester grade reports" },
      { value: "syllabus", label: "Course Syllabus", hint: "Learning objectives, grading weights, reading lists" },
      { value: "assignment_brief", label: "Assignment Brief", hint: "Submission guidelines, rubrics, deadlines" },
      { value: "exam_notice", label: "Exam Notice / Schedule", hint: "Dates, hall tickets, timetable" },
      { value: "offer_letter", label: "Admission Offer Letter", hint: "Acceptance letters and scholarship grants" },
      { value: "other", label: "Other Academic Document", hint: "Any education-related record" },
    ],
    sampleTips: [
      "Calculates credits, course grades & reported GPA accurately",
      "Converts assignment evaluation criteria and deadlines into checklists",
      "Highlights strict late submission policies and attendance criteria",
    ],
  },
  "employment-government": {
    slug: "employment-government",
    backendSlug: "employment_government",
    name: "Employment & Government",
    tagline: "Offer Letters, Payslips, HR Policies, Circulars & Applications",
    accentColor: "#4f46e5",
    icon: BriefcaseBusiness,
    subtypes: [
      { value: "offer_letter", label: "Offer / Appointment Letter", hint: "Job offers and compensation packages" },
      { value: "employment_contract", label: "Employment Contract", hint: "Formal employee agreements and HR terms" },
      { value: "payslip", label: "Payslip / Salary Statement", hint: "Monthly earnings, basic, HRA and deductions" },
      { value: "experience_letter", label: "Experience / Relieving Letter", hint: "Service certificates and exit letters" },
      { value: "government_notice", label: "Government Notice / Circular", hint: "Gazette notices, official orders, guidelines" },
      { value: "scheme_guideline", label: "Scheme / Grant Guidelines", hint: "Public benefit criteria and subsidies" },
      { value: "application_instructions", label: "Application Instructions", hint: "Exam forms, eligibility, required documents" },
      { value: "other", label: "Other Official Notice", hint: "Any employment or official government paperwork" },
    ],
    sampleTips: [
      "Itemizes compensation components: gross, net, allowances & deductions",
      "Flags restrictive covenants: non-compete, notice period & training bonds",
      "Builds action checklists for government schemes and application deadlines",
    ],
  },
};

export function getWorkspaceConfig(slug: string): WorkspaceMeta {
  const normalized = slug.toLowerCase().replace(/_/g, "-");
  return WORKSPACE_CONFIGS[normalized] || WORKSPACE_CONFIGS["legal"];
}

