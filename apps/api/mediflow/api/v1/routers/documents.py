"""
Documents API Router (v1).
Handles secure medical document upload, retrieval, metadata updates, and soft-archival.
NOTE: file_path is NEVER included in any response body.
"""
from __future__ import annotations

import urllib.parse
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.core.config import get_settings
from mediflow.core.database import get_db
from mediflow.core.dependencies import get_current_patient
from mediflow.modules.documents.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentType,
    DocumentUpdateRequest,
    ReviewStatus,
)
from mediflow.modules.documents.service import DocumentService
from mediflow.modules.patients.models import PatientProfile

router = APIRouter(prefix="/documents", tags=["documents"])

settings = get_settings()


def _storage_root() -> Path:
    """Return the configured document storage root path."""
    return Path(settings.upload_dir).resolve()


def _max_bytes() -> int:
    return settings.max_upload_size_mb * 1024 * 1024


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a medical document",
)
async def upload_document(
    file: UploadFile,
    document_type: DocumentType = Form(default="other"),
    title: str = Form(default=""),
    description: str | None = Form(default=None),
    document_date: date | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_patient: PatientProfile = Depends(get_current_patient),
) -> DocumentResponse:
    """
    Upload a medical document (PDF, JPEG, PNG, WebP, TIFF).
    - Validates MIME type against both Content-Type header and file magic bytes.
    - Enforces max upload size via streaming.
    - Stores file under a UUID-based filename to prevent path traversal.
    """
    doc = await DocumentService.upload_document(
        db=db,
        patient=current_patient,
        upload_file=file,
        document_type=document_type,
        title=title,
        description=description,
        document_date=document_date,
        storage_root=_storage_root(),
        max_size_bytes=_max_bytes(),
    )
    return DocumentResponse.model_validate(doc)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List patient's documents (paginated)",
)
async def list_documents(
    document_type: DocumentType | None = Query(default=None),
    review_status: ReviewStatus | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    q: str | None = Query(default=None),
    include_archived: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_patient: PatientProfile = Depends(get_current_patient),
) -> DocumentListResponse:
    """Return a paginated list of the authenticated patient's documents."""
    items, total = await DocumentService.list_documents(
        db=db,
        patient=current_patient,
        document_type=document_type,
        review_status=review_status,
        start_date=start_date,
        end_date=end_date,
        search=q,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


# ---------------------------------------------------------------------------
# Get metadata
# ---------------------------------------------------------------------------


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document metadata",
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_patient: PatientProfile = Depends(get_current_patient),
) -> DocumentResponse:
    """
    Return document metadata for the authenticated patient.
    Returns 403 Forbidden if owned by another patient, 404 if not found.
    """
    doc = await DocumentService.get_document(
        db=db,
        document_id=document_id,
        patient=current_patient,
    )
    return DocumentResponse.model_validate(doc)


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


@router.get(
    "/{document_id}/download",
    summary="Download (stream) a document file",
)
async def download_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_patient: PatientProfile = Depends(get_current_patient),
) -> FileResponse:
    """
    Stream the document file back to the authenticated patient.
    - Ownership and storage containment are enforced before file streaming.
    - Returns 403 Forbidden for cross-patient access, 410 Gone if archived.
    """
    file_path, media_type, original_filename = await DocumentService.resolve_download_path(
        db=db,
        document_id=document_id,
        patient=current_patient,
        storage_root=_storage_root(),
    )
    encoded_name = urllib.parse.quote(original_filename)
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
            "X-Content-Type-Options": "nosniff",
        },
    )


# ---------------------------------------------------------------------------
# Update metadata
# ---------------------------------------------------------------------------


@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Update document metadata",
)
async def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_patient: PatientProfile = Depends(get_current_patient),
) -> DocumentResponse:
    """Update title, description, document_date, document_type, or review_status."""
    doc = await DocumentService.update_document(
        db=db,
        document_id=document_id,
        patient=current_patient,
        payload=payload,
    )
    return DocumentResponse.model_validate(doc)


# ---------------------------------------------------------------------------
# Soft-archive (DELETE)
# ---------------------------------------------------------------------------


@router.delete(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Archive (soft-delete) a document",
)
async def archive_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_patient: PatientProfile = Depends(get_current_patient),
) -> DocumentResponse:
    """
    Soft-archive a document:
    - Marks it archived in the database.
    - Removes the file from disk.
    - Preserves metadata and timeline audit trail.
    """
    doc = await DocumentService.archive_document(
        db=db,
        document_id=document_id,
        patient=current_patient,
    )
    return DocumentResponse.model_validate(doc)
