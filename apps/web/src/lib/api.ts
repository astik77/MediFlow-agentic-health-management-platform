import type {
  AuthStatus,
  LoginPayload,
  OnboardingPayload,
  PatientProfile,
  ProfileUpdatePayload,
  RegisterPayload,
  User,
} from "@/types/auth";
import type {
  HealthEvent,
  HealthObservation,
  HealthOverview,
  PatientAllergy,
  PatientCondition,
  PatientSymptom,
  RecordRevision,
  TimelineResponse,
} from "@/types/health";

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

export const healthRecordsApi = {
  getOverview: (): Promise<HealthOverview> =>
    apiRequest<HealthOverview>("/api/v1/health-records/overview"),

  // Conditions
  listConditions: (): Promise<PatientCondition[]> =>
    apiRequest<PatientCondition[]>("/api/v1/health-records/conditions"),
  createCondition: (payload: {
    name: string;
    status?: string;
    severity?: string | null;
    onset_date?: string | null;
    notes?: string | null;
  }): Promise<PatientCondition> =>
    apiRequest<PatientCondition>("/api/v1/health-records/conditions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  correctCondition: (
    id: string,
    payload: Record<string, unknown>
  ): Promise<PatientCondition> =>
    apiRequest<PatientCondition>(`/api/v1/health-records/conditions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  archiveCondition: (id: string, reason?: string): Promise<PatientCondition> =>
    apiRequest<PatientCondition>(
      `/api/v1/health-records/conditions/${id}${
        reason ? `?reason=${encodeURIComponent(reason)}` : ""
      }`,
      { method: "DELETE" }
    ),
  getConditionHistory: (id: string): Promise<RecordRevision[]> =>
    apiRequest<RecordRevision[]>(
      `/api/v1/health-records/conditions/${id}/history`
    ),

  // Allergies
  listAllergies: (): Promise<PatientAllergy[]> =>
    apiRequest<PatientAllergy[]>("/api/v1/health-records/allergies"),
  createAllergy: (payload: {
    allergen: string;
    category?: string;
    reaction?: string | null;
    severity?: string;
    status?: string;
    onset_date?: string | null;
    notes?: string | null;
  }): Promise<PatientAllergy> =>
    apiRequest<PatientAllergy>("/api/v1/health-records/allergies", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  correctAllergy: (
    id: string,
    payload: Record<string, unknown>
  ): Promise<PatientAllergy> =>
    apiRequest<PatientAllergy>(`/api/v1/health-records/allergies/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  archiveAllergy: (id: string, reason?: string): Promise<PatientAllergy> =>
    apiRequest<PatientAllergy>(
      `/api/v1/health-records/allergies/${id}${
        reason ? `?reason=${encodeURIComponent(reason)}` : ""
      }`,
      { method: "DELETE" }
    ),
  getAllergyHistory: (id: string): Promise<RecordRevision[]> =>
    apiRequest<RecordRevision[]>(
      `/api/v1/health-records/allergies/${id}/history`
    ),

  // Symptoms
  listSymptoms: (): Promise<PatientSymptom[]> =>
    apiRequest<PatientSymptom[]>("/api/v1/health-records/symptoms"),
  createSymptom: (payload: {
    name: string;
    severity?: string;
    frequency?: string | null;
    body_location?: string | null;
    status?: string;
    started_at?: string | null;
    notes?: string | null;
  }): Promise<PatientSymptom> =>
    apiRequest<PatientSymptom>("/api/v1/health-records/symptoms", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  correctSymptom: (
    id: string,
    payload: Record<string, unknown>
  ): Promise<PatientSymptom> =>
    apiRequest<PatientSymptom>(`/api/v1/health-records/symptoms/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  archiveSymptom: (id: string, reason?: string): Promise<PatientSymptom> =>
    apiRequest<PatientSymptom>(
      `/api/v1/health-records/symptoms/${id}${
        reason ? `?reason=${encodeURIComponent(reason)}` : ""
      }`,
      { method: "DELETE" }
    ),
  getSymptomHistory: (id: string): Promise<RecordRevision[]> =>
    apiRequest<RecordRevision[]>(
      `/api/v1/health-records/symptoms/${id}/history`
    ),

  // Observations
  listObservations: (params?: {
    observation_type?: string;
    display_name?: string;
  }): Promise<HealthObservation[]> => {
    const query = new URLSearchParams();
    if (params?.observation_type)
      query.set("observation_type", params.observation_type);
    if (params?.display_name) query.set("display_name", params.display_name);
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return apiRequest<HealthObservation[]>(
      `/api/v1/health-records/observations${suffix}`
    );
  },
  createObservation: (payload: {
    observation_type?: string;
    display_name: string;
    value_raw: string;
    unit_raw?: string | null;
    reference_range_text?: string | null;
    abnormality_flag?: string | null;
    observed_at?: string | null;
    notes?: string | null;
  }): Promise<HealthObservation> =>
    apiRequest<HealthObservation>("/api/v1/health-records/observations", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  correctObservation: (
    id: string,
    payload: Record<string, unknown>
  ): Promise<HealthObservation> =>
    apiRequest<HealthObservation>(`/api/v1/health-records/observations/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  archiveObservation: (
    id: string,
    reason?: string
  ): Promise<HealthObservation> =>
    apiRequest<HealthObservation>(
      `/api/v1/health-records/observations/${id}${
        reason ? `?reason=${encodeURIComponent(reason)}` : ""
      }`,
      { method: "DELETE" }
    ),
  getObservationHistory: (id: string): Promise<RecordRevision[]> =>
    apiRequest<RecordRevision[]>(
      `/api/v1/health-records/observations/${id}/history`
    ),
};

export const timelineApi = {
  list: (params?: {
    category?: string;
    start_date?: string;
    end_date?: string;
    q?: string;
    limit?: number;
    offset?: number;
  }): Promise<TimelineResponse> => {
    const query = new URLSearchParams();
    if (params?.category) query.set("category", params.category);
    if (params?.start_date) query.set("start_date", params.start_date);
    if (params?.end_date) query.set("end_date", params.end_date);
    if (params?.q) query.set("q", params.q);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return apiRequest<TimelineResponse>(`/api/v1/timeline${suffix}`);
  },

  createEvent: (payload: {
    event_category?: string;
    title: string;
    summary?: string | null;
    event_occurred_at?: string | null;
  }): Promise<HealthEvent> =>
    apiRequest<HealthEvent>("/api/v1/timeline/events", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
