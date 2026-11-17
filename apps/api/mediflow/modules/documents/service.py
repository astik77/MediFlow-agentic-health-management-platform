"""
Document Service — business logic for secure file upload, retrieval and management.

Security controls implemented here:
- SEC-001/002: Strict patient ownership enforcement via enforce_patient_ownership (403 Forbidden)
- SEC-007: Allowed MIME type validation (Content-Type header + magic-byte signature)
- SEC-008: File signature mismatch detection
- SEC-009: Path traversal prevention (UUID-only stored filenames + storage root containment check)
- SEC-010: Resource exhaustion guard (chunked streaming with strict max upload size enforcement)
"""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, date, datetime, time
from pathlib import Path

import structlog
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.core.dependencies import enforce_patient_ownership
from mediflow.modules.documents.models import Document
from mediflow.modules.documents.schemas import DocumentType, DocumentUpdateRequest
from mediflow.modules.health_records.models import HealthEvent
from mediflow.modules.patients.models import PatientProfile

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# MIME-type / file-signature validation tables
# SEC-007 & SEC-008
# ---------------------------------------------------------------------------

#: Allowed MIME types -> canonical extension
ALLOWED_MIME_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/tiff": "tif",
}

#: Magic-byte signatures for each allowed MIME type (first N bytes)
MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "application/pdf": [b"%PDF"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [],  # Validated by RIFF + WEBP marker below
    "image/tiff": [b"II*\x00", b"MM\x00*"],
}

WEBP_RIFF = b"RIFF"
WEBP_MARKER = b"WEBP"
STREAM_CHUNK_BYTES = 1024 * 1024  # 1 MiB chunks for streaming reads


def _validate_magic(data: bytes, mime_type: str) -> bool:
    """Return True if *data* starts with a known magic signature for *mime_type*."""
    if mime_type == "image/webp":
        return len(data) >= 12 and data[:4] == WEBP_RIFF and data[8:12] == WEBP_MARKER
    sigs = MAGIC_SIGNATURES.get(mime_type, [])
    if not sigs:
        return False
    return any(data[: len(sig)] == sig for sig in sigs)


def _sanitize_filename(raw_name: str | None) -> str:
    """
    Strip POSIX/Windows path separators and control characters from a user-supplied filename.
    Used ONLY for display metadata (original_filename); never used to build storage paths.
    """
    if not raw_name:
        return "upload"
    cleaned = raw_name.replace("\x00", "")
    leaf = re.split(r"[/\\]", cleaned)[-1].strip()
    leaf = re.sub(r"[\x00-\x1f\x7f]", "", leaf)
    if not leaf or leaf in {".", ".."}:
        return "upload"
    return leaf[:255]


def _date_to_utc_datetime(value: date | None) -> datetime:
    """Convert an optional clinical date to a timezone-aware UTC datetime."""
    if value is None:
        return datetime.now(UTC)
    return datetime.combine(value, time.min, tzinfo=UTC)


def _assert_within_storage_root(file_path: Path, storage_root: Path) -> Path:
    """Verify resolved file_path stays strictly inside storage_root (SEC-009 defense-in-depth)."""
    resolved_root = storage_root.resolve()
    resolved_target = file_path.resolve()
    if not resolved_target.is_relative_to(resolved_root):
        logger.error(
            "storage_path_escape_blocked",
            resolved_target=str(resolved_target),
            resolved_root=str(resolved_root),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document storage path.",
        )
    return resolved_target


# ---------------------------------------------------------------------------
# DocumentService
# ---------------------------------------------------------------------------


class DocumentService:
    """Encapsulates all document management business logic."""

    # --- Upload ---------------------------------------------------------------

    @staticmethod
    async def upload_document(
        *,
        db: AsyncSession,
        patient: PatientProfile,
        upload_file: UploadFile,
        document_type: DocumentType,
        title: str,
        description: str | None,
        document_date: date | None,
        storage_root: Path,
        max_size_bytes: int,
    ) -> Document:
        """
        Validate and store an uploaded file, then create a Document row and timeline event.

        Raises HTTP 400/413/415 on validation failure.
        """
        # SEC-007: Check declared MIME type
        content_type = (upload_file.content_type or "").split(";")[0].strip().lower()
        if content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=(
                    f"Unsupported file type '{content_type}'. "
                    f"Allowed: {', '.join(ALLOWED_MIME_TYPES)}"
                ),
            )

        # SEC-009: UUID-based stored filename — no user-supplied path segments ever used
        stored_name = f"{uuid.uuid4().hex}.{ALLOWED_MIME_TYPES[content_type]}"
        patient_dir = _assert_within_storage_root(
            storage_root / str(patient.id), storage_root
        )
        patient_dir.mkdir(parents=True, exist_ok=True)
        file_path = _assert_within_storage_root(patient_dir / stored_name, storage_root)

        # SEC-008 & SEC-010: Stream in chunks, validate magic header early, enforce max size
        hasher = hashlib.sha256()
        total_bytes = 0
        header_buffer = bytearray()
        magic_checked = False
        chunk_size = min(STREAM_CHUNK_BYTES, max(max_size_bytes + 1, 1024))

        try:
            with file_path.open("wb") as out_fp:
                while True:
                    chunk = await upload_file.read(chunk_size)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > max_size_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                            detail=(
                                f"File exceeds the maximum allowed size of "
                                f"{max(1, max_size_bytes // (1024 * 1024))} MiB."
                            ),
                        )

                    if not magic_checked:
                        header_buffer.extend(chunk[:32])
                        if len(header_buffer) >= 12:
                            if not _validate_magic(bytes(header_buffer), content_type):
                                raise HTTPException(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=(
                                        "File content does not match the declared MIME type. "
                                        "Upload rejected for security reasons."
                                    ),
                                )
                            magic_checked = True

                    hasher.update(chunk)
                    out_fp.write(chunk)

            if total_bytes == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded file is empty.",
                )

            if not magic_checked and not _validate_magic(bytes(header_buffer), content_type):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "File content does not match the declared MIME type. "
                        "Upload rejected for security reasons."
                    ),
                )
        except Exception:
            if file_path.exists():
                file_path.unlink()
            raise

        sha256 = hasher.hexdigest()
        safe_original = _sanitize_filename(upload_file.filename)
        display_title = title.strip()[:255] if title.strip() else safe_original

        doc = Document(
            id=uuid.uuid4(),
            patient_id=patient.id,
            uploader_user_id=patient.user_id,
            original_filename=safe_original,
            stored_filename=stored_name,
            file_path=str(file_path),
            mime_type=content_type,
            file_size_bytes=total_bytes,
            sha256_hash=sha256,
            document_type=document_type,
            upload_status="ready",
            review_status="unreviewed",
            title=display_title,
            description=description,
            document_date=document_date,
            is_archived=False,
        )
        db.add(doc)

        # Record corresponding timeline event using HealthEvent schema
        db.add(
            HealthEvent(
                patient_id=patient.id,
                event_category="document",
                title=f"Document uploaded: {display_title}",
                summary=(
                    f"Uploaded {document_type.replace('_', ' ')} "
                    f"({content_type}, {total_bytes:,} bytes)"
                ),
                event_occurred_at=_date_to_utc_datetime(document_date),
                source_type="patient_reported",
                review_status="confirmed",
                related_entity_type="document",
                related_entity_id=doc.id,
                metadata_json={
                    "action": "uploaded",
                    "document_type": document_type,
                    "mime_type": content_type,
                    "file_size_bytes": total_bytes,
                },
            )
        )

        try:
            await db.commit()
            await db.refresh(doc)
        except Exception:
            await db.rollback()
            if file_path.exists():
                file_path.unlink()
            raise

        logger.info(
            "document_uploaded",
            document_id=str(doc.id),
            patient_id=str(patient.id),
            mime_type=content_type,
            bytes=total_bytes,
        )
        return doc

    # --- Read / list ----------------------------------------------------------

    @staticmethod
    async def get_document(
        *,
        db: AsyncSession,
        document_id: uuid.UUID,
        patient: PatientProfile,
    ) -> Document:
        """
        Fetch a document by ID and enforce strict patient ownership.
        Raises 403 Forbidden if owned by another patient (SEC-001/002),
        or 404 Not Found if nonexistent.
        """
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found.",
            )
        enforce_patient_ownership(doc.patient_id, patient)
        return doc

    @staticmethod
    async def list_documents(
        *,
        db: AsyncSession,
        patient: PatientProfile,
        document_type: str | None = None,
        review_status: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        search: str | None = None,
        include_archived: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Document], int]:
        """Return a paginated list of documents for the authenticated patient."""
        query = select(Document).where(Document.patient_id == patient.id)
        if not include_archived:
            query = query.where(Document.is_archived.is_(False))
        if document_type:
            query = query.where(Document.document_type == document_type)
        if review_status:
            query = query.where(Document.review_status == review_status)
        if start_date is not None:
            query = query.where(Document.document_date >= start_date)
        if end_date is not None:
            query = query.where(Document.document_date <= end_date)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Document.title.ilike(term),
                    Document.description.ilike(term),
                    Document.original_filename.ilike(term),
                )
            )

        count_q = select(func.count()).select_from(query.subquery())
        total: int = (await db.execute(count_q)).scalar_one()

        query = (
            query.order_by(Document.uploaded_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await db.execute(query)).scalars().all()
        return list(rows), total

    # --- Update ---------------------------------------------------------------

    @staticmethod
    async def update_document(
        *,
        db: AsyncSession,
        document_id: uuid.UUID,
        patient: PatientProfile,
        payload: DocumentUpdateRequest,
    ) -> Document:
        """Update mutable metadata fields on a document owned by the patient."""
        doc = await DocumentService.get_document(
            db=db, document_id=document_id, patient=patient
        )
        if doc.is_archived:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot update an archived document.",
            )

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(doc, field, value)

        await db.commit()
        await db.refresh(doc)
        return doc

    # --- Delete (soft-archive) ------------------------------------------------

    @staticmethod
    async def archive_document(
        *,
        db: AsyncSession,
        document_id: uuid.UUID,
        patient: PatientProfile,
    ) -> Document:
        """
        Soft-archive a document:
        1. Mark is_archived=True and upload_status='archived'.
        2. Delete the actual file from disk.
        3. Record a timeline event and preserve metadata for audit trails.
        """
        doc = await DocumentService.get_document(
            db=db, document_id=document_id, patient=patient
        )
        if doc.is_archived:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document is already archived.",
            )

        file_path = Path(doc.file_path)
        if file_path.exists():
            file_path.unlink()
            logger.info("document_file_deleted", document_id=str(doc.id))

        doc.is_archived = True
        doc.upload_status = "archived"

        db.add(
            HealthEvent(
                patient_id=patient.id,
                event_category="document",
                title=f"Document archived: {doc.title}",
                summary="Document was archived and its stored file was removed.",
                event_occurred_at=datetime.now(UTC),
                source_type="patient_reported",
                review_status="confirmed",
                related_entity_type="document",
                related_entity_id=doc.id,
                metadata_json={"action": "archived", "document_type": doc.document_type},
            )
        )

        await db.commit()
        await db.refresh(doc)
        return doc

    # --- Download helper ------------------------------------------------------

    @staticmethod
    async def resolve_download_path(
        *,
        db: AsyncSession,
        document_id: uuid.UUID,
        patient: PatientProfile,
        storage_root: Path,
    ) -> tuple[Path, str, str]:
        """
        Returns (file_path, media_type, original_filename) for a secure download.
        Raises 403 if owned by another patient, 404 if not found, 410 if archived.
        """
        doc = await DocumentService.get_document(
            db=db, document_id=document_id, patient=patient
        )
        if doc.is_archived:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This document has been archived and its file is no longer available.",
            )
        file_path = _assert_within_storage_root(Path(doc.file_path), storage_root)
        if not file_path.exists():
            logger.error(
                "document_file_missing_on_disk",
                document_id=str(document_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file is not available.",
            )
        return file_path, doc.mime_type, doc.original_filename
