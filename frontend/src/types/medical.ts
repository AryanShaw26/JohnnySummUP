export type DocumentType = "prescription" | "laboratory_report" | "other";

export type DocumentStatus =
  | "uploaded"
  | "queued"
  | "processing"
  | "completed"
  | "failed"
  | "analysis_unavailable";

export type FlagSeverity = "info" | "review" | "high";
export type FlagType = "below_range" | "above_range" | "needs_review";

export interface DocumentAnalysis {
  id: string;
  document_id: string;
  version: number;
  status: string;
  extraction_method?: string | null;
  extracted_page_count?: number | null;
  ocr_page_count?: number | null;
  extracted_text?: string | null;
  summary?: string | null;
  key_points?: string[] | null;
  provider?: string | null;
  model_name?: string | null;
  prompt_version?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  request_id?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface ExtractedFinding {
  id: string;
  analysis_id: string;
  document_id: string;
  category: string;
  finding_type: string;
  name: string;
  value_text?: string | null;
  numeric_value?: number | null;
  unit?: string | null;
  reference_low?: number | null;
  reference_high?: number | null;
  reference_text?: string | null;
  source_page?: number | null;
  source_excerpt?: string | null;
  confidence?: number | null;
  is_extracted: boolean;
  created_at: string;
}

export interface MedicalMeasurement {
  id: string;
  document_id: string;
  source_finding_id?: string | null;
  parameter_name: string;
  parameter_code?: string | null;
  numeric_value: number;
  unit: string;
  report_date: string;
  reference_low?: number | null;
  reference_high?: number | null;
  reference_text?: string | null;
  created_at: string;
}

export interface AbnormalityFlag {
  id: string;
  document_id: string;
  source_finding_id?: string | null;
  measurement_id?: string | null;
  parameter_name: string;
  observed_value?: number | null;
  unit?: string | null;
  reference_text?: string | null;
  flag_type: FlagType;
  severity: FlagSeverity;
  explanation?: string | null;
  created_at: string;
  document_name?: string | null;
  report_date?: string | null;
}

export interface MedicalDocument {
  id: string;
  original_filename: string;
  mime_type: string;
  file_extension: string;
  file_size_bytes: number;
  document_type: DocumentType;
  report_date?: string | null;
  status: DocumentStatus;
  failure_code?: string | null;
  failure_message?: string | null;
  created_at: string;
  updated_at: string;
  latest_analysis?: DocumentAnalysis | null;
}

export interface MedicalDocumentDetail extends MedicalDocument {
  analyses: DocumentAnalysis[];
  findings: ExtractedFinding[];
  flags: AbnormalityFlag[];
  measurements: MedicalMeasurement[];
}

export interface DocumentListResponse {
  items: MedicalDocument[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface MedicalOverview {
  total_reports: number;
  prescriptions_count: number;
  lab_reports_count: number;
  important_findings_count: number;
  recent_reports: MedicalDocument[];
  important_findings: AbnormalityFlag[];
}

export interface TrendPoint {
  date: string;
  value: number;
  unit: string;
  document_id: string;
  document_name: string;
  is_abnormal: boolean;
}

export interface TrendResponse {
  parameter_name: string;
  unit: string;
  reference_range?: string | null;
  current_value?: number | null;
  previous_value?: number | null;
  change?: number | null;
  status: "normal" | "high" | "low" | "review";
  points: TrendPoint[];
  available_parameters: string[];
}

export interface ParameterComparisonRow {
  parameter_name: string;
  unit: string;
  reference_range?: string | null;
  values_by_date: Record<string, number | null>;
  trend_direction: "up" | "down" | "stable" | "unknown";
}

export interface ParameterComparisonResponse {
  report_dates: string[];
  rows: ParameterComparisonRow[];
}

export interface TimelineItem {
  document_id: string;
  report_name: string;
  report_date: string;
  document_type: string;
  status: string;
  key_measurements: Array<{ name: string; value: number; unit: string }>;
  flag_count: number;
}
