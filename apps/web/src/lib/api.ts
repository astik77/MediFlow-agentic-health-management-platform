import type {
  AIStatusResponse,
  DocumentSummaryApiResponse,
  RagReindexResponse,
  RagSearchResponse,
} from "@/types/ai";
import type {
  BiomarkerTrendsResponse,
  DashboardResponse,
  HealthSummaryItem,
  HealthSummaryListResponse,
  TrendWindow,
} from "@/types/analytics";
import type {
  ConversationDetail,
  ConversationItem,
  ConversationMessage,
  MessageTurnResponse,
} from "@/types/conversations";
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
  CandidateReviewPayload,
  DocumentExtractionResponse,
  DocumentItem,
  DocumentListResponse,
  DocumentProcessingJob,
  DocumentUpdatePayload,
  DocumentUploadPayload,
} from "@/types/documents";
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
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

  exportData: (): Promise<Record<string, unknown>> =>
    apiRequest<Record<string, unknown>>("/api/v1/patients/export", {
      method: "GET",
    }),

  deleteAccount: (payload: {
    password: string;
    confirm_text: string;
  }): Promise<{
    deleted: boolean;
    deleted_at: string;
    files_removed: number;
    message: string;
  }> =>
    apiRequest("/api/v1/patients/account", {
      method: "DELETE",
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
  listPendingCandidates: (): Promise<HealthObservation[]> =>
    apiRequest<HealthObservation[]>("/api/v1/health-records/candidates"),
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

  deleteEvent: (eventId: string): Promise<void> =>
    apiRequest<void>(`/api/v1/timeline/events/${eventId}`, {
      method: "DELETE",
    }),
};

export const documentsApi = {
  list: (params?: {
    document_type?: string;
    review_status?: string;
    start_date?: string;
    end_date?: string;
    q?: string;
    include_archived?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<DocumentListResponse> => {
    const query = new URLSearchParams();
    if (params?.document_type) query.set("document_type", params.document_type);
    if (params?.review_status) query.set("review_status", params.review_status);
    if (params?.start_date) query.set("start_date", params.start_date);
    if (params?.end_date) query.set("end_date", params.end_date);
    if (params?.q) query.set("q", params.q);
    if (params?.include_archived) query.set("include_archived", "true");
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return apiRequest<DocumentListResponse>(`/api/v1/documents${suffix}`);
  },

  get: (id: string): Promise<DocumentItem> =>
    apiRequest<DocumentItem>(`/api/v1/documents/${id}`),

  upload: async (payload: DocumentUploadPayload): Promise<DocumentItem> => {
    const formData = new FormData();
    formData.append("file", payload.file);
    formData.append("document_type", payload.document_type);
    if (payload.title && payload.title.trim()) {
      formData.append("title", payload.title.trim());
    }
    if (payload.description && payload.description.trim()) {
      formData.append("description", payload.description.trim());
    }
    if (payload.document_date) {
      formData.append("document_date", payload.document_date);
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/documents`, {
      method: "POST",
      body: formData,
      credentials: "include",
    });

    if (!response.ok) {
      let detail = `Upload failed with status ${response.status}`;
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
        detail = response.statusText || detail;
      }
      throw new ApiError(response.status, detail);
    }

    return (await response.json()) as DocumentItem;
  },

  update: (
    id: string,
    payload: DocumentUpdatePayload
  ): Promise<DocumentItem> =>
    apiRequest<DocumentItem>(`/api/v1/documents/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  archive: (id: string): Promise<DocumentItem> =>
    apiRequest<DocumentItem>(`/api/v1/documents/${id}`, {
      method: "DELETE",
    }),

  getDownloadUrl: (id: string): string =>
    `${API_BASE_URL}/api/v1/documents/${id}/download`,

  process: (id: string, force = false, autoConfirm = true): Promise<DocumentProcessingJob> => {
    const params = new URLSearchParams();
    if (force) params.set("force", "true");
    if (autoConfirm) params.set("auto_confirm", "true");
    const qs = params.toString() ? `?${params.toString()}` : "";
    return apiRequest<DocumentProcessingJob>(
      `/api/v1/documents/${id}/process${qs}`,
      { method: "POST" }
    );
  },

  autoConfirm: (id: string): Promise<{ confirmed_count: number; document_id: string }> =>
    apiRequest<{ confirmed_count: number; document_id: string }>(
      `/api/v1/documents/${id}/auto-confirm`,
      { method: "POST" }
    ),

  getExtraction: (id: string): Promise<DocumentExtractionResponse> =>
    apiRequest<DocumentExtractionResponse>(`/api/v1/documents/${id}/extraction`),

  reviewCandidate: (
    documentId: string,
    observationId: string,
    payload: CandidateReviewPayload
  ): Promise<HealthObservation> =>
    apiRequest<HealthObservation>(
      `/api/v1/documents/${documentId}/candidates/${observationId}/review`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),
};

export const aiApi = {
  getStatus: (): Promise<AIStatusResponse> =>
    apiRequest<AIStatusResponse>("/api/v1/ai/status"),

  summarizeDocument: (
    documentId: string
  ): Promise<DocumentSummaryApiResponse> =>
    apiRequest<DocumentSummaryApiResponse>(
      `/api/v1/ai/documents/${documentId}/summarize`,
      { method: "POST" }
    ),

  searchDocuments: (payload: {
    query: string;
    top_k?: number;
    document_type?: string | null;
  }): Promise<RagSearchResponse> =>
    apiRequest<RagSearchResponse>("/api/v1/ai/rag/search", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  reindexDocuments: (): Promise<RagReindexResponse> =>
    apiRequest<RagReindexResponse>("/api/v1/ai/rag/reindex", {
      method: "POST",
    }),
};

export const conversationsApi = {
  list: (includeArchived = false): Promise<ConversationItem[]> =>
    apiRequest<ConversationItem[]>(
      `/api/v1/conversations${includeArchived ? "?include_archived=true" : ""}`
    ),

  create: (title?: string): Promise<ConversationItem> =>
    apiRequest<ConversationItem>("/api/v1/conversations", {
      method: "POST",
      body: JSON.stringify(title ? { title } : {}),
    }),

  getDetail: (id: string): Promise<ConversationDetail> =>
    apiRequest<ConversationDetail>(`/api/v1/conversations/${id}`),

  archive: (id: string): Promise<ConversationItem> =>
    apiRequest<ConversationItem>(`/api/v1/conversations/${id}`, {
      method: "DELETE",
    }),

  sendMessage: (
    conversationId: string,
    content: string
  ): Promise<MessageTurnResponse> =>
    apiRequest<MessageTurnResponse>(
      `/api/v1/conversations/${conversationId}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ content }),
      }
    ),

  resolveProposal: (
    conversationId: string,
    messageId: string,
    decision: "accept" | "dismiss",
    overrides?: {
      severity?: "mild" | "moderate" | "severe";
      name?: string;
      body_location?: string;
      notes?: string;
    }
  ): Promise<ConversationMessage> =>
    apiRequest<ConversationMessage>(
      `/api/v1/conversations/${conversationId}/messages/${messageId}/proposal`,
      {
        method: "POST",
        body: JSON.stringify({ decision, ...overrides }),
      }
    ),
};

export const analyticsApi = {
  getDashboard: (): Promise<DashboardResponse> =>
    apiRequest<DashboardResponse>("/api/v1/analytics/dashboard"),

  getTrends: (params?: {
    window?: TrendWindow;
    biomarker?: string;
  }): Promise<BiomarkerTrendsResponse> => {
    const query = new URLSearchParams();
    if (params?.window) query.set("window", params.window);
    if (params?.biomarker) query.set("biomarker", params.biomarker);
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return apiRequest<BiomarkerTrendsResponse>(
      `/api/v1/analytics/trends${suffix}`
    );
  },

  generateSummary: (windowDays = 7): Promise<HealthSummaryItem> =>
    apiRequest<HealthSummaryItem>("/api/v1/analytics/summaries", {
      method: "POST",
      body: JSON.stringify({ window_days: windowDays }),
    }),

  listSummaries: (limit = 20): Promise<HealthSummaryListResponse> =>
    apiRequest<HealthSummaryListResponse>(
      `/api/v1/analytics/summaries?limit=${limit}`
    ),
};
