"""
Document Pydantic Schemas.
NOTE: file_path is intentionally absent from all response schemas.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

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
