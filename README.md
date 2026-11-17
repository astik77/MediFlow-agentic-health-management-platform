# MEDIFLOW — Agentic Health Management Platform

> **Your health history, intelligently connected.**  
> A privacy-first, AI-powered longitudinal personal healthcare management platform.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.163+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15.3+-000000?style=flat&logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+pgvector-336791?style=flat&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4+-38B2AC?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 1. Project Vision & Identity

MEDIFLOW consolidates fragmented medical records — laboratory blood panels, handwritten prescriptions, radiology summaries, doctor consultation notes, and patient-reported symptoms — into a structured, chronological personal health record. 

Unlike generic health chatbots, MEDIFLOW emphasizes:
- **Verified Clinical Provenance**: Preserves original values, normalized values, units, reference ranges, and source document page references.
- **Patient Review & Confirmation**: AI-extracted facts are marked as `candidate` until explicitly confirmed or corrected by the patient.
- **Patient-Scoped Retrieval (RAG)**: Zero cross-patient leakage with hybrid vector + full-text search anchored strictly to authenticated records.
- **Deterministic AI Safety**: Strictly informational; does not diagnose, prescribe, or alter dosages. Deterministic escalations for urgent symptoms.
- **Cost & Resource Discipline**: Developed using 100% free and open-source infrastructure (FastAPI, Next.js, PostgreSQL with pgvector, and local Ollama inference).

---

## 2. Monorepo Structure

```
MediFlow-agentic-health-management-platform/
├── apps/
│   ├── web/                          # Next.js 15 App Router Frontend
│   │   ├── src/
│   │   │   ├── app/                  # Application Routes & Pages
│   │   │   ├── components/           # UI Components (shadcn/ui + Tailwind)
│   │   │   ├── lib/                  # Utilities & API Clients
│   │   └── package.json
│   │
│   └── api/                          # FastAPI Modular Monolith Backend
│       ├── mediflow/
│       │   ├── api/v1/routers/       # API Version 1 Endpoints
│       │   ├── core/                 # Config, Async Database Engine, Logging
│       │   ├── modules/              # Domain Modules (auth, health_records, etc.)
│       │   ├── ai/                   # AI Subsystem (providers, RAG, safety)
│       │   └── main.py               # FastAPI App Factory & Lifespan
│       ├── migrations/               # Alembic Async Migrations
│       ├── tests/                    # Pytest Suite (Unit, Integration, Security)
│       └── pyproject.toml
│
├── infra/
│   └── docker/
│       └── postgres/init.sql         # pgvector & uuid-ossp initialization
├── docs/
│   ├── product/                      # PRD & User Workflows
│   ├── architecture/                 # System Architecture & Database Design
│   ├── security/                     # Security Model & Threat Matrix (SEC-001–018)
│   └── quality/                      # Metrics Register, Baseline Status, Test Reports
├── docker-compose.yaml               # Reproducible PostgreSQL 16 + pgvector container
├── .env.example                      # Documented environment variables
└── README.md
```

---

## 3. Technology Stack

| Domain | Technology | Rationale |
|---|---|---|
| **Frontend** | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui | Modern, accessible, server-rendered with zero runtime overhead |
| **Data Fetching & Forms** | TanStack Query v5, React Hook Form, Zod | Declarative server-state caching and strict type-safe validation |
| **Backend API** | FastAPI 0.163, Python 3.11, Pydantic v2, structlog | High-performance asynchronous API with compile-time type verification |
| **Database & Vector** | PostgreSQL 16, pgvector, SQLAlchemy 2.0 (asyncio) | Unified relational + semantic vector store; eliminates external vector DB costs |
| **Schema Migrations** | Alembic (async runner) | Version-controlled, reproducible schema evolutions |
| **Package Management** | `uv` (Python), `pnpm` (Node.js) | Blazing fast, deterministic dependency resolution and committed lockfiles |
| **Local Inference** | Ollama (`qwen2.5:1.5b` / `phi3.5:3.8b`) | Free, private, hardware-compatible on-premise local inference |

---

## 4. Getting Started

### 4.1 Prerequisites
- **Node.js**: v20+ (v22 recommended) and `pnpm` (`npm install -g pnpm`)
- **Python**: 3.11+ and `uv` (`powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"`)
- **Docker**: Docker Desktop with WSL2 engine for PostgreSQL

### 4.2 Environment Configuration
Copy `.env.example` to `.env` in the repository root:
```bash
cp .env.example .env
```

### 4.3 Start Database
```bash
docker compose up -d
```

### 4.4 Backend Setup & Execution
```bash
cd apps/api

# Install dependencies into virtual environment
uv sync

# Run automated test suite
uv run pytest -v

# Start FastAPI development server
uv run uvicorn mediflow.main:app --reload --port 8000
```
API Documentation will be live at: `http://localhost:8000/docs`

### 4.5 Frontend Setup & Execution
```bash
cd apps/web

# Install dependencies
pnpm install

# Run production build validation
pnpm build

# Start Next.js development server
pnpm dev
```
Patient Portal will be live at: `http://localhost:3000`

---

## 5. Development Roadmap

- [x] **Phase 0: Workspace Inspection & Project Foundation**
  - Monorepo scaffolding, async database engine, health check endpoints, quality management framework, 25/25 automated tests passing.
- [x] **Phase 1: Authentication & Patient Profile**
  - Argon2id password hashing, HttpOnly server-managed sessions, session revocation, password recovery, patient onboarding & profile UI, backend ownership enforcement (SEC-001/002, SEC-004, SEC-005, SEC-006), 50/50 backend tests passing.
- [x] **Phase 2: Medical History Foundation**
  - Conditions, allergies, symptoms, numeric/non-numeric observations, immutable correction revision trail (SEC-018), chronological medical timeline, My Health & Timeline UI, strict patient isolation verified.
- [x] **Phase 3: Secure Document Management**
  - Private patient-isolated document vault, MIME & magic-byte signature validation (SEC-007/008), UUID path-traversal prevention (SEC-009), streaming size enforcement (SEC-010), SHA-256 integrity hashing, secure file download, soft-archive with disk deletion (SEC-016), FK links from health records, Document Vault UI, 91/91 backend tests passing.
- [x] **Phase 4: Document Intelligence & OCR**
  - PyMuPDF digital text & rasterization, Pillow/OpenCV preprocessing, local RapidOCR ONNX engine, SEC-011 prompt-injection quarantine, deterministic medical classifier, clinical date/unit/observation parser, page-anchored RAG chunking, idempotent processing jobs (SEC-017), archive sync (SEC-016), two-pane Document Extraction & Candidate Review UI, synthetic evaluation baseline (CER 0.36%, WER 4.17%, 100% classification & extraction), 113/113 backend tests passing.
- [x] **Phase 5: Local AI Infrastructure**
  - Local-first Ollama provider (`qwen2.5:1.5b` + `nomic-embed-text`), optional synthetic-only Gemini/Grok adapters locked behind SEC-014 Privacy Firewall, versioned Prompt Registry with SEC-011 untrusted-data boundaries, Pydantic v2 structured output validator with retry & SEC-013 patient_id guard, SEC-015 structlog secret/transcript redaction, anonymized `ai_invocation_logs`, AI Plain-Language Document Summary & AI Privacy Status UI, 131/131 backend tests passing.
- [x] **Phase 6: AI Health Assistant**
  - Patient-scoped conversational AI Health Assistant (`conversations`, `messages`), deterministic pre/post-LLM clinical safety & emergency escalation layer (`AIR-004 = 100%` on `DS-SAFE-001`), SEC-012 allowlisted read-only & proposal-only tool registry, symptom clarification & 1-click patient-confirmed symptom drafts, graceful offline Ollama fallback, `/assistant` UI, 143/143 backend tests passing.
- [x] **Phase 7: Patient-Specific RAG**
  - Patient-scoped `document_embeddings`, local Ollama `nomic-embed-text` + deterministic offline fallback embedder, hybrid Okapi BM25 + cosine vector RRF retrieval, zero-tolerance cross-patient isolation (`SEC-003` / `RAG-008 = 0.00`), vector deletion sync on archive (`SEC-016`), AI Health Assistant page-level citations, Smart Health Search UI on `/documents`, `DS-RAG-001/002` baseline (Recall@5/MRR/Citation=100%, 0 leaks), 150/150 backend tests passing.
- [x] **Phase 8: Dashboard Analytics, Biomarker Trends & 7-Day Health Summaries**
  - Patient-scoped `/api/v1/analytics/*` (`dashboard`, `trends`, `summaries`), persisted `health_summaries` (`0009`), unit-safe deterministic biomarker trend engine with reference-range bound parsing and strict candidate exclusion, `health_summary_7d@1.0.0` local AI synthesis (`SEC-013`/`SEC-014`) with seamless deterministic offline fallback, timeline `summary` event logging, interactive `/dashboard` UI powered by Recharts (`ReferenceArea` normal bands, KPI strip, pending review queue, 7-day summary generator & history), 162/162 backend tests passing.
- [x] **Phase 9: Security Hardening, Data Portability, Account Erasure & Release Verification** *(v2.0.0 — Release Ready)*
  - Pure ASGI `SecurityHeadersMiddleware` (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Cache-Control: no-store` on `/api/v1/*`) + matching Next.js headers, portable JSON vault export (`GET /api/v1/patients/export`), password-verified cascading account & disk erasure (`DELETE /api/v1/patients/account`), `/profile` Data Portability & Account Erasure UI, full Alembic `base <-> head` SQL verification, all 18/18 security controls (`SEC-001`–`SEC-018`) verified, 167/167 backend tests passing.
