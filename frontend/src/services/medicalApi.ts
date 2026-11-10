import { request } from "./api";
import type {
  AbnormalityFlag,
  DocumentAnalysis,
  DocumentListResponse,
  DocumentType,
  MedicalDocument,
  MedicalDocumentDetail,
  MedicalOverview,
  ParameterComparisonResponse,
  TimelineItem,
  TrendResponse,
} from "../types/medical";

const API_BASE_URL = import.meta.env.VITE_API_URL;

export const medicalApi = {
  getOverview: () => request<MedicalOverview>("/api/medical/overview"),

  uploadDocument: (file: File, documentType: DocumentType, reportDate?: string, provider?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", documentType);
    if (reportDate) {
      formData.append("report_date", reportDate);
    }
    if (provider) {
      formData.append("provider", provider);
    }
    return request<MedicalDocument>("/api/medical/documents", {
      method: "POST",
      body: formData,
    });
  },

  listDocuments: (params?: {
    document_type?: string;
    status?: string;
    search?: string;
    sort?: string;
    page?: number;
    page_size?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.document_type && params.document_type !== "all") {
      searchParams.append("document_type", params.document_type);
    }
    if (params?.status && params.status !== "all") {
      searchParams.append("status", params.status);
    }
    if (params?.search) {
      searchParams.append("search", params.search);
    }
    if (params?.sort) {
      searchParams.append("sort", params.sort);
    }
    if (params?.page) {
      searchParams.append("page", String(params.page));
    }
    if (params?.page_size) {
      searchParams.append("page_size", String(params.page_size));
    }
    const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<DocumentListResponse>(`/api/medical/documents${query}`);
  },

  getDocumentDetails: (id: string) => request<MedicalDocumentDetail>(`/api/medical/documents/${id}`),

  deleteDocument: (id: string) => request<void>(`/api/medical/documents/${id}`, { method: "DELETE" }),

  analyzeDocument: (id: string, provider?: string) => {
    const query = provider ? `?provider=${encodeURIComponent(provider)}` : "";
    return request<DocumentAnalysis>(`/api/medical/documents/${id}/analyze${query}`, { method: "POST" });
  },

  getProviderDiagnostics: () => request<any>("/api/medical/admin/diagnostics/provider"),

  testProviderConnectivity: (provider?: string) =>
    request<any>("/api/medical/admin/diagnostics/provider/test", {
      method: "POST",
      body: JSON.stringify(provider ? { provider } : {}),
      headers: { "Content-Type": "application/json" },
    }),

  downloadDocument: async (id: string, originalFilename: string) => {
    const response = await fetch(`${API_BASE_URL}/api/medical/documents/${id}/download`, {
      credentials: "include",
    });
    if (!response.ok) {
      throw new Error("Failed to download document");
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = originalFilename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  getFlags: (params?: { document_id?: string; severity?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.document_id) searchParams.append("document_id", params.document_id);
    if (params?.severity && params.severity !== "all") searchParams.append("severity", params.severity);
    const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<AbnormalityFlag[]>(`/api/medical/flags${query}`);
  },

  getTrends: (parameter?: string) => {
    const query = parameter ? `?parameter=${encodeURIComponent(parameter)}` : "";
    return request<TrendResponse>(`/api/medical/analytics/trends${query}`);
  },

  getComparison: () => request<ParameterComparisonResponse>("/api/medical/analytics/comparison"),

  getHistorical: () => request<ParameterComparisonResponse>("/api/medical/analytics/historical"),

  getTimeline: () => request<TimelineItem[]>("/api/medical/history/timeline"),

  getUploadHistory: () => request<MedicalDocument[]>("/api/medical/history/uploads"),

  getSummaryHistory: () => request<DocumentAnalysis[]>("/api/medical/history/summaries"),
};
