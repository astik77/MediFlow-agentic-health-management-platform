"""
Phase 5 AI Infrastructure Pydantic Schemas.
NOTE: API keys and raw prompts are NEVER included in any response schema.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MedicalTermExplanation(BaseModel):
    """Plain-language glossary item explaining a medical term from a document."""

    term: str = Field(..., min_length=1, max_length=120)
    explanation: str = Field(..., min_length=1, max_length=500)


class DocumentSummaryOutput(BaseModel):
    """
    Strictly validated structured output produced by the LLM for `doc_summary`.
    Includes patient_id so SEC-013 cross-checks against the authenticated session.
    """

    patient_id: uuid.UUID
    plain_language_summary: str = Field(..., min_length=10, max_length=2000)
    key_findings: list[str] = Field(default_factory=list, max_length=12)
    medical_terms_explained: list[MedicalTermExplanation] = Field(
        default_factory=list, max_length=10
    )
    questions_for_doctor: list[str] = Field(default_factory=list, max_length=8)
    informational_disclaimer: str = Field(
        default=(
            "This summary is generated for informational purposes only and is not "
            "a medical diagnosis, prescription, or substitute for professional medical advice."
        ),
        min_length=10,
        max_length=500,
    )


class ProviderHealthResponse(BaseModel):
    """Safe provider health telemetry (never leaks API keys)."""

    provider: str
    is_local: bool
    available: bool
    default_model: str
    installed_models: list[str] = Field(default_factory=list)
    detail: str | None = None


class PrivacyPolicyStatusResponse(BaseModel):
    """Exposes active SEC-014 privacy guardrails transparently to the patient."""

    local_first: bool
    external_ai_enabled: bool
    allow_external_ai_for_real_data: bool
    external_ai_synthetic_only: bool


class AIStatusResponse(BaseModel):
    """Response for GET /api/v1/ai/status."""

    default_provider: str
    default_model: str
    embedding_model: str
    recommended_local_models: list[str]
    privacy_policy: PrivacyPolicyStatusResponse
    providers: list[ProviderHealthResponse]
    prompt_registry: list[dict[str, str]]


class DocumentSummaryApiResponse(BaseModel):
    """API response for POST /api/v1/ai/documents/{document_id}/summarize."""

    document_id: uuid.UUID
    provider: str
    model: str
    prompt_id: str
    prompt_version: str
    latency_ms: float
    attempts: int
    summary: DocumentSummaryOutput
    generated_at: datetime


# ---------------------------------------------------------------------------
# Phase 7: Patient-Specific Hybrid RAG Schemas
# ---------------------------------------------------------------------------


class RagSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    document_type: str | None = Field(default=None, max_length=50)


class RagSearchHitResponse(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    document_type: str
    document_date: str | None
    page_start: int
    page_end: int
    section_heading: str | None
    snippet: str
    score: float
    lexical_score: float
    vector_score: float
    match_type: str


class RagSearchResponse(BaseModel):
    query: str
    embedding_model: str
    total_hits: int
    hits: list[RagSearchHitResponse]


class RagReindexResponse(BaseModel):
    documents_indexed: int
    chunks_indexed: int
    embedding_model: str
    dimensions: int
