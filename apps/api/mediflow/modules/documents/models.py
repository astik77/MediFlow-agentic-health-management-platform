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
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
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


class DocumentPage(Base):
    """
    Page-level extracted text and OCR telemetry for an uploaded document.
    Strictly scoped to patient_id for isolation and cascaded on document deletion.
    """

    __tablename__ = "document_pages"
    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_document_pages_doc_page"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    extraction_method: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # pymupdf_text | rapidocr | hybrid | failed
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    layout_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class DocumentChunk(Base):
    """
    Page-anchored text chunks derived from extracted document pages.
    Ready for Phase 7 pgvector embeddings and hybrid RAG retrieval.
    """

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_doc_idx"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    section_heading: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class DocumentProcessingJob(Base):
    """
    Tracks document intelligence execution, retries, and idempotency (SEC-017).
    """

    __tablename__ = "document_processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    pipeline_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="queued", nullable=False, index=True
    )  # queued | running | completed | failed
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


Index("ix_document_pages_patient_doc", DocumentPage.patient_id, DocumentPage.document_id)
Index("ix_document_chunks_patient_doc", DocumentChunk.patient_id, DocumentChunk.document_id)
Index(
    "ix_document_jobs_doc_created",
    DocumentProcessingJob.document_id,
    DocumentProcessingJob.created_at.desc(),
)


class DocumentEmbedding(Base):
    """
    Patient-scoped dense vector embedding for a single DocumentChunk (Phase 7 RAG).
    Carries explicit patient_id FK for zero-tolerance cross-patient isolation (SEC-003)
    and CASCADE deletion on chunk/document wipe (SEC-016).
    """

    __tablename__ = "document_embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", name="uq_document_embeddings_chunk_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_vector: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


Index("ix_doc_embeddings_patient_doc", DocumentEmbedding.patient_id, DocumentEmbedding.document_id)
