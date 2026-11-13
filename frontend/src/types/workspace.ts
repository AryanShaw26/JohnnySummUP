export type WorkspaceSlug =
  | "legal"
  | "finance"
  | "insurance"
  | "education"
  | "employment-government";

export interface WorkspaceFinding {
  id: string;
  analysis_id: string;
  document_id: string;
  workspace: string;
  finding_type: string;
  title: string;
  explanation: string;
  why_it_matters?: string | null;
  review_priority: "info" | "review" | "high";
  source_page?: number | null;
  source_section?: string | null;
  source_excerpt?: string | null;
  metadata_json?: Record<string, any> | null;
  is_reviewed: boolean;
  review_status: "pending" | "reviewed" | "dismissed";
  created_at: string;
}

export interface WorkspaceAnalysis {
  id: string;
  document_id: string;
  workspace: string;
  version: number;
  status: string;
  extracted_text?: string | null;
  summary?: string | null;
  structured_data?: Record<string, any> | null;
  key_points?: string[] | null;
  provider: string;
  model_name?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  findings?: WorkspaceFinding[];
}

export interface WorkspaceDocument {
  id: string;
  workspace: string;
  document_type: string;
  document_subtype?: string | null;
  label?: string | null;
  original_filename: string;
  mime_type: string;
  file_extension: string;
  file_size_bytes: number;
  document_date?: string | null;
  extraction_method?: string | null;
  page_count: number;
  character_count: number;
  status: "uploaded" | "extracting" | "extracted" | "classifying" | "analyzing" | "completed" | "failed";
  failure_code?: string | null;
  failure_message?: string | null;
  created_at: string;
  updated_at: string;
  analyses?: WorkspaceAnalysis[];
  findings?: WorkspaceFinding[];
}

export interface WorkspaceDocumentListResponse {
  items: WorkspaceDocument[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface WorkspaceOverview {
  workspace: string;
  total_documents: number;
  completed_documents: number;
  failed_documents: number;
  pending_documents: number;
  subtypes_breakdown: Record<string, number>;
  recent_documents: WorkspaceDocument[];
  urgent_findings: WorkspaceFinding[];
  deadlines: WorkspaceFinding[];
}

export interface WorkspaceCompareResponse {
  workspace: string;
  document_a: {
    id: string;
    filename: string;
    document_type: string;
    document_subtype?: string;
    created_at: string;
    summary?: string;
  };
  document_b: {
    id: string;
    filename: string;
    document_type: string;
    document_subtype?: string;
    created_at: string;
    summary?: string;
  };
  summary_comparison: {
    total_additions_count: number;
    total_deletions_count: number;
    changed_fields_count: number;
  };
  field_changes: Array<{
    field: string;
    document_a_value: any;
    document_b_value: any;
  }>;
  sample_additions: string[];
  sample_deletions: string[];
  raw_diff: string;
}
