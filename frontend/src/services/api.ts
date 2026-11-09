import type { AuthPayload, RegisterPayload, User } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_URL;

if (!API_BASE_URL) {
  throw new Error("VITE_API_URL is required. Set it in frontend/.env and restart the Vite server.");
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
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
  } catch {
    throw new ApiError("Unable to reach JohnnySummUP. Check your connection and try again.", 0);
  }

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail =
      typeof body === "object" && body !== null && "detail" in body && typeof body.detail === "string"
        ? body.detail
        : "Something went wrong. Please try again.";
    throw new ApiError(detail, response.status);
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
