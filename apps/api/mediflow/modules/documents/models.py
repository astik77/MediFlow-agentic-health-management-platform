"""
Document Database Model.
Tracks uploaded medical documents with metadata, storage paths, and processing status.
Never exposes file_path to API clients — it is an internal server-side field only.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from mediflow.core.database import Base


def utc_now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(UTC)


class Document(Base):
    """
    Represents an uploaded medical document owned by a patient.

    Invariants:
    - file_path is NEVER sent to the client. It is an internal server field.
    - stored_filename is UUID-based to prevent path traversal.
    - sha256_hash enables deduplication and integrity verification.
    - Soft-archive: DELETE endpoint sets is_archived=True and removes the file from disk,
      but keeps the metadata row for audit purposes.
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploader_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # --- File Identity ---
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    # file_path is INTERNAL ONLY — never serialised to Pydantic response schemas
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)

    # --- File Properties ---
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # --- Document Classification ---
    document_type: Mapped[str] = mapped_column(
        String(50), default="other", nullable=False
    )
    # lab_report | prescription | discharge_summary | imaging | clinical_note | insurance | other

    source_type: Mapped[str] = mapped_column(
        String(32), default="patient_uploaded", nullable=False
    )
    # patient_uploaded | document_extracted | ai_proposed

    # --- Status ---
    upload_status: Mapped[str] = mapped_column(
        String(32), default="ready", nullable=False
    )
    # pending | processing | ready | failed | archived

    review_status: Mapped[str] = mapped_column(
        String(32), default="unreviewed", nullable=False
    )
    # unreviewed | reviewed | flagged

    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # --- Content Metadata ---
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )  # Clinical date on the document
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- Lifecycle ---
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


# Efficient patient-scoped chronological queries
Index("ix_documents_patient_uploaded", Document.patient_id, Document.uploaded_at.desc())
Index("ix_documents_patient_type", Document.patient_id, Document.document_type)
