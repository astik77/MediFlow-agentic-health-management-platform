# MEDIFLOW — Database Design Specification

## 1. Principles & Standards
1. **Relational Integrity**: Every patient-owned entity possesses a foreign key relationship to the primary patient profile or user identifier.
2. **Immutable Identifiers**: Primary keys utilize UUIDs (UUIDv7 or UUIDv4) generated server-side or via database defaults. Sequential IDs are never exposed externally.
3. **Auditability & Provenance**: Core clinical observations retain original raw values, normalized values, measurement units, reference ranges, source document IDs, and extraction statuses.
4. **Candidate vs Confirmed**: AI-extracted facts remain in a `candidate` state until explicitly reviewed and confirmed by the patient.

---

## 2. Entity-Relationship Overview

```mermaid
erDiagram
    USERS ||--|| PATIENT_PROFILES : "has"
    USERS ||--o{ SESSIONS : "holds"
    PATIENT_PROFILES ||--o{ HEALTH_EVENTS : "experiences"
    PATIENT_PROFILES ||--o{ HEALTH_OBSERVATIONS : "records"
    PATIENT_PROFILES ||--o{ DOCUMENTS : "owns"
    PATIENT_PROFILES ||--o{ CONVERSATIONS : "engages"
    PATIENT_PROFILES ||--o{ PATIENT_CONDITIONS : "diagnosed_with"
    PATIENT_PROFILES ||--o{ PATIENT_ALLERGIES : "suffers"
    PATIENT_PROFILES ||--o{ PATIENT_SYMPTOMS : "reports"
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : "divided_into"
    DOCUMENT_CHUNKS ||--o{ EMBEDDINGS : "vectorized_as"
    CONVERSATIONS ||--o{ MESSAGES : "contains"
    DOCUMENTS ||--o{ HEALTH_OBSERVATIONS : "sources"

    USERS {
        uuid id PK
        string email UK
        string password_hash
        boolean is_active
        boolean is_verified
        timestamp created_at
        timestamp updated_at
    }

    PATIENT_PROFILES {
        uuid id PK
        uuid user_id FK
        string full_name
        date date_of_birth
        string biological_sex
        string blood_group
        float height_cm
        float weight_kg
        jsonb emergency_contact
        timestamp created_at
    }

    DOCUMENTS {
        uuid id PK
        uuid patient_id FK
        string original_filename
        string file_path
        string mime_type
        integer file_size_bytes
        string sha256_hash
        string document_type
        string processing_status
        timestamp document_date
        timestamp uploaded_at
    }

    HEALTH_OBSERVATIONS {
        uuid id PK
        uuid patient_id FK
        uuid document_id FK
        string test_name
        string category
        string raw_value
        string raw_unit
        float normalized_value
        string normalized_unit
        string reference_range
        string abnormality_flag
        string review_status
        timestamp observation_date
    }

    HEALTH_EVENTS {
        uuid id PK
        uuid patient_id FK
        string event_type
        string title
        text description
        string source_type
        uuid source_id
        timestamp event_timestamp
    }
```

---

## 3. Migration Strategy (Alembic)
- Migrations are managed inside `apps/api/migrations/`.
- `alembic.ini` and `env.py` use an async SQLAlchemy runner connecting to PostgreSQL.
- Database naming conventions ensure clean, deterministic constraint names (`ix_`, `uq_`, `ck_`, `fk_`, `pk_`).
- Destructive schema drops are disallowed in production without explicit review and rollback scripts.
