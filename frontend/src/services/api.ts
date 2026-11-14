import type { AuthPayload, RegisterPayload, User } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(!isFormData ? { "Content-Type": "application/json" } : {}),
    ...(init?.headers as Record<string, string>),
  };

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: "include",
      headers,
    });
  } catch (err) {
    if (typeof window !== "undefined") {
      console.warn(
        "API request failed. Verify that backend is running and CORS allows origin:",
        window.location.origin,
        "Target URL:",
        `${API_BASE_URL}${path}`,
        err
      );
    }
    throw new ApiError(
      "Cannot connect to the backend server. Please verify the API server is running on " + API_BASE_URL,
      0,
      "NETWORK_ERROR"
    );
  }

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    let detail = "Something went wrong. Please try again.";
    let code: string | undefined;
    let requestId: string | undefined;

    if (typeof body === "object" && body !== null && "detail" in body) {
      const d = (body as any).detail;
      if (typeof d === "string") {
        detail = d;
      } else if (typeof d === "object" && d !== null) {
        detail = d.message || detail;
        code = d.code;
        requestId = d.request_id;
      }
    } else {
      if (response.status === 401) {
        detail = "Your session has expired. Please sign in again.";
      } else if (response.status === 403) {
        detail = "You do not have permission to access this resource.";
      } else if (response.status === 404) {
        detail = "The requested resource could not be found.";
      } else if (response.status >= 500) {
        detail = "Workspace service is temporarily unavailable. Please try again.";
      }
    }

    throw new ApiError(detail, response.status, code, requestId);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  currentUser: () => request<User>("/api/users/me"),
  register: (payload: RegisterPayload) =>
    request<User>("/api/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload: AuthPayload) =>
    request<User>("/api/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
};
