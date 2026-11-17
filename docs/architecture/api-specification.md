# MEDIFLOW — API Specification (v1)

**Current Status:** Phase 0 (Health), Phase 1 (Authentication, Sessions, Patient Profiles), & Phase 2 (Medical History & Timeline) Implemented & Verified.  
**Base URL (Local Dev):** `http://localhost:8000`  
**API Prefix:** `/api/v1`  
**Authentication Mechanism:** Server-managed opaque sessions transmitted via `HttpOnly`, `SameSite=Lax`, `Secure` (production) cookie named `mediflow_session`. Optional `Authorization: Bearer <token>` fallback supported for automated testing.

---

## 1. Health & Diagnostics

### `GET /health`
Lightweight liveness probe (no database query).
- **Auth:** Public
- **200 OK Response:**
```json
{
  "status": "ok",
  "service": "mediflow-api",
  "version": "0.1.0",
  "environment": "development",
  "uptime_seconds": 12.4
}
```

### `GET /api/v1/health`
Comprehensive component readiness check (database + pgvector). Gracefully returns `"status": "degraded"` if database is unreachable.
- **Auth:** Public
- **200 OK Response:**
```json
{
  "status": "ok",
  "service": "mediflow-api",
  "version": "0.1.0",
  "environment": "development",
  "uptime_seconds": 15.8,
  "python": "3.11.4",
  "components": {
    "database": { "status": "healthy" },
    "pgvector": { "status": "installed", "version": "0.8.0" }
  }
}
```

---

## 2. Authentication (`/api/v1/auth`)

### `POST /api/v1/auth/register`
Creates a new patient user account (Argon2id hashed password) and an associated initial `PatientProfile`.
- **Auth:** Public
- **Request Body:**
```json
{
  "email": "patient@example.com",
  "password": "ValidPassword123!",
  "full_name": "Aarav Sharma"
}
```
- **201 Created:** `UserResponse` (`id`, `email`, `is_active`, `is_verified`, `created_at`)
- **400 Bad Request:** Email already registered
- **422 Unprocessable Entity:** Validation failed (e.g., invalid email or password < 8 characters)

### `POST /api/v1/auth/login`
Verifies credentials, generates a 256-bit cryptographic session token, persists only its SHA-256 hash in `sessions`, and attaches `mediflow_session` HttpOnly cookie.
- **Auth:** Public
- **Request Body:**
```json
{
  "email": "patient@example.com",
  "password": "ValidPassword123!"
}
```
- **200 OK:** `UserResponse` + `Set-Cookie: mediflow_session=...; HttpOnly; SameSite=lax; Path=/`
- **401 Unauthorized:** Invalid email or password

### `POST /api/v1/auth/logout`
Revokes the active server session (`is_revoked = true`) and clears the `mediflow_session` cookie (SEC-006).
- **Auth:** Optional (safe no-op if unauthenticated)
- **200 OK:** `{ "message": "Logged out successfully." }`

### `GET /api/v1/auth/me`
Checks current session validity and returns authentication status, user identity, patient ID, and onboarding flag.
- **Auth:** Session Cookie / Bearer
- **200 OK:**
```json
{
  "authenticated": true,
  "user": {
    "id": "uuid",
    "email": "patient@example.com",
    "is_active": true,
    "is_verified": false,
    "created_at": "2026-11-18T00:00:00Z"
  },
  "patient_id": "uuid",
  "is_onboarded": true
}
```

### `POST /api/v1/auth/sessions/revoke-all`
Revokes all active sessions across all devices for the authenticated user and clears the current cookie.
- **Auth:** Required (401 if unauthenticated — SEC-004)
- **200 OK:** `{ "message": "All active sessions have been revoked.", "revoked_count": 2 }`

### `POST /api/v1/auth/password-reset/request`
Generates a one-time cryptographic recovery token (1-hour expiry). Always returns a generic success message to prevent user email enumeration. In development/test mode only, includes `dev_reset_token`.
- **Auth:** Public
- **Request Body:** `{ "email": "patient@example.com" }`
- **200 OK:** `{ "message": "If an account matches that email, password reset instructions have been generated." }`

### `POST /api/v1/auth/password-reset/confirm`
Consumes a valid one-time recovery token, updates the user's Argon2id password hash, and revokes all existing active sessions.
- **Auth:** Public
- **Request Body:** `{ "token": "<opaque-token>", "new_password": "NewSecurePassword456!" }`
- **200 OK:** `{ "message": "Password has been successfully updated. Please log in with your new password." }`
- **400 Bad Request:** Token invalid, expired, or already used

---

## 3. Patient Profiles (`/api/v1/patients`)

All patient endpoints enforce authentication (401 on missing/expired/revoked session) and server-side patient ownership (403 on cross-patient access — SEC-001/SEC-002).

### `GET /api/v1/patients/profile`
Retrieves the authenticated patient's profile.
- **Auth:** Required (`get_current_patient`)
- **200 OK:** `PatientProfileResponse`

### `PUT /api/v1/patients/profile`
Applies partial demographic and baseline updates to the authenticated patient's profile.
- **Auth:** Required (`get_current_patient`)
- **Request Body (all fields optional):**
```json
{
  "full_name": "Aarav Sharma",
  "date_of_birth": "1994-05-15",
  "biological_sex": "male",
  "blood_group": "O+",
  "height_cm": 175.0,
  "weight_kg": 72.5,
  "emergency_contact": {
    "name": "Priya Sharma",
    "relationship": "Spouse",
    "phone_number": "+91-9876543210"
  },
  "medical_baseline": {
    "existing_conditions": ["Hypertension"],
    "known_allergies": ["Penicillin"]
  }
}
```
- **200 OK:** Updated `PatientProfileResponse`

### `POST /api/v1/patients/onboarding`
Saves initial baseline health parameters, emergency contact, existing conditions, and known allergies, and marks `is_onboarded = true`.
- **Auth:** Required (`get_current_patient`)
- **200 OK:** Updated `PatientProfileResponse`

### `GET /api/v1/patients/{patient_id}`
Retrieves a patient profile by UUID with strict server-side ownership enforcement (`enforce_patient_ownership`).
- **Auth:** Required (`get_current_patient`)
- **200 OK:** `PatientProfileResponse` (only when `patient_id == current_patient.id`)
- **403 Forbidden:** When `patient_id != current_patient.id` (prevents both cross-patient access and ID enumeration)


---

## 4. Medical History Records (`/api/v1/health-records`)

All endpoints require authentication (`401 Unauthorized`) and enforce strict patient ownership (`403 Forbidden` on cross-patient record access or modification — SEC-001/SEC-018). Every creation, correction, and archival operation atomically appends an immutable entry to `record_revisions` and updates `health_events`.

### `GET /api/v1/health-records/overview`
Returns summary counts (`conditions_count`, `active_conditions_count`, `allergies_count`, `symptoms_count`, `ongoing_symptoms_count`, `observations_count`, `timeline_events_count`) and the 5 most recent timeline events.

### Conditions (`/api/v1/health-records/conditions`)
- `GET /conditions?include_archived=false` — List patient conditions
- `POST /conditions` — Create condition (`201 Created`) + initial revision + timeline event
- `GET /conditions/{condition_id}` — Fetch single condition (ownership enforced)
- `PATCH /conditions/{condition_id}` — Non-destructive correction with optional `correction_reason`
- `DELETE /conditions/{condition_id}?reason=...` — Soft-archive condition & log `archived` revision
- `GET /conditions/{condition_id}/history` — Chronological `RecordRevision` trail

### Allergies (`/api/v1/health-records/allergies`)
- `GET /allergies`, `POST /allergies`, `GET /allergies/{id}`, `PATCH /allergies/{id}`, `DELETE /allergies/{id}`, `GET /allergies/{id}/history`

### Symptoms (`/api/v1/health-records/symptoms`)
- `GET /symptoms`, `POST /symptoms`, `GET /symptoms/{id}`, `PATCH /symptoms/{id}`, `DELETE /symptoms/{id}`, `GET /symptoms/{id}/history`

### Health Observations (`/api/v1/health-records/observations`)
Supports both numeric (`"13.5"`) and non-numeric (`"122/78"`, `"Positive"`) values while preserving `value_raw`, `unit_raw`, `value_numeric`, `reference_range_text`, `abnormality_flag`, and `observed_at`.
- `GET /observations?observation_type=...&display_name=...&include_archived=false`
- `POST /observations`, `GET /observations/{id}`, `PATCH /observations/{id}`, `DELETE /observations/{id}`, `GET /observations/{id}/history`

---

## 5. Medical Timeline (`/api/v1/timeline`)

### `GET /api/v1/timeline`
Returns paginated chronological events (`event_occurred_at DESC, created_at DESC`) strictly scoped to the authenticated patient.
- **Query Parameters:** `category`, `start_date`, `end_date`, `q` (search), `review_status`, `limit` (1–200, default 50), `offset` (default 0)
- **200 OK Response:** `{ "items": [...], "total": 12, "limit": 50, "offset": 0 }`

### `POST /api/v1/timeline/events`
Records a standalone patient-reported health event on the chronological timeline (`201 Created`).

---

## 6. Secure Document Vault (`/api/v1/documents`)

All endpoints require authentication (`401 Unauthorized`) and enforce strict server-side patient ownership (`403 Forbidden` on cross-patient access — SEC-001/002). Internal server filesystem paths (`file_path`) are **never** returned in any API payload.

### `POST /api/v1/documents`
Uploads a medical document via `multipart/form-data`.
- **Auth:** Required (`get_current_patient`)
- **Fields:** `file` (required binary), `document_type` (`lab_report`, `prescription`, `discharge_summary`, `imaging`, `clinical_note`, `insurance`, `other`), `title` (optional; defaults to sanitized filename), `description` (optional), `document_date` (optional ISO date `YYYY-MM-DD`)
- **Security Controls:**
  - `SEC-007`: Allowed MIME types only (`application/pdf`, `image/jpeg`, `image/png`, `image/webp`, `image/tiff`) — `415 Unsupported Media Type` otherwise
  - `SEC-008`: Magic-byte signature validated against declared `Content-Type` — `400 Bad Request` on mismatch
  - `SEC-009`: UUID-based stored filename inside `{upload_dir}/{patient_id}/` + `.resolve().is_relative_to()` containment check; user-supplied path separators stripped
  - `SEC-010`: Chunked streaming enforces `max_upload_size_mb` (`413 Content Too Large`) and rejects empty files (`400 Bad Request`) with automatic disk cleanup on failure
- **Side Effects:** Computes SHA-256 hash and creates a linked `document` entry in `health_events`
- **201 Created:** `DocumentResponse`

### `GET /api/v1/documents`
Returns a paginated list of the authenticated patient's documents (`uploaded_at DESC`).
- **Query Parameters:** `document_type`, `review_status`, `start_date`, `end_date`, `q` (search title/description/filename), `include_archived` (default `false`), `page` (default `1`), `page_size` (1–100, default `20`)
- **200 OK:** `{ "items": [...], "total": 5, "page": 1, "page_size": 20, "has_next": false }`

### `GET /api/v1/documents/{document_id}`
Returns metadata for a single document (`200 OK`, `403 Forbidden` if another patient's document, `404 Not Found` if missing).

### `GET /api/v1/documents/{document_id}/download`
Streams the document file as an attachment (`Content-Disposition: attachment; filename*=UTF-8''...`, `X-Content-Type-Options: nosniff`).
- **200 OK:** Binary stream with verified media type
- **403 Forbidden:** Cross-patient access attempt
- **410 Gone:** Document has been soft-archived and its disk file removed (SEC-016)

### `PATCH /api/v1/documents/{document_id}`
Updates mutable metadata (`title`, `description`, `document_type`, `document_date`, `review_status`). Returns `409 Conflict` if the document is archived.

### `DELETE /api/v1/documents/{document_id}`
Soft-archives the document: marks `is_archived = true`, sets `upload_status = "archived"`, deletes the physical file from disk, wipes derived `document_pages` and `document_chunks`, archives unconfirmed `candidate` observations (preserving patient-confirmed historical records), and logs an archival event on the timeline (`SEC-016`). Returns `409 Conflict` if already archived.

---

## 7. Document Intelligence, OCR & Candidate Review (Phase 4)

### `POST /api/v1/documents/{document_id}/process`
Runs the local-first document intelligence pipeline (PyMuPDF digital text extraction / rasterization, Pillow + OpenCV preprocessing, RapidOCR ONNX inference, `SEC-011` prompt-injection scanner, deterministic medical document classifier, clinical date/unit/observation parser, and page-anchored chunker).
- **Query Parameters:** `force` (boolean, default `false`)
- **Idempotency (`SEC-017`):** Returns the existing completed `DocumentProcessingJob` if already processed for the current `pipeline_version` when `force=false`. Rejects concurrent runs with `409 Conflict`. Re-processing with `force=true` refreshes pages, chunks, and unconfirmed candidates while preserving patient-confirmed observations.
- **200 OK:** `DocumentProcessingJobResponse`

### `GET /api/v1/documents/{document_id}/extraction`
Returns the document metadata, latest processing job, per-page extracted text & OCR confidence (`document_pages`), RAG-ready page-anchored chunks (`document_chunks`), classification summary, `SEC-011` security flags, and linked extracted/confirmed `HealthObservation` records.
- **200 OK:** `DocumentExtractionResponse` (`403 Forbidden` on cross-patient access)

### `POST /api/v1/documents/{document_id}/candidates/{observation_id}/review`
Applies explicit patient governance over an extracted `candidate` observation (extracted observations are never auto-confirmed).
- **Request Body:** `{ "action": "confirm" | "edit_confirm" | "reject", "display_name"?, "value_raw"?, "unit_raw"?, "reference_range_text"?, "abnormality_flag"?, "observed_at"?, "notes"?, "reason"? }`
- **Side Effects:** Appends an immutable `RecordRevision` snapshot, creates a `HealthEvent` on confirmation, and automatically transitions `document.review_status` to `"reviewed"` once all candidates for the document are finalized.
- **200 OK:** Updated `ObservationResponse` (`409 Conflict` if already finalized)

### `GET /api/v1/health-records/candidates`
Returns all active unreviewed `review_status = "candidate"` observations across the authenticated patient's documents to power the patient review queue.

---

## 8. Local AI Infrastructure (`/api/v1/ai`)

All endpoints require authentication (`401 Unauthorized`). Local Ollama (`qwen2.5:1.5b` + `nomic-embed-text`) is the default provider. External providers (`gemini`, `grok`) are disabled by default and hard-blocked on real patient data by the `SEC-014` Privacy Firewall (`403 Forbidden`). API keys and raw prompts/transcripts are never returned or logged (`SEC-015`).

### `GET /api/v1/ai/status`
Returns active provider configuration, recommended local models for host hardware, `SEC-014` privacy policy state, live reachability of local/external providers, and registered versioned prompt metadata (`prompt_id`, `version`, `sha256`).
- **200 OK:** `AIStatusResponse`

### `POST /api/v1/ai/documents/{document_id}/summarize`
Generates a schema-validated, plain-language, strictly informational summary of an already-processed medical document (`doc_summary@1.0.0`).
- **Query Parameters:** `provider` (optional override; external providers blocked for real patient data with `403`)
- **Security & Validation:**
  - Enforces document ownership (`403 Forbidden`)
  - Wraps extracted document text in `<UNTRUSTED_DOCUMENT_DATA>` delimiters (`SEC-011`)
  - Validates JSON output against `DocumentSummaryOutput` with automatic 1-retry repair (`AIR-001`)
  - Cross-checks emitted `patient_id` against authenticated session (`SEC-013`, rejects mismatch with `422`)
  - Persists anonymized telemetry row to `ai_invocation_logs`
- **200 OK:** `DocumentSummaryApiResponse` (`409 Conflict` if unprocessed/archived, `503 Service Unavailable` if Ollama offline)

---

## 9. AI Health Assistant & Conversations (`/api/v1/conversations`)

All endpoints require authentication (`401 Unauthorized`) and enforce strict cross-patient ownership (`403 Forbidden` — `SEC-001/SEC-002`). Assistant turns execute deterministic pre-LLM emergency & clinical-boundary safety triage (`AIR-004 = 100%`), read patient context strictly via `SEC-012` allowlisted read-only tools, and never autonomously write records to medical history.

### `POST /api/v1/conversations`
Creates a new active patient-scoped conversation (`201 Created`).

### `GET /api/v1/conversations?include_archived=false`
Lists the authenticated patient's conversations ordered by `last_message_at DESC`.

### `GET /api/v1/conversations/{conversation_id}`
Returns the conversation metadata and its chronological `messages` array (with `safety_level`, `cited_records_json`, `clarifying_questions_json`, and `proposed_action_json`).

### `DELETE /api/v1/conversations/{conversation_id}`
Soft-archives a conversation (`is_archived = true`, `status = "archived"`). Returns `409 Conflict` if already archived.

### `POST /api/v1/conversations/{conversation_id}/messages`
Posts a patient message and generates a safety-checked, record-grounded AI Health Assistant reply (`201 Created`).
- Emergency red flags immediately return `safety_level = "emergency_escalation"` with helpline guidance (`112` / `108` / Tele-MANAS `14416`), bypassing LLM latency.
- Prescribing, dosage-change, and diagnosis requests deterministically return `safety_level = "boundary_refusal"`.
- Gracefully falls back to record-grounded mode if local Ollama is offline.

### `POST /api/v1/conversations/{conversation_id}/messages/{message_id}/proposal`
Applies the patient's explicit decision (`"accept"` or `"dismiss"`) to an AI-proposed symptom draft. Accepting creates a `PatientSymptom` (`source_type = "ai_proposed"`, `review_status = "confirmed"`) with an immutable `RecordRevision` and `HealthEvent` on the Medical Timeline. Returns `409 Conflict` if already resolved.

---

## 10. Patient-Specific Hybrid RAG (`/api/v1/ai/rag`)

Strictly scoped to the authenticated patient (`WHERE patient_id = :session_patient_id AND document.is_archived = false`) plus a post-query defense-in-depth ownership assertion (`SEC-003`, `RAG-008 = 0.00`). Archiving a document atomically deletes its `document_embeddings` rows (`SEC-016`).

### `POST /api/v1/ai/rag/search`
Executes hybrid Okapi BM25 lexical + cosine dense vector retrieval merged via Reciprocal Rank Fusion (RRF) across all active processed chunks of the authenticated patient.
- **Request Body:** `{ "query": "fasting blood sugar", "top_k": 5, "document_type": null }`
- **200 OK:** `RagSearchResponse` containing ranked hits with `document_id`, `document_title`, `page_start`, `page_end`, `snippet`, `score`, `lexical_score`, `vector_score`, and `match_type` (`hybrid` | `semantic` | `lexical`).

### `POST /api/v1/ai/rag/reindex`
Re-embeds all active processed `document_chunks` for the authenticated patient using Ollama `nomic-embed-text` (when online) or deterministic local `local-hash-256-v1` fallback.
- **200 OK:** `RagReindexResponse` (`documents_indexed`, `chunks_indexed`, `embedding_model`, `dimensions`).

---

## 11. Dashboard Analytics, Biomarker Trends & 7-Day Summaries (`/api/v1/analytics`)

All endpoints require authentication (`401 Unauthorized` — `SEC-004`) and strictly derive scope from the authenticated patient session (`SEC-001/SEC-002`). Unconfirmed `candidate` and `rejected` observations never contaminate trend series or confirmed KPI counts.

### `GET /api/v1/analytics/dashboard`
Returns aggregated patient KPIs (`active_conditions_count`, `active_allergies_count`, `ongoing_symptoms_count`, `confirmed_observations_count`, `abnormal_observations_count`, `documents_count`, `pending_candidates_count`, `pending_symptom_proposals_count`), recent confirmed out-of-range observations, documents with pending candidate observations awaiting review, available trend biomarkers, and the latest persisted longitudinal health summary.
- **200 OK:** `DashboardResponse`

### `GET /api/v1/analytics/trends`
Computes chronological, unit-safe longitudinal biomarker time-series and deterministic statistics (`latest_value`, `previous_value`, `delta_absolute`, `delta_percent`, `direction`, `min_value`, `max_value`, `mean_value`, `reference_low`, `reference_high`).
- **Query Parameters:** `window` (`30d` | `90d` | `1y` | `all`, default `all`), `biomarker` (optional case-insensitive display name filter)
- **200 OK:** `BiomarkerTrendsResponse`

### `POST /api/v1/analytics/summaries`
Generates and persists a longitudinal health summary (`health_summaries`) covering the last `window_days` days (default `7`, range `7–90`) and logs a `"summary"` event on the patient's Medical Timeline.
- **Request Body:** `{ "window_days": 7 }` (optional; defaults to `7`)
- **AI Governance:** Uses local Ollama (`health_summary_7d@1.0.0`) with `SEC-014` local-only routing and `SEC-013` `patient_id` validation when online, falling back seamlessly to a deterministic statistical summary (`generation_mode = "deterministic_fallback"`) when offline or if validation fails.
- **201 Created:** `HealthSummaryResponse`

### `GET /api/v1/analytics/summaries`
Lists the authenticated patient's persisted historical health summaries ordered by `created_at DESC`.
- **Query Parameters:** `limit` (`1–100`, default `20`)
- **200 OK:** `HealthSummaryListResponse`
