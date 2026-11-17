# MEDIFLOW — API Specification (v1)

**Current Status:** Phase 0 (Health) & Phase 1 (Authentication, Sessions, Patient Profiles) Implemented & Verified.  
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
