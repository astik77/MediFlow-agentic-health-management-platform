import type {
  AuthStatus,
  LoginPayload,
  OnboardingPayload,
  PatientProfile,
  ProfileUpdatePayload,
  RegisterPayload,
  User,
} from "@/types/auth";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
    // Always include HttpOnly session cookies for cross-origin requests
    credentials: "include",
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const errorData = (await response.json()) as {
        detail?: string | Array<{ msg?: string }>;
        message?: string;
      };
      if (typeof errorData.detail === "string") {
        detail = errorData.detail;
      } else if (Array.isArray(errorData.detail) && errorData.detail[0]?.msg) {
        detail = errorData.detail[0].msg;
      } else if (errorData.message) {
        detail = errorData.message;
      }
    } catch {
      // Fallback to status text
      detail = response.statusText || detail;
    }
    throw new ApiError(response.status, detail);
  }

  return (await response.json()) as T;
}

export const authApi = {
  getMe: (): Promise<AuthStatus> =>
    apiRequest<AuthStatus>("/api/v1/auth/me", { method: "GET" }),

  register: (payload: RegisterPayload): Promise<User> =>
    apiRequest<User>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  login: (payload: LoginPayload): Promise<User> =>
    apiRequest<User>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  logout: (): Promise<{ message: string }> =>
    apiRequest<{ message: string }>("/api/v1/auth/logout", {
      method: "POST",
    }),

  revokeAllSessions: (): Promise<{ message: string; revoked_count: number }> =>
    apiRequest<{ message: string; revoked_count: number }>(
      "/api/v1/auth/sessions/revoke-all",
      { method: "POST" }
    ),

  requestPasswordReset: (
    email: string
  ): Promise<{ message: string; dev_reset_token?: string }> =>
    apiRequest<{ message: string; dev_reset_token?: string }>(
      "/api/v1/auth/password-reset/request",
      {
        method: "POST",
        body: JSON.stringify({ email }),
      }
    ),

  confirmPasswordReset: (
    token: string,
    newPassword: string
  ): Promise<{ message: string }> =>
    apiRequest<{ message: string }>("/api/v1/auth/password-reset/confirm", {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
    }),
};

export const patientApi = {
  getProfile: (): Promise<PatientProfile> =>
    apiRequest<PatientProfile>("/api/v1/patients/profile", { method: "GET" }),

  updateProfile: (payload: ProfileUpdatePayload): Promise<PatientProfile> =>
    apiRequest<PatientProfile>("/api/v1/patients/profile", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  completeOnboarding: (payload: OnboardingPayload): Promise<PatientProfile> =>
    apiRequest<PatientProfile>("/api/v1/patients/onboarding", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
