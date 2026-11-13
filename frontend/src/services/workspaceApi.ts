import { request } from "./api";
import type {
  WorkspaceAnalysis,
  WorkspaceCompareResponse,
  WorkspaceDocument,
  WorkspaceDocumentListResponse,
  WorkspaceFinding,
  WorkspaceOverview,
} from "../types/workspace";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const workspaceApi = {
  getOverview: (workspace: string) => {
    return request<WorkspaceOverview>(`/api/workspaces/${workspace}/overview`);
  },

  uploadDocument: (
    workspace: string,
    file: File,
    subtype?: string,
    label?: string
  ) => {
    const formData = new FormData();
    formData.append("file", file);
    if (subtype && subtype !== "all") {
      formData.append("document_subtype", subtype);
    }
    if (label) {
      formData.append("label", label);
    }
    return request<WorkspaceDocument>(`/api/documents/${workspace}`, {
      method: "POST",
      body: formData,
    });
  },

  listDocuments: (
    workspace: string,
    params?: {
      search?: string;
      subtype?: string;
      status_filter?: string;
      sort?: string;
      page?: number;
      limit?: number;
    }
  ) => {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.append("search", params.search);
    if (params?.subtype && params.subtype !== "all") searchParams.append("subtype", params.subtype);
    if (params?.status_filter && params.status_filter !== "all") searchParams.append("status_filter", params.status_filter);
    if (params?.sort) searchParams.append("sort", params.sort);
    if (params?.page) searchParams.append("page", String(params.page));
    if (params?.limit) searchParams.append("limit", String(params.limit));

    const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<WorkspaceDocumentListResponse>(`/api/documents/${workspace}${qs}`);
  },

  getDocument: (workspace: string, documentId: string) => {
    return request<WorkspaceDocument>(`/api/documents/${workspace}/${documentId}`);
  },

  updateDocument: (
    workspace: string,
    documentId: string,
    payload: { document_subtype?: string; label?: string }
  ) => {
    return request<WorkspaceDocument>(`/api/documents/${workspace}/${documentId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  getStatus: (workspace: string, documentId: string) => {
    return request<{
      id: string;
      status: string;
      failure_code: string | null;
      failure_message: string | null;
      extraction_method: string | null;
      page_count: number;
      character_count: number;
      updated_at: string;
    }>(`/api/documents/${workspace}/${documentId}/status`);
  },

  getAnalysis: (workspace: string, documentId: string) => {
    return request<WorkspaceAnalysis>(`/api/documents/${workspace}/${documentId}/analysis`);
  },

  getFindings: (workspace: string, documentId: string) => {
    return request<WorkspaceFinding[]>(`/api/documents/${workspace}/${documentId}/findings`);
  },

  getWorkspaceFindings: (
    workspace: string,
    params?: { priority?: string; is_reviewed?: boolean; limit?: number }
  ) => {
    const searchParams = new URLSearchParams();
    if (params?.priority && params.priority !== "all") searchParams.append("priority", params.priority);
    if (params?.is_reviewed !== undefined) searchParams.append("is_reviewed", String(params.is_reviewed));
    if (params?.limit) searchParams.append("limit", String(params.limit));
    const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<WorkspaceFinding[]>(`/api/workspaces/${workspace}/findings${qs}`);
  },

  updateWorkspaceFinding: (
    workspace: string,
    findingId: string,
    payload: { is_reviewed?: boolean; review_status?: string }
  ) => {
    return request<WorkspaceFinding>(`/api/workspaces/${workspace}/findings/${findingId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  updateFinding: (
    workspace: string,
    documentId: string,
    findingId: string,
    payload: { is_reviewed?: boolean; review_status?: string }
  ) => {
    return request<WorkspaceFinding>(`/api/documents/${workspace}/${documentId}/findings/${findingId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  retryAnalysis: (workspace: string, documentId: string) => {
    return request<WorkspaceDocument>(`/api/documents/${workspace}/${documentId}/retry`, {
      method: "POST",
    });
  },

  deleteDocument: (workspace: string, documentId: string) => {
    return request<{ message: string }>(`/api/documents/${workspace}/${documentId}`, {
      method: "DELETE",
    });
  },

  compareDocuments: (workspace: string, doc1Id: string, doc2Id: string) => {
    return request<WorkspaceCompareResponse>(`/api/documents/${workspace}/compare`, {
      method: "POST",
      body: JSON.stringify({ document_id_1: doc1Id, document_id_2: doc2Id }),
    });
  },

  getDownloadUrl: (workspace: string, documentId: string) => {
    return `${API_BASE_URL}/api/documents/${workspace}/${documentId}/download`;
  },
};
