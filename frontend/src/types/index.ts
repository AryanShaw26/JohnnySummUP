// ─── JohnnySummUP V1 Frontend Types ──────────────────────────────

export type DocumentType =
  | 'lab_report'
  | 'prescription'
  | 'imaging_report'
  | 'discharge_summary'
  | 'other';

export type ProcessingStatus =
  | 'uploaded'
  | 'queued'
  | 'processing'
  | 'completed'
  | 'needs_review'
  | 'failed'
  | 'deleted';

export type RangeStatus =
  | 'within_range'
  | 'below_range'
  | 'above_range'
  | 'not_comparable'
  | 'unknown';

export type FindingType =
  | 'below_report_range'
  | 'above_report_range'
  | 'source_flagged'
  | 'needs_review'
  | 'notable_change'
  | 'document_observation';

// ─── User & Auth ───────────────────────────────────────────────
export interface User {
  id: string;
  email: string;
  fullName: string;
  isActive: boolean;
  emailVerified: boolean;
  role: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  fullName?: string;
  acceptTerms?: boolean;
  acceptPrivacy?: boolean;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn?: number;
}

export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
  accessToken?: string;
}

// ─── Medical Document ──────────────────────────────────────────
export interface MedicalDocumentItem {
  id: string;
  originalFilename: string;
  documentTitle: string;
  documentType: DocumentType;
  testDate?: string;
  uploadedAt: string;
  processingStatus: ProcessingStatus;
  pageCount?: number;
  measurementCount: number;
  findingCount: number;
}

export interface ReferenceRange {
  low?: number;
  high?: number;
  rawText?: string;
}

export interface SourceLocation {
  page?: number;
  snippet?: string;
  boundingBox?: Record<string, unknown>;
}

export interface ExtractedMeasurement {
  id: string;
  documentId: string;
  parameterCode?: string;
  parameterName: string;
  parameterDisplayName?: string;
  rawValueText: string;
  numericValue?: string;
  sourceUnit?: string;
  referenceRange?: ReferenceRange;
  sourceFlag?: string;
  calculatedRangeStatus: RangeStatus;
  testDate?: string;
  confidence?: number;
  reviewStatus: string;
  source?: SourceLocation;
}

export interface FindingEvidence {
  documentId?: string;
  page?: number;
  snippet?: string;
  measurementId?: string;
}

export interface MedicalFinding {
  id: string;
  documentId: string;
  measurementId?: string;
  findingType: FindingType;
  title: string;
  explanation: string;
  ruleCode?: string;
  evidence: FindingEvidence[];
  reviewStatus: string;
  createdAt: string;
}

export interface KeyPoint {
  text: string;
  evidenceIds: string[];
  category: string;
}

export interface StructuredSummary {
  overview: string;
  keyPoints: KeyPoint[];
  limitations: string[];
  questionsForClinician: string[];
  safetyNotice: string;
}

export interface DocumentSummary {
  id: string;
  summaryText: string;
  structuredSummary?: StructuredSummary;
  modelProvider?: string;
  validationStatus: string;
  createdAt?: string;
}

export interface PrescriptionItem {
  id: string;
  documentId: string;
  documentTitle?: string;
  date?: string;
  medicineName: string;
  strength?: string;
  dose?: string;
  route?: string;
  frequency?: string;
  duration?: string;
  instructions?: string;
  confidence?: number;
  reviewStatus: string;
  sourceSnippet?: string;
  sourcePage?: number;
}

export interface DocumentDetail {
  id: string;
  originalFilename: string;
  documentTitle: string;
  documentType: DocumentType;
  testDate?: string;
  uploadedAt: string;
  pageCount?: number;
  providerName?: string;
  facilityName?: string;
  status: ProcessingStatus;
  summary?: DocumentSummary;
  measurements: ExtractedMeasurement[];
  findings: MedicalFinding[];
  prescriptions: PrescriptionItem[];
}

// ─── Dashboard & Analytics ─────────────────────────────────────
export interface TrackedParameterPreview {
  parameterCode: string;
  displayName: string;
  category: string;
  unit: string;
  readingCount: number;
  latestValue: string;
  latestStatus: RangeStatus;
  latestDate?: string;
}

export interface DashboardStats {
  reportCount: number;
  analysedCount: number;
  needsReviewCount: number;
  trackedParameterCount: number;
  recentDocuments: MedicalDocumentItem[];
  recentFindings: MedicalFinding[];
  trackedParameterPreviews: TrackedParameterPreview[];
}

export interface TrendPoint {
  measurementId: string;
  documentId: string;
  documentTitle?: string;
  testDate: string;
  value: number;
  rawValue: string;
  unit: string;
  referenceLow?: number;
  referenceHigh?: number;
  calculatedRangeStatus: RangeStatus;
  reviewStatus: string;
}

export interface TrendData {
  parameterCode: string;
  displayName: string;
  unit: string;
  comparabilityStatus: 'comparable' | 'insufficient_data' | 'incompatible_units' | 'needs_review';
  explanation: string;
  points: TrendPoint[];
}

export interface ComparisonData {
  documents: Array<{
    id: string;
    title: string;
    testDate?: string;
    documentType: string;
  }>;
  alignedMeasurements: Array<{
    parameterCode?: string;
    parameterName: string;
    unit?: string;
    valuesByDocument: Record<string, {
      rawValue: string;
      numericValue?: number;
      status: RangeStatus;
      referenceText?: string;
      sourceFlag?: string;
    }>;
  }>;
}

// ─── Capabilities & Generic Response ───────────────────────────
export interface Capabilities {
  supportedMimeTypes: string[];
  maxFileSizeBytes: number;
  maxPages: number;
  supportedDocumentTypes: string[];
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: {
    requestId?: string;
    timestamp: string;
  };
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  pagination: {
    page: number;
    pageSize: number;
    totalItems: number;
    totalPages: number;
  };
}

export interface ApiError {
  message: string;
  code?: string;
  status: number;
  errors?: Record<string, string[]>;
}
