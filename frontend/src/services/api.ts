import type {
  ApiResponse,
  AuthResponse,
  Capabilities,
  ComparisonData,
  DashboardStats,
  DocumentDetail,
  LoginRequest,
  MedicalDocumentItem,
  PaginatedResponse,
  PrescriptionItem,
  RegisterRequest,
  TrendData,
  User,
  MedicalFinding,
} from '../types';

const API_BASE = '/api/v1';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getHeaders(): HeadersInit {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    const token = localStorage.getItem('access_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = options.body instanceof FormData
      ? {
          ...(localStorage.getItem('access_token')
            ? { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
            : {}),
          ...options.headers,
        }
      : {
          ...this.getHeaders(),
          ...options.headers,
        };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMsg = 'An error occurred';
      let errorCode = 'UNKNOWN_ERROR';
      try {
        const body = await response.json();
        if (body.error) {
          errorMsg = body.error.message || errorMsg;
          errorCode = body.error.code || errorCode;
        } else if (body.detail) {
          errorMsg = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
        }
      } catch {
        // ignore parse errors
      }

      if (response.status === 401 && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/register')) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
      }

      throw new Error(errorMsg);
    }

    if (response.status === 204) {
      return {} as T;
    }

    const json = await response.json();
    return json.data !== undefined ? json.data : json;
  }

  // ── Auth ──────────────────────────────────────────────────────────
  async login(data: LoginRequest): Promise<AuthResponse> {
    return this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async register(data: RegisterRequest): Promise<AuthResponse> {
    return this.request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async forgotPassword(email: string): Promise<{ message: string }> {
    return this.request<{ message: string }>('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  async updateProfile(data: Partial<User>): Promise<User> {
    return this.request<User>('/auth/me', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // ── Capabilities ──────────────────────────────────────────────────
  async getCapabilities(): Promise<Capabilities> {
    return this.request<Capabilities>('/medical/capabilities');
  }

  // ── Documents ─────────────────────────────────────────────────────
  async getDocuments(params?: {
    page?: number;
    pageSize?: number;
    search?: string;
    document_type?: string;
    status?: string;
  }): Promise<{ items: MedicalDocumentItem[]; total: number; totalPages: number }> {
    const sp = new URLSearchParams();
    if (params?.page) sp.set('page', String(params.page));
    if (params?.pageSize) sp.set('page_size', String(params.pageSize));
    if (params?.search) sp.set('search', params.search);
    if (params?.document_type) sp.set('document_type', params.document_type);
    if (params?.status) sp.set('status', params.status);

    const query = sp.toString();
    const url = `${this.baseUrl}/medical/documents${query ? `?${query}` : ''}`;
    const token = localStorage.getItem('access_token');
    const res = await fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    const json = await res.json();
    return {
      items: json.data || [],
      total: json.pagination?.totalItems || 0,
      totalPages: json.pagination?.totalPages || 1,
    };
  }

  async getDocument(id: string): Promise<DocumentDetail> {
    return this.request<DocumentDetail>(`/medical/documents/${id}`);
  }

  async uploadDocument(
    file: File,
    documentType: string = 'lab_report',
    documentTitle?: string,
    testDate?: string
  ): Promise<{ documentId: string; jobId: string }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    if (documentTitle) formData.append('document_title', documentTitle);
    if (testDate) formData.append('test_date', testDate);

    return this.request<{ documentId: string; jobId: string }>(
      '/medical/documents/upload',
      {
        method: 'POST',
        body: formData,
      }
    );
  }

  async deleteDocument(id: string): Promise<void> {
    await this.request<void>(`/medical/documents/${id}`, { method: 'DELETE' });
  }

  getDocumentFileUrl(id: string): string {
    return `${this.baseUrl}/medical/documents/${id}/file`;
  }

  // ── Jobs ──────────────────────────────────────────────────────────
  async getJobStatus(jobId: string): Promise<{
    jobId: string;
    documentId: string;
    status: string;
    stage: string;
    progressPercent: number;
    safeMessage: string;
    retryable: boolean;
  }> {
    return this.request(`/medical/jobs/${jobId}`);
  }

  async retryJob(jobId: string): Promise<{ jobId: string; status: string }> {
    return this.request(`/medical/jobs/${jobId}/retry`, { method: 'POST' });
  }

  // ── Dashboard ─────────────────────────────────────────────────────
  async getDashboardStats(): Promise<DashboardStats> {
    return this.request<DashboardStats>('/medical/dashboard');
  }

  // ── Analytics ─────────────────────────────────────────────────────
  async getParameters(): Promise<Array<{ parameterCode: string; displayName: string; category: string }>> {
    return this.request('/medical/analytics/parameters');
  }

  async getTrends(parameterCode: string): Promise<TrendData> {
    return this.request<TrendData>(`/medical/analytics/trends?parameterCode=${encodeURIComponent(parameterCode)}`);
  }

  async compareReports(documentIds: string[]): Promise<ComparisonData> {
    return this.request<ComparisonData>('/medical/compare', {
      method: 'POST',
      body: JSON.stringify({ documentIds }),
    });
  }

  // ── Prescriptions ─────────────────────────────────────────────────
  async getPrescriptions(): Promise<PrescriptionItem[]> {
    return this.request<PrescriptionItem[]>('/medical/prescriptions');
  }

  // ── Insights ──────────────────────────────────────────────────────
  async getInsights(): Promise<MedicalFinding[]> {
    return this.request<MedicalFinding[]>('/medical/insights');
  }

  // ── Exports ───────────────────────────────────────────────────────
  async exportDocumentPdf(documentId: string): Promise<{ exportId: string; downloadUrl: string }> {
    return this.request<{ exportId: string; downloadUrl: string }>('/medical/exports', {
      method: 'POST',
      body: JSON.stringify({ documentId }),
    });
  }
}

export const api = new ApiClient(API_BASE);
export default api;
