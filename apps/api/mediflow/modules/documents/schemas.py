"""
Document Pydantic Schemas.
NOTE: file_path is intentionally absent from all response schemas.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from mediflow.modules.health_records.schemas import AbnormalityFlag, ObservationResponse

# ---------------------------------------------------------------------------
# Enumerations (plain Literals for strict validation)
# ---------------------------------------------------------------------------

DocumentType = Literal[
    "lab_report",
    "prescription",
    "discharge_summary",
    "imaging",
    "clinical_note",
    "insurance",
    "other",
]

UploadStatus = Literal["pending", "processing", "ready", "failed", "archived"]
ReviewStatus = Literal["unreviewed", "reviewed", "flagged"]


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class DocumentUpdateRequest(BaseModel):
    """Fields the patient is allowed to update after upload."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    document_type: DocumentType | None = None
    document_date: date | None = None
    review_status: ReviewStatus | None = None


# ---------------------------------------------------------------------------
# Response schemas  (file_path is NEVER included)
# ---------------------------------------------------------------------------


class DocumentResponse(BaseModel):
    """Public document metadata returned to the client."""

    id: uuid.UUID
    patient_id: uuid.UUID
    original_filename: str
    stored_filename: str
    mime_type: str
    file_size_bytes: int
    sha256_hash: str
    document_type: DocumentType
    source_type: str
    upload_status: UploadStatus
    review_status: ReviewStatus
    processing_error: str | None
    title: str
    description: str | None
    document_date: date | None
    page_count: int | None
    is_archived: bool
    uploaded_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Paginated document list."""

    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


# ---------------------------------------------------------------------------
# Phase 4: Document Intelligence & Candidate Review Schemas
# ---------------------------------------------------------------------------

JobStatus = Literal["queued", "running", "completed", "failed"]
CandidateReviewAction = Literal["confirm", "edit_confirm", "reject"]


class DocumentPageResponse(BaseModel):
    """Extracted text and OCR telemetry for a single page."""

    id: uuid.UUID
    document_id: uuid.UUID
    page_number: int
    extraction_method: str
    raw_text: str
    ocr_confidence: float | None
    char_count: int
    layout_metadata: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentChunkResponse(BaseModel):
    """Page-anchored chunk derived from extracted document pages."""

    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    page_start: int
    page_end: int
    content: str
    token_estimate: int
    section_heading: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentProcessingJobResponse(BaseModel):
    """Status and metrics of a document processing job."""

    id: uuid.UUID
    document_id: uuid.UUID
    pipeline_version: str
    status: JobStatus
    attempt_count: int
    error_message: str | None
    metrics_json: dict[str, Any] | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentExtractionResponse(BaseModel):
    """Full Phase 4 extraction inspection payload for a patient document."""

    document: DocumentResponse
    latest_job: DocumentProcessingJobResponse | None
    pages: list[DocumentPageResponse]
    chunks_count: int
    chunks: list[DocumentChunkResponse]
    observations: list[ObservationResponse]
    classification: dict[str, Any] | None
    security_flags: list[dict[str, Any]]


class CandidateReviewRequest(BaseModel):
    """Patient review decision on an AI/parser-extracted candidate observation."""

    action: CandidateReviewAction
    display_name: str | None = Field(None, min_length=1, max_length=255)
    value_raw: str | None = Field(None, min_length=1, max_length=255)
    unit_raw: str | None = Field(None, max_length=64)
    reference_range_text: str | None = Field(None, max_length=255)
    abnormality_flag: AbnormalityFlag | None = None
    observed_at: datetime | None = None
    notes: str | None = None
    reason: str | None = Field(None, max_length=500)
