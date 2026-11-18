# MEDIFLOW — Agentic Health Management Platform

> **Your health history, intelligently connected.**  
> A privacy-first, local-first, AI-powered longitudinal personal healthcare management platform.

[![Release](https://img.shields.io/badge/Release-v2.0.0%20MVP-2457A6?style=flat)](https://github.com/astik77/MediFlow-agentic-health-management-platform/releases/tag/v2.0.0)
[![Tests](https://img.shields.io/badge/Tests-167%2F167%20Passing-157A5B?style=flat)](docs/quality/reports/TEST_REPORT_010_2026-11-18.txt)
[![Security](https://img.shields.io/badge/Security%20Controls-18%2F18%20Verified-157A5B?style=flat)](docs/quality/reports/BASELINE_STATUS.txt)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.163+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15.3+-000000?style=flat&logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+pgvector-336791?style=flat&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Ollama](https://img.shields.io/badge/Local%20AI-Ollama-172033?style=flat)](https://ollama.com/)
[![Docker](https://img.shields.io/badge/Self--Hosted-Docker%20%2B%20Caddy-2496ED?style=flat&logo=docker&logoColor=white)](docs/deployment/self-hosted-guide.md)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 1. Project Vision & Core Capabilities

MEDIFLOW consolidates fragmented personal medical records — laboratory blood panels, prescriptions, discharge summaries, imaging reports, and patient-reported symptoms — into a structured, chronological, patient-owned health vault.

Unlike generic health chatbots, MEDIFLOW is engineered around strict clinical governance and privacy guarantees:
- **Verified Clinical Provenance**: Preserves original raw values, normalized numeric values, units, reference ranges, source document page numbers, and immutable correction history (`SEC-018`).
- **Patient-in-the-Loop Governance**: OCR-extracted observations remain `candidate` and AI-suggested symptoms remain `pending` until explicitly confirmed, edited, or rejected by the patient — unconfirmed records never contaminate trend charts or KPI totals.
- **Zero-Leakage Patient-Specific Hybrid RAG**: Combines Okapi BM25 lexical search with dense vector similarity (`nomic-embed-text`) via Reciprocal Rank Fusion strictly scoped by authenticated `patient_id` (`SEC-003` / `RAG-008 = 0.00`).
- **Deterministic Clinical Safety**: Strictly informational; refuses diagnosis, prescribing, and dosage-change requests while deterministically escalating emergency red-flag symptoms (`AIR-004 = 100%`).
- **100% Local & Free Infrastructure**: Zero paid APIs required. Runs fully locally with FastAPI, Next.js, PostgreSQL + `pgvector`, RapidOCR ONNX, and local Ollama (`qwen2.5:1.5b` + `nomic-embed-text`), with graceful offline fallbacks when Ollama is unavailable.
- **Patient Data Sovereignty**: Full portable JSON health vault export (`GET /api/v1/patients/export`) and password-verified cascading account & physical disk erasure (`DELETE /api/v1/patients/account`).

---

## 2. Measured Quality & Security Benchmarks (`v2.0.0`)

| Evaluation Area | Measured Result | Target / Gate |
|---|---|---|
| **Automated Backend Suite** | **167/167 passed (100%, 0 warnings)** | 100% pass |
| **Security Controls (`SEC-001`–`SEC-018`)** | **18/18 verified** | 18/18 |
| **Document OCR (`DS-LAB/PRES/DISC/IMG`)** | **CER 0.36%, WER 4.17%, Completeness 100%** | CER < 5%, WER < 10% |
| **Classification & Numeric Extraction** | **100.0%** across all 12 synthetic docs | > 90% |
| **Clinical Safety Triage (`DS-SAFE-001`)** | **100.0% (30/30, 0 unsafe passes)** | 100% |
| **Hybrid RAG Retrieval (`DS-RAG-001/002`)** | **Recall@5 100%, Precision@1 100%, MRR 1.00** | Recall@5 > 80% |
| **Cross-Patient RAG Leakage (`RAG-008`)** | **0.00 (0 leaks / 20 adversarial queries)** | 0.00 (zero tolerance) |
| **Frontend Build (`tsc` + `eslint` + `next build`)** | **0 errors, 0 warnings, 15/15 static + dynamic built** | 0 errors |

Full quality reports and audit trails are tracked in [`docs/quality/`](docs/quality/reports/BASELINE_STATUS.txt).

---

## 3. Monorepo Structure

```
MediFlow-agentic-health-management-platform/
├── apps/
│   ├── web/                          # Next.js 15 App Router Frontend (TypeScript + Tailwind + Recharts)
│   │   ├── src/
│   │   │   ├── app/                  # Routes: /dashboard, /health, /documents, /timeline, /assistant, /profile
│   │   │   ├── components/           # Shared UI & Navigation Components
│   │   │   ├── features/             # Auth Context & Domain Hooks
│   │   │   └── lib/                  # Typed API Clients & Utilities
│   │   ├── Dockerfile                # Multi-stage standalone production build
│   │   └── package.json
│   │
│   └── api/                          # FastAPI Modular Monolith Backend (Python 3.11 + SQLAlchemy 2.0)
│       ├── mediflow/
│       │   ├── api/v1/routers/       # Versioned REST API Routers
│       │   ├── core/                 # Config, Async DB Engine, Security Headers, Logging
│       │   ├── modules/              # auth, patients, health_records, documents, conversations, analytics
│       │   ├── ai/                   # Ollama/Mock Providers, Prompt Registry, Safety, Agent, Hybrid RAG
│       │   └── main.py               # FastAPI App Factory & Lifespan
│       ├── migrations/               # Alembic Async Migrations (0001–0009, 19 tables)
│       ├── tests/                    # Pytest Suite (Unit, Integration, Security SEC-001–018)
│       ├── scripts/                  # Synthetic Evaluation Harnesses (OCR, Safety, RAG)
│       ├── Dockerfile                # Hardened non-root production image + auto-migrations
│       └── pyproject.toml
│
├── infra/
│   └── docker/
│       ├── postgres/init.sql         # pgvector & uuid-ossp initialization
│       └── caddy/Caddyfile           # Same-origin reverse proxy + automatic Let's Encrypt HTTPS
├── docs/
│   ├── product/                      # PRD & User Workflows
│   ├── architecture/                 # System Architecture, DB Design & API Specification
│   ├── deployment/                   # Self-Hosted Production Deployment Guide
│   ├── security/                     # Security Model & Threat Matrix (SEC-001–018)
│   └── quality/                      # Metrics Register, History, Baseline Status & Test Reports
├── docker-compose.yaml               # Local dev PostgreSQL 16 + pgvector container
├── docker-compose.prod.yaml          # Full self-hosted stack (Caddy + Web + API + Postgres + Ollama)
├── .env.example                      # Local development environment template
├── .env.prod.example                 # Self-hosted production environment template
└── README.md
```

---

## 4. Technology Stack

| Domain | Technology | Rationale |
|---|---|---|
| **Frontend** | Next.js 15 (App Router), TypeScript, Tailwind CSS, Recharts | Fast, accessible React UI with interactive biomarker trend charts |
| **State & Validation** | TanStack Query v5, React Hook Form, Zod | Declarative server-state caching and strict client validation |
| **Backend API** | FastAPI 0.163, Python 3.11, Pydantic v2, structlog | Async REST API with schema enforcement and secret-redacted logging |
| **Database & Vector** | PostgreSQL 16, `pgvector`, SQLAlchemy 2.0 (asyncio), Alembic | Unified relational + vector store with 9 versioned migrations |
| **Document OCR & Parsing** | PyMuPDF (`pymupdf`), Pillow, OpenCV, RapidOCR ONNX | Zero-OS-binary, CPU-friendly digital PDF & scanned report extraction |
| **Local AI & RAG** | Ollama (`qwen2.5:1.5b` + `nomic-embed-text`), BM25 + RRF | Free, private on-premise inference with deterministic offline fallbacks |
| **Deployment & Proxy** | Docker Compose, Caddy 2 (auto-HTTPS), `uv`, `pnpm` | Single-command self-hosted stack with same-origin `HttpOnly` cookies |

---

## 5. Self-Hosted Production Deployment (Recommended)

Deploy the complete stack (**Caddy + Next.js + FastAPI + PostgreSQL 16/pgvector + Local Ollama**) on your own PC, home server, or 4–8 GB RAM VPS with zero external API keys:

```bash
# 1. Copy production env template and fill in generated random secrets
cp .env.prod.example .env.prod

# 2. Launch stack (reusing host Ollama at http://host.docker.internal:11434)
docker compose -f docker-compose.prod.yaml --env-file .env.prod up -d --build

# Or on a fresh VPS with bundled Ollama + automatic model pulls:
docker compose -f docker-compose.prod.yaml --profile bundled-ollama --env-file .env.prod up -d --build
```

Open **`http://localhost`** (or your custom HTTPS domain configured via `MEDIFLOW_SITE_ADDRESS` in `.env.prod`).  
See the full setup, automatic HTTPS, Tailscale, backup, and upgrade instructions in [`docs/deployment/self-hosted-guide.md`](docs/deployment/self-hosted-guide.md).

---

## 6. Local Development Setup

### Prerequisites
- **Node.js** v20+ (v22 recommended) & `pnpm`
- **Python** 3.11+ & `uv`
- **Docker** (for PostgreSQL 16 + `pgvector`)
- **Ollama** *(optional)*: `ollama pull qwen2.5:1.5b && ollama pull nomic-embed-text`

### Run Locally
```bash
# 1. Environment & Database
cp .env.example .env
docker compose up -d

# 2. Backend API (Terminal 1)
cd apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn mediflow.main:app --reload --port 8000

# 3. Frontend (Terminal 2)
cd apps/web
pnpm install
pnpm dev
```

- **Patient Portal:** `http://localhost:3000`
- **API Swagger Docs:** `http://localhost:8000/docs`
- **Run Full Test Suite:** `cd apps/api && uv run pytest -v`

---

## 7. Development Roadmap (All Phases Complete)

- [x] **Phase 0: Workspace Inspection & Project Foundation**
  - Monorepo scaffolding, async database engine, health check endpoints, quality management framework, 25/25 automated tests passing.
- [x] **Phase 1: Authentication & Patient Profile**
  - Argon2id password hashing, HttpOnly server-managed sessions, session revocation, password recovery, patient onboarding & profile UI, backend ownership enforcement (`SEC-001/002`, `SEC-004`, `SEC-005`, `SEC-006`), 50/50 backend tests passing.
- [x] **Phase 2: Medical History Foundation**
  - Conditions, allergies, symptoms, numeric/non-numeric observations, immutable correction revision trail (`SEC-018`), chronological medical timeline, My Health & Timeline UI, strict patient isolation verified.
- [x] **Phase 3: Secure Document Management**
  - Private patient-isolated document vault, MIME & magic-byte signature validation (`SEC-007/008`), UUID path-traversal prevention (`SEC-009`), streaming size enforcement (`SEC-010`), SHA-256 integrity hashing, secure file download, soft-archive with disk deletion (`SEC-016`), FK links from health records, Document Vault UI, 91/91 backend tests passing.
- [x] **Phase 4: Document Intelligence & OCR**
  - PyMuPDF digital text & rasterization, Pillow/OpenCV preprocessing, local RapidOCR ONNX engine, `SEC-011` prompt-injection quarantine, deterministic medical classifier, clinical date/unit/observation parser, page-anchored RAG chunking, idempotent processing jobs (`SEC-017`), archive sync (`SEC-016`), two-pane Document Extraction & Candidate Review UI, synthetic evaluation baseline (CER 0.36%, WER 4.17%, 100% classification & extraction), 113/113 backend tests passing.
- [x] **Phase 5: Local AI Infrastructure**
  - Local-first Ollama provider (`qwen2.5:1.5b` + `nomic-embed-text`), optional synthetic-only Gemini/Grok adapters locked behind `SEC-014` Privacy Firewall, versioned Prompt Registry with `SEC-011` untrusted-data boundaries, Pydantic v2 structured output validator with retry & `SEC-013` `patient_id` guard, `SEC-015` structlog secret/transcript redaction, anonymized `ai_invocation_logs`, AI Plain-Language Document Summary & AI Privacy Status UI, 131/131 backend tests passing.
- [x] **Phase 6: AI Health Assistant**
  - Patient-scoped conversational AI Health Assistant (`conversations`, `messages`), deterministic pre/post-LLM clinical safety & emergency escalation layer (`AIR-004 = 100%` on `DS-SAFE-001`), `SEC-012` allowlisted read-only & proposal-only tool registry, symptom clarification & 1-click patient-confirmed symptom drafts, graceful offline Ollama fallback, `/assistant` UI, 143/143 backend tests passing.
- [x] **Phase 7: Patient-Specific Hybrid RAG**
  - Patient-scoped `document_embeddings`, local Ollama `nomic-embed-text` + deterministic offline fallback embedder, hybrid Okapi BM25 + cosine vector RRF retrieval, zero-tolerance cross-patient isolation (`SEC-003` / `RAG-008 = 0.00`), vector deletion sync on archive (`SEC-016`), AI Health Assistant page-level citations, Smart Health Search UI on `/documents`, `DS-RAG-001/002` baseline (Recall@5/MRR/Citation = 100%, 0 leaks), 150/150 backend tests passing.
- [x] **Phase 8: Dashboard Analytics, Biomarker Trends & 7-Day Health Summaries**
  - Patient-scoped `/api/v1/analytics/*` (`dashboard`, `trends`, `summaries`), persisted `health_summaries` (`0009`), unit-safe deterministic biomarker trend engine with reference-range bound parsing and strict candidate exclusion, `health_summary_7d@1.0.0` local AI synthesis (`SEC-013`/`SEC-014`) with seamless deterministic offline fallback, timeline `summary` event logging, interactive `/dashboard` UI powered by Recharts (`ReferenceArea` normal bands, KPI strip, pending review queue, 7-day summary generator & history), 162/162 backend tests passing.
- [x] **Phase 9: Security Hardening, Data Portability, Account Erasure & Release Verification** *(v2.0.0 — Release Ready)*
  - Pure ASGI `SecurityHeadersMiddleware` (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Cache-Control: no-store` on `/api/v1/*`) + matching Next.js headers, portable JSON vault export (`GET /api/v1/patients/export`), password-verified cascading account & disk erasure (`DELETE /api/v1/patients/account`), `/profile` Data Portability & Account Erasure UI, full Alembic `base <-> head` SQL verification, all 18/18 security controls (`SEC-001`–`SEC-018`) verified, 167/167 backend tests passing.
